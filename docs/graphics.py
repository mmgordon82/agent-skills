#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Render the README graphics (light + dark) into docs/assets/. Reads upstreams.toml, skills/, dist/."""

from __future__ import annotations

import re
import tomllib
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets"

THEMES = {
    "light": dict(bg="#ffffff", panel="#f6f8fa", line="#d1d9e0", ink="#1f2328", muted="#59636e", grid="#e6eaef",
                  own="#8250df", derived="#0969da", patched="#9a6700", add="#1a7f37", add_bg="#dafbe1",
                  rm="#cf222e", rm_bg="#ffebe9", hunk="#0969da"),
    "dark": dict(bg="#0d1117", panel="#151b23", line="#30363d", ink="#e6edf3", muted="#9198a1", grid="#1c232c",
                 own="#bc8cff", derived="#58a6ff", patched="#e3b341", add="#3fb950", add_bg="#12261e",
                 rm="#f85149", rm_bg="#2d1215", hunk="#58a6ff"),
}

GROUPS = {
    "Workflow": ["poteto-mode", "delegate", "swarm", "arena", "architect", "reflect", "setup-pstack",
                 "run-validation", "agent-workdir", "consulting-grok"],
    "Design & UI": ["impeccable", "design-taste-frontend", "pfd", "make-bot-ui"],
    "Ship & secure": ["ship-audit", "security-hunt", "web-perimeter-audit", "db-migrations",
                      "git-guardrails-claude-code", "self-hosting"],
    "Writing": ["unslop", "technical-writing", "no-comments", "writing-for-agents"],
}
KIND_LABEL = {"own": "own", "derived": "derived fork + LICENSE", "patched": "pinned upstream + patch"}

SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"


def svg(w: int, h: int, title: str, body: str, c: dict, extra_css: str = "") -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="t">
<title id="t">{escape(title)}</title>
<style>
  .sans {{ font-family: {SANS}; }}
  .mono {{ font-family: {MONO}; }}
  .flow {{ stroke-dasharray: 4 6; animation: flow 1.2s linear infinite; }}
  @keyframes flow {{ to {{ stroke-dashoffset: -20; }} }}
  {extra_css}
  @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; opacity: 1 !important; transform: none !important; }} }}
</style>
<defs>
  <pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.2" fill="{c['grid']}"/></pattern>
  <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path d="M0,0 L10,5 L0,10 z" fill="{c['muted']}"/></marker>
