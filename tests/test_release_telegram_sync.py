import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_PATH = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "sync_release_telegram.py"


def load_sync_module():
    spec = importlib.util.spec_from_file_location("sync_release_telegram", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReleaseTelegramSyncTests(unittest.TestCase):
    def setUp(self):
        self.module = load_sync_module()

    def test_env_truthy_accepts_common_enabled_values(self):
        with patch.dict(os.environ, {"TELEGRAM_MIRROR_DISCUSSION": "true"}, clear=True):
            self.assertTrue(self.module.env_truthy("TELEGRAM_MIRROR_DISCUSSION"))

        with patch.dict(os.environ, {"TELEGRAM_MIRROR_DISCUSSION": "0"}, clear=True):
            self.assertFalse(self.module.env_truthy("TELEGRAM_MIRROR_DISCUSSION"))

    def test_resolve_discussion_group_id_prefers_explicit_env(self):
        with patch.dict(os.environ, {"TELEGRAM_DISCUSSION_GROUP_ID": "-100123"}, clear=True):
            with patch.object(self.module, "telegram_request") as telegram_request:
                self.assertEqual(
                    self.module.resolve_discussion_group_id("token", "-100456"),
                    "-100123",
                )
                telegram_request.assert_not_called()

    def test_resolve_discussion_group_id_reads_linked_chat(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(
                self.module,
                "telegram_request",
                return_value={"ok": True, "result": {"linked_chat_id": -100789}},
            ) as telegram_request:
                self.assertEqual(
                    self.module.resolve_discussion_group_id("token", "-100456"),
                    "-100789",
                )
                telegram_request.assert_called_once_with(
                    "getChat",
                    "token",
                    {"chat_id": "-100456"},
                )

    def test_mirror_to_discussion_group_forwards_channel_message(self):
        calls = []

        def fake_request(method, token, payload):
            calls.append((method, token, payload))
            return {"ok": True, "result": {"linked_chat_id": -100789}}

        with patch.dict(os.environ, {}, clear=True):
            with patch.object(self.module, "telegram_request", side_effect=fake_request):
                result = self.module.mirror_to_discussion_group("token", "-100456", "12")

        self.assertEqual(result, {"enabled": True, "mirrored": True})
        self.assertEqual(calls[0][0], "getChat")
        self.assertEqual(
            calls[1],
            (
                "forwardMessage",
                "token",
                {
                    "chat_id": "-100789",
                    "from_chat_id": "-100456",
                    "message_id": "12",
                    "disable_notification": "true",
                },
            ),
        )


if __name__ == "__main__":
    unittest.main()
