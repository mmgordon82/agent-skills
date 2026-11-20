#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Regenerate the npx-skills part of skills/skill-critique/agents.toml from the agent table in the
`skills` npm package. Reads the package source as text; never runs it. The hand-verified section
above the marker line is kept as is, and its ids win.

    mkdir -p /tmp/skills-pkg && cd /tmp/skills-pkg && npm pack skills && tar xzf skills-*.tgz
    uv run tools/npx_agents.py /tmp/skills-pkg/package
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "skills" / "skill-critique" / "agents.toml"
MARKER = "# ---- From npx skills"

# Entries the parser can't translate (helper functions, multi-line checks). Checks on the current
# project folder are dropped: the registry describes what's installed on the machine.
MANUAL = {
    "astrbot": dict(label="AstrBot", home="~/.astrbot", skills="~/.astrbot/data/skills"),
    "codebuddy": dict(label="CodeBuddy", home="~/.codebuddy", skills="~/.codebuddy/skills"),
    "continue": dict(label="Continue", home="~/.continue", skills="~/.continue/skills"),
    "jazz": dict(label="Jazz", home="~/.jazz", skills="~/.jazz/skills"),
    "openclaw": dict(label="OpenClaw", home="~/.openclaw", skills="~/.openclaw/skills", alt=["~/.clawdbot", "~/.moltbot"]),
    "kimchi": dict(label="Kimchi", home="~/.config/kimchi", skills="~/.config/kimchi/harness/skills"),
    "minimax-code": dict(label="MiniMax Code", home="~/.minimax", skills="~/.minimax/skills", alt=["/Applications/MiniMax Code.app"]),
    "posit-assistant": dict(label="Posit Assistant", home="~/.posit/assistant", skills="~/.posit/assistant/skills", alt=["~/.positai"]),
    "zcode": dict(label="ZCode", home="~/.zcode", skills="~/.zcode/skills", alt=["/Applications/ZCode.app"]),
    "reasonix": dict(label="Reasonix", home="~/.reasonix", skills="~/.reasonix/skills"),
    "zed": dict(label="Zed", home="~/.config/zed", skills="~/.agents/skills"),
}
SKIP = {"eve", "promptscript", "replit", "universal"}  # project-only detection, or never detected


def parse(src: str) -> tuple[dict[str, dict], list[str]]:
    consts = {"home": "~", "configHome": "~/.config"}
    for m in re.finditer(r'const (\w+Home) = process\.env\.\w+\?\.trim\(\) \|\| join\(home, "([^"]+)"\);', src):
        consts[m.group(1)] = "~/" + m.group(2)

    def path(e: str) -> str | None:
        e = e.strip()
        m = re.fullmatch(r'join\((\w+), ("[^"]+"(?:, "[^"]+")*)\)', e)
        if m and m.group(1) in consts:
            return "/".join([consts[m.group(1)], *re.findall(r'"([^"]+)"', m.group(2))])
        return consts.get(e)

    body = src[src.index("const agents = {"):src.index("async function detectInstalledAgents")]
    out, unparsed = {}, []
    for m in re.finditer(r'\n\t"?([\w-]+)"?: \{\n(.*?)\n\t\}', body, re.S):
        aid, block = m.group(1), m.group(2)
        label = re.search(r'displayName: "([^"]+)"', block)
        skills = re.search(r"globalSkillsDir: (.+?),\n", block)
        det = re.search(r"detectInstalled: async \(\) => \{\s*return (.+?);\s*\}", block, re.S)
        dirs = [re.fullmatch(r"existsSync\((.+)\)", c.strip()) for c in det.group(1).split("||")] if det else []
        paths = [path(d.group(1)) if d else None for d in dirs]
        skills_path = path(skills.group(1)) if skills else None
        if not label or not skills_path or not paths or None in paths:
            unparsed.append(aid)
            continue
        out[aid] = dict(label=label.group(1), home=paths[0], skills=skills_path, alt=paths[1:])
    return out, unparsed


def toml_entry(aid: str, e: dict) -> str:
    lines = [f"[agents.{aid}]", f'label = "{e["label"]}"', f'home = "{e["home"]}"', f'skills = "{e["skills"]}"']
    if e.get("alt"):
        lines += ["check_dir = " + json.dumps(e["alt"]), 'check_boolean_operator = "OR"']
    return "\n".join(lines)


def main() -> None:
    pkg = Path(sys.argv[1]) if len(sys.argv) > 1 else sys.exit(__doc__)
    chunk = next((p for p in (pkg / "dist").rglob("*.mjs") if "const agents = {" in p.read_text(errors="ignore")), None)
    if not chunk:
        sys.exit(f"no agent table found under {pkg}/dist")
    version = json.loads((pkg / "package.json").read_text()).get("version", "?")
    parsed, unparsed = parse(chunk.read_text())
    entries = {**parsed, **MANUAL}
    text = REGISTRY.read_text()
    head = text[:text.index(MARKER)] if MARKER in text else text.rstrip() + "\n\n"
    verified = set(re.findall(r"^\[agents\.([\w-]+)\]", head, re.M))
    if missing := sorted(set(unparsed) - set(MANUAL) - SKIP - verified):
        sys.exit(f"can't translate {', '.join(missing)}: add them to MANUAL or SKIP")
    body = "\n\n".join(toml_entry(a, entries[a]) for a in sorted(entries) if a not in verified and a not in SKIP)
    REGISTRY.write_text(head + f"{MARKER} {version}'s agent table: detection translated from its source (project-only\n"
                        "# checks dropped). Measured with /skill-critique's generic rules. ----\n\n" + body + "\n")
    print(f"wrote {len(entries) - len(verified & set(entries))} npx agents from skills {version} into {REGISTRY.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
