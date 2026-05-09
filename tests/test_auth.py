import unittest

from core.auth import parse_authorized_user_ids


class AuthTests(unittest.TestCase):
    def test_parse_authorized_user_ids_uses_comma_separated_ids(self):
        self.assertEqual(parse_authorized_user_ids("111, 222", fallback_user_id="333"), {111, 222})

    def test_parse_authorized_user_ids_keeps_legacy_single_id_fallback(self):
        self.assertEqual(parse_authorized_user_ids("", fallback_user_id="333"), {333})

    def test_parse_authorized_user_ids_rejects_empty_configuration(self):
        with self.assertRaises(ValueError):
            parse_authorized_user_ids("", fallback_user_id="")

    def test_parse_authorized_user_ids_rejects_invalid_id(self):
        with self.assertRaises(ValueError):
            parse_authorized_user_ids("111, not-a-number", fallback_user_id="")


if __name__ == "__main__":
    unittest.main()
