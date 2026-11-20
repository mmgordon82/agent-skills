from __future__ import annotations

import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from typer.testing import CliRunner

import build
from ci import release


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cache = build.ROOT / ".cache"
        self.cache.mkdir(exist_ok=True)
        self.runner = CliRunner()

    def temporary_directory(self):
        return tempfile.TemporaryDirectory(dir=self.cache)

    def test_failed_build_preserves_dist(self) -> None:
        with self.temporary_directory() as tmp:
            root = Path(tmp)
            dist = root / "dist"
            staged = root / "staged"
            dist.mkdir()
            staged.mkdir()
            marker = dist / "existing.txt"
            marker.write_text("keep me")
            with (
                patch.object(build, "DIST", dist),
                patch.object(build, "staging", return_value=staged),
                patch.object(build, "load", return_value={}),
                patch.object(build, "build_into", return_value=[("patches", "broken.patch", "does not apply")]),
            ):
                result = self.runner.invoke(build.app, ["build"])
            self.assertEqual(result.exit_code, 1)
            self.assertEqual(marker.read_text(), "keep me")
            self.assertFalse(staged.exists())

    def test_verify_accepts_an_identical_install(self) -> None:
        with self.temporary_directory() as tmp:
            root = Path(tmp)
            staged = root / "staged"
            installed = root / "installed"
            staged.mkdir()
            installed.mkdir()

            def make_skill(out: Path, _upstreams: dict):
                (out / "demo").mkdir()
                (out / "demo" / "SKILL.md").write_text("demo")
                return []

            (installed / "demo").mkdir()
            (installed / "demo" / "SKILL.md").write_text("demo")
            with (
                patch.object(build, "staging", return_value=staged),
                patch.object(build, "load", return_value={}),
                patch.object(build, "build_into", side_effect=make_skill),
            ):
                result = self.runner.invoke(build.app, ["verify", "--against", str(installed)])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("identical", result.output)

    def test_verify_fails_when_a_skill_is_missing(self) -> None:
        with self.temporary_directory() as tmp:
            root = Path(tmp)
            staged = root / "staged"
            installed = root / "installed"
            staged.mkdir()
            installed.mkdir()

            def make_skill(out: Path, _upstreams: dict):
                (out / "demo").mkdir()
                (out / "demo" / "SKILL.md").write_text("demo")
                return []

            with (
                patch.object(build, "staging", return_value=staged),
                patch.object(build, "load", return_value={}),
                patch.object(build, "build_into", side_effect=make_skill),
            ):
                result = self.runner.invoke(build.app, ["verify", "--against", str(installed)])
            self.assertEqual(result.exit_code, 1)
            self.assertIn("not installed", result.output)

    def test_release_publishes_fallback_notes_then_fails(self) -> None:
        with self.temporary_directory() as tmp:
            root = Path(tmp)
            dist = root / "dist"
            release_tmp = root / "release-tmp"
            (dist / "demo").mkdir(parents=True)
            release_tmp.mkdir()
            (dist / "demo" / "SKILL.md").write_text("demo")
            calls: list[tuple[str, ...]] = []
            original_mkdtemp = tempfile.mkdtemp

            def fake_run(*args: str, cwd: Path = release.ROOT, env: dict | None = None) -> str:
                calls.append(args)
                if args == ("git", "status", "--porcelain", "upstreams.toml"):
                    return ""
                if args == ("git", "rev-parse", "HEAD"):
                    return "a" * 40
                if args[:2] == ("git", "commit-tree"):
                    return "b" * 40
                return ""

            with (
                patch.object(release, "DIST", dist),
                patch.object(release, "run", side_effect=fake_run),
                patch.object(release, "branch_tip", return_value=None),
                patch.object(release, "published", return_value=None),
                patch.object(release, "tree_of", return_value="new-tree"),
                patch.object(release, "next_version", return_value="20990101"),
                patch.object(release, "evidence", return_value="evidence"),
                patch.object(release, "changelog", side_effect=RuntimeError("test outage")),
                patch.object(
                    release.tempfile,
                    "mkdtemp",
                    side_effect=lambda *args, **kwargs: original_mkdtemp(dir=release_tmp),
                ),
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                with self.assertRaises(SystemExit) as raised:
                    release.main()

            self.assertIn("release published with fallback notes", str(raised.exception))
            gh_call = next(call for call in calls if call[:3] == ("gh", "release", "create"))
            notes_path = Path(gh_call[gh_call.index("--notes-file") + 1])
            notes = notes_path.read_text()
            self.assertIn("Automated changelog generation failed", notes)
            self.assertIn("agent-skills-20990101.tar.gz", notes)
            push_index = next(i for i, call in enumerate(calls) if call[:2] == ("git", "push"))
            self.assertLess(push_index, calls.index(gh_call))

    def test_diff_round_trip_preserves_header_and_applies(self) -> None:
        with self.temporary_directory() as tmp:
            root = Path(tmp)
            base = root / "base"
            edited = root / "edited"
            patches = root / "patches"
            (base / "demo").mkdir(parents=True)
            (edited / "demo").mkdir(parents=True)
            (patches / "up").mkdir(parents=True)
            (base / "demo" / "SKILL.md").write_text("old\n")
            (edited / "demo" / "SKILL.md").write_text("new\n")
            patch_file = patches / "up" / "demo.patch"
            patch_file.write_text("Why: preserve the local change\n")
            upstream = build.Upstream(
                repo="owner/repo", rev="a" * 40, license="MIT", paths={"demo": "skills/demo"}
            )
            original_temporary_directory = tempfile.TemporaryDirectory

            def copy_base(_upstream: build.Upstream, out: Path) -> None:
                build.copy(base / "demo", out / "demo")

            with (
                patch.object(build, "PATCHES", patches),
                patch.object(build, "load", return_value={"up": upstream}),
                patch.object(build, "copy_upstream", side_effect=copy_base),
                patch.object(
                    build.tempfile,
                    "TemporaryDirectory",
                    side_effect=lambda *args, **kwargs: original_temporary_directory(dir=root),
                ),
            ):
                result = self.runner.invoke(build.app, ["diff", "up", "--from", str(edited)])

            self.assertEqual(result.exit_code, 0, result.output)
            text = patch_file.read_text()
            self.assertTrue(text.startswith("Why: preserve the local change\n"))
            self.assertIn("-old", text)
            self.assertIn("+new", text)
            applied = root / "applied"
            applied.mkdir()
            build.copy(base / "demo", applied / "demo")
            build.git("apply", str(patch_file), cwd=applied)
            self.assertEqual((applied / "demo" / "SKILL.md").read_text(), "new\n")

    def test_bump_holds_back_a_pin_when_its_patch_fails(self) -> None:
        with self.temporary_directory() as tmp:
            root = Path(tmp)
            staged = root / "staged"
            staged.mkdir()
            config = root / "upstreams.toml"
            old_rev = "a" * 40
            new_rev = "b" * 40
            config.write_text(
                '[up]\nrepo = "owner/repo"\nrev = "' + old_rev
                + '"\nlicense = "MIT"\npaths = { demo = "skills/demo" }\n'
            )
            upstream = build.Upstream(
                repo="owner/repo", rev=old_rev, license="MIT", paths={"demo": "skills/demo"}
            )

            def fake_git(*args: str, cwd: Path | None = None) -> str:
                if args[0] == "rev-parse":
                    return new_rev + "\n"
                if args[0] == "log":
                    return "abc123 change\n"
                return ""

            with (
                patch.object(build, "UPSTREAMS", config),
                patch.object(build, "load", return_value={"up": upstream}),
                patch.object(build, "checkout", return_value=root),
                patch.object(build, "git", side_effect=fake_git),
                patch.object(build, "staging", return_value=staged),
                patch.object(build, "build_into", return_value=[("up", "demo.patch", "does not apply")]),
            ):
                result = self.runner.invoke(build.app, ["bump", "up", "--rev", new_rev])

            self.assertEqual(result.exit_code, 1)
            self.assertIn(old_rev, config.read_text())
            self.assertNotIn(new_rev, config.read_text())
            self.assertFalse(staged.exists())

    def test_install_is_idempotent(self) -> None:
        with self.temporary_directory() as tmp:
            root = Path(tmp)
            dist = root / "dist"
            target = root / "target"
            settings = root / "settings.toml"
            (dist / "demo").mkdir(parents=True)
            (dist / "demo" / "SKILL.md").write_text("demo")
            args = ["install", "--target", str(target)]
            with patch.object(build, "DIST", dist), patch.object(build, "SETTINGS", settings):
                first = self.runner.invoke(build.app, args)
                second = self.runner.invoke(build.app, args)
            self.assertEqual(first.exit_code, 0, first.output)
            self.assertEqual(second.exit_code, 0, second.output)
            self.assertTrue((target / "demo").is_symlink())
            self.assertEqual((target / "demo" / "SKILL.md").read_text(), "demo")
            self.assertTrue(settings.exists())

    def test_release_reuses_a_previously_pushed_commit(self) -> None:
        with self.temporary_directory() as tmp:
            root = Path(tmp)
            dist = root / "dist"
            release_tmp = root / "release-tmp"
            (dist / "demo").mkdir(parents=True)
            release_tmp.mkdir()
            (dist / "demo" / "SKILL.md").write_text("demo")
            tip = "b" * 40
            previous = "c" * 40
            calls: list[tuple[str, ...]] = []
            original_mkdtemp = tempfile.mkdtemp

            def fake_run(*args: str, cwd: Path = release.ROOT, env: dict | None = None) -> str:
                calls.append(args)
                if args == ("git", "rev-parse", f"{previous}^{{tree}}"):
                    return "old-tree"
                if args == ("git", "rev-parse", f"{tip}^{{tree}}"):
                    return "new-tree"
                if args[:3] == ("git", "log", "-1"):
                    return ""
                return ""

            with (
                patch.object(release, "DIST", dist),
                patch.object(release, "run", side_effect=fake_run),
                patch.object(release, "branch_tip", return_value=tip),
                patch.object(release, "published", return_value=previous),
                patch.object(release, "tree_of", return_value="new-tree"),
                patch.object(release, "next_version", return_value="20990101"),
                patch.object(release, "evidence", return_value="evidence"),
                patch.object(release, "changelog", return_value="## Changes\n- Updated demo."),
                patch.object(
                    release.tempfile,
                    "mkdtemp",
                    side_effect=lambda *args, **kwargs: original_mkdtemp(dir=release_tmp),
                ),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                release.main()

            gh_call = next(call for call in calls if call[:3] == ("gh", "release", "create"))
            self.assertEqual(gh_call[gh_call.index("--target") + 1], tip)
            self.assertFalse(any(call[:2] == ("git", "commit-tree") for call in calls))
            self.assertFalse(any(call[:2] == ("git", "push") for call in calls))


if __name__ == "__main__":
    unittest.main()
