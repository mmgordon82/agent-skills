# Maintaining agent-skills

For working on this repo. Using the skills: [README](../README.md).

## build.py commands

`dist/` is gitignored. It includes upstream assets (one skill alone is 39 MB), so you build it locally or download a [release](#releases).

| Command | What it does |
|---|---|
| `build` | Builds `dist/` from pins, patches and `skills/`. Fails without touching `dist/` if any patch doesn't apply. |
| `verify [--against DIR]` | Builds to a temp dir and diffs every skill against an installed copy (default `~/.agents/skills`). Shows exactly which files differ; missing or changed skills exit 1. |
| `diff <upstream> [--from DIR]` | Rewrites that upstream's patches from edited skills (default `dist/`). Keeps each patch's `Why:` header. |
| `bump [UPSTREAM…] [--rev SHA]` | Moves pins to upstream `HEAD` (default: all). A pin moves only if all its patches still apply; otherwise it stays, and the command exits 1. |
| `workspace <upstream> <dir>` | Starts rebuilding broken patches: lays out the upstream at its pin as a git repo, applies its patches (3-way where they conflict) and lists which to rewrite from their Why. |
| `install [--target] [--force]` | Points every `~/.agents/skills/<skill>` at `dist/<skill>` (live development; agents link there via npx skills). Creates the settings file if missing. |

## Working with patches

For an upstream with `tiered = true` (pstack), the build can retarget a failed patch when each hunk matches uniquely after masking model IDs and versioned model names. It prints the substitutions and keeps the patch's added text unchanged. Model effort suffixes can change; standalone effort rules, other wording changes, extra model entries, ambiguous matches, and older references remaining outside the hunk still require repair. Upstreams without that field use exact patch matching. The worked example is [How a tiered patch follows a renamed model](model-names.md).

Generated patches include full base hashes so three-way repair can fetch older base blobs from partial upstream clones.

**Change a patched skill:**

```sh
uv run build.py build
$EDITOR dist/unslop/SKILL.md             # edit the built copy
uv run build.py diff pstack              # writes patches/pstack/unslop.patch, keeps its Why: line
uv run build.py build && git add patches && git commit
```

To capture edits you made in your installed skills, run `diff pstack --from ~/.agents/skills`.

**Patch a new upstream skill:** add it to that upstream's `paths` in `upstreams.toml`, build, edit `dist/<skill>`, then run `diff`. Add a `Why:` line at the top of the new patch.

### When an upstream breaks patches

An upstream release can rewrite the lines a patch touches. pstack 0.15.43 did: it rewrote the same paragraphs, renamed the model ids our patches replace, and deleted two skills' model choices outright. The weekly job then fails at the bump step and releases nothing.

**Automatically:** the job then runs [`ci/fix_patches.py`](../ci/fix_patches.py). It lays out each broken upstream at its new commit, has `gpt-6.1-terra` resolve every conflicted file by the patch's header, regenerates the patches and runs the checks below. One retry gets the failures fed back. It opens a PR on `auto-fix/<upstream>-<sha>` (a draft if checks still fail) with what changed, every patch line it dropped and why, and the check results. Review the patch diffs and merge, then run **Actions → release → Run workflow** or wait for the next weekly release.

Checks the PR must pass, all code ([`ci/intent_checks.py`](../ci/intent_checks.py)); the first four also run on every PR and push:

- Every `SKILL.md` parses as strict YAML, `name` matches its folder, the description is at most 1024 characters, and typed-only skills have the Codex policy.
- Against the upstream original, a patch changes only `description` and adds or removes only `disable-model-invocation`. Any other frontmatter change fails; allowing a key is a one-line change in `intent_checks.py`.
- The only YAML file a patch adds is `agents/openai.yaml`, with only `interface.display_name`, `interface.short_description` and `policy.allow_implicit_invocation: false`.
- An upstream with `tiered = true` (pstack) contains no vendor model ids such as `claude-opus-5-5-high-fast` or `Opus 5.5`; its patches use tiers. The same model-reference pattern drives patch matching and this check. Another upstream opts in by setting the field; the registry name does not.
- A new always-on check is a function `(BuiltSkills) -> list[str]` appended to `CHECKS` in `ci/intent_checks.py`. Fixer-only checks take the previous build and are called from `ci/fix_patches.py`.
- Fixer only: every line the old patches added is still there or listed as dropped; no skill flips between typed-only and model-invocable; the model writes only the files git marked as conflicted.

**By hand** (or when the PR's checks fail): rebuild the patches from their intent, not by forcing the old diff on:

```sh
uv run build.py bump pstack                       # shows the new commit and which patches fail
# set pstack's rev in upstreams.toml to the new commit, then:
uv run build.py workspace pstack ~/tmp/pstack-ws  # new upstream as a git repo, patches applied where they can be
```

`workspace` prints one line per patch: applies, merged (check it), or rewrite from its Why, with conflicts marked. For each patch to rewrite, read its header and redo the change on the new upstream text: keep what upstream added, restate it in the patch's terms, and drop parts upstream made unnecessary. `git -C ~/tmp/pstack-ws diff HEAD` shows your edits against plain upstream. Then:

```sh
uv run build.py diff pstack --from ~/tmp/pstack-ws   # rewrites the patches, keeps each header
uv run build.py build && uv run tests/run.py
```

`diff` deletes a patch that has nothing left to change. Update a header when its reasoning changed, so the next rebuild starts from the right intent.

`build` always starts from a clean copy of each upstream's folders at the pin, then applies the patches. Files upstream adds or deletes come and go with it; nothing from an older `dist/` survives.

**Check nothing drifted:** `uv run build.py verify` builds to a temp dir and compares every skill with `~/.agents/skills`, byte for byte. Missing or changed skills exit 1.

**Run development checks:** `uv run tests/run.py`. The PR/main workflow ([`check.yml`](../.github/workflows/check.yml)) also builds and verifies `dist/`, runs `ci/intent_checks.py`, and fails if the generated graphics or README agent blocks are out of date.

## Releases

[`.github/workflows/release.yml`](../.github/workflows/release.yml) runs every Monday and on manual dispatch (**Actions → release → Run workflow**):

1. `build.py bump` moves every pin to its upstream `HEAD`. If any upstream's patches no longer apply, the job fails right here: nothing is built or released. `ci/fix_patches.py` rebuilds the patches in a PR; review and merge it before the next scheduled or manual release ([how](#when-an-upstream-breaks-patches)).
2. `build.py build` writes `dist/`.
3. [`ci/release.py`](../ci/release.py) compares `dist/` with the last published release, as git trees (file contents and modes). If nothing changed (for example, an upstream commit only touched its CI config), it stops. No release.
4. Otherwise it commits the moved pins to `main`, then commits `dist/` as one new commit on the **`release` branch**: the skill folders at the root, nothing else, with a `Source: <main sha>` trailer. So `git diff 20261119 20261126` (or GitHub's compare view) shows exactly what changed for users between two releases, and `npx skills add …#release` installs it.
5. It tags that commit with the date (`20261119`; a second release that day is `20261119.2`) and publishes a GitHub release with `agent-skills-<version>.tar.gz` and `.zip`. Each archive holds the skill folders, ready to extract into a skills directory.
6. The release notes are a bullet-point changelog that OpenAI `gpt-6.1-terra` writes from the diff between the two release commits, the upstream commit logs and this repo's commits. If generation fails, the release still publishes with fallback notes, then the job exits 1 to alert you. The prompt and model are in `ci/release.py`.

Setup: add an `OPENAI_API_KEY` repository secret. To preview a release locally: `OPENAI_API_KEY=… uv run ci/release.py --dry-run`. A run that pushed the branch but failed to publish finishes the same release on the next run.

## Repo layout

```
AGENTS.template.md     global instructions, placeholders for personal parts
settings.example.toml  defaults for ~/.config/agent-skills/settings.toml
upstreams.toml         pins: repo, sha, license, paths
patches/<upstream>/    one .patch per skill, each with a Why: header
skills/                own skills, plus forks that carry their own LICENSE
skills/skill-critique/agents.toml   the agent registry
build.py               build · verify · diff · bump · workspace · install (uv script)
tools/npx_agents.py    refresh the npx part of the agent registry
ci/release.py          compare with the last release, release branch commit, changelog, archives
ci/fix_patches.py      rebuild broken patches from their Why headers, open a PR
ci/intent_checks.py    deterministic checks on the built skills (CI and the fixer)
tests/                 behavioral tests: uv run tests/run.py
.github/workflows/     release.yml (weekly + manual release), check.yml (PRs and main)
docs/graphics.py       renders docs/assets/*.svg and the README's agent blocks from the repo data
```

`docs/graphics.py` reads `upstreams.toml`, `skills/`, `patches/`, `dist/` and the agent registry, so the counts, the skill map and the agent table stay accurate. Run `uv run docs/graphics.py` after adding a skill or an agent. It fails if a skill isn't placed in a column.
