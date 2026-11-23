#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["typer>=0.12", "pydantic>=2.7", "rich>=13", "tomlkit>=0.13", "pyyaml>=6"]
# ///
"""Deterministic checks on the built skills (default: dist/). Exits 1 and names every problem.

- Every SKILL.md has strict-YAML frontmatter, `name` = its folder, a description of at most 1024 characters,
  and a Codex policy file when it is typed-only.
- Against the upstream original, a patch changes only the frontmatter keys in FRONTMATTER_VALUE_CHANGES and
  adds or removes only those in FRONTMATTER_ADD_REMOVE.
- The only YAML file a patch adds is agents/openai.yaml, with only the keys in OPENAI_YAML_KEYS.
- Skills from build.TIERED upstreams name no vendor model ids; their patches map models through tiers.

ci/fix_patches.py also runs the fixer-only checks: lines a patch added survive, and typed-only state holds.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build  # noqa: E402

FRONTMATTER_VALUE_CHANGES = {"description"}
FRONTMATTER_ADD_REMOVE = {"disable-model-invocation"}
OPENAI_YAML_KEYS = {"interface.display_name", "interface.short_description", "policy.allow_implicit_invocation"}
MAX_DESCRIPTION = 1024
TEXT = {".md", ".yaml", ".yml", ".toml", ".json", ".py", ".sh", ".txt"}


class StrictLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate keys instead of keeping the last one."""

    def construct_mapping(self, node, deep=False):
        keys = [self.construct_object(k, deep=deep) for k, _ in node.value]
        if dupes := sorted({str(k) for k in keys if keys.count(k) > 1}):
            raise yaml.constructor.ConstructorError(None, None, f"duplicate key(s): {', '.join(dupes)}", node.start_mark)
        return super().construct_mapping(node, deep=deep)


def load_yaml(text: str):
    """Parse strictly. Raises ValueError with the reason."""
    try:
        return yaml.load(text, Loader=StrictLoader)
    except yaml.YAMLError as e:
        raise ValueError(f"invalid YAML: {str(e).splitlines()[0]}") from None


def frontmatter(skill_md: Path) -> dict:
    """The SKILL.md frontmatter, parsed strictly. Raises ValueError with the reason."""
    m = re.match(r"^---\n(.*?)\n---\n", skill_md.read_text(), re.S)
    if not m:
        raise ValueError("no frontmatter")
    data = load_yaml(m.group(1))
    if not isinstance(data, dict):
        raise ValueError("frontmatter is not a mapping")
    return data


def typed_only(fm: dict) -> bool:
    return fm.get("disable-model-invocation") is True


def flat_keys(data: dict, prefix: str = "") -> set[str]:
    keys = set()
    for k, v in data.items():
        keys |= flat_keys(v, f"{prefix}{k}.") if isinstance(v, dict) and v else {f"{prefix}{k}"}
    return keys


def check_skill_files(dist: Path) -> list[str]:
    problems = []
    for md in sorted(dist.glob("*/SKILL.md")):
        skill = md.parent.name
        try:
            fm = frontmatter(md)
        except ValueError as e:
            problems.append(f"{skill}: SKILL.md {e}")
            continue
        if fm.get("name") != skill:
            problems.append(f"{skill}: frontmatter name is {fm.get('name')!r}, not the folder name")
        if len(str(fm.get("description") or "")) > MAX_DESCRIPTION:
            problems.append(f"{skill}: description longer than {MAX_DESCRIPTION} characters")
        if typed_only(fm):
            policy = md.parent / "agents" / "openai.yaml"
            try:
                data = load_yaml(policy.read_text()) if policy.exists() else None
            except ValueError as e:
                problems.append(f"{skill}: agents/openai.yaml {e}")
                continue
            if not (isinstance(data, dict) and (data.get("policy") or {}).get("allow_implicit_invocation") is False):
                problems.append(f"{skill}: typed-only but agents/openai.yaml doesn't set allow_implicit_invocation: false (Codex would load it)")
    return problems


def check_frontmatter_changes(base: Path, dist: Path, skills: list[str]) -> list[str]:
    problems = []
    for skill in skills:
        try:
            a, b = frontmatter(base / skill / "SKILL.md"), frontmatter(dist / skill / "SKILL.md")
        except (ValueError, FileNotFoundError):
            continue  # reported by check_skill_files
        for k in sorted(set(b) - set(a) - FRONTMATTER_ADD_REMOVE):
            problems.append(f"{skill}: patch adds frontmatter key '{k}' (allowed: {', '.join(sorted(FRONTMATTER_ADD_REMOVE))})")
        for k in sorted(set(a) - set(b) - FRONTMATTER_ADD_REMOVE):
            problems.append(f"{skill}: patch removes frontmatter key '{k}'")
        for k in sorted(set(a) & set(b) - FRONTMATTER_VALUE_CHANGES - FRONTMATTER_ADD_REMOVE):
            if a[k] != b[k]:
                problems.append(f"{skill}: patch changes frontmatter key '{k}' (allowed: {', '.join(sorted(FRONTMATTER_VALUE_CHANGES))})")
    return problems


