"""
工具函数模块
提供全项目通用的工具函数
"""

from datetime import datetime
from html import escape as html_escape
import math
from typing import Optional, Sequence, TypeVar
import pytz

T = TypeVar("T")


MARKDOWN_SPECIAL_CHARS = "\\_*[]()`"


def mask_sensitive_id(value: object, visible: int = 3) -> str:
    """Mask IDs in logs while keeping enough context for debugging."""
    text = str(value)
    if len(text) <= visible * 2:
        return "*" * len(text)
    return f"{text[:visible]}***{text[-visible:]}"


def redact_sensitive_text(text: object, secrets: list[object]) -> str:
    """Redact known secret values before logging external exception text."""
    redacted = str(text)
    for secret in secrets:
        if secret:
            redacted = redacted.replace(str(secret), "<redacted>")
    return redacted


def escape_markdown_text(text: object) -> str:
    """Escape text used in Telegram Markdown fields."""
    escaped = str(text or "")
    for char in MARKDOWN_SPECIAL_CHARS:
        escaped = escaped.replace(char, f"\\{char}")
    return escaped


def escape_html_text(text: object) -> str:
    """Escape text used in Telegram HTML parse mode."""
    return html_escape(str(text or ""), quote=False)


def build_telegram_user_link(name: object, username: object = None, user_id: object = None) -> str:
    """Build a best-effort Telegram Markdown user link."""
    display_name = escape_markdown_text(name or "Unknown")
    if username:
        username_text = str(username).strip().lstrip("@")
        if username_text:
            return f"[{display_name}](https://t.me/{username_text})"

    if user_id not in (None, ""):
        return f"[{display_name}](tg://user?id={int(user_id)})"

    return display_name


def build_telegram_text_link(label: object, url: str) -> str:
    """Build a Telegram Markdown text link with an escaped label."""
    return f"[{escape_markdown_text(label)}]({url})"


def build_telegram_html_link(label: object, url: str) -> str:
    """Build a Telegram HTML text link with escaped label and href."""
    escaped_url = html_escape(str(url), quote=True)
    return f'<a href="{escaped_url}">{escape_html_text(label)}</a>'


def build_telegram_user_url(username: object = None, user_id: object = None) -> Optional[str]:
    """Build the best available Telegram profile URL for a user."""
    if username:
        username_text = str(username).strip().lstrip("@")
        if username_text:
            return f"https://t.me/{username_text}"

    if user_id not in (None, ""):
        return f"tg://user?id={int(user_id)}"

    return None


def build_telegram_user_html_link(name: object, username: object = None, user_id: object = None) -> str:
    """Build a best-effort Telegram HTML user link."""
    display_name = name or "Unknown"
    username_url = build_telegram_user_url(username=username)
    if username_url:
        return build_telegram_html_link(display_name, username_url)

    if user_id not in (None, ""):
        user_id_text = str(int(user_id))
        user_link = build_telegram_html_link(display_name, build_telegram_user_url(user_id=user_id_text))
        return f'{user_link} <code>{user_id_text}</code>'

    return escape_html_text(display_name)


def paginate_items(items: Sequence[T], page: int, page_size: int) -> tuple[list[T], int, int]:
    """Return a clamped page slice and pagination metadata."""
    if page_size <= 0:
        raise ValueError("page_size must be greater than zero")

    total_pages = max(1, math.ceil(len(items) / page_size))
    current_page = min(max(page, 0), total_pages - 1)
    start = current_page * page_size
    end = start + page_size
    return list(items[start:end]), current_page, total_pages


def get_current_time(timezone: str = 'Asia/Shanghai', format: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    获取当前时间
    
    Args:
        timezone: 时区，默认为上海时区
        format: 时间格式，默认为 'YYYY-MM-DD HH:MM:SS'
        
    Returns:
        格式化后的时间字符串
    """
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)
    return now.strftime(format)


def format_timestamp(timestamp: float, timezone: str = 'Asia/Shanghai', format: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    格式化时间戳
    
    Args:
        timestamp: Unix 时间戳
        timezone: 时区，默认为上海时区
        format: 时间格式，默认为 'YYYY-MM-DD HH:MM:SS'
        
    Returns:
        格式化后的时间字符串
    """
    tz = pytz.timezone(timezone)
    dt = datetime.fromtimestamp(timestamp, tz)
    return dt.strftime(format)


def format_datetime(dt: datetime, timezone: str = 'Asia/Shanghai', format: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    格式化 datetime 对象
    
    Args:
        dt: datetime 对象
        timezone: 时区，默认为上海时区
        format: 时间格式，默认为 'YYYY-MM-DD HH:MM:SS'
        
    Returns:
        格式化后的时间字符串
    """
    if dt.tzinfo is None:
        # 如果没有时区信息，假设为 UTC
        dt = pytz.utc.localize(dt)
    
    tz = pytz.timezone(timezone)
    dt_local = dt.astimezone(tz)
    return dt_local.strftime(format)


def get_relative_time(dt: datetime) -> str:
    """
    获取相对时间描述
    
    Args:
        dt: datetime 对象
        
    Returns:
        相对时间描述，如 "刚刚"、"5分钟前"、"2小时前"
    """
    now = datetime.now(pytz.utc)
    
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    
    diff = now - dt
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "刚刚"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes}分钟前"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours}小时前"
    elif seconds < 2592000:  # 30天
        days = int(seconds / 86400)
        return f"{days}天前"
    else:
        return format_datetime(dt, format='%Y-%m-%d')
