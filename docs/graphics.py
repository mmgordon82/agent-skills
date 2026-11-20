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
# An entry ending in "*" is one card for every skill with that prefix.
COLUMNS = [
    [("Workflow", ["poteto-mode", "delegate", "swarm", "arena", "architect", "reflect", "setup-pstack",
                   "adversarial-review"]),
     ("Agent setup", ["run-validation", "agent-workdir", "handoff", "skill-critique"])],
    [("Used by /poteto-mode", ["principle-*", "why", "how", "interrogate", "figure-it-out", "show-me-your-work",
                               "tdd", "ketchup", "benchmark-checklist", "create-*"]),
     ("Design & UI", ["impeccable", "design-taste-frontend", "pfd"])],
    [("Ship & secure", ["ship-audit", "security-hunt", "web-perimeter-audit", "db-migrations",
                        "git-guardrails-claude-code", "docker-packaging", "airgap"]),
     ("Writing", ["unslop", "technical-writing", "no-comments", "writing-for-agents"])],
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
KIND_LABEL = {"own": "own", "derived": "fork + LICENSE", "patched": "pinned upstream"}

CANVAS = 920  # README shows graphics at ~830px, so 14 units render at ~12.6px
MIN_FONT = 14
MONO_W = 0.6  # average glyph width / font size, for layout estimates


def tw(s: str, size: float, mono: bool = False, bold: bool = False) -> float:
    """Estimated rendered width of s."""
    return len(s) * size * (MONO_W if mono else 0.53 if bold else 0.5)


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
  @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
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
    return text(x, y, f"{num}  {label.upper()}", c, 14, "mono", c["muted"], 600, extra='letter-spacing="1.5"')


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
    placed = [s for col in COLUMNS for _, entries in col for e in entries
              for s in (sorted(n for n in info if n.startswith(e[:-1])) if e.endswith("*") else [e])]
    twice = {s for s in placed if placed.count(s) > 1}
    if set(placed) != set(info) or twice:
        raise SystemExit(f"COLUMNS out of sync: missing {set(info) - set(placed)}, unknown {set(placed) - set(info)}, "
                         f"placed twice {twice}")
    forks = {s for names in FORKS.values() for s in names}
    derived = {s for s, i in info.items() if i["kind"] == "derived"}
    if forks != derived:
        raise SystemExit(f"FORKS out of sync: missing {derived - forks}, unknown {forks - derived}")
    return info


# ---------- hero ----------

# Brand marks from Simple Icons (CC0 path data, saved in docs/icons/ with their source line). Agents
# without one get a monogram tile; never a hand-drawn imitation of a real logo.
ICONS = {"claude-code": "claude", "kimi-code-cli": "kimi", "pi": "pi"}


def agent_tile(cx: float, cy: float, agent, c: dict) -> str:
    out = card(cx - 22, cy - 22, 44, 44, c, r=11)
    if agent.id in ICONS:
        d = re.search(r' d="([^"]+)"', (ROOT / "docs" / "icons" / f"{ICONS[agent.id]}.svg").read_text()).group(1)
        out += f'<path transform="translate({cx - 12},{cy - 12})" d="{d}" fill="{c["ink"]}"/>'
    else:
        out += text(cx, cy + 7, agent.label[0], c, 20, weight=700, anchor="middle")
    return out + text(cx, cy + 40, agent.label, c, 14, fill=c["muted"], anchor="middle")


def hero(c: dict, n_skills: int) -> str:
    H, PITCH = 400, 72
    mid = H / 2
    b = []
    b.append(text(40, mid - 14, "agent-skills", c, 52, weight=700, extra='letter-spacing="-1.2"'))
    b.append(text(42, mid + 22, "One opinionated skill set", c, 18, fill=c["muted"]))
    b.append(text(42, mid + 46, "for every coding agent.", c, 18, fill=c["muted"]))

    FX, FW, FH = 480, 112, 84  # shared folder: center x, size
    fx, fy = FX - FW / 2, mid - FH / 2 - 14
    b.append(f'<path d="M{fx},{fy + 10} q0,-10 10,-10 h30 l10,12 h{FW - 60} q10,0 10,10 v{FH - 22} q0,10 -10,10 '
             f'h{-(FW - 20)} q-10,0 -10,-10 z" fill="{c["panel"]}" stroke="{c["ink"]}" stroke-width="2"/>')
    b.append(f'<line x1="{fx}" y1="{fy + 26}" x2="{fx + FW}" y2="{fy + 26}" stroke="{c["line"]}" stroke-width="2"/>')
    b.append(text(FX, fy + 62, "SKILL.md ×" + str(n_skills), c, 14, "mono", c["muted"], anchor="middle"))
    b.append(text(FX, fy + FH + 30, "~/.agents/skills", c, 15, "mono", c["ink"], 600, "middle"))
    b.append(text(FX, fy + FH + 52, "one copy", c, 14, fill=c["muted"], anchor="middle"))

    AX = CANVAS - 110
    ys = [mid - 14 + (k - (len(AGENTS) - 1) / 2) * PITCH for k in range(len(AGENTS))]
    for y in ys:
        b.append(curve(FX + FW / 2 + 4, mid - 14, AX - 30, y, c))
    for agent, y in zip(AGENTS, ys):
        b.append(agent_tile(AX, y, agent, c))
    return svg(CANVAS, H, f"agent-skills: one opinionated skill set in one folder, ~/.agents/skills, shared by {joined(LABELS)}",
               "\n".join(b), c)


# ---------- cooking pot ----------

def chip_width(owner: str, repo: str, sub: str) -> float:
    return max(tw(owner, 14, mono=True), tw(repo, 15, bold=True), tw(sub, 14, mono=True)) + 52


def chip(cx, cy, rot, owner, repo, sub, color, c, delay):
    w = chip_width(owner, repo, sub)
    x, y = -w / 2, -34
    return (f'<g transform="translate({cx:.0f},{cy}) rotate({rot})"><g class="bob" style="animation-delay:{delay}s">'
            + card(x, y, w, 68, c, stroke=color, r=12)
            + f'<circle cx="{x + 20}" cy="0" r="6" fill="{color}"/>'
            + text(x + 36, y + 20, owner, c, 14, "mono", c["muted"])
            + text(x + 36, y + 41, repo, c, 15, weight=700)
            + text(x + 36, y + 60, sub, c, 14, "mono", color)
            + "</g></g>")


def spread(widths: list[float]) -> list[float]:
    """Centers for chips of these widths, spread edge to edge across the canvas."""
    span = CANVAS - 80
    if sum(widths) > span:
        raise SystemExit(f"pot(): a chip row is {sum(widths):.0f} wide, more than {span}; shorten labels or add a row")
    gap = (span - sum(widths)) / max(len(widths) - 1, 1)
    xs, x = [], 40.0
    for w in widths:
        xs.append(x + w / 2)
        x += w + gap
    return xs


def pot(c: dict, info: dict) -> str:
    ups = upstreams()
    own = sorted(s for s, i in info.items() if i["kind"] == "own")
    plural = lambda n, word: f"{n} {word}{'s' * (n != 1)}"
    top = []
    for name, u in ups.items():
        owner, repo = u["repo"].split("/")
        top.append((owner + "/", repo, plural(len({d.split("/")[0] for d in u["paths"]}), "skill"), c["patched"]))
    forks = [(f.split("/")[0] + "/", f.split("/")[1], plural(len(n), "skill") + ", forked", c["derived"])
             for f, n in FORKS.items()]
    bottom = forks[:1] + [("mine/", "own skills", plural(len(own), "skill"), c["own"])] + forks[1:]
    top_x = spread([chip_width(*ing[:3]) for ing in top])
    if len(bottom) != len(top) - 1:
        raise SystemExit(f"pot(): {len(bottom)} lower chips need {len(bottom) + 1} upstreams above them to sit between")
    # Each lower chip sits in a gap between two upper chips, so the upper chips' lines fall past it.
    # The widest lower chip takes the widest gap.
    gaps = sorted(zip(top_x, top_x[1:]), key=lambda g: g[1] - g[0])
    bottom = sorted(bottom, key=lambda ing: chip_width(*ing[:3]))
    for ing, (a, z) in zip(bottom, gaps):
        if chip_width(*ing[:3]) > z - a - 16:
            raise SystemExit(f"pot(): {ing[1]} is too wide for the gap between the upstream chips above it")
    bottom_x = [(a + z) / 2 for a, z in gaps]
    placed = ([(x, 64, r, ing) for x, r, ing in zip(top_x, [-3, 2, -2, 3], top)]
              + [(x, 164, r, ing) for x, r, ing in zip(bottom_x, [2, -2, -3], bottom)])

    b = []
    PX, MY = 280, 270  # pot center x, mouth y
    mouths = [PX - 140 + 280 * k / max(len(placed) - 1, 1) for k in range(len(placed))]
    for (cx, cy, _, _), tx in zip(sorted(placed, key=lambda p: p[0]), mouths):
        mid = (cy + 36 + MY) / 2
        b.append(f'<path class="flow" d="M{cx:.0f},{cy + 36} C{cx:.0f},{mid} {tx:.0f},{mid} {tx:.0f},{MY - 4}" fill="none" '
                 f'stroke="{c["muted"]}" stroke-width="1.4" opacity="0.7"/>')
    for k, (cx, cy, rot, (owner, repo, sub, color)) in enumerate(placed):
        b.append(chip(cx, cy, rot, owner, repo, sub, color, c, k * 0.4))

    b.append(f'<path d="M{PX - 180},{MY} L{PX - 170},{MY + 100} Q{PX - 166},{MY + 136} {PX - 130},{MY + 136} '
             f'L{PX + 130},{MY + 136} Q{PX + 166},{MY + 136} {PX + 170},{MY + 100} L{PX + 180},{MY} Z" '
             f'fill="{c["panel"]}" stroke="{c["ink"]}" stroke-width="2"/>')
    for hx in (PX - 210, PX + 176):
        b.append(f'<rect x="{hx}" y="{MY + 16}" width="34" height="20" rx="10" fill="{c["panel"]}" stroke="{c["ink"]}" stroke-width="2"/>')
    b.append(f'<ellipse cx="{PX}" cy="{MY}" rx="190" ry="26" fill="{c["panel"]}" stroke="{c["ink"]}" stroke-width="2"/>')
    b.append(f'<ellipse cx="{PX}" cy="{MY + 3}" rx="172" ry="17" fill="{c["broth"]}"/>')
    for i, (dx, br) in enumerate([(-110, 6), (-50, 4), (10, 7), (70, 5), (120, 4)]):
        b.append(f'<circle class="bubble" style="animation-delay:{i * 0.5}s" cx="{PX + dx}" cy="{MY + 3 + (i % 2) * 5}" '
                 f'r="{br}" fill="none" stroke="{c["patched"]}" stroke-width="1.4"/>')
    b.append(text(PX, MY + 78, "agent-skills", c, 28, "mono", c["ink"], 700, "middle"))
    b.append(text(PX, MY + 106, "build.py: pin · patch · build", c, 14, "mono", c["muted"], anchor="middle"))
    for i, fx in enumerate(range(PX - 110, PX + 111, 37)):
        b.append(f'<path class="flame" style="animation-delay:{i * 0.15}s" d="M{fx},{MY + 174} q-9,-12 0,-26 q9,14 0,26 z" fill="{c["flame"]}"/>')
    b.append(f'<line x1="{PX - 150}" y1="{MY + 178}" x2="{PX + 150}" y2="{MY + 178}" stroke="{c["line"]}" stroke-width="3" stroke-linecap="round"/>')

    RX, RW = 560, CANVAS - 600
    b.append(card(RX, MY - 14, RW, 96, c))
    b.append(text(RX + 20, MY + 12, "RECIPE", c, 14, "mono", c["muted"], 600, extra='letter-spacing="1.5"'))
    b.append(text(RX + 20, MY + 38, "upstreams.toml", c, 16, "mono", c["patched"], 700))
    b.append(text(RX + 20, MY + 62, "pinned to a sha, re-checked weekly", c, 14, fill=c["muted"]))
    b.append(card(RX, MY + 102, RW, 112, c, stroke=c["add"]))
    b.append(text(RX + 20, MY + 128, "SERVES", c, 14, "mono", c["muted"], 600, extra='letter-spacing="1.5"'))
    b.append(text(RX + 20, MY + 154, f"{len(info)} skills, one copy", c, 17, weight=700))
    b.append(text(RX + 20, MY + 178, " · ".join(LABELS[:3]), c, 14, fill=c["muted"]))
    b.append(text(RX + 20, MY + 198, " · ".join(LABELS[3:]) + " and more", c, 14, fill=c["muted"]))
    b.append(curve(RX - 2, MY + 34, PX + 214, MY + 26, c))
    b.append(curve(PX + 172, MY + 92, RX - 4, MY + 158, c))

    css = (".bob { animation: bob 3.2s ease-in-out infinite; }"
           " @keyframes bob { 50% { transform: translateY(6px); } }"
           "  .bubble { transform-box: fill-box; transform-origin: center; animation: pop 2.5s ease-in-out infinite; }"
           " @keyframes pop { 50% { transform: scale(1.35); } }"
           " .flame { transform-box: fill-box; transform-origin: bottom; animation: flick 0.9s ease-in-out infinite alternate; }"
           " @keyframes flick { to { transform: scaleY(0.75); } }")
    return svg(CANVAS, MY + 236, "What's cooking: pinned upstream skills, forks and my own skills go into one pot "
               f"and come out as one skill set for {joined(LABELS)}", "\n".join(b), c, css)


# ---------- settings map ----------

# Which skills read each settings section. graphics.py fails if settings.example.toml gains a
# section that isn't listed here.
SETTINGS_READERS = {
    "workdir": ["agent-workdir", "handoff", "adversarial-review", "skill-critique"],
    "handoff": ["handoff"],
    "review": ["adversarial-review"],
    "offline": ["airgap"],
    "validation": ["run-validation"],
    "agents.<id>": ["skill-critique"],
    "<your-skill>": ["your own skills"],
}


def keys_line(keys: list[str], width: float, size: int) -> str:
    """Whole keys that fit in width, then ", …"; never cuts a key in half."""
    out = []
    for k in keys:
        if tw(", ".join(out + [k, "…"]), size, mono=True) > width:
            return ", ".join(out + ["…"])
        out.append(k)
    return ", ".join(out)


def settings_map(c: dict) -> str:
    example = tomllib.loads((ROOT / "settings.example.toml").read_text())
    sections = [(name, list(keys)) for name, keys in example.items()]
    sections += [("agents.<id>", ["label", "home", "skills", "checks"]), ("<your-skill>", ["anything your skill reads"])]
    if missing := {s for s, _ in sections} - set(SETTINGS_READERS):
        raise SystemExit(f"SETTINGS_READERS has no entry for: {', '.join(sorted(missing))}")
    readers = list(dict.fromkeys(r for s, _ in sections for r in SETTINGS_READERS[s]))
    b = []
    X, Y, W, ROW = 40, 84, 400, 56
    b.append(text(X, 48, "~/.config/agent-skills/settings.toml", c, 15, "mono", c["muted"], 600))
    H = 24 + ROW * len(sections)
    b.append(card(X, Y - 14, W, H, c, r=12))
    row_y = {}
    for i, (name, keys) in enumerate(sections):
        y = Y + 14 + i * ROW
        row_y[name] = y + 6
        own = name.startswith("<") or name.startswith("agents")
        b.append(text(X + 20, y + 4, f"[{name}]", c, 15, "mono", c["own"] if own else c["patched"], 600))
        b.append(text(X + 20, y + 26, keys_line(keys, W - 40, 14), c, 14, "mono", c["muted"]))
    RX, RW = 600, CANVAS - 640
    step = (H - 40) / max(len(readers) - 1, 1)
    reader_y = {}
    for i, r in enumerate(readers):
        y = Y + 6 + i * step
        reader_y[r] = y
        mine = r == "your own skills"
        b.append(card(RX, y - 17, RW, 34, c, stroke=c["own"] if mine else c["line"], r=17))
        b.append(f'<circle cx="{RX + 18}" cy="{y}" r="5" fill="{c["own"]}"/>')
        b.append(text(RX + 34, y + 5, r, c, 15, "mono", c["ink"], 600 if mine else 400))
    for name, _ in sections:
        for r in SETTINGS_READERS[name]:
            y1, y2 = row_y[name], reader_y[r]
            b.append(f'<path class="flow" d="M{X + W},{y1} C{X + W + 80},{y1} {RX - 80},{y2:.0f} {RX - 6},{y2:.0f}" fill="none" '
                     f'stroke="{c["muted"]}" stroke-width="1.3" opacity="0.75" marker-end="url(#arrow)"/>')
    by = Y - 14 + H + 36
    b.append(text(X, by, "No file or no key: the default. A broken value: the default, and a warning.", c, 14, fill=c["muted"]))
    return svg(CANVAS, by + 28, "settings.toml: each section and the skills that read it", "\n".join(b), c)


# ---------- pipeline ----------

def pipeline(c: dict, n_skills: int, n_own: int) -> str:
    """Four steps in a U: Pin → Patch (top row), then down to Build and back left to Install."""
    ups = upstreams()
    L, R, CW = 40, 480, 400
    b = []
    # 1 pin
    T1 = 72
    b.append(eyebrow(L, T1 - 20, "1", "Pin", c))
    y = T1
    for name, u in ups.items():
        owner, repo = u["repo"].split("/")
        b.append(card(L, y, CW, 38, c))
        b.append(f'<rect x="{L}" y="{y + 9}" width="3" height="20" rx="1.5" fill="{c["patched"]}"/>')
        b.append(text(L + 18, y + 25, owner + "/", c, 14, "mono", c["muted"]))
        b.append(text(L + 18 + tw(owner + "/", 14, mono=True) + 4, y + 25, repo, c, 16, weight=600))
        y += 46
    own_y = y + 6
    b.append(card(L, own_y, CW, 38, c, stroke=c["own"]))
    b.append(text(L + 18, own_y + 25, "skills/", c, 15, "mono", c["own"], 600))
    b.append(text(L + 18 + tw("skills/", 15, mono=True) + 12, own_y + 25, f"{n_own} own + forked skills", c, 14, fill=c["muted"]))
    row1 = own_y + 38 - T1
    # 2 patch
    b.append(eyebrow(R, T1 - 20, "2", "Patch", c))
    b.append(card(R, T1, CW, row1 - 52, c))
    b.append(text(R + 18, T1 + 30, "patches/<upstream>/<skill>.patch", c, 15, "mono", c["patched"], 600))
    b.append(text(R + 18, T1 + 56, "each opens with a Why: line", c, 14, fill=c["muted"]))
    for k, why in enumerate(["Why: model tiers, not vendor ids", "Why: typed-only /pfd", "Why: trigger words first"]):
        b.append(text(R + 18, T1 + 86 + k * 24, why, c, 14, "mono", c["patched"]))
    b.append(card(R, T1 + row1 - 42, CW, 42, c, stroke=c["add"]))
    b.append(text(R + 18, T1 + row1 - 15, "git apply", c, 15, "mono", c["add"], 600))
    b.append(text(R + 18 + tw("git apply", 15, mono=True) + 12, T1 + row1 - 15, "fails loudly if upstream moved", c, 14, fill=c["muted"]))
    # 3 build (right, under patch)
    T2 = T1 + row1 + 64
    cmds = [("build", "pins + patches → dist/"), ("verify", "diff vs installed"), ("diff", "your edit → .patch"),
            ("bump", "move pins, hold back broken"), ("install", "symlink dist/")]
    b.append(eyebrow(R, T2 - 20, "3", "Build", c))
    row2 = 56 + len(cmds) * 32
    b.append(card(R, T2, CW, row2, c, stroke=c["ink"]))
    b.append(text(R + 18, T2 + 30, "uv run build.py", c, 15, "mono", c["ink"], 700))
    for k, (cmd, desc) in enumerate(cmds):
        yy = T2 + 64 + k * 32
        b.append(text(R + 18, yy, cmd, c, 15, "mono", c["derived"], 600))
        b.append(text(R + 110, yy, desc, c, 14, fill=c["muted"]))
    # 4 install (left, under pin)
    b.append(eyebrow(L, T2 - 20, "4", "Install", c))
    b.append(card(L, T2, CW, 42, c, stroke=c["add"]))
    b.append(text(L + 18, T2 + 27, "dist/", c, 15, "mono", c["add"], 600))
    b.append(text(L + 18 + tw("dist/", 15, mono=True) + 12, T2 + 27, f"{n_skills} skills, or a weekly release", c, 14, fill=c["muted"]))
    for k, (cmd, who) in enumerate([("npx skills add …#release", "any agent"), ("build.py install", "maintainer: live links to dist/")]):
        yy = T2 + 58 + k * 66
        b.append(card(L, yy, CW, 56, c))
        b.append(text(L + 18, yy + 24, cmd, c, 15, "mono", weight=600))
        b.append(text(L + 18, yy + 44, who, c, 14, fill=c["muted"]))
    # flow: pin → patch, skills/ → build, patch → build, build → install
    b.append(curve(L + CW + 2, T1 + 60, R - 4, T1 + 60, c))
    b.append(curve(L + CW + 2, own_y + 19, R - 4, T2 + 30, c))
    b.append(f'<path class="flow" d="M{R + CW - 60},{T1 + row1 + 2} L{R + CW - 60},{T2 - 4}" stroke="{c["muted"]}" stroke-width="1.6" marker-end="url(#arrow)"/>')
    b.append(curve(R - 2, T2 + 86, L + CW + 4, T2 + 86, c))
    return svg(CANVAS, T2 + row2 + 32, "Build pipeline: pin upstreams, apply patches, build dist, install with npx skills into any agent",
               "\n".join(b), c)


# ---------- skill map ----------

def card_names(entry: str, info: dict[str, dict]) -> list[str]:
    """A COLUMNS entry is a skill name, or a prefix ending in "*" that stands for every skill it matches."""
    return sorted(n for n in info if n.startswith(entry[:-1])) if entry.endswith("*") else [entry]


def skill_map(c: dict, info: dict[str, dict]) -> str:
    b = []
    W, PITCH = 268, 36
    tallest = 0
    for x, groups in zip([40, 326, 612], COLUMNS):
        y = 48
        for group, entries in groups:
            n = sum(len(card_names(e, info)) for e in entries)
            b.append(text(x, y, group, c, 17, weight=700))
            b.append(text(x + W, y, str(n), c, 14, "mono", c["muted"], anchor="end"))
            b.append(f'<line x1="{x}" y1="{y + 12}" x2="{x + W}" y2="{y + 12}" stroke="{c["line"]}"/>')
            y += 26
            for e in entries:
                names = card_names(e, info)
                i = info[names[0]]
                typed = all(info[m]["typed"] for m in names)
                label = ("/" if typed else "") + e + (f" ×{len(names)}" if e.endswith("*") else "")
                if 30 + tw(label, 14, mono=True) + 12 > W:
                    raise SystemExit(f"skill_map(): '{label}' overflows its card; widen the columns or shorten it")
                b.append(card(x, y, W, 28, c, r=14))
                b.append(f'<circle cx="{x + 16}" cy="{y + 14}" r="5" fill="{c[i["kind"]]}"/>')
                b.append(text(x + 30, y + 19, label, c, 14, "mono"))
                y += PITCH
            y += 30
        tallest = max(tallest, y - 30)
    ly = tallest + 26
    b.append(f'<line x1="40" y1="{ly - 12}" x2="{CANVAS - 40}" y2="{ly - 12}" stroke="{c["line"]}"/>')
    x = 40
    for kind in ("own", "derived", "patched"):
        n = sum(1 for i in info.values() if i["kind"] == kind)
        label = f"{KIND_LABEL[kind]} ({n})"
        b.append(f'<circle cx="{x + 6}" cy="{ly + 12}" r="5" fill="{c[kind]}"/>')
        b.append(text(x + 18, ly + 17, label, c, 14, "mono", c["muted"]))
        x += 18 + tw(label, 14, mono=True) + 30
    b.append(text(40, ly + 43, "/name = typed-only command", c, 14, "mono", c["muted"]))
    return svg(CANVAS, ly + 66, f"Skill map: {len(info)} skills grouped by job, colored by source", "\n".join(b), c)


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
        for name, out in [("hero", hero(c, len(info))), ("pot", pot(c, info)), ("pipeline", pipeline(c, len(info), n_own)),
                          ("settings", settings_map(c)), ("skills", skill_map(c, info))]:
            if small := sorted({float(s) for s in re.findall(r'font-size="([\d.]+)"', out) if float(s) < MIN_FONT}):
                raise SystemExit(f"{name}: font sizes {small} are below {MIN_FONT}; they won't read at README width")
            (OUT / f"{name}-{theme}.svg").write_text(out)
    print(f"wrote {len(list(OUT.glob('*.svg')))} SVGs to {OUT.relative_to(ROOT)}")
    update_readme()
    print("updated README.md agent blocks")


if __name__ == "__main__":
    main()
