#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["typer>=0.12", "pydantic>=2.7", "rich>=13", "tomlkit>=0.13", "pyyaml>=6", "openai>=2"]
# ///
"""Rebuild patches that a moved upstream broke, from their Why headers, and open a PR with the result.

For each upstream whose patches no longer apply at its remote HEAD: lay out a workspace at the new commit,
ask the model to resolve each conflicted file by the patch's header, regenerate the patches, rebuild, and run
ci/intent_checks.py plus two fixer-only checks (added lines survive; typed-only state holds). One retry
with the failures fed back. Then push `auto-fix/<upstream>-<sha>` and open a PR (a draft if checks still
fail). Nothing is released here; merging the PR runs the release workflow.

Needs a clean working tree, OPENAI_API_KEY, and (unless --dry-run) gh and push rights.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Annotated

import tomlkit
import typer
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build  # noqa: E402
from ci import intent_checks  # noqa: E402

MODEL = "gpt-6.1-terra"
ATTEMPTS = 2
MARKERS = ("<<<<<<< ", "=======", ">>>>>>> ")

SYSTEM = """You rebuild a patch that no longer applies after its upstream moved.

The patch exists for the reasons in its header (Why, Problem, Change, Keep when rebasing, Reapply). Each
file you get contains git conflict markers: "ours" is the new upstream text, "theirs" is the patched text
from before. You also get upstream's own diff for that file between the old and the new commit.

Return the full new content of every file you were given, with every conflict resolved so that:
- what upstream changed or added is kept, unless the header says the patch replaces it;
- the patch's intent from its header still holds, restated in the new upstream text where needed;
- nothing else changes: no new frontmatter keys, no new files, no reformatting, no comments about the merge.

If a line the patch added is no longer needed (upstream now does the same, or removed what it changed),
leave it out and list it in `dropped` with a one-sentence reason. Every other added line must survive.
`summary` says in two or three sentences what you changed and why, for the reviewer of the pull request."""

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["files", "dropped", "summary"],
    "properties": {
        "files": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["path", "content"],
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}}}},
        "dropped": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["line", "reason"],
            "properties": {"line": {"type": "string"}, "reason": {"type": "string"}}}},
        "summary": {"type": "string"},
    },
}


class FileOut(BaseModel):
    path: str
    content: str


class Dropped(BaseModel):
    line: str
    reason: str


class Rewrite(BaseModel):
    files: list[FileOut]
    dropped: list[Dropped]
    summary: str


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class FixError(RuntimeError):
    pass


Ask = Callable[[str], tuple[Rewrite, Usage]]


def ask_model(prompt: str) -> tuple[Rewrite, Usage]:
    from openai import OpenAI

    resp = OpenAI().responses.create(
        model=MODEL, instructions=SYSTEM, input=prompt, reasoning={"effort": "high"},
        text={"format": {"type": "json_schema", "name": "patch_rewrite", "schema": SCHEMA, "strict": True}},
    )
    usage = Usage(input_tokens=resp.usage.input_tokens, output_tokens=resp.usage.output_tokens)
    return Rewrite.model_validate_json(resp.output_text), usage


def sh(*args: str, cwd: Path = ROOT) -> str:
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        raise FixError(f"{' '.join(args)}: {(r.stderr or r.stdout).strip()}")
    return r.stdout


def header(patch: Path) -> str:
    return patch.read_text().split("diff --git", 1)[0].strip()


def upstream_path(u: build.Upstream, rel: str) -> str:
    """dist-relative path (arena/SKILL.md) → path in the upstream repo (skills/arena/SKILL.md)."""
    dest = max((d for d in u.paths if rel == d or rel.startswith(d + "/")), key=len)
    return u.paths[dest] + rel[len(dest):]


def broken(ups: dict[str, build.Upstream]) -> dict[str, str]:
    """Upstreams whose patches don't apply at remote HEAD → that HEAD."""
    out = {}
    for name, u in ups.items():
        new = build.remote_head(u)
        if new == u.rev:
            continue
        out_dir = build.staging()
        try:
            rows = build.build_into(out_dir, {name: u.model_copy(update={"rev": new})})
            if any(err for *_, err in rows):
                out[name] = new
        except build.GitError as e:
            raise FixError(f"{name}: can't lay out {u.repo}@{new[:7]} ({e}); fix upstreams.toml by hand") from None
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)
    return out


