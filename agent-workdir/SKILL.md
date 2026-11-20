---
name: agent-workdir
description: Use before writing any audit, report, probe, scratch/test script, log, screenshot, handoff, plan, spec, or research output. Decides the <root>/<project>/<date>-<topic>/ path (default root ~/agent-work) so agent output never lands inside a checkout.
---

# Agent work dir

Agent output that a human might want later goes to `<root>/<project>/<YYYY-MM-DD>-<topic>/`,
never inside a git checkout. Session-only throwaways go to the session scratchpad.

## Resolve `<root>`

Read `${XDG_CONFIG_HOME:-$HOME/.config}/agent-skills/settings.toml`, key `root` under `[workdir]`.

| Situation | Do |
|---|---|
| No file, or no `root` key | Use the default, `~/agent-work`. Don't ask. |
| `root` set and valid | Use it. Expand a leading `~`. |
| File doesn't parse as TOML, or `root` isn't a string, isn't absolute or `~`-prefixed, or points inside a git checkout | Use `~/agent-work` for this task. Tell the user once: the file, the key, what's wrong. |
| `<root>` doesn't exist | Create it (`mkdir -p`). |
| `<root>` can't be created or written | Stop and ask the user. Never fall back to the repo or the current directory. |

## Where things go

| Output | Where |
|---|---|
| Audits, reports, probes, research notes | `<root>/<project>/<date>-<topic>/` |
| Scratch/test scripts, logs, screenshots | same dir (screenshots for a browser check: scratchpad) |
| Skill outputs (plans, specs) | same dir, unless the user names a path |
| Handoffs | `<root>/<project>/<handoff dir>/<date>-<short-name>.md`; `<handoff dir>` is `[handoff] dir` in the settings, default `handoffs` |
| Code or docs the user asked to add to the repo | the repo |
| One-off intermediate files you will delete | scratchpad |

`<date>` is today as `YYYY-MM-DD` (`date +%F`).

## Resolve `<project>`

1. In a git checkout (worktrees included), use the main checkout's directory name:
   ```sh
   basename "$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")"
   ```
2. Otherwise, the working folder's name.
3. If `<root>` already has a dir for the same project under another name, reuse it.
4. Not meaningful (home dir, `/tmp`, a hash) → `<root>/_misc/<session-id or timestamp>/`.

`<topic>` is 2–4 kebab-case words (`2026-11-19-auth-audit`). Reuse today's dir for the same topic.

## Rules
- Create the dir when you first write to it; no README, index, or `latest` symlink.
- Tell the user the full path of anything they will want to open.
- Don't move existing project files into the work dir; this applies to new agent output only.
