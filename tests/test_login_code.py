import unittest

from core.login_code import (
    decode_login_state,
    encode_login_state,
    is_plain_login_code_message,
    normalize_login_code,
)
from bot.keyboards import verification_code_keyboard


class LoginCodeTests(unittest.TestCase):
    def test_normalize_login_code_keeps_plain_digits(self):
        self.assertEqual(normalize_login_code("91772"), "91772")

    def test_normalize_login_code_accepts_obfuscated_digits(self):
        self.assertEqual(normalize_login_code("9 1 7-7_2"), "91772")

    def test_plain_login_code_message_detects_unsafe_text(self):
        self.assertTrue(is_plain_login_code_message("14163"))
        self.assertFalse(is_plain_login_code_message("1 4 1 6 3"))

    def test_login_state_round_trips_phone_and_code(self):
        state = encode_login_state("+1234567890", "1 2-3")

        self.assertEqual(decode_login_state(state), ("+1234567890", "123"))

    def test_login_state_accepts_legacy_plain_phone(self):
        self.assertEqual(decode_login_state("+1234567890"), ("+1234567890", ""))

    def test_verification_code_keyboard_has_digits_and_submit(self):
        markup = verification_code_keyboard()
        callback_data = [
            button.callback_data
            for row in markup.inline_keyboard
            for button in row
        ]

        self.assertIn("code_digit_0", callback_data)
        self.assertIn("code_digit_9", callback_data)
        self.assertIn("code_delete", callback_data)
        self.assertIn("code_submit", callback_data)


if __name__ == "__main__":
    unittest.main()
