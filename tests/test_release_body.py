import importlib.util
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "build_release_body.py"
spec = importlib.util.spec_from_file_location("build_release_body", SCRIPT_PATH)
build_release_body = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_release_body)


CHANGELOG = """# Changelog

## [Unreleased]

## [2.0.1] - 2026-05-09

### Added
- Added multiple administrator support with `AUTHORIZED_USER_IDS`.
- Added pagination for forwarding target selection.

### Changed
- Forwarded messages now use safe HTML formatting instead of Markdown.

### Fixed
- Fixed forwarding loops when the target group is also monitored.
- Fixed invalid message links for basic private groups.

## [2.0.0] - 2026-04-26

### Added
- Initial release.
"""


class ReleaseBodyTests(unittest.TestCase):
    def test_extract_changelog_section_accepts_tag_version(self):
        section = build_release_body.extract_changelog_section(CHANGELOG, "v2.0.1")

        self.assertIn("## [2.0.1] - 2026-05-09", section)
        self.assertIn("Fixed invalid message links", section)
        self.assertNotIn("Initial release", section)

    def test_extract_highlights_returns_first_four_user_facing_items(self):
        section = build_release_body.extract_changelog_section(CHANGELOG, "v2.0.1")

        self.assertEqual(
            build_release_body.extract_highlights(section),
            [
                "Added multiple administrator support with `AUTHORIZED_USER_IDS`.",
                "Added pagination for forwarding target selection.",
                "Forwarded messages now use safe HTML formatting instead of Markdown.",
                "Fixed forwarding loops when the target group is also monitored.",
            ],
        )

    def test_build_release_body_puts_highlights_before_downloads(self):
        section = build_release_body.extract_changelog_section(CHANGELOG, "v2.0.1")
        body = build_release_body.build_release_body(
            "v2.0.1",
            section,
            "luoyanglang/TelegramMonitor",
            "luoyanglangge",
            "telegram-monitor",
        )

        self.assertIn("### Highlights", body)
        self.assertIn("- Added multiple administrator support with `AUTHORIZED_USER_IDS`.", body)
        self.assertIn("### Update Notes", body)
        self.assertIn("### Downloads", body)
        self.assertIn("docker pull luoyanglangge/telegram-monitor:v2.0.1", body)


if __name__ == "__main__":
    unittest.main()
