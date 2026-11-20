---
name: handoff
description: Write a handoff document so a fresh agent can continue this conversation or change from the same spot.
argument-hint: "What will the next session focus on?"
disable-model-invocation: true
---

# Handoff

Write one Markdown file that lets a new agent, in a new conversation, continue exactly where this one stops. The next agent has none of this conversation. It knows only what the file says and what it can read on disk.

If the user passed arguments, they describe what the next session will do. Shape the document around that.

## Where to save it

`<root>/<project>/<dir>/<date>-<short-name>.md`:

- `<root>` and `<project>`: resolve them exactly as the `agent-workdir` skill says. It reads `[workdir] root` from `${XDG_CONFIG_HOME:-$HOME/.config}/agent-skills/settings.toml`, default `~/agent-work`, and covers a missing or broken settings file. Without that skill, apply the same default and use the repo's directory name as `<project>`.
- `<dir>`: `[handoff] dir` from the same settings file, default `handoffs`. A value that isn't a plain relative folder name → use `handoffs` and tell the user.
- Never inside the repo, unless the user names a path there.

`<date>` is today in `YYYY-MM-DD` form: run `date +%F`. Don't write it from memory.

`<short-name>` is 2–4 kebab-case words for the work (`auth-token-refresh`). If the file exists, add `-2`, `-3`. Never overwrite.

## Gather facts first

Don't write from memory. Check:

```bash
git status --short; git branch --show-current; git log --oneline -10
git diff --stat; git stash list; git worktree list
```

Also note anything still running or left behind: background jobs, dev servers, containers, VMs, temp branches, worktrees, open PRs. Only state a check passed if it ran in this session and you saw the result. Otherwise write "not run".

## Template

```markdown
# Handoff: <short name>

<YYYY-MM-DD> · repo `<path>` · branch `<branch>` @ `<sha>` · tree: <clean | N uncommitted files>

## Goal
<What the user wants, in their words. The constraints and preferences they stated in this
conversation: "no new dependencies", "don't touch X", "wait for my review before pushing".>

## What happened before
<How we got here: what was investigated, what was tried and failed (and why, so it is not
retried), and the decisions made, each with its reason.>

## What changed, and why
<Per file or commit: what changed and the reason. Reference commits and diffs, don't paste them.>

## Current state
- Works, verified: <what, and how it was verified>
- Broken or unverified: <what>
- Uncommitted or unpushed: <what>
- Still running or left behind: <servers, containers, worktrees, temp branches>

## Next steps
1. <first concrete action, with the command>
2. ...

## Open questions
<Decisions waiting on the user, and assumptions the next agent must not treat as settled.>

## References
<Specs, plans, logs, issues, PRs, by path or URL.>
Suggested skills: <skills the next agent should load, and when>
```

## Rules

- Write for a reader with zero context. Use full paths, exact commands, exact error text.
- Reference artifacts that already exist (specs, plans, ADRs, commits, issues) by path or URL. Don't copy them in.
- Keep it short. A section with nothing to say gets "none". Don't drop the heading.
- Redact secrets, tokens, passwords and personal data.
- Finish by telling the user the file's full path and a one-line starter for the next session: `Read <path> and continue from "Next steps".`
