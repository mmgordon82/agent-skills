from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "skill-critique" / "scripts"))
import agents  # noqa: E402


class AgentRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.warnings: list[str] = []
        self.defaults = self.dir / "agents.toml"
        self.settings = self.dir / "settings.toml"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def load(self, defaults: str, settings: str = "") -> dict[str, agents.Agent]:
        self.defaults.write_text(defaults)
        self.settings.write_text(settings)
        found = agents.load_agents(self.defaults, self.settings, warn=self.warnings.append)
        return {a.id: a for a in found}

    def test_shipped_registry_loads(self) -> None:
        found = agents.load_agents(user=False, warn=self.warnings.append)
        self.assertGreaterEqual(len(found), 1)
        self.assertEqual(self.warnings, [])
        for a in found:
            self.assertTrue(a.label and str(a.home) and str(a.skills))

    def test_user_table_adds_an_agent_and_overrides_a_field(self) -> None:
        found = self.load(
            '[agents.one]\nlabel = "One"\nhome = "~/.one"\nskills = "~/.one/skills"\n',
            '[agents.one]\nskills = "~/.agents/skills"\n\n[agents.two]\nlabel = "Two"\nhome = "~/.two"\nskills = "~/.two/skills"\n')
        self.assertEqual(found["one"].label, "One")
        self.assertEqual(found["one"].skills, Path("~/.agents/skills").expanduser())
        self.assertIn("two", found)

    def test_and_needs_every_check_or_needs_one(self) -> None:
        home = self.dir / "home"
        home.mkdir()
        table = f'label = "X"\nhome = "{home}"\nskills = "{home}/skills"\ncheck_dir = ["{self.dir}/missing"]\n'
        found = self.load(f"[agents.both]\n{table}\n[agents.either]\n{table}check_boolean_operator = \"or\"\n")
        self.assertFalse(found["both"].installed())    # home exists, check_dir doesn't
        self.assertTrue(found["either"].installed())   # OR: home is enough

    def test_binary_check(self) -> None:
        found = self.load(f'[agents.sh]\nlabel = "S"\nhome = "{self.dir}"\nskills = "{self.dir}/s"\ncheck_binary = ["sh"]\n'
                          f'[agents.nope]\nlabel = "N"\nhome = "{self.dir}"\nskills = "{self.dir}/s"\n'
                          f'check_binary = ["no-such-binary-xyz"]\n')
        self.assertTrue(found["sh"].installed())
        self.assertFalse(found["nope"].installed())

    def test_detection_ignores_skills(self) -> None:
        a = self.load(f'[agents.empty]\nlabel = "E"\nhome = "{self.dir}"\nskills = "{self.dir}/no-skills-here"\n')["empty"]
        self.assertTrue(a.installed())                 # installed with no skills dir at all

    def test_unknown_fields_warn(self) -> None:
        found = self.load(f'[agents.old]\nlabel = "O"\nhome = "{self.dir}"\nskills = "{self.dir}/s"\ncheck_env = ["X"]\n')
        self.assertIn("old", found)
        self.assertTrue(any("unknown field" in w and "check_env" in w for w in self.warnings))

    def test_bad_entries_are_skipped_with_a_warning(self) -> None:
        found = self.load('[agents.nolabel]\nhome = "~/.x"\nskills = "~/.x/s"\n'
                          '[agents.badop]\nlabel = "B"\nhome = "~/.b"\nskills = "~/.b/s"\ncheck_boolean_operator = "XOR"\n')
        self.assertNotIn("nolabel", found)
        self.assertEqual(found["badop"].operator, "AND")
        self.assertEqual(len(self.warnings), 2)

    def test_broken_settings_file_keeps_the_shipped_agents(self) -> None:
        found = self.load('[agents.one]\nlabel = "One"\nhome = "~/.one"\nskills = "~/.one/s"\n', "this is = not [toml")
        self.assertIn("one", found)
        self.assertTrue(any("unreadable" in w for w in self.warnings))


if __name__ == "__main__":
    unittest.main()