def prompt(u_old: build.Upstream, u_new: build.Upstream, patch: Path, files: dict[str, str], feedback: list[str]) -> str:
    parts = [f"Patch {patch.parent.name}/{patch.name}. Its header:\n\n{header(patch)}\n"]
    for rel, text in files.items():
        diff = build.git("diff", u_old.rev, u_new.rev, "--", upstream_path(u_new, rel), cwd=u_new.cache)
        parts.append(f"=== FILE {rel} (with conflict markers)\n{text}\n=== UPSTREAM DIFF {u_old.rev[:7]}..{u_new.rev[:7]} for {rel}\n{diff or '(none)'}")
    if feedback:
        parts.append("Your previous attempt failed these checks; fix them:\n" + "\n".join(f"- {f}" for f in feedback))
    return "\n\n".join(parts)


def resolve(name: str, u_old: build.Upstream, new: str, ws: Path, ask: Ask, feedback: list[str]) -> tuple[list[tuple[str, Rewrite]], Usage]:
    """Workspace at `new`, model-resolved conflicts written back, patches regenerated. Returns each rewrite."""
    u_new = u_old.model_copy(update={"rev": new})
    rewrites, usage = [], Usage()
    for r in build.make_workspace(u_new, name, ws):
        if r.status != "conflict":
            continue
        if not r.conflicts:
            raise FixError(f"{r.patch}: doesn't apply and git marked no conflicts (a file it patches is gone?); rebuild it by hand")
        patch = build.PATCHES / name / r.patch
        files = {rel: (ws / rel).read_text() for rel in r.conflicts}
        rw, u = ask(prompt(u_old, u_new, patch, files, feedback))
        usage.input_tokens += u.input_tokens
        usage.output_tokens += u.output_tokens
        got = {f.path for f in rw.files}
        if got != set(files):
            raise FixError(f"{r.patch}: model returned {sorted(got)}, expected exactly {sorted(files)}; refusing to write")
        for f in rw.files:
            if any(line.startswith(MARKERS) for line in f.content.splitlines()):
                raise FixError(f"{r.patch}: model left conflict markers in {f.path}")
            (ws / f.path).write_text(f.content)
        rewrites.append((r.patch, rw))
    build.write_patches(name, u_new, ws)
    return rewrites, usage


def set_revs(revs: dict[str, str]) -> None:
    doc = tomlkit.parse(build.UPSTREAMS.read_text())
    for name, rev in revs.items():
        doc[name]["rev"] = rev
    build.UPSTREAMS.write_text(tomlkit.dumps(doc))


def attempt(targets: dict[str, str], old: dict[str, build.Upstream], old_patches: dict[str, str], old_dist: Path,
            ask: Ask, feedback: list[str], tmp: Path) -> tuple[dict, list[str], Usage]:
    sh("git", "checkout", "HEAD", "--", "upstreams.toml", "patches")
    set_revs(targets)
    rewrites, usage = {}, Usage()
    for name, new in targets.items():
        ws = Path(tempfile.mkdtemp(dir=tmp, prefix=f"{name}-"))
        rewrites[name], u = resolve(name, old[name], new, ws, ask, feedback)
        usage.input_tokens += u.input_tokens
        usage.output_tokens += u.output_tokens
    ups = build.load()
    new_dist = Path(tempfile.mkdtemp(dir=tmp, prefix="dist-"))
    shutil.rmtree(new_dist)
    new_dist.mkdir()
    rows = build.build_into(new_dist, ups)
    problems = [f"{src}/{item}: still doesn't apply: {err}" for src, item, err in rows if err]
    if not problems:
        dropped = {f"{name}/{patch}": {d.line.strip() for d in rw.dropped} for name, rws in rewrites.items() for patch, rw in rws}
        skills = [s for name in targets for s in ups[name].skills]
        problems = (intent_checks.run_all(new_dist, ups)
                    + intent_checks.check_added_lines(old_patches, new_dist, dropped)
                    + intent_checks.check_typed_state(old_dist, new_dist, skills))
    return rewrites, problems, usage


