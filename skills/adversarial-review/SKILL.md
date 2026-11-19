---
name: adversarial-review
description: Use for an adversarial review or second opinion from a different agent CLI (Claude, Codex, Grok, Kimi, Pi, others) after non-trivial changes, plans or claims. Runs it headless and read-only to find bugs, holes and what you missed.
---

# Adversarial review

Run a second agent from the shell to attack your work. It looks for bugs, gaps, wrong assumptions, unhandled cases, and claims you did not prove. It is a reviewer, not an authority: you verify every finding before acting on it.

Use it after a non-trivial change, plan, root-cause claim or design decision, before you report "done". Skip it for one-liners.

## 1. Pick the reviewer

Prefer a CLI from a different vendor than you. A different model misses different things. The user's preference order is `[review] reviewers` in `${XDG_CONFIG_HOME:-$HOME/.config}/agent-skills/settings.toml`: take the first installed CLI in that list that isn't you. No file or no key → `codex, grok, claude, kimi, pi`. A broken value → that default, and tell the user.

```bash
for c in claude codex grok kimi pi gemini opencode; do command -v "$c" >/dev/null && echo "$c"; done
```

If the user names a CLI, use it. For a CLI not listed below:

1. Find the one-shot flag: `<cli> --help | grep -iE 'print|prompt|exec|single|-p'`.
2. Find how to make it read-only: a sandbox, a plan mode, a tool allowlist, or an agent profile that lists only read, search and list tools.
3. Prove it before the real run: ask it to create a file and edit one, and check that nothing changed.
4. No way to make it read-only → don't use it. Pick another CLI or tell the user. Never review a copy of the repo instead.

## 2. Write the brief

Write the brief to a file: `$WORK/review-brief.md`. `$WORK` is this task's dir under the agent work dir (the `agent-workdir` skill; default `~/agent-work/<project>/<date>-<topic>/`). Fill in this template:

```markdown
You are an adversarial reviewer. Another agent did the work below and believes it is correct.
Your job is to prove it wrong. Do not praise, summarize, or restate the work.

## Goal
<what the user asked for, in their words>

## What was done
<diff range or changed files, plan path, commands run; reference paths, don't paste whole files>

## Claims to attack
<each claim the agent makes: "X works because Y", "Z is the root cause", "tests cover W">

## Known gaps
<what the agent already knows is unverified>

## Find
- Bugs: wrong logic, edge cases, error paths, races, off-by-one, bad input at boundaries.
- Holes: requirements from the goal that are missing or only half done.
- Unproven claims: anything asserted but not shown by a test, a run, or the code.
- Surprises: inputs, environments or usage the author did not expect.
- Regressions: callers or behavior the change breaks elsewhere.

Read the code and run read-only commands to check before you report. A finding needs
evidence: file:line, a command and its output, or a concrete failing input.

## Output
One block per finding, worst first:
[critical|high|medium|low] file:line — the problem
Evidence: <what you read or ran>
Failure: <concrete input/state → wrong result>
End with "Not checked:" listing what you could not verify. No findings → say so plainly.
```

Never put secrets, credentials, customer data or private hostnames in the brief. The reviewer is a cloud model. If the repo itself is sensitive, ask the user before sending it.

## 3. Run it headless and read-only

`$REPO` is the project root. `$BRIEF` is the brief file.

| CLI | Command |
|---|---|
| Claude Code | `cd "$REPO" && claude -p --permission-mode plan "$(cat "$BRIEF")"` |
| Codex | `codex exec -s read-only -C "$REPO" -o "$WORK/review.md" - < "$BRIEF"` |
| Grok | `grok -p "$(cat "$BRIEF")" --cwd "$REPO" --tools read_file,grep,list_dir --max-turns 100` |
| Kimi Code | `cd "$REPO" && kimi -p "$(cat "$BRIEF")" --agent-file "$WORK/kimi-reviewer.md"` with the profile below. Without it, `-p` applies edits automatically, and it refuses `--plan`. |
| Pi | `cd "$REPO" && pi -p --tools read,grep,find,ls --exclude-tools 'mcp__*,codemode' "$(cat "$BRIEF")"` (`--tools` alone keeps MCP tools) |

The Grok binary may also be installed as `agent`. Kimi's read-only profile, `$WORK/kimi-reviewer.md` (only these tools exist for the session: no shell, no edits, no MCP, no subagents):

```markdown
---
name: reviewer
description: Read-only adversarial reviewer
tools: Read, Grep, Glob
---
You are a read-only reviewer. You cannot change files or run commands.
```

Save the output to `$WORK/review.md`. A whole-repo review can take 10 minutes or more, so run it in the background if your harness supports that, and keep working.

## 4. Triage

For each finding:

1. Check it against the real code or a real run. Do not trust it, and do not dismiss it without checking.
2. Mark it **confirmed** (fix it), **rejected** (one-line reason, with evidence), or **needs the user** (a scope or product decision).
3. After fixing confirmed findings, rerun the affected checks.

Run a second round only after substantial fixes, with a fresh brief. Report to the user: reviewer CLI, confirmed and fixed, rejected with reasons, still open.

## Common mistakes

| Mistake | Fix |
|---|---|
| Asking "is this good?" | Ask it to prove the work wrong, with evidence per finding. |
| Anchoring it on your conclusion | List claims to attack, not your reasoning for them. |
| Write access for a review | Read-only flags, or a throwaway worktree. |
| Pasting whole files | Give paths and the diff range; the reviewer can read the repo. |
| Applying findings unchecked | Verify each one; reviewers are confidently wrong too. |
