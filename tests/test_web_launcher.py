from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class WebLauncherTests(unittest.TestCase):
    def test_launcher_uses_existing_course_database_and_fixed_port(self) -> None:
        script = (ROOT / "scripts" / "launch-web.ps1").read_text(encoding="utf-8")
        self.assertIn("data\\study_assistant.db", script)
        self.assertIn("127.0.0.1", script)
        self.assertIn('"8000"', script)
        self.assertIn("Google\\Chrome", script)

    def test_shortcut_runs_hidden_launcher(self) -> None:
        script = (ROOT / "scripts" / "install-web-shortcut.ps1").read_text(encoding="utf-8")
        self.assertIn("Open Coursework AI.lnk", script)
        self.assertIn("-WindowStyle Hidden", script)
        self.assertIn("launch-web.ps1", script)


if __name__ == "__main__":
    unittest.main()
