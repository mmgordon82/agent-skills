#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["typer>=0.12", "openai>=2"]
# ///
"""Release dist/ if it differs from the `release` branch: one commit per release on that branch
(installable with `npx skills add <repo>#release`), a date tag on it, an OpenAI-written changelog,
and .tar.gz + .zip of the skill dirs. Run after `build.py bump` and `build.py build`."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

import typer
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
CACHE = ROOT / ".cache"
BRANCH = "release"
MODEL = "gpt-6.1-terra"
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"  # git's empty tree; the base for the first release
EVIDENCE_LIMIT = 150_000  # chars of diff sent to the model; the file list is always complete
FILE_DIFF_LINES = 120

sys.path.insert(0, str(ROOT / "skills" / "skill-critique" / "scripts"))
from agents import load_agents  # noqa: E402

AGENT_LABELS = ", ".join(a.label for a in load_agents(user=False) if a.verified)

SYSTEM = f"""You write release notes for agent-skills: a set of agent skills (folders with a SKILL.md)
shared by coding agents such as {AGENT_LABELS}. Some skills are the author's own; others are
pinned upstream skills with small local patches. Readers drop the skills into their skills directory.
They care how agent behavior changes, not which files moved.

Rules:
1. Describe what an agent using the skill now does differently, or what the user can now do.
   No internal file names unless the user calls them directly (a script, a reference doc).
2. Merge related changes into one bullet. Never one bullet per file or per commit.
3. Drop noise: license text, whitespace, formatting, upstream CI, docs that don't ship in a skill.
4. Keep concrete numbers and limits from the evidence.
5. Don't invent anything the evidence doesn't show. If the impact is unclear, write one cautious,
   accurate line or leave it out.
6. Removed or renamed skills, and skills that became typed-only (/name), are breaking: say what to do.

Output Markdown only, no title, no commentary. Omit empty sections:

## New skills
- **skill-name:** what it does, when it triggers.
## Changes
- **skill-name:** what changed, and why it matters when that isn't obvious.
## Breaking
- **skill-name:** what changed and what the user should do.
## Upstream
- **upstream-name** `old` → `new`: the user-visible effect of the upstream commits.

