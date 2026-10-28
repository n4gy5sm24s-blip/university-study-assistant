import json
from pathlib import Path
import unittest


class ChromeExtensionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1] / "chrome-extension"

    def test_manifest_uses_active_tab_not_broad_browsing_access(self) -> None:
        manifest = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["manifest_version"], 3)
        self.assertIn("activeTab", manifest["permissions"])
        self.assertIn("scripting", manifest["permissions"])
        self.assertNotIn("tabs", manifest["permissions"])
        self.assertEqual(manifest["host_permissions"], ["http://127.0.0.1:8000/*"])

    def test_popup_discloses_page_reading_and_has_no_auto_submit(self) -> None:
        html = (self.root / "popup.html").read_text(encoding="utf-8")
        script = (self.root / "popup.js").read_text(encoding="utf-8")
        manifest_text = (self.root / "manifest.json").read_text(encoding="utf-8")
        self.assertIn("只有点击下方按钮后才读取", html)
        self.assertIn("active: true", script)
        self.assertNotIn("submit()", script)
        self.assertNotIn("<all_urls>", manifest_text)


if __name__ == "__main__":
    unittest.main()