def check_added_yaml(base: Path, dist: Path, skills: list[str]) -> list[str]:
    problems = []
    for skill in skills:
        for f in sorted((dist / skill).rglob("*")):
            rel = f.relative_to(dist / skill)
            if f.suffix not in (".yaml", ".yml") or (base / skill / rel).exists():
                continue
            if str(rel) != "agents/openai.yaml":
                problems.append(f"{skill}: patch adds YAML file {rel} (only agents/openai.yaml is allowed)")
                continue
            try:
                data = load_yaml(f.read_text())
            except ValueError as e:
                problems.append(f"{skill}: {rel} {e}")
                continue
            if not isinstance(data, dict):
                problems.append(f"{skill}: agents/openai.yaml is not a mapping")
                continue
            if extra := flat_keys(data) - OPENAI_YAML_KEYS:
                problems.append(f"{skill}: agents/openai.yaml has keys outside the allowlist: {', '.join(sorted(extra))}")
            elif data.get("policy", {}).get("allow_implicit_invocation", False) is not False:
                problems.append(f"{skill}: agents/openai.yaml may only set allow_implicit_invocation: false")
    return problems


def check_vendor_ids(dist: Path, skills: list[str]) -> list[str]:
    problems = []
    for skill in skills:
        for f in sorted((dist / skill).rglob("*")):
            if not f.is_file() or f.suffix not in TEXT:
                continue
            for n, line in enumerate(f.read_text(errors="ignore").splitlines(), 1):
                if ids := sorted({m.group(0) for m in build.MODEL_REF.finditer(line)}, key=len)[-1:]:
                    problems.append(f"{skill}: vendor model id '{ids[0]}' at {f.relative_to(dist)}:{n} (use a tier)")
    return problems


def added_lines(patch_text: str) -> list[tuple[str, str]]:
    """(path, line) for every non-blank line a patch adds."""
    out, path, in_header = [], None, False
    for line in patch_text.splitlines():
        if line.startswith("diff --git "):
            in_header = True
        elif in_header and line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("@@"):
            in_header = False
        elif not in_header and path and line.startswith("+") and line[1:].strip():
            out.append((path, line[1:].rstrip()))
    return out


def check_added_lines(old_patches: dict[str, str], dist: Path, dropped: dict[str, set[str]]) -> list[str]:
    """Fixer-only: every line an old patch added is still in the build, or that patch's rewrite dropped it on purpose."""
    problems = []
    for name, text in old_patches.items():
        for path, line in added_lines(text):
            f = dist / path
            have = {l.rstrip() for l in f.read_text(errors="ignore").splitlines()} if f.exists() else set()
            if line not in have and line.strip() not in dropped.get(name, set()):
                problems.append(f"{name}: line it added is gone from {path} and not listed as dropped: {line.strip()[:120]}")
    return problems


def check_typed_state(old_dist: Path, new_dist: Path, skills: list[str]) -> list[str]:
    """Fixer-only: no skill flips between typed-only and model-invocable."""
    problems = []
    for skill in skills:
        try:
            old, new = typed_only(frontmatter(old_dist / skill / "SKILL.md")), typed_only(frontmatter(new_dist / skill / "SKILL.md"))
        except (ValueError, FileNotFoundError):
            continue
        if old != new:
            problems.append(f"{skill}: was {'typed-only' if old else 'model-invocable'}, now {'typed-only' if new else 'model-invocable'}")
    return problems


def run_all(dist: Path, ups: dict[str, build.Upstream]) -> list[str]:
    """Every check that holds for any build; compares patched skills with fresh upstream copies at their pins."""
    base = build.staging()
    try:
        for u in ups.values():
            build.copy_upstream(u, base)
        skills = [s for u in ups.values() for s in u.skills]
        tiered = [s for name, u in ups.items() if name in build.TIERED for s in u.skills]
        return (check_skill_files(dist) + check_frontmatter_changes(base, dist, skills)
                + check_added_yaml(base, dist, skills) + check_vendor_ids(dist, tiered))
    finally:
        shutil.rmtree(base, ignore_errors=True)


def main() -> None:
    dist = Path(sys.argv[1]) if len(sys.argv) > 1 else build.DIST
    problems = run_all(dist, build.load())
    for p in problems:
        print(f"::error::{p}" if "GITHUB_ACTIONS" in os.environ else p)
    print(f"{len(problems)} problem(s)" if problems else "intent checks passed")
    raise SystemExit(1 if problems else 0)


if __name__ == "__main__":
    main()
