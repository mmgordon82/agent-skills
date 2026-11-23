from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from typer.testing import CliRunner

import build
from ci import intent_checks


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cache = self.root / "cache"
        self.repo = self.cache / "acme__skills"
        self.md = self.repo / "skills/demo/SKILL.md"
        self.md.parent.mkdir(parents=True)
        self.git("init", "-q")
        self.source = self.root / "edited"
        self.source.joinpath("demo").mkdir(parents=True)
        self.own = self.root / "own"
        self.own.mkdir()
        self.runner = CliRunner()
        for key, value in {"ROOT": self.root, "CACHE": self.cache, "PATCHES": self.root / "patches", "OWN": self.own,
                           "DIST": self.root / "dist"}.items():
            mock = patch.object(build, key, value)
            mock.start()
            self.addCleanup(mock.stop)

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], check=True, text=True,
                              capture_output=True).stdout.strip()

    def commit(self, model="claude-opus-5-5-high-fast", instruction="Keep this instruction.", effort="high"):
        self.md.write_text(f"---\nname: demo\ndescription: A demo\n---\n\n{instruction}\n"
                           f"Default: `{model}`.\nBudget: {effort}.\nAliases: `auto`, `inherit-parent`.\n")
        self.git("add", "-A")
        self.git("-c", "user.name=test", "-c", "user.email=test@example.com", "commit", "-qm", "upstream")
        return build.Upstream(repo="acme/skills", rev=self.git("rev-parse", "HEAD"), license="MIT",
                              paths={"demo": "skills/demo"})

    def invoke(self, u, *args, upstream="pstack"):
        with patch.object(build, "load", return_value={upstream: u}):
            return self.runner.invoke(build.app, list(args))

    def tier_patch(self, u, instruction="Keep this instruction.", upstream="pstack"):
        expected = (self.repo / "skills/demo/SKILL.md").read_text().replace(
            "`claude-opus-5-5-high-fast`", "the strong tier").replace("Keep this instruction.", instruction)
        (self.source / "demo/SKILL.md").write_text(expected)
        result = self.invoke(u, "diff", upstream, "--from", str(self.source), upstream=upstream)
        self.assertEqual(result.exit_code, 0, result.output)
        return expected

    def test_model_renames_apply_the_same_policy_and_keep_other_instructions(self):
        u = self.commit()
        expected = self.tier_patch(u)
        for model in ("gemini-4-neon-xhigh", "gpt-6.2-medium", "grok-5-low", "Opus 6.1", "Gemini 5"):
            with self.subTest(model=model):
                u = self.commit(model=model)
                result = self.invoke(u, "build")
                self.assertEqual(result.exit_code, 0, result.output)
                self.assertIn("tier policy unchanged", " ".join(result.output.split()))
                self.assertEqual((build.DIST / "demo/SKILL.md").read_text(), expected)
        u = self.commit(model="gpt-6.2-high", effort="low")
        result = self.invoke(u, "build")
        self.assertEqual(result.exit_code, 1, result.output)
        self.assertEqual((build.DIST / "demo/SKILL.md").read_text(), expected)

    def test_unpatched_model_is_reported_by_intent_check(self):
        u = self.commit()
        result = self.invoke(u, "build")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("vendor model id", intent_checks.check_vendor_ids(build.DIST, ["demo"])[0])

    def test_workspace_can_merge_a_real_conflict_after_normalization(self):
        old = self.commit()
        self.tier_patch(old, instruction="Local instruction.")
        patch_path = build.PATCHES / "pstack/demo.patch"
        patch_path.write_text("Why: preserve configured roles.\n\n" + patch_path.read_text())
        new = self.commit(model="gemini-4-neon-xhigh", instruction="Upstream instruction.")
        ws = self.root / "workspace"
        result = self.invoke(new, "workspace", "pstack", str(ws))
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("conflicts marked in demo/SKILL.md", result.output)
        conflicted = (ws / "demo/SKILL.md").read_text()
        self.assertIn("<<<<<<<", conflicted)
        self.assertIn("Upstream instruction.", conflicted)
        self.assertIn("Local instruction.", conflicted)
        resolved = self.md.read_text().replace("`gemini-4-neon-xhigh`", "the strong tier").replace(
            "Upstream instruction.", "Upstream and local instruction.")
        (ws / "demo/SKILL.md").write_text(resolved)
        result = self.invoke(new, "diff", "pstack", "--from", str(ws))
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertTrue(patch_path.read_text().startswith("Why: preserve configured roles.\n"))
        result = self.invoke(new, "build")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual((build.DIST / "demo/SKILL.md").read_text(), resolved)

    def test_workspace_applies_model_renames_without_conflict_markers(self):
        old = self.commit()
        expected = self.tier_patch(old)
        new = self.commit(model="gemini-4-neon-xhigh")
        ws = self.root / "workspace"
        result = self.invoke(new, "workspace", "pstack", str(ws))
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("applies", result.output)
        self.assertEqual((ws / "demo/SKILL.md").read_text(), expected)

    def test_other_upstreams_still_require_exact_patch_text(self):
        old = self.commit()
        self.tier_patch(old, upstream="demo")
        new = self.commit(model="gemini-4-neon-xhigh")
        result = self.invoke(new, "build", upstream="demo")
        self.assertEqual(result.exit_code, 1, result.output)

    def test_changed_words_extra_models_and_ambiguous_matches_are_refused(self):
        old = self.commit()
        self.tier_patch(old)
        patch_path = build.PATCHES / "pstack/demo.patch"
        for model, instruction, repeat in (("gpt-6.2-high", "New instruction.", 1),
                                            ("Opus 5.5 or Sonnet 4.6", "Keep this instruction.", 1),
                                            ("gpt-6.2-high", "Keep this instruction.", 2)):
            with self.subTest(model=model, repeat=repeat):
                new = self.commit(model=model, instruction=instruction)
                out = self.root / "rejected"
                build.copy_upstream(new, out)
                target = out / "demo/SKILL.md"
                before = target.read_text() * repeat
                target.write_text(before)
                with self.assertRaises(build.GitError):
                    build.apply_patch(patch_path, out, tiered=True)
                self.assertEqual(target.read_text(), before)

    def test_one_bad_file_prevents_every_file_in_a_patch_from_changing(self):
        old = self.commit()
        notes = self.md.with_name("notes.md")
        notes.write_text("Required upstream text.\n")
        self.git("add", "-A")
        self.git("-c", "user.name=test", "-c", "user.email=test@example.com", "commit", "-qm", "notes")
        old = old.model_copy(update={"rev": self.git("rev-parse", "HEAD")})
        self.tier_patch(old)
        (self.source / "demo/notes.md").write_text("Local text.\n")
        self.assertEqual(self.invoke(old, "diff", "pstack", "--from", str(self.source)).exit_code, 0)
        new = self.commit(model="gemini-4-neon-xhigh")
        notes.write_text("Changed upstream text.\n")
        self.git("add", "-A")
        self.git("-c", "user.name=test", "-c", "user.email=test@example.com", "commit", "-qm", "changed notes")
        new = new.model_copy(update={"rev": self.git("rev-parse", "HEAD")})
        out = self.root / "rejected"
        build.copy_upstream(new, out)
        before = {p: p.read_bytes() for p in (out / "demo").iterdir()}
        with self.assertRaises(build.GitError):
            build.apply_patch(build.PATCHES / "pstack/demo.patch", out, tiered=True)
        self.assertEqual({p: p.read_bytes() for p in before}, before)

    def test_later_conflict_fetches_the_older_patch_base_in_a_fresh_partial_clone(self):
        old = self.commit()
        self.tier_patch(old, instruction="Local instruction.")
        base = self.git("rev-parse", f"{old.rev}:skills/demo/SKILL.md")
        renamed = self.commit(model="gemini-4-neon-xhigh")
        conflicted = self.commit(model="gemini-4-neon-xhigh", instruction="Upstream instruction.")
        bare = self.root / "origin.git"
        subprocess.run(["git", "clone", "-q", "--bare", str(self.repo), str(bare)], check=True, capture_output=True)
        build.git("config", "uploadpack.allowFilter", "true", cwd=bare)
        cache = self.root / "partial"
        clone = cache / "acme__skills"
        subprocess.run(["git", "clone", "-q", "--filter=blob:none", bare.as_uri(), str(clone)],
                       check=True, capture_output=True)
        with patch.object(build, "CACHE", cache):
            out = self.root / "adapted"
            build.copy_upstream(renamed, out)
            build.apply_patch(build.PATCHES / "pstack/demo.patch", out, tiered=True)
            self.assertIn(f"?{base}", build.git("rev-list", "--objects", "--all", "--missing=print", cwd=clone))
            ws = self.root / "workspace"
            result = self.invoke(conflicted, "workspace", "pstack", str(ws))
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("conflicts marked in demo/SKILL.md", result.output)
            self.assertIn("<<<<<<<", (ws / "demo/SKILL.md").read_text())

    def test_model_mask_keeps_sentence_punctuation(self):
        out = self.root / "punctuation"
        (out / "demo").mkdir(parents=True)
        target = out / "demo/SKILL.md"
        target.write_text("Default: gpt-6\n")
        patch_path = self.root / "punctuation.patch"
        patch_path.write_text("--- a/demo/SKILL.md\n+++ b/demo/SKILL.md\n@@ -1 +1 @@\n"
                              "-Default: gpt-5.\n+Default: the strong tier.\n")
        with self.assertRaises(build.GitError):
            build.apply_patch(patch_path, out, tiered=True)
        self.assertEqual(target.read_text(), "Default: gpt-6\n")

    def test_reworded_original_block_is_not_confused_with_another_models_block(self):
        out = self.root / "blocks"
        (out / "demo").mkdir(parents=True)
        target = out / "demo/SKILL.md"
        before = "Intro.\n\nReworded role:\nUse gpt-5\nThen verify.\n\nRole:\nUse gpt-6\nThen verify.\nOutro.\n"
        target.write_text(before)
        patch_path = self.root / "blocks.patch"
        patch_path.write_text("--- a/demo/SKILL.md\n+++ b/demo/SKILL.md\n@@ -3,3 +3,3 @@\n"
                              " Role:\n-Use gpt-5\n+Use the strong tier\n Then verify.\n")
        with self.assertRaises(build.GitError):
            build.apply_patch(patch_path, out, tiered=True)
        self.assertEqual(target.read_text(), before)

    def test_multiple_hunks_keep_each_roles_added_policy_byte_for_byte(self):
        old = self.commit()
        self.md.write_text(self.md.read_text() + "\n".join(f"Workflow instruction {n}." for n in range(10))
                           + "\nPanel: `gemini-4-high`.\n")
        self.git("add", "-A")
        self.git("-c", "user.name=test", "-c", "user.email=test@example.com", "commit", "-qm", "panel")
        old = old.model_copy(update={"rev": self.git("rev-parse", "HEAD")})
        expected = self.tier_patch(old).replace("`gemini-4-high`", "the panel tier at high")
        (self.source / "demo/SKILL.md").write_text(expected)
        self.assertEqual(self.invoke(old, "diff", "pstack", "--from", str(self.source)).exit_code, 0)
        self.md.write_text(self.md.read_text().replace("claude-opus-5-5-high-fast", "gpt-6.2-xhigh")
                           .replace("gemini-4-high", "kimi-6-low"))
        self.git("add", "-A")
        self.git("-c", "user.name=test", "-c", "user.email=test@example.com", "commit", "-qm", "renamed roles")
        new = old.model_copy(update={"rev": self.git("rev-parse", "HEAD")})
        result = self.invoke(new, "build")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual((build.DIST / "demo/SKILL.md").read_bytes(), expected.encode())
        self.md.write_text(self.md.read_text().replace("kimi-6-low", "<model>"))
        self.git("add", "-A")
        self.git("-c", "user.name=test", "-c", "user.email=test@example.com", "commit", "-qm", "model placeholder")
        changed = new.model_copy(update={"rev": self.git("rev-parse", "HEAD")})
        result = self.invoke(changed, "build")
        self.assertEqual(result.exit_code, 1, result.output)
        self.assertEqual((build.DIST / "demo/SKILL.md").read_bytes(), expected.encode())

    def test_workspace_uses_a_generated_base_it_already_has(self):
        old = self.commit()
        self.md.write_text(self.md.read_text().replace("description: A demo\n", "description: A demo\ndisable-model-invocation: true\n"))
        self.git("add", "-A")
        self.git("-c", "user.name=test", "-c", "user.email=test@example.com", "commit", "-qm", "typed only")
        old = old.model_copy(update={"rev": self.git("rev-parse", "HEAD")})
        self.tier_patch(old, instruction="Local instruction.")
        policy = self.source / "demo/agents/openai.yaml"
        policy.parent.mkdir()
        policy.write_text("policy:\n  allow_implicit_invocation: false\ninterface:\n  display_name: Demo\n")
        self.assertEqual(self.invoke(old, "diff", "pstack", "--from", str(self.source)).exit_code, 0)
        self.md.write_text(self.md.read_text().replace("Keep this instruction.", "Upstream instruction."))
        self.git("add", "-A")
        self.git("-c", "user.name=test", "-c", "user.email=test@example.com", "commit", "-qm", "new instruction")
        new = old.model_copy(update={"rev": self.git("rev-parse", "HEAD")})
        ws = self.root / "workspace"
        result = self.invoke(new, "workspace", "pstack", str(ws))
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("conflicts marked in demo/SKILL.md", result.output)
        self.assertIn("display_name: Demo", (ws / "demo/agents/openai.yaml").read_text())

    def test_workspace_reports_an_unavailable_base_instead_of_an_empty_conflict(self):
        old = self.commit()
        self.tier_patch(old, instruction="Local instruction.")
        base = self.git("rev-parse", f"{old.rev}:skills/demo/SKILL.md")
        path = build.PATCHES / "pstack/demo.patch"
        path.write_text(path.read_text().replace(base, "f" * 40))
        new = self.commit(instruction="Upstream instruction.")
        result = self.invoke(new, "workspace", "pstack", str(self.root / "workspace"))
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("cannot load patch base", " ".join(result.output.split()))
