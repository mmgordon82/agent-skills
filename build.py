#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["typer>=0.12", "pydantic>=2.7", "rich>=13", "tomlkit>=0.13"]
# ///
"""Build the skill set: own skills + pinned upstream skills with local patches applied."""

from __future__ import annotations

import filecmp
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Annotated, Literal, NamedTuple

import tomlkit
import typer
from pydantic import BaseModel, Field, ValidationError
from rich.console import Console
from rich.table import Table

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / ".cache"
OWN = ROOT / "skills"
PATCHES = ROOT / "patches"
UPSTREAMS = ROOT / "upstreams.toml"
DIST = ROOT / "dist"
SETTINGS = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "agent-skills" / "settings.toml"
JUNK = {".DS_Store", "__pycache__", ".git"}
# Model ids and versioned display names; harness names such as Claude Code stay intact.
MODEL_REF = re.compile(r"\b(?:claude|gemini|gpt|grok|kimi)-[a-z0-9.-]*\d(?:[a-z0-9.-]*[a-z0-9])?\b"
                       r"|\b[a-z0-9.-]+-(?:x?high|medium|low)-fast\b"
                       r"|\b(?:Claude|Opus|Sonnet|Haiku|Fable|Gemini|GPT|Grok|Kimi)[ -]?\d+(?:\.\d+)?\b")

app = typer.Typer(no_args_is_help=True, add_completion=False, help=__doc__)
console = Console()


class Upstream(BaseModel):
    name: str = ""  # table key in upstreams.toml; load() sets it. Not a field you write twice.
    repo: str = Field(pattern=r"^[\w.-]+/[\w.-]+$")
    rev: str = Field(pattern=r"^[0-9a-f]{40}$")
    license: str
    paths: dict[str, str]  # dist path -> path in the upstream repo, copied in order
    license_file: str | None = None  # copied into every skill dir, before patches
    tiered: bool = False  # retarget model-id patches; forbid vendor model ids in this upstream's skills

    @property
    def cache(self) -> Path:
        return CACHE / self.repo.replace("/", "__")

    @property
    def skills(self) -> list[str]:
        return sorted({dest.split("/")[0] for dest in self.paths})

    @property
    def patch_dir(self) -> Path:
        if not self.name:
            raise GitError(f"{self.repo} has no registry name")
        return PATCHES / self.name


def with_name(u: Upstream, name: str) -> Upstream:
    """The table key wins over a name carried on the record."""
    return u if u.name == name else u.model_copy(update={"name": name})


class Step(NamedTuple):
    source: str
    item: str
    error: str = ""  # empty when this patch or own skill copied cleanly


class GitError(RuntimeError):
    pass


def git(*args: str, cwd: Path | None = None, input: str | None = None) -> str:
    # Ceiling stops git from resolving this repo when it runs in a staging dir under .cache/.
    env = {**os.environ, "GIT_CEILING_DIRECTORIES": str(CACHE)}
    r = subprocess.run(["git", *args], cwd=cwd, env=env, input=input, capture_output=True, text=True)
    if r.returncode:
        raise GitError((r.stderr or r.stdout).strip())
    return r.stdout


def adapt_model_patch(text: str, out: Path) -> tuple[str, list[tuple[str, str]]] | None:
    """Adapt only uniquely matched preimages whose non-model text is unchanged."""
    # shortcut: quoted paths and missing final newlines use normal repair; extend if an upstream needs them.
    if "\\ No newline at end of file" in text:
        return None
    lines, changes, path, i = text.splitlines(keepends=True), [], None, 0
    mask = MODEL_REF.split
    while i < len(lines):
        if lines[i].startswith("--- "):
            path = Path(lines[i][6:].rstrip("\n")) if lines[i].startswith("--- a/") else None
            if path and (path.is_absolute() or ".." in path.parts):
                return None
        if not lines[i].startswith("@@ "):
            i += 1
            continue
        end = i + 1
        while end < len(lines) and lines[end][:1] in {" ", "+", "-"}:
            end += 1
        old = [j for j in range(i + 1, end) if lines[j][0] in " -"]
        if old:
            if path is None or not (out / path).is_file():
                return None
            try:
                source = (out / path).read_text().splitlines(keepends=True)
            except (OSError, UnicodeError):
                return None
            wanted = [mask(lines[j][1:]) for j in old]
            masked = [mask(line) for line in source]
            matches = [start for start in range(len(source) - len(old) + 1)
                       if masked[start:start + len(old)] == wanted]
            if len(matches) != 1:
                return None
            start = matches[0]
            preimage = source[start:start + len(old)]
            before_names = set(MODEL_REF.findall("".join(lines[j][1:] for j in old)))
            after_names = set(MODEL_REF.findall("".join(preimage)))
            # An older reference elsewhere can identify a reworded original target.
            elsewhere = "".join(source[:start] + source[start + len(old):])
            if (before_names - after_names) & set(MODEL_REF.findall(elsewhere)):
                return None
            for j, actual in zip(old, preimage):
                changes.extend((a, b) for a, b in zip(MODEL_REF.findall(lines[j][1:]), MODEL_REF.findall(actual)) if a != b)
                lines[j] = lines[j][0] + actual
        i = end
    return ("".join(lines), changes) if changes else None


