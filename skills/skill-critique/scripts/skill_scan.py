#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["typer>=0.12", "rich>=13", "pyyaml>=6"]
# ///
"""Survey the agent skills on this machine.

  load       what each agent CLI loads into every new session: global instructions, the skill
             listing (name + description of each model-invocable skill), plugin skills, commands
             and agents; plus hooks, MCP servers, duplicates, broken links, bad frontmatter.
  inventory  every skill found on disk, once per real directory: which CLIs see it and whether it
             loads there, its per-session and on-use cost, size, age, and where it came from.

Tokens are estimated as chars / 4."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tomllib
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated

import typer
import yaml
from rich.console import Console
from rich.table import Table

H = Path.home()
console = Console(width=None if sys.stdout.isatty() else 220)  # agents read this captured
app = typer.Typer(add_completion=False, help=__doc__)


@dataclass
class Item:
    kind: str  # instructions | skill | plugin-skill | command | agent
    name: str
    path: Path
    chars: int
    loaded: bool = True  # False = typed-only, costs nothing until called


@dataclass
class Report:
    agent: str
    items: list[Item] = field(default_factory=list)
    hooks: list[str] = field(default_factory=list)
    mcp: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)


def load(path: Path, rep: Report) -> dict:
    """A JSON or TOML config as a dict; a missing file is {}, a broken one is {} plus an issue."""
    if not path.exists():
        return {}
    try:
        text = path.read_text()
        data = tomllib.loads(text) if path.suffix == ".toml" else json.loads(text)
    except (ValueError, tomllib.TOMLDecodeError) as e:
        rep.issues.append(f"unreadable config, skipped: {path} ({e.__class__.__name__})")
        return {}
    return data if isinstance(data, dict) else {}


def section(cfg: dict, key: str) -> dict:
    v = cfg.get(key)
    return v if isinstance(v, dict) else {}


def frontmatter(md: Path, issues: list[str]) -> dict:
    """Parsed frontmatter; {"_invalid": True, ...} when the YAML is broken (lenient loaders still read name/description)."""
    text = md.read_text(errors="replace")
    m = re.match(r"---\s*\n(.*?)\n---", text, re.S)
    if not m:
        issues.append(f"no frontmatter: {md}")
        return {}
    try:
        data = yaml.safe_load(m.group(1)) or {}
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError:
        issues.append(f"invalid YAML frontmatter (strict parsers such as Codex skip it): {md}")
        return {**dict(re.findall(r"^(name|description):\s*(.*)$", m.group(1), re.M)), "_invalid": True}


def codex_typed_only(skill_dir: Path) -> bool:
    y = skill_dir / "agents" / "openai.yaml"
    if not y.exists():
        return False
    try:
        data = yaml.safe_load(y.read_text())
    except yaml.YAMLError:
        return False
    policy = data.get("policy") if isinstance(data, dict) else None
    return isinstance(policy, dict) and policy.get("allow_implicit_invocation") is False


def find_skills(d: Path, depth: int = 3) -> list[Path]:
    """SKILL.md files under d, following symlinks; a skill dir's own subfolders are not searched.
    Hidden dirs are skipped, except Codex's bundled `.system`."""
    out = []
    for child in sorted(d.iterdir()) if d.is_dir() else []:
        if child.name.startswith(".") and child.name != ".system" or child.name == "node_modules":
            continue
        if (child / "SKILL.md").is_file():
            out.append(child / "SKILL.md")
        elif child.is_dir() and depth > 1:
            out += find_skills(child, depth - 1)
    return out


def scan_skills(roots: list[Path], kind: str, rep: Report, typed_only, prefix: str = "", strict: bool = False) -> None:
    """Walk roots in priority order; the first valid skill with a given name wins, like the CLIs do."""
    seen = {i.name: i for i in rep.items if i.kind in ("skill", "plugin-skill")}
    for root in roots:
        if not root.is_dir():
            continue
        for md in find_skills(root):
            fm = frontmatter(md, rep.issues)
            name = prefix + str(fm.get("name") or md.parent.name)
            desc = str(fm.get("description") or "")
            if strict and fm.get("_invalid"):
                continue  # this CLI drops it; the issue is already reported
            if not desc:
                rep.issues.append(f"no description, not loaded: {md}")
                continue
            if name in seen:
                other = seen[name].path
                if other.resolve() != md.resolve() and other.read_bytes() != md.read_bytes():
                    rep.issues.append(f"name clash, different content: {name}: {other} vs {md}")
                continue
            item = Item(kind, name, md, len(name) + len(desc), not typed_only(md.parent, fm))
            seen[name] = item
            rep.items.append(item)
        for p in root.iterdir():
            if p.is_symlink() and not p.exists():
                rep.issues.append(f"broken symlink: {p} -> {os.readlink(p)}")