def pr_body(targets: dict[str, str], old: dict[str, build.Upstream], rewrites: dict, problems: list[str], usage: Usage) -> str:
    out = ["Upstream moved and some patches stopped applying. This PR rebuilds them from their `Why:` headers "
           f"with `{MODEL}`, then checks the result. **Review the patch diffs**: merging releases them.", ""]
    for name, new in targets.items():
        u = old[name]
        log = build.git("log", "--oneline", f"{u.rev}..{new}", "--", *u.paths.values(), cwd=u.cache).strip()
        out += [f"## {name}: `{u.rev[:7]}` → `{new[:7]}`", "", "Upstream commits touching our paths:", "",
                "```", log or "(none)", "```", ""]
        for patch, rw in rewrites.get(name, []):
            out += [f"### {patch}", "", rw.summary, ""]
            if rw.dropped:
                out += ["Dropped lines:", ""] + [f"- `{d.line.strip()}`: {d.reason}" for d in rw.dropped] + [""]
    out += ["## Checks", ""]
    out += [f"- {p}" for p in problems] if problems else ["All passed: build, intent checks (`ci/intent_checks.py`), "
                                                          "added lines kept or listed as dropped, typed-only state unchanged."]
    out += ["", f"Tokens: {usage.input_tokens} in, {usage.output_tokens} out."]
    return "\n".join(out)


def publish(targets: dict[str, str], body: str, draft: bool, dry_run: bool) -> None:
    branch = "auto-fix/" + "-".join(f"{name}-{rev[:7]}" for name, rev in targets.items())
    title = "Rebuild patches for " + ", ".join(f"{name}@{rev[:7]}" for name, rev in targets.items())
    sh("git", "checkout", "-B", branch)
    sh("git", "add", "upstreams.toml", "patches")
    sh("git", "commit", "-q", "-m", title, "-m", "Rebuilt by ci/fix_patches.py from each patch's Why header.")
    if dry_run:
        print(f"--dry-run: committed on local branch {branch}; not pushed.\n\n{body}")
        return
    sh("git", "push", "-q", "--force", "origin", branch)
    body_file = Path(tempfile.mkstemp(suffix=".md")[1])
    body_file.write_text(body)
    number = sh("gh", "pr", "list", "--head", branch, "--state", "open", "--json", "number", "-q", ".[0].number").strip()
    if number:
        sh("gh", "pr", "edit", number, "--title", title, "--body-file", str(body_file))
        sh("gh", "pr", "ready", number, *(["--undo"] if draft else []))
        print(f"updated PR #{number} ({'draft' if draft else 'ready for review'})")
    else:
        print(sh("gh", "pr", "create", "--base", "main", "--head", branch, "--title", title,
                 "--body-file", str(body_file), *(["--draft"] if draft else [])).strip())


def run(ask: Ask = ask_model, dry_run: bool = False) -> int:
    if sh("git", "status", "--porcelain").strip():
        raise FixError("working tree isn't clean; commit or stash first (in CI, restore upstreams.toml after bump)")
    old = build.load()
    targets = broken(old)
    if not targets:
        print("every pin's patches apply at upstream HEAD; nothing to fix")
        return 0
    old_patches = {f"{n}/{p.name}": p.read_text() for n in targets for p in sorted((build.PATCHES / n).glob("*.patch"))}
    with tempfile.TemporaryDirectory(dir=build.CACHE) as t:
        tmp = Path(t)
        old_dist = tmp / "old-dist"
        old_dist.mkdir()
        build.build_into(old_dist, old)
        feedback, total = [], Usage()
        for n in range(ATTEMPTS):
            try:
                rewrites, problems, usage = attempt(targets, old, old_patches, old_dist, ask, feedback, tmp)
            except FixError as e:  # a malformed answer; retry with the reason, then give up
                if n == ATTEMPTS - 1:
                    raise
                feedback = [str(e)]
                continue
            total.input_tokens += usage.input_tokens
            total.output_tokens += usage.output_tokens
            if not problems:
                break
            feedback = problems
    publish(targets, pr_body(targets, old, rewrites, problems, total), draft=bool(problems), dry_run=dry_run)
    return 0


def main(dry_run: Annotated[bool, typer.Option(help="Commit on a local branch; don't push or open a PR")] = False) -> None:
    try:
        raise typer.Exit(run(dry_run=dry_run))
    except (FixError, build.GitError) as e:
        print(f"::error::{e}" if not dry_run else f"error: {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    typer.run(main)
