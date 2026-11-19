---
name: consulting-grok
description: Use when you want a second opinion, an adversarial review, or a sounding board from a different model, or when you want to delegate/offload a self-contained coding or research task to an autonomous agent. Runs xAI Grok locally via the `agent` CLI — for brainstorming, cross-checking a plan, rubber-ducking, or spawning Grok as a headless sub-agent.
---

# Consulting Grok

## Overview

`agent` (the Grok CLI binary, here symlinked as `agent` on PATH; substitute `grok` if you didn't alias it) runs **xAI Grok** from the shell. Use it two ways:

- **Consult** — bounce an idea, get a blunt second opinion, cross-check a plan, adversarially review your own reasoning. Grok is a *sounding board, not ground truth* — verify anything load-bearing yourself.
- **Delegate** — hand Grok a self-contained task and let it act as an autonomous agent (it has its own read/edit/bash/web tools and can spawn its own sub-agents).

**Core command:** `agent -p "PROMPT"` runs one headless turn, prints the answer to stdout, and exits.

## When to use

- You've made a design/architecture call and want a different model to poke holes in it.
- You're stuck and want to rubber-duck against something that can read the code.
- A task is well-scoped and offloadable ("migrate this file", "draft these tests") and you'd rather delegate than do it inline.
- You want N independent takes on a hard question before committing.

## When NOT to use

- **Anything secret or sensitive.** `agent` sends the prompt (and whatever tools read) to xAI's cloud. Never feed it credentials, private keys, customer data, or air-gapped/lab specifics. Treat every call as public. If a repo *might* be sensitive but the user wants Grok's take, **ask before sending** — explicit authorization for that specific repo overrides this default (then scope it read-only). The rule guards against leaking secrets by reflex, not a hard ban.
- As the final authority. Grok can be confidently wrong — it informs *your* judgment, it doesn't replace verification.
- For trivial things you can just do. Don't add a network round-trip for a one-liner.

## Two default recipes

**Consult (read-only, safe default).** Let Grok inspect the repo but change nothing:

```bash
agent -p "Second opinion: is identity-hashing state on src+dst path the right call? Read run_state.py and critique. Be blunt about failure modes." \
  --tools "read_file,grep,list_dir" \
  --output-format json | jq -r '.text'
```

**Delegate (autonomous, write access).** Only when the user asked for the change:

```bash
agent -p "Add a --dry-run flag to clone_env.py that logs actions without executing them. Match the existing CLI style." \
  -m grok-build --cwd . --yolo --max-turns 100
```

`--yolo` auto-approves every tool call (writes, shell). Powerful and unsupervised — use only with a scoped prompt in a trusted dir, and add guardrails: `--tools`/`--deny` (below), `--max-turns` to bound it, and `--sandbox <profile>` to fence filesystem/network access. Without `--yolo`, headless tool calls that need approval will stall.

## Quick reference

| Need | Flag |
|------|------|
| One-shot prompt | `-p "PROMPT"` (a.k.a. `--single`) |
| Pick model | `-m grok-build` |
| Parse the reply | `--output-format json` → `.text` |
| Stream tokens/thoughts live | `--output-format streaming-json` |
| Auto-approve tools (unattended) | `--yolo` (or `--always-approve`) |
| Work in another dir | `--cwd PATH` |
| Cap agent loops | `--max-turns N` (whole-repo reviews want 100+) |
| Effort | `--effort low\|medium\|high\|xhigh\|max` |
| Extra system rules / guardrails | `--rules "Never delete files"` |
| Read-only toolset | `--tools "read_file,grep,list_dir"` |
| Strip specific tools | `--disallowed-tools "run_terminal_cmd,web_search"` |
| Forbid sub-agents | `--disallowed-tools "Agent"` |
| Allow/deny by pattern | `--allow "Bash(npm*)" --deny "Bash(sudo*)"` |
| Sandbox fs/network | `--sandbox PROFILE` |
| Continue a conversation | `--resume <sessionId>` or `-c` |
| Self-verify loop | `--check` |
| N tries, keep best | `--best-of-n N` |

Full flag list: `agent --help`, `agent agent --help`. Live models: `agent models`.

## Models

| ID | Use | Context |
|----|-----|---------|
| `grok-composer-2.5-fast` | Fast coding model — **the default** | 200k |
| `grok-build` | Best for heavy coding/agentic tasks | 512k |

Omitting `-m` uses the default (`grok-composer-2.5-fast`). For serious delegation or long-context work, pass `-m grok-build` explicitly. Confirm the live list and default with `agent models`.

## Output formats & parsing

- **plain** (default) — human text on stdout. Good for reading, bad for scripting.
- **json** — one object after completion:
  ```json
  {"text":"...","stopReason":"EndTurn","sessionId":"019f...","requestId":"9f74...","thought":"..."}
  ```
  On failure it emits `{"type":"error","message":"..."}` instead — check `type` before reading `text`.
- **streaming-json** — newline-delimited events, switch on `type`: `text` (chunk), `thought` (reasoning), `end` (metadata), `error`. Treat the type list as non-exhaustive.

**stdout stays clean; logs, update notices, and MCP spawn errors go to stderr.** Parse stdout, ignore stderr (or capture it separately for debugging with `RUST_LOG=debug ... 2>debug.log`).

## Multi-turn (context across calls)

Each `-p` call is a **fresh session** by default. To continue a thread:

```bash
# Turn 1 — capture the session id
SID=$(agent -p "Sketch a VLAN allocation scheme for parallel cohorts." --output-format json | jq -r '.sessionId')
# Turn 2 — same context
agent -p "Now stress-test that scheme for the 907-910 id range." --resume "$SID" --output-format json | jq -r '.text'
```

`-c`/`--continue` resumes the most recent session in the current dir. (Note: `-s/--session-id` is ignored in headless mode on this build — use `--resume`/`-c`.)

## Getting context into the prompt

Headless mode does **not** read piped stdin into the prompt. Inject context with command substitution or a file:

```bash
agent -p "Write a concise commit message for these changes:

$(git diff --staged)"

agent --prompt-file ./prompt.txt
```

Or just let Grok read the repo itself via its `read_file`/`grep` tools (`--cwd` points it at the project; it walks up to the nearest `.git`).

## Tool IDs (for `--tools` / `--disallowed-tools`)

`run_terminal_cmd` (bash), `read_file`, `search_replace` (edit), `list_dir`, `grep`, `web_search`, `web_fetch`, `todo_write`, `task`. `Agent` / `Agent(explore)` control sub-agent spawning. `--tools` is an allowlist (disables everything else); `--deny` runs after `--tools`; deny beats allow.

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Delegating with write access when only an opinion was wanted | Default to consult + `--tools "read_file,grep,list_dir"`; reserve `--yolo` for explicit change requests |
| Parsing `plain` output with string hacks | Use `--output-format json` and `jq -r '.text'` |
| Expecting memory between calls | Sessions are stateless by default — capture `sessionId`, then `--resume` |
| Piping a file into `agent -p` via `stdin` | Use `$(...)` substitution or `--prompt-file` |
| Sending sensitive/lab data to Grok | Don't — it's an external cloud call. See "When NOT to use". |
| `--yolo` in an untrusted dir with a vague prompt | Scope the prompt, `--cwd` a safe dir, add `--deny "Bash(rm*)"` / `--max-turns` |
| Assuming Grok honored your output format (it may drop requested severity tags, JSON schema, section structure) | Verify/normalize the shape yourself; don't pipe it straight into a strict parser |

## Exit codes

`0` success · `1` error (auth/network/runtime) · `130` SIGINT · `143` SIGTERM. On interrupt, session state is saved but tool file writes are **not** rolled back.

## Auth

Already logged in here (cached in `~/.grok/auth.json`). For CI/headless boxes set `XAI_API_KEY` (from console.x.ai) or `agent login --device-auth` (a.k.a. `--device-code`).

## Interactive TUI (for the human, not automation)

`agent` alone opens the full interactive UI; `agent "task"` starts it on a task. That's for a person at a keyboard — for programmatic use, always use `-p`.