</defs>
<rect width="{w}" height="{h}" rx="16" fill="{c['bg']}"/>
<rect width="{w}" height="{h}" rx="16" fill="url(#dots)"/>
<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="16" fill="none" stroke="{c['line']}"/>
{body}
</svg>
"""


def text(x, y, s, c, size=14, cls="sans", fill=None, weight=400, anchor="start", extra=""):
    return (f'<text x="{x}" y="{y}" class="{cls}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill or c["ink"]}" text-anchor="{anchor}" {extra}>{escape(s)}</text>')


def card(x, y, w, h, c, stroke=None, fill=None, r=10):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill or c["panel"]}" stroke="{stroke or c["line"]}"/>'


def eyebrow(x, y, num, label, c):
    return text(x, y, f"{num}  {label.upper()}", c, 12, "mono", c["muted"], 600, extra='letter-spacing="1.5"')


# ---------- data ----------

def skills_data() -> dict[str, dict]:
    ups = tomllib.loads((ROOT / "upstreams.toml").read_text())
    info: dict[str, dict] = {}
    for name, u in ups.items():
        for dest in u["paths"]:
            info[dest.split("/")[0]] = dict(kind="patched", source=u["repo"])
    for d in (ROOT / "skills").iterdir():
        if d.is_dir():
            info[d.name] = dict(kind="derived" if (d / "LICENSE").exists() else "own", source="skills/")
    for name, i in info.items():
        md = (ROOT / "dist" / name / "SKILL.md")
        if not md.exists():
            raise SystemExit(f"dist/{name} missing; run `uv run build.py build` first")
        i["typed"] = bool(re.search(r"^disable-model-invocation:\s*true", md.read_text(), re.M))
    grouped = {s for g in GROUPS.values() for s in g}
    if grouped != set(info):
        raise SystemExit(f"GROUPS out of sync: missing {set(info) - grouped}, unknown {grouped - set(info)}")
    return info


# ---------- hero ----------

def hero(c: dict, n_skills: int, n_patches: int, n_ups: int) -> str:
    b = []
    b.append(text(64, 92, "OVERLAY SKILL SET  ·  CLAUDE CODE  ·  CODEX  ·  KIMI  ·  GROK", c, 12, "mono", c["muted"], 600, extra='letter-spacing="1.5"'))
    b.append(text(60, 172, "agent-skills", c, 68, weight=700, extra='letter-spacing="-1.5"'))
    b.append(text(64, 222, "My own agent skills, plus pinned upstream", c, 21, fill=c["muted"]))
    b.append(text(64, 252, "skills with small, readable patches on top.", c, 21, fill=c["muted"]))
    stats = [(str(n_skills), "skills"), (str(n_patches), "patches"), (str(n_ups), "pinned upstreams")]
    x = 64
    for num, lab in stats:
        b.append(text(x, 322, num, c, 34, weight=700, fill=c["ink"]))
        b.append(text(x, 346, lab, c, 13, "mono", c["muted"]))
        x += 150
    # diff card
    X, Y, W = 640, 56, 500
    rows = [
        ("why", "Why: drop the curl | sudo sh install."),
        ("hunk", "@@ make-bot-ui/SKILL.md @@"),
        ("ctx", " Use HTTP. Do not add HTTPS unless the user asks."),
        ("rm", "-If Tailscale is not installed, install it:"),
        ("rm", "-curl -fsSL https://tailscale.com/install.sh | sudo sh"),
        ("add", "+If Tailscale is not installed, stop and ask the"),
        ("add", "+user to install it. Do not install it yourself."),
        ("ctx", " Once installed, start the node with a short ..."),
    ]
    H = 64 + len(rows) * 28 + 48
    b.append(f'<g>{card(X, Y, W, H, c, r=12)}')
    b.append(f'<line x1="{X}" y1="{Y + 44}" x2="{X + W}" y2="{Y + 44}" stroke="{c["line"]}"/>')
    b.append(text(X + 20, Y + 28, "patches/pstack/make-bot-ui.patch", c, 13, "mono", c["ink"], 600))
    b.append(f'<g>{card(X + W - 104, Y + 12, 88, 22, c, stroke=c["add"], fill=c["add_bg"], r=11)}'
             + text(X + W - 60, Y + 27, "applies ✓", c, 12, "mono", c["add"], 600, "middle") + "</g>")
    y = Y + 56
    for kind, s in rows:
        if kind in ("rm", "add"):
            b.append(f'<rect x="{X + 1}" y="{y}" width="{W - 2}" height="28" fill="{c[kind + "_bg"]}"/>')
        col = {"why": c["patched"], "hunk": c["hunk"], "ctx": c["muted"], "rm": c["rm"], "add": c["add"]}[kind]
        b.append(text(X + 20, y + 19, s, c, 13, "mono", col, 600 if kind == "why" else 400))
        y += 28
    b.append(f'<line x1="{X}" y1="{y + 8}" x2="{X + W}" y2="{y + 8}" stroke="{c["line"]}"/>')
    b.append(text(X + 20, y + 32, "pinned  backnotprop/pstack @ 059190e", c, 12, "mono", c["muted"]))
    b.append("</g>")
    return svg(1200, 420, "agent-skills: own skills plus pinned upstream skills with readable patches", "\n".join(b), c)


# ---------- pipeline ----------

def pipeline(c: dict, n_skills: int, n_own: int) -> str:
    ups = tomllib.loads((ROOT / "upstreams.toml").read_text())
    patches = {name: len(list((ROOT / "patches" / name).glob("*.patch"))) for name in ups}
    b = []
    cols = [40, 330, 620, 910]
    W = 250
    titles = [("1", "Pin"), ("2", "Patch"), ("3", "Build"), ("4", "Install")]
    for x, (n, t) in zip(cols, titles):
        b.append(eyebrow(x, 52, n, t, c))
    # 1 pin
    y = 72
    for name, u in ups.items():
        owner, repo = u["repo"].split("/")
        b.append(card(cols[0], y, W, 62, c))
        b.append(f'<rect x="{cols[0]}" y="{y + 12}" width="3" height="38" rx="1.5" fill="{c["patched"]}"/>')
        b.append(text(cols[0] + 18, y + 26, owner, c, 12, "mono", c["muted"]))
        b.append(text(cols[0] + 18, y + 47, repo, c, 15, weight=600))
        lic = u["license"].replace("CC-BY-SA-4.0", "CC BY-SA")
        b.append(text(cols[0] + W - 14, y + 26, f"@{u['rev'][:7]} · {lic}", c, 12, "mono", c["patched"], anchor="end"))
        y += 74
    b.append(card(cols[0], y + 8, W, 62, c, stroke=c["own"]))
    b.append(text(cols[0] + 18, y + 34, "skills/", c, 15, "mono", c["own"], 600))
    b.append(text(cols[0] + 18, y + 55, f"{n_own} own + derived skills", c, 13, fill=c["muted"]))
    # 2 patch
    y = 72
    b.append(card(cols[1], y, W, 4 * 74 - 12, c))
    b.append(text(cols[1] + 18, y + 30, "patches/", c, 15, "mono", c["patched"], 600))
    yy = y + 62
    for name, n in patches.items():
        b.append(text(cols[1] + 30, yy, f"{name}/", c, 13, "mono"))
        b.append(text(cols[1] + W - 18, yy, f"{n} patch{'es' if n > 1 else ''}", c, 12, "mono", c["muted"], anchor="end"))
        yy += 28
    b.append(f'<line x1="{cols[1] + 18}" y1="{yy - 6}" x2="{cols[1] + W - 18}" y2="{yy - 6}" stroke="{c["line"]}"/>')
    b.append(text(cols[1] + 18, yy + 16, "one .patch per skill,", c, 13, fill=c["muted"]))
    b.append(text(cols[1] + 18, yy + 34, "each opens with a Why: line", c, 13, fill=c["muted"]))
    b.append(text(cols[1] + 18, yy + 60, "Why: generic model tiers", c, 12, "mono", c["patched"]))
    b.append(text(cols[1] + 18, yy + 78, "Why: typed-only /pfd", c, 12, "mono", c["patched"]))
    b.append(text(cols[1] + 18, yy + 96, "Why: no curl | sudo sh", c, 12, "mono", c["patched"]))
    b.append(card(cols[1], y + 4 * 74 + 8 - 12 + 12, W, 62, c, stroke=c["add"]))
    b.append(text(cols[1] + 18, y + 4 * 74 + 42, "git apply", c, 15, "mono", c["add"], 600))
    b.append(text(cols[1] + 18, y + 4 * 74 + 62, "fails loudly if upstream moved", c, 13, fill=c["muted"]))
    # 3 build
    y = 72
    cmds = [("build", "pins + patches → dist/"), ("verify", "diff vs installed"), ("diff", "your edit → .patch"),
            ("bump", "move a pin, re-check"), ("install", "symlink dist/")]
    b.append(card(cols[2], y, W, 370, c, stroke=c["ink"]))
    b.append(text(cols[2] + 18, y + 32, "uv run build.py", c, 15, "mono", c["ink"], 700))
    b.append(text(cols[2] + 18, y + 54, "typer · pydantic · rich", c, 12, "mono", c["muted"]))
    yy = y + 92
    for cmd, desc in cmds:
        b.append(card(cols[2] + 14, yy - 20, W - 28, 50, c, fill=c["bg"], r=8))
        b.append(text(cols[2] + 28, yy, cmd, c, 14, "mono", c["derived"], 600))
        b.append(text(cols[2] + 28, yy + 20, desc, c, 12.5, fill=c["muted"]))
        yy += 58
    # 4 install
    y = 72
    b.append(card(cols[3], y, W, 62, c, stroke=c["add"]))
    b.append(text(cols[3] + 18, y + 26, "dist/", c, 15, "mono", c["add"], 600))
    b.append(text(cols[3] + 18, y + 47, f"{n_skills} skills, gitignored", c, 13, fill=c["muted"]))
    targets = [("~/.agents/skills", "Codex · Kimi Code", 170), ("~/.claude/skills", "Claude Code · Grok", 290)]
    for d, who, ty in targets:
        b.append(card(cols[3], y + ty - 50, W, 74, c))
        b.append(text(cols[3] + 18, y + ty - 22, d, c, 14, "mono", weight=600))
        b.append(text(cols[3] + 18, y + ty, who, c, 13, fill=c["muted"]))
    b.append(text(cols[3] + 18, y + 362, "Claude/Grok link into", c, 12, fill=c["muted"]))
    b.append(text(cols[3] + 18, y + 380, "~/.agents, one source", c, 12, "mono", c["muted"]))
    # connectors
    def arrow(x1, y1, x2, y2):
        return f'<path class="flow" d="M{x1},{y1} C{(x1 + x2) / 2},{y1} {(x1 + x2) / 2},{y2} {x2},{y2}" fill="none" stroke="{c["muted"]}" stroke-width="1.6" marker-end="url(#arrow)"/>'
    for i in range(4):
        b.append(arrow(cols[0] + W, 103 + i * 74, cols[1] - 4, 210))
    b.append(arrow(cols[0] + W, 72 + 4 * 74 + 39, cols[1] - 4, 72 + 4 * 74 + 39))
    b.append(arrow(cols[1] + W, 210, cols[2] - 4, 257))
    b.append(arrow(cols[1] + W, 72 + 4 * 74 + 39, cols[2] - 4, 257))
    b.append(arrow(cols[2] + W, 257, cols[3] - 4, 103))
    b.append(f'<path class="flow" d="M{cols[3] + 40},{72 + 62} L{cols[3] + 40},{72 + 120 - 2}" stroke="{c["muted"]}" stroke-width="1.6" marker-end="url(#arrow)"/>')
    b.append(f'<path class="flow" d="M{cols[3] + 40},{72 + 194} L{cols[3] + 40},{72 + 240 - 2}" stroke="{c["muted"]}" stroke-width="1.6" marker-end="url(#arrow)"/>')
    return svg(1200, 480, "Build pipeline: pin upstreams, apply patches, build dist, install for four CLIs", "\n".join(b), c)


# ---------- skill map ----------

def skill_map(c: dict, info: dict[str, dict]) -> str:
    b = []
    cols = [40, 330, 620, 910]
    W = 250
    tallest = 0
    for x, (group, names) in zip(cols, GROUPS.items()):
        b.append(text(x, 52, group, c, 17, weight=700))
        b.append(text(x + W, 52, str(len(names)), c, 13, "mono", c["muted"], anchor="end"))
        b.append(f'<line x1="{x}" y1="66" x2="{x + W}" y2="66" stroke="{c["line"]}"/>')
        y = 82
        for n in names:
            i = info[n]
            col = c[i["kind"]]
            label = ("/" if i["typed"] else "") + n
            b.append(card(x, y, W, 32, c, r=16))
            b.append(f'<circle cx="{x + 18}" cy="{y + 16}" r="5" fill="{col}"/>')
            b.append(text(x + 34, y + 21, label, c, 13, "mono"))
            y += 40
        tallest = max(tallest, y)
    ly = tallest + 30
    b.append(f'<line x1="40" y1="{ly - 14}" x2="1160" y2="{ly - 14}" stroke="{c["line"]}"/>')
    x = 40
    for kind in ("own", "derived", "patched"):
        n = sum(1 for i in info.values() if i["kind"] == kind)
        b.append(f'<circle cx="{x + 6}" cy="{ly + 12}" r="5" fill="{c[kind]}"/>')
        label = f"{KIND_LABEL[kind]} ({n})"
        b.append(text(x + 20, ly + 17, label, c, 13, "mono", c["muted"]))
        x += 20 + len(label) * 7.9 + 36
    b.append(text(1160, ly + 17, "/name = typed-only command", c, 13, "mono", c["muted"], anchor="end"))
    return svg(1200, ly + 44, "Skill map: 24 skills grouped by job, colored by source", "\n".join(b), c)


def main() -> None:
    info = skills_data()
    OUT.mkdir(parents=True, exist_ok=True)
    n_own = sum(1 for i in info.values() if i["kind"] != "patched")
    for theme, c in THEMES.items():
        (OUT / f"hero-{theme}.svg").write_text(hero(c, len(info), len(list((ROOT / "patches").glob("*/*.patch"))),
                                                        len(tomllib.loads((ROOT / "upstreams.toml").read_text()))))
        (OUT / f"pipeline-{theme}.svg").write_text(pipeline(c, len(info), n_own))
        (OUT / f"skills-{theme}.svg").write_text(skill_map(c, info))
    print(f"wrote {len(list(OUT.glob('*.svg')))} SVGs to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
