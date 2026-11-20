#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["typer>=0.12", "rich>=13", "pyyaml>=6"]
# ///
"""Survey the agent skills on this machine. Agents come from ../agents.toml plus [agents.*] in the
user's settings file; any agent works with the generic rules, known ones get exact handling.

  load       what each installed agent loads into every new session: global instructions, the
             skill listing (name + description of each model-invocable skill), plugin skills,
             commands and subagents; plus hooks, MCP servers, name clashes, broken links.
  overview   every skill on disk, once per real directory: totals, auto-load cost per agent,
             collisions, duplicates, near-duplicates, unseen skills; --json for the full data.

Tokens are estimated as chars / 4."""

from __future__ import annotations

import difflib
import hashlib
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
from rich.markup import escape
from rich.table import Table

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents import SHARED_SKILLS, Agent, load_agents  # noqa: E402

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


# ---------- per-agent probes ----------
# Every agent gets `generic`. Agents with known, verified behavior get a quirk function instead.

def generic(a: Agent) -> Report:
    rep = Report(f"{a.label} (generic rules)")
    add_instructions(rep, a.home / "AGENTS.md")
    scan_skills([a.skills], "skill", rep, fm_typed)
    rep.mcp += list(section(load(a.home / "mcp.json", rep), "mcpServers"))
    return rep


def claude(a: Agent) -> Report:
    base = a.home
    rep = Report(a.label)
    add_instructions(rep, base / "CLAUDE.md")
    settings = load(base / "settings.json", rep)
    # settings.json skillOverrides can hide a skill from the model without touching its frontmatter.
    hidden = {k for k, v in section(settings, "skillOverrides").items() if v in ("user-invocable-only", "off")}
    scan_skills([a.skills], "skill", rep, lambda d, fm: fm_typed(d, fm) or str(fm.get("name") or d.name) in hidden)
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


def codex(a: Agent) -> Report:
    base = a.home
    rep = Report(a.label)
    add_instructions(rep, base / "AGENTS.md")
    typed = lambda d, fm: codex_typed_only(d)
    scan_skills([a.skills, base / "skills"], "skill", rep, typed, strict=True)
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


def kimi(a: Agent) -> Report:
    base = Path(os.environ.get("KIMI_CODE_HOME", a.home))
    rep = Report(a.label)
    add_instructions(rep, H / ".agents" / "AGENTS.md")
    extra = [Path(p).expanduser() for p in load(base / "config.toml", rep).get("extra_skill_dirs") or []]
    scan_skills([base / "skills", a.skills, *extra], "skill", rep, fm_typed)
    rep.mcp += list(section(load(base / "mcp.json", rep), "mcpServers"))
    return rep


def grok(a: Agent) -> Report:
    base = a.home
    rep = Report(a.label)
    add_instructions(rep, base / "AGENTS.md")
    cfg = section(load(base / "config.toml", rep), "skills")
    extra = [Path(p).expanduser() for p in cfg.get("paths") or []]
    scan_skills([a.skills, SHARED_SKILLS, H / ".claude" / "skills", *extra], "skill", rep, fm_typed)
    disabled = set(cfg.get("disabled") or [])
    for i in rep.items:
        if i.name in disabled:
            i.loaded = False
    rep.mcp += list(section(load(base / "config.toml", rep), "mcp_servers"))
    return rep


def pi(a: Agent) -> Report:
    base = Path(os.environ.get("PI_CODING_AGENT_DIR", a.home))
    rep = Report(a.label)
    add_instructions(rep, *(base / n for n in ("AGENTS.override.md", "AGENTS.md", "CLAUDE.md")))
    extra = [Path(p).expanduser() for p in load(base / "settings.json", rep).get("skills") or [] if isinstance(p, str)]
    scan_skills([base / "skills", a.skills, *extra], "skill", rep, fm_typed)
    rep.mcp += list(section(load(base / "mcp.json", rep), "mcpServers"))
    return rep


QUIRKS = {"claude-code": claude, "codex": codex, "kimi-code-cli": kimi, "grok": grok, "pi": pi}


def warn(msg: str) -> None:
    console.print(f"[yellow]! {msg}[/]")


def probe_all(only: str | None = None) -> list[tuple[Agent, Report]]:
    """Every installed agent (from the registry) with its report."""
    out = []
    for a in load_agents(warn=warn):
        if only in (None, a.id) and a.installed():
            out.append((a, QUIRKS.get(a.id, generic)(a)))
    return out


def tok(chars: int) -> str:
    return f"{chars // 4:,}"


@app.command("load")
def session_load(
    top: Annotated[int, typer.Option(help="Show the N heaviest always-loaded entries")] = 15,
    only: Annotated[str | None, typer.Option(help="One agent id from the registry")] = None,
) -> None:
    """What each installed agent loads into every new session."""
    reports = [r for _, r in probe_all(only)]
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
                  " load per server unless the agent defers them.\n")
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


# ---------- overview ----------

