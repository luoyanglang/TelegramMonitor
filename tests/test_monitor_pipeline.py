import os
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace


os.environ.setdefault("BOT_TOKEN", "123456:TEST_TOKEN")
os.environ.setdefault("TELEGRAM_API_ID", "123456")
os.environ.setdefault("TELEGRAM_API_HASH", "0" * 32)
os.environ.setdefault("AUTHORIZED_USER_ID", "123456789")

from core.telegram_client import TelegramClientManager


class FakeClient:
    def __init__(self):
        self.handlers = []
        self.catch_up_calls = 0

    def add_event_handler(self, handler, event_builder):
        self.handlers.append((handler, event_builder))

    def remove_event_handler(self, handler, event_builder):
        self.handlers = [
            item for item in self.handlers
            if item[0] is not handler
        ]

    async def catch_up(self):
        self.catch_up_calls += 1


class FakeMessage:
    id = 88
    sender_id = 123456
    chat_id = -1002780532153
    text = "北京"
    date = datetime(2026, 5, 13, 6, 0, tzinfo=timezone.utc)

    async def get_sender(self):
        return SimpleNamespace(first_name="狼哥", username=None)

    async def get_chat(self):
        return SimpleNamespace(title="Source Group", username=None)


class FakeMessageWithUsername(FakeMessage):
    async def get_sender(self):
        return SimpleNamespace(first_name="狼哥", username="luoyanglang")


class FakeEntityClient:
    async def get_entity(self, entity_id):
        if entity_id == 123456:
            return SimpleNamespace(first_name="狼哥", username="luoyanglang")
        raise ValueError("unknown entity")


class FakeMessageUserRefClient:
    async def get_input_entity(self, entity_id):
        return SimpleNamespace(id=entity_id)

    async def __call__(self, request):
        return [SimpleNamespace(first_name="狼哥", username="luoyanglang")]

    async def get_entity(self, entity_id):
        raise ValueError("entity lookup should not be needed")


class FailingEntityClient:
    async def get_input_entity(self, entity_id):
        raise ValueError("input entity lookup failed")

    async def __call__(self, request):
        raise ValueError("request failed")

    async def get_entity(self, entity_id):
        raise ValueError("entity lookup failed")


class MonitorPipelineTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self):
        if hasattr(self, "manager"):
            await self.manager.stop_monitoring()

    async def test_start_monitoring_catches_up_after_registering_handler(self):
        self.manager = TelegramClientManager()
        self.manager.client = FakeClient()
        self.manager.target_chat_id = 12345
        self.manager.is_logged_in = _async_return(True)

        self.assertTrue(await self.manager.start_monitoring(SimpleNamespace()))

        self.assertEqual(len(self.manager.client.handlers), 1)
        self.assertEqual(self.manager.client.catch_up_calls, 1)

    async def test_event_callback_enqueues_without_processing_inline(self):
        self.manager = TelegramClientManager()
        self.manager._message_queue = None
        processed = []

        async def fake_handle(event, keyword_matcher):
            processed.append((event, keyword_matcher))

        self.manager._handle_new_message = fake_handle
        event = SimpleNamespace(message=SimpleNamespace(id=1))
        keyword_matcher = SimpleNamespace()

        await self.manager._enqueue_message_event(event, keyword_matcher)

        self.assertEqual(processed, [])
        self.assertEqual(self.manager._message_queue.qsize(), 1)

    async def test_format_message_resolves_full_sender_entity_for_username_link(self):
        self.manager = TelegramClientManager()
        self.manager.client = FakeEntityClient()
        keyword = SimpleNamespace(content="北京")

        formatted = await self.manager._format_message(FakeMessage(), [keyword])

        self.assertIn('<a href="https://t.me/luoyanglang">狼哥</a>', formatted)

    async def test_format_message_resolves_sender_from_message_reference(self):
        self.manager = TelegramClientManager()
        self.manager.client = FakeMessageUserRefClient()
        keyword = SimpleNamespace(content="北京")

        formatted = await self.manager._format_message(FakeMessage(), [keyword])

        self.assertIn('<a href="https://t.me/luoyanglang">狼哥</a>', formatted)

    async def test_format_message_uses_cached_username_for_min_sender(self):
        self.manager = TelegramClientManager()
        self.manager.client = FailingEntityClient()
        keyword = SimpleNamespace(content="北京")

        await self.manager._format_message(FakeMessageWithUsername(), [keyword])
        formatted = await self.manager._format_message(FakeMessage(), [keyword])

        self.assertIn('<a href="https://t.me/luoyanglang">狼哥</a>', formatted)

    async def test_format_message_keeps_template_when_sender_lookup_fails(self):
        self.manager = TelegramClientManager()
        self.manager.client = FailingEntityClient()
        keyword = SimpleNamespace(content="北京")

        formatted = await self.manager._format_message(FakeMessage(), [keyword])

        self.assertNotEqual("北京", formatted)
        self.assertIn("用户:", formatted)
        self.assertIn("来源:", formatted)
        self.assertIn("命中关键词: 北京", formatted)


def _async_return(value):
    async def inner(*args, **kwargs):
        return value

    return inner


if __name__ == "__main__":
    unittest.main()