def apply_patch(patch: Path, out: Path, *, tiered: bool = False) -> None:
    try:
        git("apply", "--whitespace=nowarn", str(patch), cwd=out)
    except GitError as original:
        adapted = adapt_model_patch(patch.read_text(), out) if tiered else None
        if adapted is None:
            raise
        text, changes = adapted
        try:
            git("apply", "--whitespace=nowarn", "-", cwd=out, input=text)
        except GitError:
            raise original from None
        for old, new in dict.fromkeys(changes):
            console.print(f"{patch.name}: model reference {old} → {new} (tier policy unchanged)")


def load() -> dict[str, Upstream]:
    data = tomlkit.parse(UPSTREAMS.read_text()).unwrap()
    try:
        ups = {name: with_name(Upstream.model_validate(u), name) for name, u in data.items()}
    except ValidationError as e:
        console.print(f"[red]{UPSTREAMS.name} is invalid:[/]\n{e}")
        raise typer.Exit(1)
    seen: dict[str, str] = {}
    for name, u in ups.items():
        for s in u.skills:
            if s in seen or (OWN / s).exists():
                console.print(f"[red]skill '{s}' defined twice ({seen.get(s, 'skills/')} and {name})[/]")
                raise typer.Exit(1)
            seen[s] = name
    return ups


def checkout(u: Upstream) -> Path:
    if not u.cache.exists():
        CACHE.mkdir(exist_ok=True)
        git("clone", "-q", "--filter=blob:none", f"https://github.com/{u.repo}", str(u.cache))
    try:
        git("cat-file", "-e", f"{u.rev}^{{commit}}", cwd=u.cache)
    except GitError:
        git("fetch", "-q", "origin", cwd=u.cache)
    git("checkout", "-q", "--force", "--detach", u.rev, cwd=u.cache)
    return u.cache


def remote_head(u: Upstream, rev: str | None = None) -> str:
    """Full sha of `rev` (default: the upstream's remote HEAD), fetched into the cache."""
    new = rev or git("ls-remote", f"https://github.com/{u.repo}", "HEAD").split()[0]
    git("fetch", "-q", "origin", cwd=checkout(u))
    return git("rev-parse", f"{new}^{{commit}}", cwd=u.cache).strip()


def copy(src: Path, dest: Path) -> None:
    if src.is_dir():
        shutil.copytree(src, dest, dirs_exist_ok=True, ignore=shutil.ignore_patterns(*JUNK))
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def copy_upstream(u: Upstream, out: Path) -> None:
    src = checkout(u)
    for dest, path in u.paths.items():
        if not (src / path).exists():
            raise GitError(f"{u.repo}@{u.rev[:7]} has no '{path}'")
        # A symlink would copy whatever it points at on this machine (CI env, keys) into the build.
        if links := [p for p in [src / path, *(src / path).rglob("*")] if p.is_symlink()]:
            raise GitError(f"{u.repo}@{u.rev[:7]} has a symlink at '{links[0].relative_to(src)}'; refusing to copy")
        copy(src / path, out / dest)
    if u.license_file:
        for skill in u.skills:
            shutil.copy2(src / u.license_file, out / skill / "LICENSE")
    for skill in u.skills:
        codex_typed_only(out / skill)


