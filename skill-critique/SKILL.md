---
name: skill-critique
description: Review every agent skill on this machine. An overview with counts by category, auto-load cost per agent, collisions and near-duplicates, then cuts, dedupes and one shared layout, applied after approval.
argument-hint: "Optional: one agent id, a category, or a project path"
disable-model-invocation: true
---

# Skill critique

A review of every skill on the machine, not only the ones that load. Priority follows cost: a
model-invocable skill puts its name and description into every new session of every agent that
lists it. So do instruction files, plugin skills, commands and subagent definitions; hooks can add
more. Typed-only and unseen skills cost nothing per session, but they still clutter, drift,
collide and duplicate.

Deliver, in order:

1. **Overview:** the user's skills at a glance: counts, categories, auto-load cost per agent,
   collisions, duplicates, near-duplicates, unseen skills.
2. **Load:** what each agent loads into every session, in tokens.
3. **Cuts:** ranked changes, always-loaded first, each with its saving.
4. **Cleanup:** after approval, apply them and leave one copy on disk that every agent reads.

Save reports, data and backups to this task's dir under the agent work dir (the `agent-workdir`
skill; default `~/agent-work/<project>/<date>-<topic>/`). `$SCAN` is
`uv run <this-skill-dir>/scripts/skill_scan.py`.

## Agents

Agents come from [agents.toml](agents.toml) plus `[agents.<id>]` tables in
`${XDG_CONFIG_HOME:-$HOME/.config}/agent-skills/settings.toml` (same shape; a shipped id is
overridden field by field). Each has a label, a home dir and the dir it reads skills from;
detection is that dir check plus optional `check_binary` (programs on PATH) and `check_dir` (more
dirs), combined with `check_boolean_operator` (AND by default). Detection never looks at skills, so
an installed agent with no skills still shows up, with 0 loaded. An agent the scan has no special
handling for gets the generic rules: skills from its `skills` dir, typed-only via
`disable-model-invocation`, instructions in `<home>/AGENTS.md`. Say so in the report when an
agent was measured with the generic rules. Never hardcode an agent list; refer to agents by id.

## 1. Collect

```bash
$SCAN overview --json "$WORK/skills.json"     # --list prints every skill an agent sees
$SCAN overview --extra ~/Projects/some-repo/.claude/skills   # also search more dirs
```

It finds every skill on disk (each installed agent's skills dir, the shared dir, every cached
plugin, enabled or not), counts each real directory once, and prints:

