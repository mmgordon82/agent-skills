# AGENTS.md — Personal preferences (<YOUR NAME>)

Cross-cutting preferences for ALL my work, every repo. Project/org rules live in that
project's own AGENTS.md/CLAUDE.md (e.g. ~/Projects/<project>/AGENTS.md) and override this on conflict.
Single source: `~/.agents/AGENTS.md`; `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`,
`~/.grok/AGENTS.md` are symlinks to it.

## How to talk to me
- Lead with the answer or recommendation. No preamble, no restating my request, no
  flattery ("Great question", "You're absolutely right"). Get to the point.
- Default to LESS information — the decision plus the one or two things I need to make
  it. I'll ask for more if I want it.
- When there's a real choice, label options (A / B / C), one line of tradeoff each,
  recommend one, then ask. Don't dump an exhaustive menu.
- Challenge me when I'm wrong. Don't agree just to be agreeable.

## Match effort to the task
- Small, well-scoped changes: just do them — no brainstorm/plan/TODO ceremony. This rule
  wins over any skill that mandates ceremony (brainstorming, planning, TDD): skip it.
- Big, risky, or multi-step work: short spec → I approve → plan → implement. Stop at
  that gate; don't run ahead of approval.

## Engineering taste (priority order — do not invert)
1. Simplicity and clarity — the simplest thing that fully works. Simple is the goal.
2. Maintainability and clean handover.
3. Correctness, with explicit, honest failure modes.
4. Performance / scale / elegance — last.

- DRY the structure, not every line — three similar lines beat a premature abstraction.
- Simple ≠ naive — USE the framework's strengths (FastAPI → Pydantic response models;
  Django → the ORM). Don't hand-roll what the framework already does well.
- Validate and parse at boundaries (CLI, config, network, DB) into typed models; trust
  internals, no re-checks. Logic in pure functions, thin shell.
- State-mutating scripts/ops must be safe to rerun and resume after a crash: read current
  state, apply the diff; write temp + rename.
- Tests assert observable behavior through the public interface. Keep a test only if it
  fails when behavior breaks and survives a pure refactor.
- Don't add error handling, logging, retries, or config knobs unless I ask or the
  failure is real and likely.
- My solo/internal code has no external consumer: make clean breaking changes. No
  back-compat shims, flags, or deprecation warnings unless I ask.

## Languages & dependencies
- Language preference, in order: **Python** first (simplicity — scripts, tools, data,
  APIs), **Go** when I want one static self-contained binary that does a thing, **Bash**
  for portable glue/automation that runs anywhere, **JavaScript/Node** as a last resort
  (when the platform forces it — browser, or a JS-only ecosystem).
- Use well-maintained libraries when they make the code cleaner or the dev experience
  better (Python: typer, pydantic, requests, httpx, rich). Don't hand-roll what a solid
  library does. This overrides ponytail's stdlib-first rung; ponytail still governs YAGNI/scope.
- "Fewer dependencies" means deployed shape: one Go binary or one small Docker image
  beats a sprawl of runtime services, not "avoid libraries".
- Python: uv. Scripts declare deps inline (PEP 723, `uv run script.py`); projects use
  pyproject.toml + uv.lock.

## Self-hosting
- Default to self-hostable, dockerizable designs. Online dependencies (CDNs, fonts, APIs)
  are fine by default; I'll say when a target is offline/air-gapped.
- Packaging, image choice, and offline-target rules → read the `self-hosting` skill
  (`~/.agents/skills/self-hosting/SKILL.md`).
## Behavior I expect
- Verify against the source of truth; don't assume. Read the real code/output and run
  it — especially before claiming something works or naming a root cause.
- Two fixes failed on the same assumption → write the assumption down and test it
  before trying a third.
- Non-trivial repetitive edits or checks → a rerunnable script/codemod, not hand edits.
  The script is the proof.
- A correction repeated twice → encode it as a lint/check/script/hook, not more
  instruction text.
- State assumptions explicitly.
- Prefer explicit failure (clear error/refusal) over silently producing wrong output.
- Confirm changes by running the real entrypoint or test. For services, hit the actual
  endpoint. Use a container only when it is the deployment unit or affects behavior.
- Before adding complexity for a speculative or vanishingly unlikely race or security edge
  case, explain the concrete failure mode, likelihood, and complexity cost and get my
  buy-in. Do not silently expand scope for theoretical robustness.

## Tools & delegation
- Lean on subagents and skills — use them more, not less. Default to dispatching a
  subagent for codebase exploration/mapping, research, and end-of-task review so the
  main thread stays focused; invoke a relevant skill rather than improvising.
- Browser checks: chrome-devtools MCP only, never Claude in Chrome — details in the
  `run-validation` skill.

## Where to run validation
Before planning or running tests, builds, containers, VMs, or browser checks → read the
`run-validation` skill (`~/.agents/skills/run-validation/SKILL.md`). Core rule: state the claim being tested, then use the first environment that contains
every property relevant to it — 1. Local Mac, 2. Local Docker (arm64), 3. Linux amd64 VM
(your VM tool; machine-specific commands in a private `local-tooling` skill). Never claim deployment or architecture compatibility from a lower tier.

## Agent work dir (~/agent-work)
Agent output (audits, reports, probes, scratch scripts, logs, screenshots, handoffs, plans,
specs, research) → `~/agent-work/<project>/<YYYY-MM-DD>-<topic>/`, never inside a checkout.
Before writing any of it, read the `agent-workdir` skill (`~/.agents/skills/agent-workdir/SKILL.md`).
## Scripts & tooling (KISS)
- No hidden state, no silent magic auto-discovery.
- Safe defaults: never delete or overwrite without an explicit flag.
- Short, single-purpose, obvious-from-the-code scripts.
- No convenience cruft unless asked (no `latest` symlinks, checksum sidecars, metadata).

## Building sites, UIs & content
- UI design, build, critique, or UX review → use the `impeccable` skill; for UX judgment read
  `~/.agents/skills/impeccable/reference/usability.md`.
- Build only what's asked — no unrequested copy. No taglines, hero blurbs, footers,
  "about"/"how it works"/privacy/credits lines, or marketing voice unless I ask (e.g.
  don't write "an offline SQL detective lab" or "progress saved in this browser, no
  login"). Nothing that signals it was AI-built. Unsure → ship less text, and match the
  site's existing voice.
- Exercises/labs/CTF challenges: keep the intended difficulty. No hints, clues,
  walkthroughs, or solution reveals, and don't make a challenge easier than asked.
  Unclear difficulty → ask, don't soften it.

## Docs & comments
- Concise and information-dense — no long prose. Write for the next person: explicit
  commands/paths over paragraphs, checklists over essays. Don't restate what filenames
  or `ls` already show. Update docs in the same change.
- READMEs/docs target Linux users (Ubuntu/Debian) — I'm the only one on a Mac, and the
  docs are for the team, not me. No macOS instructions/commands in docs unless I ask.
- Comment only what isn't obvious from the code; keep comments short.