def codex_typed_only(skill: Path) -> None:
    """Codex ignores `disable-model-invocation`; it needs this policy file to keep a skill typed-only."""
    policy = skill / "agents" / "openai.yaml"
    if policy.exists() or not re.search(r"^disable-model-invocation:\s*true\s*$", (skill / "SKILL.md").read_text(), re.M):
        return
    policy.parent.mkdir(exist_ok=True)
    policy.write_text("policy:\n  allow_implicit_invocation: false\n")


def build_into(out: Path, ups: dict[str, Upstream]) -> list[Step]:
    """Copy each upstream, apply its patches, then copy skills/. One row per patch and own skill."""
    rows = []
    for name, upstream in ups.items():
        u = with_name(upstream, name)
        copy_upstream(u, out)
        for patch in sorted(u.patch_dir.glob("*.patch")):
            try:
                apply_patch(patch, out, tiered=u.tiered)
                rows.append(Step(name, patch.name))
            except GitError as e:
                rows.append(Step(name, patch.name, str(e)))
    for skill in sorted(p for p in OWN.iterdir() if p.is_dir()):
        copy(skill, out / skill.name)
        rows.append(Step("skills/", skill.name))
    return rows


def show(rows: list[Step]) -> bool:
    t = Table("source", "item", "result", box=None)
    for row in rows:
        t.add_row(row.source, row.item, f"[red]{row.error}[/]" if row.error else "[green]ok[/]")
    console.print(t)
    return not any(row.error for row in rows)


def files(d: Path) -> set[str]:
    return {str(p.relative_to(d)) for p in d.rglob("*") if p.is_file() and not JUNK & set(p.parts)}


def staging() -> Path:
    CACHE.mkdir(exist_ok=True)
    return Path(tempfile.mkdtemp(dir=CACHE, prefix="build-"))


@app.command()
def build() -> None:
    """Build dist/ from upstreams.toml, patches/ and skills/. dist/ is replaced only on success."""
    out = staging()
    if not show(build_into(out, load())):
        shutil.rmtree(out)
        console.print("[red]build failed; dist/ unchanged[/]")
        raise typer.Exit(1)
    old = DIST.with_name("dist.old")
    if DIST.exists():
        DIST.rename(old)
    out.rename(DIST)
    shutil.rmtree(old, ignore_errors=True)
    console.print(f"[green]built {len(list(DIST.iterdir()))} skills into dist/[/]")


@app.command()
def verify(against: Annotated[Path, typer.Option(help="Installed skills dir to compare with")] = Path("~/.agents/skills")) -> None:
    """Build to a temp dir and diff every skill against an installed copy."""
    against = against.expanduser()
    out = staging()
    try:
        if not show(build_into(out, load())):
            raise typer.Exit(1)
        t = Table("skill", "vs " + str(against), box=None)
        bad = 0
        for skill in sorted(p.name for p in out.iterdir()):
            a, b = out / skill, against / skill
            if not b.exists():
                t.add_row(skill, "[yellow]not installed[/]")
                bad += 1
                continue
            fa, fb = files(a), files(b)
            changed = sorted(f for f in fa & fb if not filecmp.cmp(a / f, b / f, shallow=False))
            diffs = [f"+{f}" for f in sorted(fb - fa)] + [f"-{f}" for f in sorted(fa - fb)] + [f"~{f}" for f in changed]
            bad += bool(diffs)
            t.add_row(skill, "[green]identical[/]" if not diffs else f"[red]{', '.join(diffs[:6])}{' …' if len(diffs) > 6 else ''}[/]")
        console.print(t)
        if bad:
            raise typer.Exit(1)
    finally:
        shutil.rmtree(out, ignore_errors=True)


@app.command()
def diff(
    upstream: str,
    source: Annotated[Path, typer.Option("--from", help="Dir holding your edited skills")] = DIST,
) -> None:
    """Regenerate patches/<upstream>/<skill>.patch from edited skills (default: dist/). Keeps each patch's header."""
    ups = load()
    if upstream not in ups:
        console.print(f"[red]unknown upstream '{upstream}'; have: {', '.join(ups)}[/]")
        raise typer.Exit(1)
    write_patches(with_name(ups[upstream], upstream), source.expanduser())


