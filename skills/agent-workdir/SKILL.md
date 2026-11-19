---
name: agent-workdir
description: Use before writing any audit, report, probe, scratch/test script, log, screenshot, handoff, plan, spec, or research output. Decides the ~/agent-work/<project>/<date>-<topic>/ path so agent output never lands inside a checkout.
---

# Agent work dir

Agent output that a human might want later goes to `~/agent-work/<project>/<YYYY-MM-DD>-<topic>/`,
never inside a git checkout. Session-only throwaways go to the session scratchpad.

| Output | Where |
|---|---|
| Audits, reports, probes, research notes | `~/agent-work/<project>/<date>-<topic>/` |
| Scratch/test scripts, logs, screenshots | same dir (screenshots for a browser check: scratchpad) |
| Skill outputs (plans, specs, handoffs) | same dir, unless the user names a path |
| Code or docs the user asked to add to the repo | the repo |
| One-off intermediate files you will delete | scratchpad |

## Resolve `<project>`

1. In a git checkout (worktrees included), use the main checkout's directory name:
   ```sh
   basename "$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")"
   ```
2. Otherwise, the working folder's name.
3. If `~/agent-work/` already has a dir for the same project under another name, reuse it.
4. Not meaningful (home dir, `/tmp`, a hash) → `~/agent-work/_misc/<session-id or timestamp>/`.

`<topic>` is 2–4 kebab-case words (`2026-11-19-auth-audit`). Reuse today's dir for the same topic.

## Rules
- Create the dir when you first write to it; no README, index, or `latest` symlink.
- Tell the user the full path of anything they will want to open.
- Don't move existing project files into agent-work; this applies to new agent output only.
