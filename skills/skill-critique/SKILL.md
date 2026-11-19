---
name: skill-critique
description: Review every agent skill on this machine. A categorized overview of what's installed, what each CLI loads into every session, then cuts, dedupes and one shared layout, applied after approval.
argument-hint: "Optional: one agent (claude, codex, kimi, grok, pi), a category, or a project path"
disable-model-invocation: true
---

# Skill critique

A review of every skill on the machine, not only the ones that load. Priority follows cost: a
model-invocable skill puts its name and description into every new session, in every CLI that
lists it. So do instruction files, plugin skills, commands and subagent definitions; hooks can add
more. Typed-only and unused skills cost nothing per session, but they still clutter, drift,
duplicate and conflict.

Deliver, in order:

1. **Overview:** every skill, grouped by category: what the user has, where it comes from, where
   it loads.
2. **Load:** what each CLI loads into every session, in tokens.
3. **Cuts:** ranked changes, always-loaded first, each with its saving.
4. **Cleanup:** after approval, apply them and leave one copy on disk that every CLI reads.

Save reports, inventories and backups to this task's dir under the agent work dir (the
`agent-workdir` skill; default `~/agent-work/<project>/<date>-<topic>/`). `$SCAN` is
`uv run <this-skill-dir>/scripts/skill_scan.py`.

## 1. Inventory

```bash
$SCAN inventory --json "$WORK/inventory.json"     # add --all to list unseen skills one by one
$SCAN inventory --extra ~/Projects/some-repo/.claude/skills   # also search more dirs
```

It finds every skill on disk (all CLI skill dirs, every cached plugin, enabled or not) and lists
each real directory once:

| Column | Meaning |
|---|---|
| loads in | `C` Claude Code, `X` Codex, `K` Kimi, `G` Grok, `P` Pi. Uppercase: listed to the model. Lowercase: visible but typed-only. `-`: no CLI sees it. |
| ~tok/session | name + description, paid in every session where it's listed |
| ~tok on use | the SKILL.md body, paid each time the skill is invoked |
| files, size, modified | weight and age on disk |
| origin | plugin, git remote, skills CLI lock entry, symlink target, or `local copy` |
| (dup) | the same name exists in more than one real directory |

Skills no CLI sees (cached plugins that aren't enabled, stray copies) are summarized per source;
`--all` lists them. The JSON has everything, including every path a skill appears at.

## 2. Overview by category

Read the JSON and each skill's description (open the SKILL.md when the description isn't enough).
Put every skill in exactly one category. Build the categories from what the user actually has;
typical ones: workflow and planning, code review and quality, testing and debugging, design and
UI, writing and docs, security, infrastructure and deployment, data and databases, a specific
language or framework, a specific product or vendor, skill and agent management.

Show the user a preview: one short table per category, most expensive first.

```markdown
### Design & UI — 9 skills, ~1.4k tokens/session
| Skill | Loads in | /session | On use | Origin | Notes |
|---|---|---|---|---|---|
| impeccable | C X K G P | 190 | 2.5k | git agent-skills | lead UI skill |
| frontend-design | - | 0 | 1.1k | plugin (off) | overlaps impeccable |
```

Then a summary: skills per category, how many load somewhere, typed-only, unseen, duplicate
names. Notes flag what the next steps will act on: overlap within a category, duplicates, broken
frontmatter, very large bodies, stale copies, skills for tools the user doesn't use.

## 3. Session load

```bash
$SCAN load                       # every CLI found in $HOME
$SCAN load --only codex --top 30
```

For each CLI: global instruction size, skills listed and typed-only, plugin skills, commands and
subagents, tokens per session, hooks, MCP servers, and problems (name clashes, broken symlinks,
missing descriptions, invalid YAML; strict parsers such as Codex drop a skill whose description
has an unquoted `: `).

It can't measure these, so check them by hand:

- **Hooks:** `SessionStart` and `UserPromptSubmit` hooks inject text. Read each hook script to see
  what it prints and estimate the size. Never run a hook to find out.
- **MCP:** CLIs that don't defer tool schemas load every tool of every server at startup. Count the
  tools per server.
- **Project scope:** when critiquing a project, also measure its `AGENTS.md`/`CLAUDE.md`,
  `.claude/skills` and `.agents/skills`.

Show one table: CLI → tokens per session, plus the three biggest contributors to each.

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
| Same name, different content | Diff the two, keep the better one, merge anything unique from the other. |
| Several skills for one job in one category (three anti-slop skills, four code reviewers) | Keep one. Merge the unique rules into it, or into a reference file it reads. |
| Generic filler that restates what the model already does ("senior engineer", "clean code", best-practice lists) | Delete. |
| Skills for tools or CLIs the user doesn't use, or one vendor's model names | Delete, or patch them to be generic. |
| Long or rarely needed, and the user would call it by name | Make it typed-only: `disable-model-invocation: true` in frontmatter (Claude, Grok, Kimi, Pi), plus `agents/openai.yaml` with `policy: allow_implicit_invocation: false` (Codex). For a skill you don't own, Claude's `skillOverrides` in `settings.json` (`"name": "user-invocable-only"`) does the same without editing it. |
| Description over about 250 characters, or trigger words buried | Rewrite: "Use when …" with the words a user would say, first. Codex shows about 80 characters. |
| A very large SKILL.md body (high "on use") | Move detail into reference files the skill reads only when needed. |
| Seen by no CLI: plugin caches that aren't enabled, stray copies, old backups | Remove the cache or copy, or enable the plugin if the user wants it. |
| Instruction file over a few thousand tokens | Move procedures that apply only sometimes into skills. Leave a one-line rule plus the `SKILL.md` path. |
| Subagent definitions with long, example-heavy descriptions | Trim the description, or delete unused agents. |
| Plugins enabled but unused, or hooks that inject text on every prompt | Disable them. |
| MCP servers loaded eagerly by a CLI that doesn't need them | Disable per CLI, or scope to the projects that use them. |
| Broken frontmatter, broken symlinks, find-and-replace damage (a rename that rewrote "Claude" to "Codex" inside text) | Fix, or restore from upstream. |
| An installer that will undo the cleanup | Remove it, or record it in the provenance table. |

## 6. Propose, then wait

Group the cuts as options (A, B, C…). Each gets one line: what changes, why, tokens saved per
session (or disk and clutter, for unseen skills), risk. Recommend an order. Change nothing until
the user approves.

## 7. Apply

1. **Back up first.** Archive everything you'll change or remove: `tar czf <workdir>/<topic>-backup.tgz -C ~ <paths>`. Write the restore command next to it.
2. **One copy on disk:**
   - Real skill dirs go in `~/.agents/skills`. Codex, Kimi, Grok and Pi read it directly.
   - Each `~/.claude/skills/<name>` is a relative symlink: `../../.agents/skills/<name>`.
   - One instruction file, `~/.agents/AGENTS.md`. `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, `~/.grok/AGENTS.md` and `~/.pi/agent/AGENTS.md` are symlinks to it. Kimi reads it directly.
3. **Keep edits to upstream skills as patches.** Record a diff against the upstream commit, so an update can't silently drop them.
4. **Remove re-installers** you found in step 4, or tell the user what will come back.
5. **Re-run** `$SCAN load` and `$SCAN inventory`. Report before → after per CLI and in the overview, what changed, and where the backups are.

## Rules

- Measure, don't guess. Every saving you claim comes from the script or a file size.
- Never delete without approval and a backup.
- The user's own skills: improve them. Delete only when they ask.
- A skill the user calls often stays model-invocable. Typed-only is for the rest.