def write_patches(u: Upstream, source: Path) -> None:
    """Rewrite patches/<upstream>/<skill>.patch from the skills in `source`, keeping each patch's header."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        copy_upstream(u, repo)
        g = lambda *a: git("-c", "user.name=build", "-c", "user.email=build@localhost", "-c", "commit.gpgsign=false", *a, cwd=repo)
        g("init", "-q")
        g("add", "-A")
        g("commit", "-q", "-m", "base")
        for skill in u.skills:
            shutil.rmtree(repo / skill)
            copy(source / skill, repo / skill)
        g("add", "-A")
        for skill in u.skills:
            text = g("diff", "--cached", "--binary", "--full-index", "--", skill)
            path = u.patch_dir / f"{skill}.patch"
            header = path.read_text().split("diff --git", 1)[0] if path.exists() else ""
            if text:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(header + text)
                console.print(f"wrote {path.relative_to(ROOT)}")
            elif path.exists():
                path.unlink()
                console.print(f"removed {path.relative_to(ROOT)} (no changes left)")


@app.command()
def bump(
    names: Annotated[list[str] | None, typer.Argument(help="Upstreams to bump; default: all")] = None,
    rev: Annotated[str | None, typer.Option(help="Commit sha for a single upstream; default: remote HEAD")] = None,
) -> None:
    """Move pins to upstream HEAD (or --rev). A pin moves only if all its patches still apply; exits 1 if any was held back."""
    ups = load()
    names = names or list(ups)
    if unknown := set(names) - set(ups):
        console.print(f"[red]unknown upstream {', '.join(unknown)}; have: {', '.join(ups)}[/]")
        raise typer.Exit(1)
    if rev and len(names) != 1:
        console.print("[red]--rev needs exactly one upstream[/]")
        raise typer.Exit(1)
    doc = tomlkit.parse(UPSTREAMS.read_text())
    held = []
    for name in names:
        u = ups[name]
        new = remote_head(u, rev)
        if new == u.rev:
            console.print(f"{name}: up to date @{new[:7]}")
            continue
        log = git("log", "--oneline", f"{u.rev}..{new}", "--", *u.paths.values(), cwd=u.cache)
        console.print(f"{name}: {u.rev[:7]} → {new[:7]}, {len(log.splitlines())} commits touch our paths\n{log}")
        out = staging()
        try:
            ok = show(build_into(out, {name: u.model_copy(update={"rev": new})}))
        except GitError as e:  # e.g. upstream moved a mapped folder
            console.print(f"[red]{name}: {e}[/]")
            ok = False
        finally:
            shutil.rmtree(out, ignore_errors=True)
        if ok:
            doc[name]["rev"] = new
        else:
            held.append(name)
    UPSTREAMS.write_text(tomlkit.dumps(doc))
    if held:
        console.print(f"[red]held back {', '.join(held)}: patches don't apply at the new commit. Rebuild them from their "
                      f"Why: set the new rev in upstreams.toml, run `build.py workspace <upstream> <dir>`, fix, "
                      f"then `build.py diff <upstream> --from <dir>`.[/]")
        raise typer.Exit(1)
    console.print("[green]pins updated; run build[/]")


class PatchResult(BaseModel):
    patch: str
    status: Literal["applies", "merged", "conflict"]
    conflicts: list[str] = []  # files with conflict markers, relative to the workspace
    error: str = ""  # failures for which git could not produce conflict markers


def make_workspace(u: Upstream, into: Path) -> list[PatchResult]:
    """Lay out `u` at its pin in `into` as a git repo (first commit: plain upstream), then apply each patch,
    3-way where it doesn't apply cleanly, leaving conflict markers in the files it can't merge."""
    copy_upstream(u, into)
    g = lambda *a: git("-c", "user.name=build", "-c", "user.email=build@localhost", "-c", "commit.gpgsign=false", *a, cwd=into)
    g("init", "-q")
    (into / ".git" / "objects" / "info" / "alternates").write_text(str(u.cache.resolve() / ".git" / "objects") + "\n")
    g("add", "-A")
    g("commit", "-q", "-m", f"{u.repo} @ {u.rev[:7]} (upstream)")
    results = []
    for patch in sorted(u.patch_dir.glob("*.patch")):
        try:
            apply_patch(patch, into, tiered=u.tiered)
            results.append(PatchResult(patch=patch.name, status="applies"))
        except GitError:
            try:
                # Model-only bumps can leave a patch's base older than the pin in a partial clone.
                for base in dict.fromkeys(re.findall(r"^index ([0-9a-f]{40})\.\.", patch.read_text(), re.M)):
                    if base != "0" * 40:
                        try:
                            g("cat-file", "-e", base)
                        except GitError:
                            try:
                                git("cat-file", "-e", base, cwd=u.cache)
                            except GitError as e:
                                raise GitError(f"cannot load patch base {base}: {e or 'object unavailable'}") from None
                g("apply", "--3way", "--whitespace=nowarn", str(patch))
                results.append(PatchResult(patch=patch.name, status="merged"))
            except GitError as e:
                marked = [l[2:] for l in str(e).splitlines() if l.startswith("U ")]
                results.append(PatchResult(patch=patch.name, status="conflict", conflicts=marked, error="" if marked else str(e)))
    return results


@app.command()
def workspace(
    upstream: str,
    into: Annotated[Path, typer.Argument(help="New directory to create")],
) -> None:
    """Start rebuilding broken patches: lay out UPSTREAM at its pin in INTO (a git repo whose first commit
    is plain upstream), apply its patches, 3-way where they conflict, and list what needs rewriting."""
    ups = load()
    if upstream not in ups:
        console.print(f"[red]unknown upstream '{upstream}'; have: {', '.join(ups)}[/]")
        raise typer.Exit(1)
    into = into.expanduser()
    if into.exists():
        console.print(f"[red]{into} exists; pick a new directory[/]")
        raise typer.Exit(1)
    t = Table("patch", "result", box=None)
    for r in make_workspace(with_name(ups[upstream], upstream), into):
        if r.status == "applies":
            t.add_row(r.patch, "[green]applies[/]")
        elif r.status == "merged":
            t.add_row(r.patch, "[green]merged (3-way); check it still matches the Why[/]")
        else:
            detail = "conflicts marked in " + ", ".join(r.conflicts) if r.conflicts else r.error
            t.add_row(r.patch, f"[red]rewrite from its Why[/]{': ' + detail if detail else ''}")
    console.print(t)
    console.print(f"Next: edit {into} until each patch's Why holds again, then\n"
                  f"  uv run build.py diff {upstream} --from {into}   # rewrites patches/{upstream}/, keeps each header\n"
                  f"  uv run build.py build && uv run tests/run.py\n"
                  f"Update a Why when its reasoning changed; `git -C {into} diff HEAD` shows your edits against upstream.")


@app.command()
def install(
    target: Annotated[Path, typer.Option(help="Skills dir to point at dist/")] = Path("~/.agents/skills"),
    force: Annotated[bool, typer.Option(help="Replace existing skills with the same name")] = False,
) -> None:
    """Maintainer tool: point every TARGET/<skill> at dist/<skill>, so each rebuild is live in every agent
    that links to TARGET. Agents get their links from npx skills (see README). Creates the settings file if missing."""
    if not DIST.exists():
        console.print("[red]no dist/; run build first[/]")
        raise typer.Exit(1)
    target = target.expanduser()
    target.mkdir(parents=True, exist_ok=True)
    skipped = 0
    for skill in sorted(p.name for p in DIST.iterdir()):
        link, want = target / skill, Path(os.path.relpath(DIST / skill, target))
        if link.is_symlink() and Path(os.readlink(link)) == want:
            continue
        if link.exists() or link.is_symlink():
            if not force:
                console.print(f"[yellow]skip {link}: exists (use --force to replace)[/]")
                skipped += 1
                continue
            shutil.rmtree(link) if link.is_dir() and not link.is_symlink() else link.unlink()
        link.symlink_to(want)
    console.print(f"[green]linked {target} to dist/[/]" + (f", {skipped} skipped" if skipped else ""))
    if SETTINGS.exists():
        console.print(f"settings: {SETTINGS} (kept)")
    else:
        SETTINGS.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "settings.example.toml", SETTINGS)
        console.print(f"settings: created {SETTINGS} from settings.example.toml; edit it to customize")

if __name__ == "__main__":
    app()