1–2 sentences per bullet. Order by importance to the reader."""


def run(*args: str, cwd: Path = ROOT, env: dict | None = None) -> str:
    r = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"{' '.join(args)}: {(r.stderr or r.stdout).strip()}")
    return r.stdout.strip()


def branch_tip() -> str | None:
    """Tip of origin/release (the parent of the next release commit); None if the branch doesn't exist yet."""
    r = subprocess.run(["git", "fetch", "--quiet", "origin", f"+refs/heads/{BRANCH}:refs/remotes/origin/{BRANCH}"],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode and "couldn't find remote ref" in r.stderr:
        return None
    if r.returncode:  # a network or auth error must not look like "first release"
        raise SystemExit(f"git fetch {BRANCH}: {r.stderr.strip()}")
    return run("git", "rev-parse", f"origin/{BRANCH}")


def published() -> str | None:
    """Commit of the latest published GitHub release; the base for comparing and for the changelog."""
    r = subprocess.run(["gh", "release", "view", "--json", "tagName", "-q", ".tagName"], cwd=ROOT, capture_output=True, text=True)
    if r.returncode and "release not found" in r.stderr:
        return None
    if r.returncode:
        raise SystemExit(f"gh release view: {r.stderr.strip()}")
    return run("git", "rev-parse", f"{r.stdout.strip()}^{{commit}}")


def tree_of(d: Path, index: Path) -> str:
    """Write d's contents as a git tree object (modes and symlinks included) without touching any checkout."""
    env = {**os.environ, "GIT_INDEX_FILE": str(index), "GIT_DIR": str(ROOT / ".git"), "GIT_WORK_TREE": str(d)}
    run("git", "add", "--all", "--force", ".", cwd=d, env=env)
    return run("git", "write-tree", cwd=d, env=env)


def next_version() -> str:
    base = datetime.now(timezone.utc).strftime("%Y%m%d")
    tags = set(run("git", "tag", "--list", f"{base}*").split())
    version, n = base, 1
    while version in tags:
        n += 1
        version = f"{base}.{n}"
    return version


def evidence(base: str, tree: str, prev_source: str | None) -> str:
    top = lambda rev: set(run("git", "ls-tree", "--name-only", rev).split())
    new_skills, gone = sorted(top(tree) - top(base)), sorted(top(base) - top(tree))
    status = run("git", "diff", "--name-status", base, tree)
    out = [f"# Evidence: {'previous release' if base != EMPTY_TREE else 'first release'} → this release",
           f"New skills: {', '.join(new_skills) or 'none'}", f"Removed skills: {', '.join(gone) or 'none'}",
           "Changed files (git diff --name-status):", status, ""]
    for s in new_skills:
        out.append(f"## New skill {s}: SKILL.md\n{(DIST / s / 'SKILL.md').read_text(errors='replace')[:4000]}")

    if prev_source:
        old_pins = tomllib.loads(run("git", "show", f"{prev_source}:upstreams.toml"))
        for name, u in tomllib.loads((ROOT / "upstreams.toml").read_text()).items():
            old = old_pins.get(name, {}).get("rev")
            if old and old != u["rev"]:
                log = run("git", "log", "--format=%h %s%n%b", f"{old}..{u['rev']}", "--", *u["paths"].values(),
                          cwd=CACHE / u["repo"].replace("/", "__"))
                out.append(f"## Upstream {name} ({u['repo']}) {old[:7]} → {u['rev'][:7]}\n{log or '(no commits touch shipped paths)'}")
        log = run("git", "log", "--format=%h %s%n%b", f"{prev_source}..HEAD", "--", "skills", "patches", "upstreams.toml")
        out.append(f"## Commits in this repo since the previous release\n{log or '(none)'}")

    out.append("## Diffs of modified files")
    size = sum(map(len, out))
    for line in status.splitlines():
        kind, _, path = line.partition("\t")
        if path.split("/")[0] in new_skills or path.split("/")[0] in gone:
            continue  # whole skill added or removed: covered above
        d = run("git", "diff", base, tree, "--", path).splitlines()
        more = len(d) - FILE_DIFF_LINES
        block = "\n".join(d[:FILE_DIFF_LINES]) + (f"\n… {more} more diff lines" if more > 0 else "")
        if size + len(block) > EVIDENCE_LIMIT:
            out.append(f"{path}: diff omitted (evidence size limit)")
            continue
        out.append(block)
        size += len(block)
    return "\n".join(out)


def changelog(text: str) -> str:
    resp = OpenAI().responses.create(model=MODEL, instructions=SYSTEM, input=text)
    return resp.output_text.strip()


def main(dry_run: Annotated[bool, typer.Option(help="Write notes and archives to a temp dir; don't push or release")] = False) -> None:
    if not DIST.is_dir():
        raise SystemExit("no dist/; run `uv run build.py build` first")
    run("git", "fetch", "--tags", "--quiet")
    tip, prev = branch_tip(), published()
    work = Path(tempfile.mkdtemp(prefix="release-"))
    tree = tree_of(DIST, work / "index")
    if prev and tree == run("git", "rev-parse", f"{prev}^{{tree}}"):
        if tip and tree != run("git", "rev-parse", f"{tip}^{{tree}}") and not dry_run:
            # A failed publish left unpublished content on the branch; point it back at the release.
            fix = run("git", "commit-tree", tree, "-p", tip, "-m", f"Restore last release ({prev[:7]})")
            run("git", "push", "origin", f"{fix}:refs/heads/{BRANCH}")
            print(f"{BRANCH} restored to the last release's content")
        print(f"dist/ is identical to the last release ({prev[:7]}); nothing to release")
        return

    version = next_version()
    prev_source = run("git", "log", "-1", "--format=%(trailers:key=Source,valueonly)", prev) if prev else None
    notes = work / "notes.md"
    notes_failed = False
    try:
        summary = changelog(evidence(prev or EMPTY_TREE, tree, prev_source))
    except Exception as e:
        notes_failed = True
        summary = "## Changes\n- Updated the agent skill set. Automated changelog generation failed; see the release diff for details."
        typer.echo(f"changelog generation failed: {e}; publishing with fallback notes", err=True)
    notes.write_text(summary + (
        f"\n\n---\nInstall: `npx skills add mmgordon82/agent-skills#{version} -g --skill '*'` (Node.js 22.20+), "
        f"or extract `agent-skills-{version}.tar.gz` into your skills directory "
        f"(`tar xzf agent-skills-{version}.tar.gz -C ~/.agents/skills`). Skills with the same name are replaced.\n"))
    archives = [shutil.make_archive(str(work / f"agent-skills-{version}"), fmt, root_dir=DIST) for fmt in ("gztar", "zip")]
    print(f"release {version} (previous: {prev[:7] if prev else 'none'})\nnotes: {notes}\n" + "\n".join(archives))
    if dry_run:
        print(notes.read_text())
        if notes_failed:
            raise SystemExit("dry run used fallback release notes")
        return

    if run("git", "status", "--porcelain", "upstreams.toml"):
        run("git", "commit", "-m", f"Bump upstream pins for release {version}", "upstreams.toml")
        run("git", "push")
    if tip and tree == run("git", "rev-parse", f"{tip}^{{tree}}"):
        commit = tip  # pushed by a run whose `gh release create` failed; release it now
    else:
        msg = f"Release {version}\n\nSource: {run('git', 'rev-parse', 'HEAD')}"
        commit = run("git", "commit-tree", tree, *(["-p", tip] if tip else []), "-m", msg)
        run("git", "push", "origin", f"{commit}:refs/heads/{BRANCH}")
    run("gh", "release", "create", version, "--target", commit, "--title", version,
        "--notes-file", str(notes), *archives)
    print(f"released {version}: {BRANCH} @ {commit[:7]}")
    if notes_failed:
        raise SystemExit("release published with fallback notes; changelog generation failed")


if __name__ == "__main__":
    typer.run(main)
