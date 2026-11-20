---
name: delegate
description: Use for multi-file features, cross-component debugging, repo-wide changes, parallel workstreams, or when asked to use subagents. Root plans and integrates; bounded subagents explore, implement, test, research, review.
---

# Delegate

The root agent owns the goal, the architecture, the integration, and the final answer. Subagents return evidence and bounded execution. Never hand architectural ownership to a subagent.

## Gate

Do it yourself only when the task is small and local. Delegate when any of these hold:
- it spans several files, modules, or services, or has two or more independent workstreams;
- the repo needs exploring before you can implement;
- debugging crosses components;
- external or version-specific facts need checking;
- an independent review after the change would catch real risk;
- the user asks for subagents or parallelism.

Once delegating, actually spawn the subagents. If spawning fails, say so. Don't quietly do the delegated work in the root.

## Roles and models

| Role | Job | Writes? | Model |
|---|---|---|---|
| explorer | map code paths, symbols, tests, config | no | fast |
| worker | bounded implementation with named file ownership | yes | fast |
| tester | reproduce, run targeted tests, report exact evidence | tests only | fast |
| researcher | version-specific APIs and docs, from primary sources | no | fast |
| reviewer | correctness, security, regression, and missing-test review | no | strong |

Use the harness's role definitions when it has them (e.g. `~/.codex/agents/*.toml`). Otherwise pick models per the tiers in the **poteto-mode** skill's Subagents section. Only the root escalates a subagent to a stronger model, when it reports a real reasoning blocker.

## Contract for every subagent

Give each one: objective (one outcome), scope (exact files or question), only the context it needs, constraints (what must not change), deliverable, and acceptance check. Explorers and reviewers must not edit files. Each file has one writer.

> Bad: "Fix the backend." Good: "Trace where POST /invoices validates currency. Return the files, the validation path, and existing tests. Don't edit files."

Subagents report back instead of widening scope when they hit an architectural choice, a breaking API or schema change, a new dependency, a security-sensitive choice, unclear requirements, or another worker's files.

## Order

- Independent tasks: spawn all of them, then wait for all.
- Dependent work runs in sequence: explore → root decides → implement → test → review → fix material findings → verify.
- Use only the roles that help. Don't let workers attempt competing fixes unless the root asks for alternatives.
- Subagents return conclusions, paths, line refs, commands run, and results. They don't return raw logs or whole files.

## Done when

- Every subagent you spawned has completed or explicitly failed, and none is still running.
- Findings are integrated and conflicts resolved.
- You read the final diff yourself, not only the subagents' summaries.
- You never claim a subagent did work unless the spawn actually succeeded.