@dataclass
class Skill:
    name: str
    real: Path
    description: str
    body_chars: int
    files: int
    size: int
    modified: str
    origin: str
    content_hash: str
    paths: list[str] = field(default_factory=list)
    listed_by: list[str] = field(default_factory=list)     # agent ids that list it to the model
    typed_only_in: list[str] = field(default_factory=list)  # agent ids that see it as a typed-only command

    @property
    def per_session(self) -> int:  # chars paid in each session of each agent that lists it
        return len(self.name) + len(self.description) if self.listed_by else 0


def plugin_roots() -> list[Path]:
    """Skill dirs of every cached plugin, enabled or not (latest version of each)."""
    caches = [p for a in load_agents(warn=lambda m: None) for p in (a.home / "plugins" / "cache",)]
    out = []
    for cache in caches:
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


WORD = re.compile(r"[a-z][a-z0-9]{3,}")
STOP = {"when", "with", "that", "this", "your", "from", "into", "user", "users", "skill", "skills", "about",
        "using", "used", "asks", "wants", "like", "such", "only", "also", "each", "them", "they", "their",
        "what", "which", "will", "than", "then", "before", "after", "work", "code"}


def near_duplicates(skills: list[Skill], threshold: float) -> list[tuple[float, Skill, Skill]]:
    """Candidate pairs: TF-IDF cosine of the descriptions, plus a small bonus when the names share a
    word (code-review / code-reviewer). The agent confirms each pair by reading both skills."""
    import math
    docs = [set(WORD.findall((s.name.replace("-", " ") + " " + s.description).lower())) - STOP for s in skills]
    df: dict[str, int] = defaultdict(int)
    for d in docs:
        for w in d:
            df[w] += 1
    idf = {w: math.log(len(docs) / c) for w, c in df.items()}
    vecs = []
    for d in docs:
        v = {w: idf[w] for w in d}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vecs.append({w: x / norm for w, x in v.items()})
    name_words = [set(WORD.findall(s.name.replace("-", " "))) - STOP for s in skills]
    out = []
    for i in range(len(skills)):
        for j in range(i + 1, len(skills)):
            cos = sum(x * vecs[j].get(w, 0.0) for w, x in vecs[i].items())
            score = cos + (0.1 if name_words[i] & name_words[j] else 0.0)
            if score >= threshold:
                out.append((min(score, 1.0), skills[i], skills[j]))
    return sorted(out, key=lambda x: -x[0])


def collect(extra: list[Path]) -> tuple[list[tuple[Agent, Report]], list[Skill]]:
    lock = load_json_quiet(H / ".agents" / ".skill-lock.json").get("skills") or {}
    skills: dict[Path, Skill] = {}

    def add(md: Path) -> Skill:
        real = md.parent.resolve()
        if real not in skills:
            issues: list[str] = []
            fm = frontmatter(md, issues)
            data = md.read_bytes()
            files, size = folder_stats(real)
            skills[real] = Skill(
                name=str(fm.get("name") or md.parent.name), real=real, description=str(fm.get("description") or ""),
                body_chars=len(data.decode(errors="replace")), files=files, size=size,
                modified=datetime.fromtimestamp(md.stat().st_mtime).strftime("%Y-%m-%d"),
                origin=origin_of(md.parent, lock), content_hash=hashlib.sha1(data).hexdigest())
        s = skills[real]
        shown = str(md.parent).replace(str(H), "~")
        if shown not in s.paths:
            s.paths.append(shown)
        return s

    reports = probe_all()
    for agent, rep in reports:
        for item in rep.items:
            if item.kind in ("skill", "plugin-skill"):
                s = add(item.path)
                (s.listed_by if item.loaded else s.typed_only_in).append(agent.id)
    roots = {SHARED_SKILLS, *(a.skills for a in load_agents(warn=lambda m: None)), *plugin_roots(), *extra}
    for root in roots:
        for md in find_skills(root, depth=4) if root.is_dir() else []:
            add(md)
    return reports, sorted(skills.values(), key=lambda s: (-s.per_session, s.name))


