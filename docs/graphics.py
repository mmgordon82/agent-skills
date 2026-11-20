#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Render the README graphics (light + dark) into docs/assets/ and the README's generated agent blocks.
Reads upstreams.toml, skills/, patches/, dist/ and the agent registry (skills/skill-critique/agents.toml)."""

from __future__ import annotations

import re
import sys
import tomllib
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets"

THEMES = {
    "light": dict(bg="#ffffff", panel="#f6f8fa", line="#d1d9e0", ink="#1f2328", muted="#59636e", grid="#e6eaef",
                  own="#8250df", derived="#0969da", patched="#9a6700", add="#1a7f37", add_bg="#dafbe1",
                  rm="#cf222e", rm_bg="#ffebe9", hunk="#0969da", broth="#f1e3c2", flame="#d1600a"),
    "dark": dict(bg="#0d1117", panel="#151b23", line="#30363d", ink="#e6edf3", muted="#9198a1", grid="#1c232c",
                 own="#bc8cff", derived="#58a6ff", patched="#e3b341", add="#3fb950", add_bg="#12261e",
                 rm="#f85149", rm_bg="#2d1215", hunk="#58a6ff", broth="#3b2f17", flame="#f0883e"),
}

# Skill map: one list per column, each a list of (group, skills).
COLUMNS = [
    [("Workflow", ["poteto-mode", "delegate", "swarm", "arena", "architect", "reflect", "setup-pstack",
                   "adversarial-review"])],
    [("Agent setup", ["run-validation", "agent-workdir", "handoff", "skill-critique"]),
     ("Design & UI", ["impeccable", "design-taste-frontend", "pfd"])],
    [("Ship & secure", ["ship-audit", "security-hunt", "web-perimeter-audit", "db-migrations",
                        "git-guardrails-claude-code", "docker-packaging", "airgap"])],
    [("Writing", ["unslop", "technical-writing", "no-comments", "writing-for-agents"])],
]
# Where the forks in skills/ came from (they carry their own LICENSE).
FORKS = {"pbakaus/impeccable": ["impeccable"],
         "affaan-m/everything-claude-code": ["db-migrations", "security-hunt", "ship-audit", "web-perimeter-audit"]}
sys.path.insert(0, str(ROOT / "skills" / "skill-critique" / "scripts"))
from agents import load_agents  # noqa: E402

# The docs name only the verified agents (shipped, never the user's own), so they read the same on
# every machine and don't change when the npx part of the registry grows.
AGENTS = [a for a in load_agents(user=False) if a.verified]
LABELS = [a.label for a in AGENTS]


def fit(labels: list[str], max_chars: int, sep: str = " · ") -> str:
    """As many labels as fit in max_chars, then "+N more", so the graphics survive a long agent list."""
    out = []
    for i, label in enumerate(labels):
        rest = len(labels) - i - 1
        candidate = sep.join(out + [label]) + (f"{sep}+{rest} more" if rest else "")
        if len(candidate) > max_chars and out:
            return sep.join(out) + f"{sep}+{len(labels) - i} more"
        out.append(label)
    return sep.join(out)


def joined(labels: list[str]) -> str:
    return ", ".join(labels[:-1]) + f" and {labels[-1]}" if len(labels) > 1 else "".join(labels)
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
  @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; transform: none !important; }} }}
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


def curve(x1, y1, x2, y2, c, vertical=False):
    if vertical:
        mid = (y1 + y2) / 2
        d = f"M{x1},{y1} C{x1},{mid} {x2},{mid} {x2},{y2}"
    else:
        mid = (x1 + x2) / 2
        d = f"M{x1},{y1} C{mid},{y1} {mid},{y2} {x2},{y2}"
    return f'<path class="flow" d="{d}" fill="none" stroke="{c["muted"]}" stroke-width="1.6" marker-end="url(#arrow)"/>'


# ---------- data ----------

def upstreams() -> dict:
    return tomllib.loads((ROOT / "upstreams.toml").read_text())


def skills_data() -> dict[str, dict]:
    info: dict[str, dict] = {}
    for name, u in upstreams().items():
        for dest in u["paths"]:
            info[dest.split("/")[0]] = dict(kind="patched", source=u["repo"])
    for d in (ROOT / "skills").iterdir():
        if d.is_dir():
            info[d.name] = dict(kind="derived" if (d / "LICENSE").exists() else "own", source="skills/")
    for name, i in info.items():
        md = ROOT / "dist" / name / "SKILL.md"
        if not md.exists():
            raise SystemExit(f"dist/{name} missing; run `uv run build.py build` first")
        i["typed"] = bool(re.search(r"^disable-model-invocation:\s*true", md.read_text(), re.M))
    placed = {s for col in COLUMNS for _, names in col for s in names}
    if placed != set(info):
        raise SystemExit(f"COLUMNS out of sync: missing {set(info) - placed}, unknown {placed - set(info)}")
    forks = {s for names in FORKS.values() for s in names}
    derived = {s for s, i in info.items() if i["kind"] == "derived"}
    if forks != derived:
        raise SystemExit(f"FORKS out of sync: missing {derived - forks}, unknown {forks - derived}")
    return info


# ---------- hero ----------

def hero(c: dict) -> str:
    patch = (ROOT / "patches" / "taste-skill" / "design-taste-frontend.patch").read_text().splitlines()
    start = patch.index("-description: >-")
    removed = []
    for line in patch[start:]:
        if not line.startswith("-"):
            break
        removed.append(line)
    saved = sum(len(l) - 1 for l in removed) // 4

    b = []
    b.append(text(64, 76, "CROSS-AGENT SKILL SET  ·  " + fit([l.upper() for l in LABELS], 60, "  ·  "), c, 12, "mono", c["muted"], 600, extra='letter-spacing="1.2"'))
    b.append(text(60, 150, "agent-skills", c, 64, weight=700, extra='letter-spacing="-1.5"'))
    b.append(text(64, 190, "One opinionated skill set for every coding agent.", c, 20, fill=c["muted"]))
    facts = [
        ("own", "Cross-agent", "One copy on disk and one layout for every coding agent."),
        ("add", "Token-lean", "174 skills cut: ~11k fewer tokens of skill listings."),
        ("patched", "Opinionated", "Tailored to me. Every patch says why."),
    ]
    y = 248
    for color, label, detail in facts:
        b.append(f'<rect x="64" y="{y - 15}" width="4" height="40" rx="2" fill="{c[color]}"/>')
        b.append(text(84, y, label, c, 17, weight=700))
        b.append(text(84, y + 22, detail, c, 15, fill=c["muted"]))
        y += 60

    X, Y, W = 650, 48, 500
    rows = [
        ("why", "Why: typed-only, short description."),
        ("hunk", "@@ design-taste-frontend/SKILL.md @@"),
        ("ctx", " name: design-taste-frontend"),
        ("rm", removed[0]),
        ("rm", removed[1][:50] + "…"),
        ("note", f"   ⋯ {len(removed) - 2} more removed lines"),
        ("add", "+description: Taste-skill website builder (comp…"),
        ("add", "+disable-model-invocation: true"),
    ]
    H = 56 + len(rows) * 28 + 52
    b.append(card(X, Y, W, H, c, r=12))
    b.append(f'<line x1="{X}" y1="{Y + 44}" x2="{X + W}" y2="{Y + 44}" stroke="{c["line"]}"/>')
    b.append(text(X + 20, Y + 28, "patches/taste-skill/…frontend.patch", c, 13, "mono", c["ink"], 600))
    b.append(card(X + W - 104, Y + 12, 88, 22, c, stroke=c["add"], fill=c["add_bg"], r=11)
             + text(X + W - 60, Y + 27, "applies ✓", c, 12, "mono", c["add"], 600, "middle"))
    y = Y + 56
    for kind, s in rows:
        if kind in ("rm", "add"):
            b.append(f'<rect x="{X + 1}" y="{y}" width="{W - 2}" height="28" fill="{c[kind + "_bg"]}"/>')
        col = {"why": c["patched"], "hunk": c["hunk"], "ctx": c["muted"], "note": c["muted"], "rm": c["rm"], "add": c["add"]}[kind]
        b.append(text(X + 20, y + 19, s, c, 13, "mono", col, 600 if kind == "why" else 400,
                      extra='font-style="italic"' if kind == "note" else ""))
        y += 28
    b.append(f'<line x1="{X}" y1="{y + 8}" x2="{X + W}" y2="{y + 8}" stroke="{c["line"]}"/>')
    b.append(text(X + 20, y + 34, "pinned  Leonxlnx/taste-skill @ f6b7657", c, 12, "mono", c["muted"]))
    b.append(text(X + W - 20, y + 34, f"−{saved} tokens / session", c, 12, "mono", c["add"], 600, anchor="end"))
    return svg(1200, 440, f"agent-skills: one opinionated, token-lean skill set shared by {joined(LABELS)}",
               "\n".join(b), c)


# ---------- cooking pot ----------

def chip(cx, cy, rot, owner, repo, sub, color, c, delay):
    w = max(len(owner) * 7.2, len(repo) * 8.6, len(sub) * 7.2) + 52
    x, y = -w / 2, -32
    return (f'<g transform="translate({cx},{cy}) rotate({rot})"><g class="bob" style="animation-delay:{delay}s">'
            + card(x, y, w, 64, c, stroke=color, r=12)
            + f'<circle cx="{x + 20}" cy="0" r="6" fill="{color}"/>'
            + text(x + 36, y + 20, owner, c, 12, "mono", c["muted"])
            + text(x + 36, y + 39, repo, c, 15, weight=700)
            + text(x + 36, y + 55, sub, c, 12, "mono", color)
            + "</g></g>")


def pot(c: dict, info: dict) -> str:
    ups = upstreams()
    own = sorted(s for s, i in info.items() if i["kind"] == "own")
    ingredients = []
    for name, u in ups.items():
        owner, repo = u["repo"].split("/")
        n = len({d.split("/")[0] for d in u["paths"]})
        ingredients.append((owner + "/", repo, f"{n} skill{'s' * (n > 1)}, patched", c["patched"]))
    for repo_full, names in FORKS.items():
        owner, repo = repo_full.split("/")
        ingredients.append((owner + "/", repo, f"{len(names)} fork{'s' * (len(names) > 1)}", c["derived"]))
    ingredients.append(("mine/", "own skills", f"{len(own)} skills", c["own"]))
    # (cx, cy, rotation) for each ingredient, in the order above: four pinned upstreams, two fork sources, own.
    spots = [(170, 82, -5), (455, 70, 4), (750, 78, -3), (1035, 86, 6), (210, 214, 4), (990, 216, -5), (600, 206, -2)]
    if len(spots) != len(ingredients):
        raise SystemExit(f"pot(): {len(ingredients)} ingredients but {len(spots)} spots; add a spot")

    b = []
    mouth = [460, 530, 670, 750, 430, 770, 600]  # pot-mouth x for each spot
    for (cx, cy, _), tx in zip(spots, mouth):
        mid = (cy + 34 + 318) / 2
        b.append(f'<path class="flow" d="M{cx},{cy + 34} C{cx},{mid} {tx},{mid} {tx},{318}" fill="none" '
                 f'stroke="{c["muted"]}" stroke-width="1.4" opacity="0.7"/>')
    for (owner, repo, sub, color), (cx, cy, rot), i in zip(ingredients, spots, range(99)):
        b.append(chip(cx, cy, rot, owner, repo, sub, color, c, i * 0.4))

    # pot
    b.append(f'<path d="M372,330 L384,452 Q388,494 430,494 L770,494 Q812,494 816,452 L828,330 Z" fill="{c["panel"]}" stroke="{c["ink"]}" stroke-width="2"/>')
    for hx in (338, 826):
        b.append(f'<rect x="{hx}" y="350" width="36" height="22" rx="11" fill="{c["panel"]}" stroke="{c["ink"]}" stroke-width="2"/>')
    b.append(f'<ellipse cx="600" cy="330" rx="236" ry="32" fill="{c["panel"]}" stroke="{c["ink"]}" stroke-width="2"/>')
    b.append(f'<ellipse cx="600" cy="333" rx="216" ry="22" fill="{c["broth"]}"/>')
    for i, (bx, br) in enumerate([(470, 6), (540, 4), (610, 7), (680, 5), (735, 4)]):
        b.append(f'<circle class="bubble" style="animation-delay:{i * 0.5}s" cx="{bx}" cy="{333 + (i % 2) * 6}" r="{br}" fill="none" stroke="{c["patched"]}" stroke-width="1.4"/>')
    b.append(text(600, 418, "agent-skills", c, 30, "mono", c["ink"], 700, "middle"))
    b.append(text(600, 446, "build.py: pin · patch · build", c, 13, "mono", c["muted"], anchor="middle"))
    for i, fx in enumerate(range(480, 740, 40)):
        b.append(f'<path class="flame" style="animation-delay:{i * 0.15}s" d="M{fx},532 q-9,-12 0,-26 q9,14 0,26 z" fill="{c["flame"]}"/>')
    b.append(f'<line x1="440" y1="536" x2="760" y2="536" stroke="{c["line"]}" stroke-width="3" stroke-linecap="round"/>')

    # recipe + serves
    b.append(card(40, 388, 280, 112, c))
    b.append(text(60, 416, "RECIPE", c, 12, "mono", c["muted"], 600, extra='letter-spacing="1.5"'))
    b.append(text(60, 442, "upstreams.toml", c, 15, "mono", c["patched"], 700))
    b.append(text(60, 464, "every upstream pinned to a sha,", c, 13, fill=c["muted"]))
    b.append(text(60, 482, "re-checked weekly by CI", c, 13, fill=c["muted"]))
    b.append(card(880, 388, 280, 112, c, stroke=c["add"]))
    b.append(text(900, 416, "SERVES", c, 12, "mono", c["muted"], 600, extra='letter-spacing="1.5"'))
    b.append(text(900, 442, f"{len(info)} skills, one copy", c, 15, weight=700))
    b.append(text(900, 464, " · ".join(LABELS[:3]), c, 13, fill=c["muted"]))
    b.append(text(900, 482, " · ".join(LABELS[3:]) + " and more", c, 13, fill=c["muted"]))
    b.append(curve(320, 444, 380, 420, c))
    b.append(curve(822, 420, 876, 444, c))

    css = (".bob { animation: bob 3.2s ease-in-out infinite; }"
           " @keyframes bob { 50% { transform: translateY(6px); } }"
           "  .bubble { transform-box: fill-box; transform-origin: center; animation: pop 2.5s ease-in-out infinite; }"
           " @keyframes pop { 50% { transform: scale(1.35); } }"
           " .flame { transform-box: fill-box; transform-origin: bottom; animation: flick 0.9s ease-in-out infinite alternate; }"
           " @keyframes flick { to { transform: scaleY(0.75); } }")
    return svg(1200, 560, "What's cooking: pinned upstream skills, forks and my own skills go into one pot "
               f"and come out as one skill set for {joined(LABELS)}", "\n".join(b), c, css)


# ---------- pipeline ----------

def pipeline(c: dict, n_skills: int, n_own: int) -> str:
    ups = upstreams()
    patched = [name for name in ups if any((ROOT / "patches" / name).glob("*.patch"))]
    b = []
    cols = [40, 330, 620, 910]
    W = 250
    for x, (n, t) in zip(cols, [("1", "Pin"), ("2", "Patch"), ("3", "Build"), ("4", "Install")]):
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
    for name in patched:
        b.append(text(cols[1] + 30, yy, f"{name}/", c, 13, "mono"))
        yy += 28
    b.append(f'<line x1="{cols[1] + 18}" y1="{yy - 6}" x2="{cols[1] + W - 18}" y2="{yy - 6}" stroke="{c["line"]}"/>')
    b.append(text(cols[1] + 18, yy + 16, "one .patch per skill,", c, 13, fill=c["muted"]))
    b.append(text(cols[1] + 18, yy + 34, "each opens with a Why: line", c, 13, fill=c["muted"]))
    b.append(text(cols[1] + 18, yy + 60, "Why: model tiers, not vendor ids", c, 12, "mono", c["patched"]))
    b.append(text(cols[1] + 18, yy + 78, "Why: typed-only /pfd", c, 12, "mono", c["patched"]))
    b.append(text(cols[1] + 18, yy + 96, "Why: trigger words first", c, 12, "mono", c["patched"]))
    b.append(card(cols[1], y + 4 * 74 + 8, W, 62, c, stroke=c["add"]))
    b.append(text(cols[1] + 18, y + 4 * 74 + 34, "git apply", c, 15, "mono", c["add"], 600))
    b.append(text(cols[1] + 18, y + 4 * 74 + 55, "fails loudly if upstream moved", c, 13, fill=c["muted"]))
    # 3 build
    y = 72
    cmds = [("build", "pins + patches → dist/"), ("verify", "diff vs installed"), ("diff", "your edit → .patch"),
            ("bump", "move pins, hold back broken"), ("install", "symlink dist/")]
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
    b.append(text(cols[3] + 18, y + 47, f"{n_skills} skills, or a weekly release", c, 13, fill=c["muted"]))
    for d, who, ty in [("npx skills add", "…#release · any agent", 170), ("build.py install", "maintainer: live links to dist/", 290)]:
        b.append(card(cols[3], y + ty - 50, W, 74, c))
        b.append(text(cols[3] + 18, y + ty - 22, d, c, 14, "mono", weight=600))
        b.append(text(cols[3] + 18, y + ty, who, c, 13, fill=c["muted"]))
    b.append(text(cols[3] + 18, y + 362, "one copy in ~/.agents/skills,", c, 12, fill=c["muted"]))
    b.append(text(cols[3] + 18, y + 380, "agents link to it", c, 12, fill=c["muted"]))
    for i in range(len(ups)):
        b.append(curve(cols[0] + W, 103 + i * 74, cols[1] - 4, 210, c))
    b.append(curve(cols[0] + W, 72 + 4 * 74 + 39, cols[1] - 4, 72 + 4 * 74 + 39, c))
    b.append(curve(cols[1] + W, 210, cols[2] - 4, 257, c))
    b.append(curve(cols[1] + W, 72 + 4 * 74 + 39, cols[2] - 4, 257, c))
    b.append(curve(cols[2] + W, 257, cols[3] - 4, 103, c))
    b.append(f'<path class="flow" d="M{cols[3] + 40},{72 + 62} L{cols[3] + 40},{72 + 120 - 2}" stroke="{c["muted"]}" stroke-width="1.6" marker-end="url(#arrow)"/>')
    b.append(f'<path class="flow" d="M{cols[3] + 40},{72 + 194} L{cols[3] + 40},{72 + 240 - 2}" stroke="{c["muted"]}" stroke-width="1.6" marker-end="url(#arrow)"/>')
    return svg(1200, 480, "Build pipeline: pin upstreams, apply patches, build dist, install with npx skills into any agent", "\n".join(b), c)


# ---------- skill map ----------

def skill_map(c: dict, info: dict[str, dict]) -> str:
    b = []
    W = 250
    tallest = 0
    for x, groups in zip([40, 330, 620, 910], COLUMNS):
        y = 52
        for group, names in groups:
            b.append(text(x, y, group, c, 17, weight=700))
            b.append(text(x + W, y, str(len(names)), c, 13, "mono", c["muted"], anchor="end"))
            b.append(f'<line x1="{x}" y1="{y + 14}" x2="{x + W}" y2="{y + 14}" stroke="{c["line"]}"/>')
            y += 30
            for n in names:
                i = info[n]
                b.append(card(x, y, W, 32, c, r=16))
                b.append(f'<circle cx="{x + 18}" cy="{y + 16}" r="5" fill="{c[i["kind"]]}"/>')
                b.append(text(x + 34, y + 21, ("/" if i["typed"] else "") + n, c, 13, "mono"))
                y += 40
            y += 34
        tallest = max(tallest, y - 34)
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
    return svg(1200, ly + 44, f"Skill map: {len(info)} skills grouped by job, colored by source", "\n".join(b), c)


# ---------- README blocks ----------

def update_readme() -> None:
    path = ROOT / "README.md"
    text = path.read_text()
    blocks = {"agents:list": joined(LABELS)}
    for key, value in blocks.items():
        pattern = re.compile(rf"(<!-- {key} -->)(.*?)(<!-- /{key} -->)", re.S)
        if not pattern.search(text):
            raise SystemExit(f"README.md has no <!-- {key} --> block")
        text = pattern.sub(lambda m: m.group(1) + value + m.group(3), text)
    path.write_text(text)


def main() -> None:
    info = skills_data()
    OUT.mkdir(parents=True, exist_ok=True)
    n_own = sum(1 for i in info.values() if i["kind"] != "patched")
    for theme, c in THEMES.items():
        (OUT / f"hero-{theme}.svg").write_text(hero(c))
        (OUT / f"pot-{theme}.svg").write_text(pot(c, info))
        (OUT / f"pipeline-{theme}.svg").write_text(pipeline(c, len(info), n_own))
        (OUT / f"skills-{theme}.svg").write_text(skill_map(c, info))
    print(f"wrote {len(list(OUT.glob('*.svg')))} SVGs to {OUT.relative_to(ROOT)}")
    update_readme()
    print("updated README.md agent blocks")


if __name__ == "__main__":
    main()
