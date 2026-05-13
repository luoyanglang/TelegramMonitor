"""
Login code helpers.
"""

import json
from typing import Tuple


def normalize_login_code(value: str) -> str:
    """Extract Telegram login code digits from an obfuscated user message."""
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def is_plain_login_code_message(value: str) -> bool:
    """Return whether a message is only login-code digits."""
    text = str(value or "").strip()
    return len(text) >= 3 and text.isdigit()


def encode_login_state(phone: str, code: str = "") -> str:
    """Store pending login phone and keypad-entered code in user state."""
    return json.dumps({"phone": phone, "code": normalize_login_code(code)}, ensure_ascii=False)


def decode_login_state(value: str) -> Tuple[str, str]:
    """Read pending login state, accepting legacy plain phone values."""
    if not value:
        return "", ""

    try:
        data = json.loads(value)
    except (TypeError, ValueError):
        return str(value), ""

    if not isinstance(data, dict):
        return str(value), ""

    return str(data.get("phone") or ""), normalize_login_code(str(data.get("code") or ""))