def add_instructions(rep: Report, *paths: Path) -> None:
    for p in paths:
        if p.exists():
            rep.items.append(Item("instructions", str(p).replace(str(H), "~"), p, len(p.read_text(errors="replace"))))
            return


def md_entries(d: Path, kind: str, rep: Report, prefix: str) -> None:
    for md in sorted(d.glob("*.md")) if d.is_dir() else []:
        fm = frontmatter(md, rep.issues)
        name = prefix + str(fm.get("name") or md.stem)
        rep.items.append(Item(kind, name, md, len(name) + len(str(fm.get("description") or ""))))


def fm_typed(_dir: Path, fm: dict) -> bool:
    return any(fm.get(k) is True for k in ("disable-model-invocation", "disableModelInvocation", "disable_model_invocation"))


def claude() -> Report | None:
    base = H / ".claude"
    if not base.exists():
        return None
    rep = Report("Claude Code")
    add_instructions(rep, base / "CLAUDE.md")
    settings = load(base / "settings.json", rep)
    # settings.json skillOverrides can hide a skill from the model without touching its frontmatter.
    hidden = {k for k, v in section(settings, "skillOverrides").items() if v in ("user-invocable-only", "off")}
    scan_skills([base / "skills"], "skill", rep, lambda d, fm: fm_typed(d, fm) or str(fm.get("name") or d.name) in hidden)
    md_entries(base / "agents", "agent", rep, "")
    md_entries(base / "commands", "command", rep, "/")
    rep.hooks += [f"{ev} (settings.json)" for ev in section(settings, "hooks")]
    paths = section(load(base / "plugins" / "installed_plugins.json", rep), "plugins")
    for plugin, on in section(settings, "enabledPlugins").items():
        if not on or not paths.get(plugin):
            continue
        root = Path(paths[plugin][-1]["installPath"])
        short = plugin.split("@")[0]
        scan_skills([root / "skills"], "plugin-skill", rep, fm_typed, prefix=f"{short}:")
        md_entries(root / "commands", "command", rep, f"/{short}:")
        md_entries(root / "agents", "agent", rep, f"{short}:")
        rep.hooks += [f"{ev} ({short})" for ev in section(load(root / "hooks" / "hooks.json", rep), "hooks")]
        servers = load(root / ".mcp.json", rep)
        rep.mcp += [f"{s} ({short})" for s in section(servers, "mcpServers") or servers]
    rep.mcp += list(section(load(H / ".claude.json", rep), "mcpServers"))
    return rep


def codex() -> Report | None:
    base = H / ".codex"
    if not base.exists():
        return None
    rep = Report("Codex")
    add_instructions(rep, base / "AGENTS.md")
    typed = lambda d, fm: codex_typed_only(d)
    scan_skills([H / ".agents" / "skills", base / "skills"], "skill", rep, typed, strict=True)
    cfg = load(base / "config.toml", rep)
    rep.mcp += list(section(cfg, "mcp_servers"))
    for plugin, conf in section(cfg, "plugins").items():
        if isinstance(conf, dict) and conf.get("enabled") is False:
            continue
        name, _, market = plugin.partition("@")
        versions = sorted((base / "plugins" / "cache" / market / name).glob("*"), key=lambda p: p.stat().st_mtime)
        if versions:
            v = versions[-1]
            scan_skills([v / "skills", v / ".codex-plugin" / "migrated-command-skills"], "plugin-skill", rep, typed,
                        prefix=f"{name}:", strict=True)
    return rep


def kimi() -> Report | None:
    base = Path(os.environ.get("KIMI_CODE_HOME", H / ".kimi-code"))
    if not base.exists():
        return None
    rep = Report("Kimi Code")
    add_instructions(rep, H / ".agents" / "AGENTS.md")
    extra = [Path(p).expanduser() for p in load(base / "config.toml", rep).get("extra_skill_dirs") or []]
    scan_skills([base / "skills", H / ".agents" / "skills", *extra], "skill", rep, fm_typed)
    rep.mcp += list(section(load(base / "mcp.json", rep), "mcpServers"))
    return rep


def grok() -> Report | None:
    base = H / ".grok"
    if not base.exists():
        return None
    rep = Report("Grok")
    add_instructions(rep, base / "AGENTS.md")
    cfg = section(load(base / "config.toml", rep), "skills")
    extra = [Path(p).expanduser() for p in cfg.get("paths") or []]
    scan_skills([base / "skills", H / ".agents" / "skills", H / ".claude" / "skills", *extra], "skill", rep, fm_typed)
    disabled = set(cfg.get("disabled") or [])
    for i in rep.items:
        if i.name in disabled:
            i.loaded = False
    rep.mcp += list(section(load(base / "config.toml", rep), "mcp_servers"))
    return rep


