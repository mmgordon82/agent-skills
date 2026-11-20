"""Agent registry: the shipped defaults (../agents.toml) merged with [agents.*] from the user's
settings file. Standard library only. Used by skill_scan.py to know which agents are installed and
where they read skills; installing skills is npx skills' job."""

from __future__ import annotations

import os
import shutil
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULTS = Path(__file__).resolve().parent.parent / "agents.toml"
SETTINGS = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "agent-skills" / "settings.toml"
SHARED_SKILLS = Path.home() / ".agents" / "skills"
FIELDS = {"label", "home", "skills", "check_binary", "check_dir", "check_boolean_operator", "verified"}


@dataclass
class Agent:
    id: str
    label: str
    home: Path
    skills: Path
    check_binary: list[str] = field(default_factory=list)
    check_dir: list[Path] = field(default_factory=list)
    operator: str = "AND"  # check_boolean_operator
    verified: bool = False  # layout and quirks checked by hand; the docs name these

    def installed(self) -> bool:
        """AND: home and every check_dir exist and every check_binary is on PATH. OR: any one of them."""
        checks = [self.home.exists(), *(d.exists() for d in self.check_dir),
                  *(shutil.which(b) is not None for b in self.check_binary)]
        return any(checks) if self.operator == "OR" else all(checks)


def _read(path: Path, warn) -> dict:
    if not path.exists():
        return {}
    try:
        data = tomllib.loads(path.read_text()).get("agents") or {}
        return data if isinstance(data, dict) else {}
    except (OSError, tomllib.TOMLDecodeError) as e:
        warn(f"{path}: unreadable ({e.__class__.__name__}); its [agents] are ignored")
        return {}


def _strings(value) -> bool:
    return isinstance(value, list) and all(isinstance(x, str) and x for x in value)


def load_agents(defaults: Path = DEFAULTS, settings: Path = SETTINGS, user: bool = True,
                warn=lambda msg: print(msg, file=sys.stderr)) -> list[Agent]:
    """All known agents. A user table with a shipped id overrides that agent field by field."""
    merged = _read(defaults, warn)
    for aid, table in (_read(settings, warn) if user else {}).items():
        if isinstance(table, dict):
            merged[aid] = {**merged.get(aid, {}), **table}
    out = []
    for aid, t in merged.items():
        if not isinstance(t, dict):
            warn(f"agent {aid}: not a table; skipped")
            continue
        if unknown := sorted(set(t) - FIELDS):
            warn(f"agent {aid}: unknown field(s) ignored: {', '.join(unknown)}")
        if not all(isinstance(t.get(k), str) and t.get(k) for k in ("label", "home", "skills")) or \
                not all(_strings(t.get(k, [])) for k in ("check_binary", "check_dir")):
            warn(f"agent {aid}: needs label, home and skills as strings, checks as lists of strings; skipped")
            continue
        operator = str(t.get("check_boolean_operator", "AND")).upper()
        if operator not in ("AND", "OR"):
            warn(f"agent {aid}: check_boolean_operator must be AND or OR, not {operator!r}; using AND")
            operator = "AND"
        out.append(Agent(aid, t["label"], Path(t["home"]).expanduser(), Path(t["skills"]).expanduser(),
                         list(t.get("check_binary", [])), [Path(d).expanduser() for d in t.get("check_dir", [])], operator,
                         t.get("verified") is True))
    return out