@app.command()
def overview(
    json_out: Annotated[Path | None, typer.Option("--json", help="Also write every skill and finding as JSON here")] = None,
    extra: Annotated[list[Path] | None, typer.Option(help="More directories to search (repeatable)")] = None,
    top: Annotated[int, typer.Option(help="Rows per section")] = 20,
    list_all: Annotated[bool, typer.Option("--list", help="Also list every skill an agent sees")] = False,
    threshold: Annotated[float, typer.Option(help="Near-duplicate score cutoff, 0..1")] = 0.3,
) -> None:
    """Every skill on disk: totals, auto-load per agent, collisions, duplicates, near-duplicates, unseen."""
    reports, rows = collect([e.expanduser() for e in extra or []])
    agents = [a for a, _ in reports]
    seen = [s for s in rows if s.listed_by or s.typed_only_in]
    unseen = [s for s in rows if not (s.listed_by or s.typed_only_in)]
    auto = [s for s in rows if s.listed_by]

    by_name: dict[str, list[Skill]] = defaultdict(list)
    for s in rows:
        by_name[s.name].append(s)
    collisions = {n: c for n, c in by_name.items() if len({s.content_hash for s in c}) > 1}
    by_hash: dict[str, list[Skill]] = defaultdict(list)
    for s in rows:
        by_hash[s.content_hash].append(s)
    duplicates = [c for c in by_hash.values() if len(c) > 1]
    names: dict[str, Skill] = {}
    for s in seen:  # one representative per name, for pairwise comparison
        names.setdefault(s.name, s)
    near = near_duplicates(list(names.values()), threshold)

    console.print(f"[bold]{len(rows)} skills on disk[/] · {len(by_name)} names · {len(auto)} auto-loaded by some agent · "
                  f"{sum(1 for s in seen if not s.listed_by)} typed-only everywhere · {len(unseen)} seen by no agent · "
                  f"{len(collisions)} name collisions · {len(duplicates)} duplicate sets · {len(near)} near-duplicate pairs · "
                  f"{len(agents)} agents installed: {', '.join(a.id for a in agents)}\n")

    t = Table("agent", "skills auto-loaded", "~tokens / session", "typed-only", title="Auto-load per agent", box=None)
    for a, rep in reports:
        listed = [i for i in rep.items if i.kind in ("skill", "plugin-skill") and i.loaded]
        t.add_row(f"{a.label} ({a.id})", str(len(listed)), tok(sum(i.chars for i in listed)),
                  str(sum(1 for i in rep.items if i.kind in ("skill", "plugin-skill") and not i.loaded)))
    console.print(t)

    t = Table("skill", "~tok / session", "auto-loaded by", "~tok on use", "origin",
              title=f"Heaviest auto-loaded skills (top {top} of {len(auto)})", box=None)
    for s in auto[:top]:
        t.add_row(s.name, tok(s.per_session), f"{len(s.listed_by)}/{len(agents)}: {', '.join(s.listed_by)}",
                  tok(s.body_chars), s.origin)
    console.print(t)

    if collisions:
        t = Table("name", "copies", "who loads which copy", title="Collisions: same name, different content", box=None)
        for n, c in sorted(collisions.items(), key=lambda kv: -len(kv[1]))[:top]:
            who = "; ".join(f"{s.paths[0]} ({', '.join(s.listed_by + s.typed_only_in) or 'nobody'})" for s in c)
            t.add_row(n, str(len(c)), who)
        console.print(t)
    if duplicates:
        t = Table("skill", "copies", "where", title="Duplicates: identical SKILL.md in several places", box=None)
        for c in sorted(duplicates, key=lambda c: -len(c))[:top]:
            t.add_row(c[0].name, str(len(c)), "; ".join(s.paths[0] for s in c))
        console.print(t)
    if near:
        t = Table("score", "skill", "skill", title="Near-duplicates (candidates: read both before acting)", box=None)
        for sc, a, b in near[:top]:
            t.add_row(f"{sc:.2f}", a.name, b.name)
        console.print(t)
    if unseen:
        by_origin: dict[str, int] = defaultdict(int)
        for s in unseen:
            by_origin[s.origin] += 1
        t = Table("source", "skills", title="On disk but seen by no agent (disabled plugins, stray copies)", box=None)
        for o, n in sorted(by_origin.items(), key=lambda kv: -kv[1])[:top]:
            t.add_row(o, str(n))
        console.print(t)
    if list_all:
        t = Table("skill", "auto-loaded by", "typed-only in", "~tok/session", "~tok on use", "files", "size",
                  "modified", "origin", title=f"Every skill an agent sees ({len(seen)})", box=None)
        for s in seen:
            t.add_row(s.name, ", ".join(s.listed_by) or "-", ", ".join(s.typed_only_in) or "-", tok(s.per_session),
                      tok(s.body_chars), str(s.files), f"{s.size / 1024:,.0f}K", s.modified, s.origin)
        console.print(t)

    if json_out:
        json_out.write_text(json.dumps({
            "agents": [{"id": a.id, "label": a.label, "skills": str(a.skills).replace(str(H), "~")} for a in agents],
            "skills": [{**{k: v for k, v in s.__dict__.items() if k != "real"}, "real": str(s.real).replace(str(H), "~"),
                        "per_session_tokens": s.per_session // 4, "on_use_tokens": s.body_chars // 4} for s in rows],
            "collisions": {n: [s.paths[0] for s in c] for n, c in collisions.items()},
            "duplicates": [[s.paths[0] for s in c] for c in duplicates],
            "near_duplicates": [{"score": round(sc, 2), "a": a.name, "b": b.name} for sc, a, b in near],
        }, indent=1))
        console.print(f"wrote {json_out}")


def load_json_quiet(path: Path) -> dict:
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


if __name__ == "__main__":
    app()