def pi() -> Report | None:
    base = Path(os.environ.get("PI_CODING_AGENT_DIR", H / ".pi" / "agent"))
    if not base.exists():
        return None
    rep = Report("Pi")
    add_instructions(rep, *(base / n for n in ("AGENTS.override.md", "AGENTS.md", "CLAUDE.md")))
    extra = [Path(p).expanduser() for p in load(base / "settings.json", rep).get("skills") or [] if isinstance(p, str)]
    scan_skills([base / "skills", H / ".agents" / "skills", *extra], "skill", rep, fm_typed)
    rep.mcp += list(section(load(base / "mcp.json", rep), "mcpServers"))
    return rep


def tok(chars: int) -> str:
    return f"{chars // 4:,}"


PROBES = dict(claude=claude, codex=codex, kimi=kimi, grok=grok, pi=pi)


@app.command("load")
def session_load(
    top: Annotated[int, typer.Option(help="Show the N heaviest always-loaded entries")] = 15,
    only: Annotated[str | None, typer.Option(help="One agent: claude, codex, kimi, grok, pi")] = None,
) -> None:
    """What each CLI loads into every new session."""
    reports = [r for k, f in PROBES.items() if (only in (None, k)) and (r := f())]
    summary = Table("agent", "instructions", "skills listed", "typed-only", "plugin skills", "commands + agents",
                    "~tokens / session", "hooks", "MCP", title="Loaded into every new session", box=None)
    for r in reports:
        by = defaultdict(int)
        n = defaultdict(int)
        for i in r.items:
            if i.loaded:
                by[i.kind] += i.chars
                n[i.kind] += 1
        hidden = sum(1 for i in r.items if not i.loaded)
        summary.add_row(
            r.agent, tok(by["instructions"]), f"{n['skill']} · {tok(by['skill'])}", str(hidden),
            f"{n['plugin-skill']} · {tok(by['plugin-skill'])}",
            f"{n['command'] + n['agent']} · {tok(by['command'] + by['agent'])}",
            f"[bold]{tok(sum(by.values()))}[/]", str(len(r.hooks)), str(len(r.mcp)))
    console.print(summary)
    console.print("Token counts: chars/4. Hooks inject text that can't be measured statically; MCP tool schemas"
                  " load per server unless the CLI defers them.\n")

    for r in reports:
        heavy = sorted((i for i in r.items if i.loaded and i.kind != "instructions"), key=lambda i: -i.chars)[:top]
        t = Table("entry", "kind", "~tokens", "path", title=f"{r.agent}: heaviest entries", box=None)
        for i in heavy:
            t.add_row(i.name, i.kind, tok(i.chars), str(i.path).replace(str(H), "~"))
        console.print(t)
        if r.hooks:
            console.print(f"  hooks: {', '.join(r.hooks)}")
        if r.mcp:
            console.print(f"  MCP servers: {', '.join(r.mcp)}")
        for msg in sorted(set(r.issues)):
            console.print(f"  [yellow]! {msg.replace(str(H), '~')}[/]")
        console.print()


# ---------- inventory ----------

SKILL_ROOTS = [".agents/skills", ".claude/skills", ".codex/skills", ".grok/skills", ".kimi-code/skills",
               ".pi/agent/skills", ".cursor/skills", ".gemini/skills"]
LETTER = dict(claude="C", codex="X", kimi="K", grok="G", pi="P")


@dataclass
class Skill:
    name: str
    real: Path
    desc_chars: int
    body_chars: int
    files: int
    size: int
    modified: str
    origin: str
    paths: list[str] = field(default_factory=list)
    seen: dict[str, bool] = field(default_factory=dict)  # CLI -> listed to the model (False = typed-only)
    issues: list[str] = field(default_factory=list)


def plugin_roots() -> list[Path]:
    """Skill dirs of every cached plugin, enabled or not (latest version of each)."""
    out = []
    for cache in (H / ".claude" / "plugins" / "cache", H / ".codex" / "plugins" / "cache"):
        for plugin in (p for m in (cache.iterdir() if cache.is_dir() else []) if m.is_dir() for p in m.iterdir() if p.is_dir()):
            versions = sorted((v for v in plugin.iterdir() if v.is_dir()), key=lambda v: v.stat().st_mtime)
            if versions:
                out += [versions[-1] / "skills", versions[-1] / ".codex-plugin" / "migrated-command-skills"]
    return out


