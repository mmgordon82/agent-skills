#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["typer>=0.12", "pydantic>=2.7", "rich>=13", "tomlkit>=0.13"]
# ///
"""Build the skill set: own skills + pinned upstream skills with local patches applied."""

from __future__ import annotations

import filecmp
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Annotated

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

app = typer.Typer(no_args_is_help=True, add_completion=False, help=__doc__)
console = Console()


class Upstream(BaseModel):
    repo: str = Field(pattern=r"^[\w.-]+/[\w.-]+$")
    rev: str = Field(pattern=r"^[0-9a-f]{40}$")
    license: str
    paths: dict[str, str]  # dist path -> path in the upstream repo, copied in order
    license_file: str | None = None  # copied into every skill dir, before patches

    @property
    def cache(self) -> Path:
        return CACHE / self.repo.replace("/", "__")

    @property
    def skills(self) -> list[str]:
        return sorted({dest.split("/")[0] for dest in self.paths})


class GitError(RuntimeError):
    pass


def git(*args: str, cwd: Path | None = None) -> str:
    # Ceiling stops git from resolving this repo when it runs in a staging dir under .cache/.
    env = {**os.environ, "GIT_CEILING_DIRECTORIES": str(CACHE)}
    r = subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True)
    if r.returncode:
        raise GitError((r.stderr or r.stdout).strip())
    return r.stdout


def load() -> dict[str, Upstream]:
    data = tomlkit.parse(UPSTREAMS.read_text()).unwrap()
    try:
        ups = {name: Upstream.model_validate(u) for name, u in data.items()}
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
        copy(src / path, out / dest)
    if u.license_file:
        for skill in u.skills:
            shutil.copy2(src / u.license_file, out / skill / "LICENSE")


def build_into(out: Path, ups: dict[str, Upstream]) -> list[tuple[str, str, str]]:
    """Returns (source, item, error-or-empty) rows."""
    rows = []
    for name, u in ups.items():
        copy_upstream(u, out)
        for patch in sorted((PATCHES / name).glob("*.patch")):
            try:
                git("apply", "--whitespace=nowarn", str(patch), cwd=out)
                rows.append((name, patch.name, ""))
            except GitError as e:
                rows.append((name, patch.name, str(e)))
    for skill in sorted(p for p in OWN.iterdir() if p.is_dir()):
        copy(skill, out / skill.name)
        rows.append(("skills/", skill.name, ""))
    return rows


def show(rows: list[tuple[str, str, str]]) -> bool:
    t = Table("source", "item", "result", box=None)
    for src, item, err in rows:
        t.add_row(src, item, f"[red]{err}[/]" if err else "[green]ok[/]")
    console.print(t)
    return not any(err for *_, err in rows)


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
    u, source = ups[upstream], source.expanduser()
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
            text = g("diff", "--cached", "--binary", "--", skill)
            path = PATCHES / upstream / f"{skill}.patch"
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
        new = rev or git("ls-remote", f"https://github.com/{u.repo}", "HEAD").split()[0]
        git("fetch", "-q", "origin", cwd=checkout(u))
        new = git("rev-parse", f"{new}^{{commit}}", cwd=u.cache).strip()
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
        console.print(f"[red]held back {', '.join(held)}: patches don't apply at the new commit. Rebase them by hand "
                      f"(git apply --3way in a checkout of the new commit), then `bump <name> --rev <sha>`.[/]")
        raise typer.Exit(1)
    console.print("[green]pins updated; run build[/]")


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
