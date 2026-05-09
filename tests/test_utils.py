import unittest

from core.utils import mask_sensitive_id, redact_sensitive_text


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


if __name__ == "__main__":
    unittest.main()