def origin_of(d: Path, lock: dict) -> str:
    real = d.resolve()
    if "cache" in real.parts and "plugins" in real.parts:
        i = real.parts.index("cache")
        return f"plugin {real.parts[i + 2]}@{real.parts[i + 1]}"
    for p in (real, *real.parents):
        if p == H or p == p.parent:
            break
        if (p / ".git").exists():
            r = subprocess.run(["git", "-C", str(p), "remote", "get-url", "origin"], capture_output=True, text=True)
            return f"git {r.stdout.strip() or str(p).replace(str(H), '~')}"
    if d.name in lock and isinstance(lock[d.name], dict):
        return f"{lock[d.name].get('source', '?')} (skills CLI)"
    if d.is_symlink():
        return f"link -> {os.readlink(d)}"
    return "local copy"


def folder_stats(d: Path) -> tuple[int, int]:
    files = size = 0
    for root, dirs, names in os.walk(d):
        dirs[:] = [x for x in dirs if x not in (".git", "node_modules", "__pycache__")]
        for n in names:
            try:
                size += (Path(root) / n).stat().st_size
                files += 1
            except OSError:
                pass
    return files, size


@app.command()
def inventory(
    json_out: Annotated[Path | None, typer.Option("--json", help="Also write the full inventory as JSON here")] = None,
    extra: Annotated[list[Path] | None, typer.Option(help="More directories to search (repeatable)")] = None,
    all_: Annotated[bool, typer.Option("--all", help="Also list skills no CLI sees, one by one")] = False,
) -> None:
    """Every skill on this machine, once per real directory, highest per-session cost first."""
    lock = (load_json_quiet(H / ".agents" / ".skill-lock.json").get("skills") or {})
    skills: dict[Path, Skill] = {}

    def add(md: Path) -> Skill:
        real = md.parent.resolve()
        if real not in skills:
            issues: list[str] = []
            fm = frontmatter(md, issues)
            text = md.read_text(errors="replace")
            files, size = folder_stats(real)
            skills[real] = Skill(
                name=str(fm.get("name") or md.parent.name), real=real,
                desc_chars=len(str(fm.get("description") or "")), body_chars=len(text),
                files=files, size=size, modified=datetime.fromtimestamp(md.stat().st_mtime).strftime("%Y-%m-%d"),
                origin=origin_of(md.parent, lock), issues=issues)
        s = skills[real]
        shown = str(md.parent).replace(str(H), "~")
        if shown not in s.paths:
            s.paths.append(shown)
        return s

    for agent, probe in PROBES.items():
        rep = probe()
        for item in rep.items if rep else []:
            if item.kind in ("skill", "plugin-skill"):
                add(item.path).seen[agent] = item.loaded
    for root in [H / r for r in SKILL_ROOTS] + plugin_roots() + [e.expanduser() for e in extra or []]:
        for md in find_skills(root, depth=4) if root.is_dir() else []:
            add(md)

    rows = sorted(skills.values(), key=lambda s: (-max((s.desc_chars for v in s.seen.values() if v), default=0), s.name))
    names: dict[str, int] = defaultdict(int)
    for s in rows:
        names[s.name] += 1
    t = Table("skill", "loads in", "~tok/session", "~tok on use", "files", "size", "modified", "origin",
              title=f"Skills on this machine ({len(rows)})", box=None)
    for s in (rows if all_ else [s for s in rows if s.seen]):
        where = " ".join(LETTER[a] if on else LETTER[a].lower() for a, on in s.seen.items()) or "-"
        per_session = tok(s.desc_chars + len(s.name)) if any(s.seen.values()) else "0"
        flag = " [yellow](dup)[/]" if names[s.name] > 1 else ""
        t.add_row(s.name + flag, where, per_session, tok(s.body_chars), str(s.files), f"{s.size / 1024:,.0f}K",
                  s.modified, s.origin)
    console.print(t)
    unseen: dict[str, int] = defaultdict(int)
    for s in rows:
        if not s.seen:
            unseen[s.origin] += 1
    if unseen and not all_:
        u = Table("source", "skills", title="On disk but seen by no CLI (disabled plugins, stray copies; --all lists them)", box=None)
        for origin, n in sorted(unseen.items(), key=lambda kv: -kv[1]):
            u.add_row(origin, str(n))
        console.print(u)
    loaded = sum(1 for s in rows if any(s.seen.values()))
    typed = sum(1 for s in rows if s.seen and not any(s.seen.values()))
    console.print(f"loads in: C Claude Code, X Codex, K Kimi, G Grok, P Pi; lowercase = visible but typed-only.\n"
                  f"{loaded} listed to a model somewhere · {typed} typed-only everywhere · "
                  f"{sum(1 for s in rows if not s.seen)} seen by no CLI (disabled plugins, stray copies) · "
                  f"{sum(1 for n, c in names.items() if c > 1)} names on more than one copy")
    if json_out:
        json_out.write_text(json.dumps([{**s.__dict__, "real": str(s.real).replace(str(H), "~")} for s in rows], indent=1))
        console.print(f"wrote {json_out}")


def load_json_quiet(path: Path) -> dict:
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


if __name__ == "__main__":
    app()
