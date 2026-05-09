import os
import unittest
from types import SimpleNamespace


os.environ.setdefault("BOT_TOKEN", "123456:TEST_TOKEN")
os.environ.setdefault("TELEGRAM_API_ID", "123456")
os.environ.setdefault("TELEGRAM_API_HASH", "0" * 32)
os.environ.setdefault("AUTHORIZED_USER_ID", "123456789")

from core.telegram_client import (
    build_target_chat_info,
    is_same_telegram_chat,
    private_message_link,
    should_skip_bot_sender,
    should_skip_message_date,
)

from datetime import datetime, timedelta, timezone


class TargetChatTests(unittest.TestCase):
    def test_channel_requires_post_permission(self):
        entity = SimpleNamespace(
            id=1001,
            title="News",
            username="news",
            broadcast=True,
            creator=False,
            admin_rights=SimpleNamespace(post_messages=True),
        )

        self.assertEqual(
            build_target_chat_info(entity, "channel"),
            {"id": 1001, "title": "News", "type": "频道", "username": "news"},
        )

    def test_channel_without_post_permission_is_hidden(self):
        entity = SimpleNamespace(
            id=1001,
            title="News",
            username=None,
            broadcast=True,
            creator=False,
            admin_rights=None,
        )

        self.assertIsNone(build_target_chat_info(entity, "channel"))

    def test_group_requires_admin_rights(self):
        entity = SimpleNamespace(
            id=2002,
            title="Group",
            username=None,
            broadcast=False,
            creator=False,
            admin_rights=SimpleNamespace(post_messages=False),
            banned_rights=None,
        )

        self.assertEqual(
            build_target_chat_info(entity, "channel"),
            {"id": 2002, "title": "Group", "type": "群组", "username": None},
        )

    def test_group_without_admin_rights_is_hidden(self):
        entity = SimpleNamespace(
            id=2002,
            title="Group",
            username=None,
            broadcast=False,
            creator=False,
            admin_rights=None,
            banned_rights=None,
        )

        self.assertIsNone(build_target_chat_info(entity, "channel"))

    def test_positive_target_matches_bot_api_supergroup_id(self):
        self.assertTrue(is_same_telegram_chat(-1002780532153, 2780532153))

    def test_different_chat_does_not_match_target(self):
        self.assertFalse(is_same_telegram_chat(-1002933906079, 2780532153))

    def test_private_supergroup_message_link_is_generated(self):
        self.assertEqual(
            private_message_link(-1002780532153, 123),
            "https://t.me/c/2780532153/123",
        )

    def test_basic_private_group_message_link_is_not_generated(self):
        self.assertIsNone(private_message_link(-5122147816, 123))

    def test_old_messages_are_skipped_after_monitor_start(self):
        started_at = datetime(2026, 5, 9, 6, 55, tzinfo=timezone.utc)
        message_date = started_at - timedelta(minutes=1)

        self.assertTrue(should_skip_message_date(message_date, started_at))

    def test_recent_messages_are_not_skipped_after_monitor_start(self):
        started_at = datetime(2026, 5, 9, 6, 55, tzinfo=timezone.utc)
        message_date = started_at + timedelta(seconds=1)

        self.assertFalse(should_skip_message_date(message_date, started_at))

    def test_bot_sender_is_skipped(self):
        self.assertTrue(should_skip_bot_sender(SimpleNamespace(bot=True)))

    def test_human_sender_is_not_skipped(self):
        self.assertFalse(should_skip_bot_sender(SimpleNamespace(bot=False)))


if __name__ == "__main__":
    unittest.main()
