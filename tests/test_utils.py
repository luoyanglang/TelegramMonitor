import unittest

from core.utils import (
    build_telegram_html_link,
    build_telegram_user_html_link,
    build_telegram_text_link,
    build_telegram_user_link,
    escape_html_text,
    escape_markdown_text,
    mask_sensitive_id,
    paginate_items,
    redact_sensitive_text,
)


class UtilsTests(unittest.TestCase):
    def test_mask_sensitive_id_hides_middle_digits(self):
        self.assertEqual(mask_sensitive_id(9876543210), "987***210")

    def test_mask_sensitive_id_handles_short_values(self):
        self.assertEqual(mask_sensitive_id(1234), "****")

    def test_redact_sensitive_text_replaces_secret_values(self):
        text = "The token 123456:SECRET was rejected"
        self.assertEqual(
            redact_sensitive_text(text, ["123456:SECRET"]),
            "The token <redacted> was rejected",
        )

    def test_build_telegram_user_link_prefers_username(self):
        self.assertEqual(
            build_telegram_user_link("Alice", username="@alice", user_id=123),
            "[Alice](https://t.me/alice)",
        )

    def test_build_telegram_user_link_falls_back_to_tg_user_id(self):
        self.assertEqual(
            build_telegram_user_link("Alice", user_id=123),
            "[Alice](tg://user?id=123)",
        )

    def test_build_telegram_user_link_falls_back_to_text(self):
        self.assertEqual(build_telegram_user_link("A [B]"), "A \\[B\\]")

    def test_build_telegram_text_link_escapes_label(self):
        self.assertEqual(
            build_telegram_text_link("A [B](C)", "https://example.com"),
            "[A \\[B\\]\\(C\\)](https://example.com)",
        )

    def test_build_telegram_html_link_escapes_label_and_url(self):
        self.assertEqual(
            build_telegram_html_link("A <B> & C", "https://example.com/?a=1&b=2"),
            '<a href="https://example.com/?a=1&amp;b=2">A &lt;B&gt; &amp; C</a>',
        )

    def test_build_telegram_user_html_link_prefers_username(self):
        self.assertEqual(
            build_telegram_user_html_link("Alice <A>", username="@alice", user_id=123),
            '<a href="https://t.me/alice">Alice &lt;A&gt;</a>',
        )

    def test_build_telegram_user_html_link_falls_back_to_user_id(self):
        self.assertEqual(
            build_telegram_user_html_link("Alice", user_id=123),
            '<a href="tg://user?id=123">Alice</a>',
        )

    def test_escape_html_text_does_not_backslash_markdown_links(self):
        self.assertEqual(
            escape_html_text("[hello](tg://user?id=123) <tag>"),
            "[hello](tg://user?id=123) &lt;tag&gt;",
        )

    def test_escape_markdown_text_escapes_embedded_links(self):
        self.assertEqual(
            escape_markdown_text("[hello](https://example.com)"),
            "\\[hello\\]\\(https://example.com\\)",
        )

    def test_paginate_items_clamps_page(self):
        page_items, page, total_pages = paginate_items(list(range(25)), page=9, page_size=10)

        self.assertEqual(page_items, [20, 21, 22, 23, 24])
        self.assertEqual(page, 2)
        self.assertEqual(total_pages, 3)


if __name__ == "__main__":
    unittest.main()