| Section | What it shows |
|---|---|
| Totals | skills on disk, names, auto-loaded somewhere, typed-only everywhere, seen by no agent, collisions, duplicate sets, near-duplicate pairs, installed agents |
| Auto-load per agent | skills each agent lists to its model, and their tokens per session |
| Heaviest auto-loaded | per skill: tokens per session, which agents load it (`3/4: codex, kimi, grok`), tokens on use, origin |
| Collisions | one name, different content: every copy and which agents load it |
| Duplicates | identical SKILL.md in several places |
| Near-duplicates | candidate pairs by description and name similarity; you confirm each |
| Unseen | skills no agent sees, per source (plugin caches that aren't enabled, stray copies) |

The JSON holds every skill (name, description, paths, origin, agents that list it or see it as
typed-only, per-session and on-use tokens, files, size, last modified) and every finding.

## 2. Overview

Read the JSON. Put every skill an agent sees in exactly one category, built from what the user
actually has (typical: workflow and planning, code review and quality, testing and debugging,
design and UI, writing and docs, security, infrastructure and deployment, data and databases, a
specific language or framework, a specific product or vendor, skill and agent management). Open a
SKILL.md when the description isn't enough. For each near-duplicate candidate, read both skills
and keep only the real overlaps, with one line on why.

Write `$WORK/skills-overview.md` and show it:

```markdown
# Skills on this machine — <YYYY-MM-DD>
**450 on disk · 337 names · 199 auto-loaded (~13k tokens in the heaviest agent) · 26 typed-only ·
225 unseen · 48 name collisions · 52 duplicate sets · 6 confirmed overlaps · agents: claude-code, codex, kimi, grok**

## By category
- **Design & UI — 8 skills, ~1.4k tokens/session:** impeccable, design-taste-frontend, pfd, …
- **Writing & docs — 5 skills, ~600 tokens/session:** unslop, technical-writing, …

## Auto-load per agent
| Agent | Auto-loaded | Tokens/session | Typed-only |
|---|---|---|---|

## Heaviest auto-loaded skills
| Skill | Tokens/session | Loaded by | Category |
|---|---|---|---|

## Collisions (same name, different content)
- **code-review**: 4 copies; the agents load `~/.claude/skills/code-review`; the 3 others sit in plugin caches.

## Overlaps (confirmed near-duplicates)
- **grill-me ≈ grill-with-docs**: same interview loop; one adds docs lookup.

## Unseen
- 76 in the mattpocock-skills plugin cache (plugin off) · 21 in data-analytics …
```

Keep it short: a reader should see what they have and where the waste is in one screen. Details
go in the tables below the summary.

## 3. Session load

```bash
$SCAN load                       # every installed agent
$SCAN load --only <agent-id> --top 30
```

Per agent: global instruction size, skills listed and typed-only, plugin skills, commands and
subagents, tokens per session, hooks, MCP servers, and problems (name clashes, broken symlinks,
missing descriptions, invalid YAML; strict loaders drop a skill whose description has an
unquoted `: `).

It can't measure these, so check them by hand:

- **Hooks:** `SessionStart` and `UserPromptSubmit` hooks inject text. Read each hook script to see
  what it prints and estimate the size. Never run a hook to find out.
- **MCP:** agents that don't defer tool schemas load every tool of every server at startup.
  Count the tools per server.
- **Project scope:** when critiquing a project, also measure its `AGENTS.md`/`CLAUDE.md` and
  project skills dirs.

## 4. Provenance

The origin column covers most skills. For each source that matters (anything you might cut or
change), also find:

- **Upstream:** repo and commit. Search for the skill's name or description when the origin is
  `local copy`.
- **What re-adds it:** plugin auto-update, npm postinstall, a skills CLI lock sync, an installer.
- **Local edits:** diff the installed copy against upstream.

Write `PROVENANCE.md`: one row per source: `source | license | how installed | skills | local edits`.

## 5. Find cuts

Always-loaded skills first (they cost every session), then the rest.

| Problem | Fix |
|---|---|
| Same skill in several dirs, or a plugin plus a loose copy of the same pack | Keep one copy. Symlink the rest. |
| Same name, different content (collision) | Diff the copies, keep the better one, merge anything unique from the others. |
| Confirmed overlap in one category (three anti-slop skills, four code reviewers) | Keep one. Merge the unique rules into it, or into a reference file it reads. |
| Generic filler that restates what the model already does ("senior engineer", "clean code", best-practice lists) | Delete. |
| Skills for tools or agents the user doesn't use, or one vendor's model names | Delete, or patch them to be generic. |
| Long or rarely needed, and the user would call it by name | Make it typed-only: `disable-model-invocation: true` in frontmatter, plus whatever the agent needs beyond that (Codex: `agents/openai.yaml` with `policy: allow_implicit_invocation: false`; Claude Code: `skillOverrides` in `settings.json` for a skill you don't own). |
| Description over about 250 characters, or trigger words buried | Rewrite: "Use when …" with the words a user would say, first. Some agents show only about 80 characters. |
| A very large SKILL.md body (high "on use") | Move detail into reference files the skill reads only when needed. |
| A local copy of a published pack | Replace it with a tracked install: `npx skills add <owner/repo> -g --skill <name> -y` (add `#<ref>` to pin), so updates come from upstream. |
| Seen by no agent: plugin caches that aren't enabled, stray copies, old backups | Remove the cache or copy, or enable the plugin if the user wants it. |
| Instruction file over a few thousand tokens | Move procedures that apply only sometimes into skills. Leave a one-line rule plus the `SKILL.md` path. |
| Subagent definitions with long, example-heavy descriptions | Trim the description, or delete unused agents. |
| Plugins enabled but unused, or hooks that inject text on every prompt | Disable them. |
| MCP servers loaded eagerly by an agent that doesn't need them | Disable per agent, or scope to the projects that use them. |
| Broken frontmatter, broken symlinks, find-and-replace damage (a rename that rewrote one agent's name to another inside text) | Fix, or restore from upstream. |
| An installer that will undo the cleanup | Remove it, or record it in the provenance table. |

## 6. Propose, then wait

Group the cuts as options (A, B, C…). Each gets one line: what changes, why, tokens saved per
session (or disk and clutter, for unseen skills), risk, and the exact command when it's an install
(`npx skills add …`). Recommend an order. Change nothing until the user approves.

## 7. Apply

1. **Back up first.** Archive everything you'll change or remove: `tar czf <workdir>/<topic>-backup.tgz -C ~ <paths>`. Write the restore command next to it.
2. **One copy on disk:** real skill dirs in the shared dir `~/.agents/skills`, linked into each
   agent's own dir. `npx skills add <source> -g -a <agent-id> …` sets up exactly that; use it
   rather than hand-made links. One instruction file, `~/.agents/AGENTS.md`, with each agent's own
   instruction file symlinked to it.
3. **Keep edits to upstream skills as patches.** Record a diff against the upstream commit, so an update can't silently drop them.
4. **Remove re-installers** you found in step 4, or tell the user what will come back.
5. **Re-run** `$SCAN overview` and `$SCAN load`. Report before → after (totals, per agent), what changed, and where the backups are.

## Rules

- Measure, don't guess. Every saving you claim comes from the script or a file size.
- Never delete without approval and a backup.
- The user's own skills: improve them. Delete only when they ask.
- A skill the user calls often stays model-invocable. Typed-only is for the rest.
