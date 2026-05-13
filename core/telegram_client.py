"""
Telegram客户端管理
对应原C#项目的TelegramClientManager
"""

import asyncio
import contextlib
import hashlib
import json
import logging
import os
import random
import uuid
from datetime import datetime, timezone
from time import monotonic
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from decouple import config
from telethon import TelegramClient, events
from telethon.errors import (
    EmailUnconfirmedError,
    PasswordHashInvalidError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
)
from telethon.network.connection import (
    ConnectionTcpMTProxyIntermediate,
    ConnectionTcpMTProxyRandomizedIntermediate,
)
from telethon.tl.types import User, Chat, Channel, Dialog

from core.database import get_config, set_config
from core.login_code import normalize_login_code
from core.utils import (
    build_telegram_html_link,
    build_telegram_user_html_link,
    escape_html_text,
    format_datetime,
)

logger = logging.getLogger(__name__)


def _has_admin_rights(entity) -> bool:
    return bool(getattr(entity, "creator", False) or getattr(entity, "admin_rights", None))


def build_target_chat_info(entity, entity_kind: str) -> Optional[Dict]:
    """Return target chat info when the current account can manage/post to it."""
    if entity_kind == "channel":
        if getattr(entity, "broadcast", False):
            admin_rights = getattr(entity, "admin_rights", None)
            can_post = bool(
                getattr(entity, "creator", False)
                or (admin_rights and getattr(admin_rights, "post_messages", False))
            )
            if not can_post:
                return None
            chat_type = "频道"
        else:
            banned_rights = getattr(entity, "banned_rights", None)
            if banned_rights and getattr(banned_rights, "send_messages", False):
                return None
            if not _has_admin_rights(entity):
                return None
            chat_type = "群组"
    elif entity_kind == "chat":
        if getattr(entity, "kicked", False) or getattr(entity, "left", False):
            return None
        if not _has_admin_rights(entity):
            return None
        chat_type = "群组"
    else:
        return None

    return {
        'id': normalize_bot_api_chat_id(entity.id, entity_kind=entity_kind),
        'title': entity.title,
        'type': chat_type,
        'username': getattr(entity, 'username', None),
    }


def normalize_bot_api_chat_id(chat_id: Optional[int], entity_kind: Optional[str] = None) -> Optional[int]:
    """Normalize Telethon positive IDs to Bot API chat IDs."""
    if chat_id is None:
        return None
    chat_id = int(chat_id)
    if chat_id > 0:
        if entity_kind == "chat":
            return -chat_id
        return -1000000000000 - chat_id
    return chat_id


def bot_api_chat_id_candidates(chat_id: Optional[int]) -> List[int]:
    """Return Bot API target ID candidates for old positive target configs."""
    if chat_id is None:
        return []

    chat_id = int(chat_id)
    primary = normalize_bot_api_chat_id(chat_id)
    candidates = [primary]

    if chat_id > 0:
        basic_group_id = -chat_id
        if basic_group_id not in candidates:
            candidates.append(basic_group_id)

    return [candidate for candidate in candidates if candidate is not None]


def is_same_telegram_chat(chat_id: Optional[int], target_chat_id: Optional[int]) -> bool:
    """Compare Telethon and Bot API chat IDs across their different formats."""
    if chat_id is None or target_chat_id is None:
        return False
    return normalize_bot_api_chat_id(chat_id) == normalize_bot_api_chat_id(target_chat_id)


def private_message_link(chat_id: Optional[int], message_id: Optional[int]) -> Optional[str]:
    """Build a t.me/c link only for private supergroups/channels."""
    if chat_id is None or message_id is None:
        return None

    normalized_chat_id = normalize_bot_api_chat_id(chat_id)
    if normalized_chat_id is None:
        return None

    chat_id_text = str(abs(normalized_chat_id))
    if not chat_id_text.startswith("100"):
        return None

    return f"https://t.me/c/{chat_id_text[3:]}/{message_id}"


def should_skip_message_date(
    message_date: Optional[datetime],
    monitor_started_at: Optional[datetime],
    grace_seconds: int = 5,
) -> bool:
    """Skip messages older than monitor startup to avoid replaying backlog."""
    if not message_date or not monitor_started_at:
        return False

    if message_date.tzinfo is None:
        message_date = message_date.replace(tzinfo=timezone.utc)
    if monitor_started_at.tzinfo is None:
        monitor_started_at = monitor_started_at.replace(tzinfo=timezone.utc)

    return (monitor_started_at - message_date).total_seconds() > grace_seconds


def should_skip_bot_sender(sender) -> bool:
    """Skip messages sent by Telegram bots."""
    return bool(getattr(sender, "bot", False))


# 真实设备数据库 - 基于市场份额的真实设备
DEVICE_DATABASE = {
    "android": [
        # 三星 Galaxy 系列 (市场份额最高)
        {"brand": "Samsung", "model": "SM-S928B", "name": "Galaxy S24 Ultra", "sdk": 34, "android": "14"},
        {"brand": "Samsung", "model": "SM-S918B", "name": "Galaxy S23 Ultra", "sdk": 34, "android": "14"},
        {"brand": "Samsung", "model": "SM-S908B", "name": "Galaxy S22 Ultra", "sdk": 34, "android": "14"},
        {"brand": "Samsung", "model": "SM-G998B", "name": "Galaxy S21 Ultra", "sdk": 33, "android": "13"},
        {"brand": "Samsung", "model": "SM-A546B", "name": "Galaxy A54 5G", "sdk": 34, "android": "14"},
        {"brand": "Samsung", "model": "SM-A536B", "name": "Galaxy A53 5G", "sdk": 34, "android": "14"},
        {"brand": "Samsung", "model": "SM-A346B", "name": "Galaxy A34 5G", "sdk": 34, "android": "14"},
        {"brand": "Samsung", "model": "SM-F946B", "name": "Galaxy Z Fold5", "sdk": 34, "android": "14"},
        {"brand": "Samsung", "model": "SM-F731B", "name": "Galaxy Z Flip5", "sdk": 34, "android": "14"},
        # 小米系列
        {"brand": "Xiaomi", "model": "2312DRA50G", "name": "Xiaomi 14 Pro", "sdk": 34, "android": "14"},
        {"brand": "Xiaomi", "model": "23127PN0CC", "name": "Xiaomi 14", "sdk": 34, "android": "14"},
        {"brand": "Xiaomi", "model": "2210132G", "name": "Xiaomi 13 Pro", "sdk": 34, "android": "14"},
        {"brand": "Xiaomi", "model": "2211133G", "name": "Xiaomi 13", "sdk": 34, "android": "14"},
        {"brand": "Redmi", "model": "23078RKD5C", "name": "Redmi Note 13 Pro+", "sdk": 34, "android": "14"},
        {"brand": "Redmi", "model": "22101316G", "name": "Redmi Note 12 Pro", "sdk": 33, "android": "13"},
        {"brand": "POCO", "model": "23113RKC6G", "name": "POCO X6 Pro", "sdk": 34, "android": "14"},
        # 华为/荣耀
        {"brand": "HUAWEI", "model": "ALN-AL00", "name": "Mate 60 Pro", "sdk": 33, "android": "12"},
        {"brand": "HUAWEI", "model": "NOH-AN00", "name": "Mate 40 Pro", "sdk": 31, "android": "12"},
        {"brand": "HONOR", "model": "PGT-AN10", "name": "Honor Magic6 Pro", "sdk": 34, "android": "14"},
        {"brand": "HONOR", "model": "REP-AN00", "name": "Honor 90 Pro", "sdk": 33, "android": "13"},
        # OPPO/一加
        {"brand": "OPPO", "model": "PHB110", "name": "Find X7 Ultra", "sdk": 34, "android": "14"},
        {"brand": "OPPO", "model": "PHK110", "name": "Find X6 Pro", "sdk": 33, "android": "13"},
        {"brand": "OnePlus", "model": "CPH2551", "name": "OnePlus 12", "sdk": 34, "android": "14"},
        {"brand": "OnePlus", "model": "CPH2449", "name": "OnePlus 11", "sdk": 34, "android": "14"},
        # vivo
        {"brand": "vivo", "model": "V2324A", "name": "X100 Pro", "sdk": 34, "android": "14"},
        {"brand": "vivo", "model": "V2227A", "name": "X90 Pro+", "sdk": 33, "android": "13"},
        # Google Pixel
        {"brand": "Google", "model": "Pixel 8 Pro", "name": "Pixel 8 Pro", "sdk": 34, "android": "14"},
        {"brand": "Google", "model": "Pixel 8", "name": "Pixel 8", "sdk": 34, "android": "14"},
        {"brand": "Google", "model": "Pixel 7 Pro", "name": "Pixel 7 Pro", "sdk": 34, "android": "14"},
        {"brand": "Google", "model": "Pixel 7", "name": "Pixel 7", "sdk": 34, "android": "14"},
    ],
    "ios": [
        # iPhone 系列
        {"model": "iPhone16,2", "name": "iPhone 15 Pro Max", "ios": "17.4"},
        {"model": "iPhone16,1", "name": "iPhone 15 Pro", "ios": "17.4"},
        {"model": "iPhone15,5", "name": "iPhone 15 Plus", "ios": "17.4"},
        {"model": "iPhone15,4", "name": "iPhone 15", "ios": "17.4"},
        {"model": "iPhone15,3", "name": "iPhone 14 Pro Max", "ios": "17.4"},
        {"model": "iPhone15,2", "name": "iPhone 14 Pro", "ios": "17.4"},
        {"model": "iPhone14,8", "name": "iPhone 14 Plus", "ios": "17.3"},
        {"model": "iPhone14,7", "name": "iPhone 14", "ios": "17.3"},
        {"model": "iPhone14,3", "name": "iPhone 13 Pro Max", "ios": "17.3"},
        {"model": "iPhone14,2", "name": "iPhone 13 Pro", "ios": "17.2"},
        {"model": "iPhone14,5", "name": "iPhone 13", "ios": "17.2"},
        {"model": "iPhone13,4", "name": "iPhone 12 Pro Max", "ios": "17.2"},
        {"model": "iPhone13,3", "name": "iPhone 12 Pro", "ios": "17.1"},
    ],
    "desktop": [
        # Windows
        {"os": "Windows", "version": "10.0", "build": "19045", "arch": "x64"},
        {"os": "Windows", "version": "10.0", "build": "22631", "arch": "x64"},  # Win11
        {"os": "Windows", "version": "10.0", "build": "22621", "arch": "x64"},  # Win11
        # macOS
        {"os": "macOS", "version": "14.4", "name": "Sonoma", "arch": "arm64"},
        {"os": "macOS", "version": "14.3", "name": "Sonoma", "arch": "arm64"},
        {"os": "macOS", "version": "13.6", "name": "Ventura", "arch": "x64"},
    ]
}

# Telegram 官方客户端版本
TELEGRAM_VERSIONS = {
    "android": ["10.14.5", "10.14.4", "10.14.3", "10.13.2", "10.12.0"],
    "ios": ["10.14.0", "10.13.0", "10.12.0", "10.11.0"],
    "desktop": ["4.16.8", "4.16.7", "4.16.6", "4.15.0"],
}


class DeviceFingerprint:
    """设备指纹生成器 - 生成真实的设备信息"""
    
    def __init__(self, session_path: Path):
        self.session_path = session_path
        self.fingerprint_file = session_path / "device_fingerprint.json"
    
    def _generate_android_fingerprint(self) -> Dict:
        """生成 Android 设备指纹"""
        device = random.choice(DEVICE_DATABASE["android"])
        tg_version = random.choice(TELEGRAM_VERSIONS["android"])
        
        # 生成真实的 Android 设备信息
        return {
            "platform": "android",
            "device_model": f"{device['brand']} {device['name']}",
            "system_version": f"SDK {device['sdk']}",
            "app_version": tg_version,
            "lang_code": random.choice(["en", "zh-hans", "zh-hant", "ja", "ko", "ru"]),
            "system_lang_code": random.choice(["en-US", "zh-CN", "zh-TW", "ja-JP", "ko-KR", "ru-RU"]),
            # 额外信息用于日志
            "_device_info": {
                "brand": device["brand"],
                "model": device["model"],
                "name": device["name"],
                "android_version": device["android"],
                "sdk": device["sdk"],
            }
        }
    
    def _generate_ios_fingerprint(self) -> Dict:
        """生成 iOS 设备指纹"""
        device = random.choice(DEVICE_DATABASE["ios"])
        tg_version = random.choice(TELEGRAM_VERSIONS["ios"])
        
        return {
            "platform": "ios",
            "device_model": device["name"],
            "system_version": device["ios"],
            "app_version": tg_version,
            "lang_code": random.choice(["en", "zh-hans", "zh-hant", "ja", "ko"]),
            "system_lang_code": random.choice(["en-US", "zh-CN", "zh-TW", "ja-JP", "ko-KR"]),
            "_device_info": {
                "model_id": device["model"],
                "name": device["name"],
                "ios_version": device["ios"],
            }
        }
    
    def _generate_desktop_fingerprint(self) -> Dict:
        """生成桌面设备指纹"""
        device = random.choice(DEVICE_DATABASE["desktop"])
        tg_version = random.choice(TELEGRAM_VERSIONS["desktop"])
        
        if device["os"] == "Windows":
            device_model = f"Desktop"
            system_version = f"Windows {device['version']}"
        else:
            device_model = f"Desktop"
            system_version = f"macOS {device['version']}"
        
        return {
            "platform": "desktop",
            "device_model": device_model,
            "system_version": system_version,
            "app_version": f"{tg_version} x64",
            "lang_code": random.choice(["en", "zh-hans", "zh-hant", "ja", "ko", "ru"]),
            "system_lang_code": random.choice(["en-US", "zh-CN", "zh-TW", "ja-JP", "ko-KR", "ru-RU"]),
            "_device_info": device
        }
    
    def generate(self, platform: str = None) -> Dict:
        """
        生成设备指纹
        platform: android, ios, desktop, 或 None (随机)
        """
        if platform is None:
            # 按市场份额随机选择平台 (Android 70%, iOS 25%, Desktop 5%)
            platform = random.choices(
                ["android", "ios", "desktop"],
                weights=[70, 25, 5]
            )[0]
        
        if platform == "android":
            fingerprint = self._generate_android_fingerprint()
        elif platform == "ios":
            fingerprint = self._generate_ios_fingerprint()
        else:
            fingerprint = self._generate_desktop_fingerprint()
        
        # 添加唯一标识
        fingerprint["device_id"] = str(uuid.uuid4())
        fingerprint["created_at"] = asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0
        
        return fingerprint
    
    def load(self) -> Optional[Dict]:
        """加载已保存的设备指纹"""
        try:
            if self.fingerprint_file.exists():
                with open(self.fingerprint_file, 'r', encoding='utf-8') as f:
                    fingerprint = json.load(f)
                    logger.info(f"加载设备指纹: {fingerprint.get('device_model')} / {fingerprint.get('system_version')}")
                    return fingerprint
        except Exception as e:
            logger.warning(f"加载设备指纹失败: {e}")
        return None
    
    def save(self, fingerprint: Dict) -> bool:
        """保存设备指纹"""
        try:
            with open(self.fingerprint_file, 'w', encoding='utf-8') as f:
                json.dump(fingerprint, f, indent=2, ensure_ascii=False)
            logger.info(f"保存设备指纹: {fingerprint.get('device_model')} / {fingerprint.get('system_version')}")
            return True
        except Exception as e:
            logger.error(f"保存设备指纹失败: {e}")
            return False
    
    def get_or_create(self, platform: str = None) -> Dict:
        """获取或创建设备指纹（持久化）"""
        fingerprint = self.load()
        if fingerprint is None:
            fingerprint = self.generate(platform)
            self.save(fingerprint)
        return fingerprint


class TelegramClientManager:
    """Telegram客户端管理器"""
    
    def __init__(self):
        self.api_id = config('TELEGRAM_API_ID', cast=int)
        self.api_hash = config('TELEGRAM_API_HASH')
        self.session_path = Path(config('SESSION_PATH', default='./sessions'))
        self.session_path.mkdir(exist_ok=True)
        
        self.client: Optional[TelegramClient] = None
        self.is_monitoring = False
        self.target_chat_id: Optional[int] = None
        self._monitor_started_at: Optional[datetime] = None
        self._message_handler = None
        self._message_queue: Optional[asyncio.Queue] = None
        self._message_worker_tasks = set()
        self._http_client = None
        self._processed_messages: Dict[Tuple[int, int], float] = {}
        self._processed_messages_lock = asyncio.Lock()
        
        # 用户和聊天缓存
        self.users: Dict[int, User] = {}
        self.chats: Dict[int, Chat] = {}
        
        # 设备指纹管理器
        self.device_fingerprint = DeviceFingerprint(self.session_path)

    def _get_monitor_queue_size(self) -> int:
        """Return the bounded queue size for decoupling updates from processing."""
        return max(1, config('MONITOR_QUEUE_SIZE', default=2000, cast=int))

    def _get_monitor_worker_count(self) -> int:
        """Return the number of concurrent message processing workers."""
        return max(1, config('MONITOR_WORKER_COUNT', default=4, cast=int))

    def _ensure_message_queue(self) -> asyncio.Queue:
        if self._message_queue is None:
            self._message_queue = asyncio.Queue(maxsize=self._get_monitor_queue_size())
        return self._message_queue

    def _start_message_workers(self, keyword_matcher) -> None:
        self._ensure_message_queue()
        if self._message_worker_tasks:
            return

        for worker_index in range(self._get_monitor_worker_count()):
            task = asyncio.create_task(
                self._message_worker(keyword_matcher),
                name=f"telegram-monitor-worker-{worker_index + 1}",
            )
            self._message_worker_tasks.add(task)
            task.add_done_callback(self._message_worker_tasks.discard)

    async def _stop_message_workers(self) -> None:
        tasks = list(self._message_worker_tasks)
        for task in tasks:
            task.cancel()

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self._message_worker_tasks.clear()
        self._message_queue = None

    async def _message_worker(self, keyword_matcher) -> None:
        queue = self._ensure_message_queue()
        while True:
            event = await queue.get()
            try:
                await self._handle_new_message(event, keyword_matcher)
            finally:
                queue.task_done()

    async def _enqueue_message_event(self, event, keyword_matcher) -> None:
        """Enqueue an event quickly so Telethon update dispatch is not doing heavy work."""
        queue = self._ensure_message_queue()
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning(
                "消息处理队列已满，等待 worker 释放空位: size=%s",
                queue.qsize(),
            )
            await queue.put(event)

    async def _get_http_client(self):
        """Reuse one HTTP client during monitoring to avoid per-message connection setup."""
        if self._http_client is None or self._http_client.is_closed:
            import httpx

            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def _close_http_client(self) -> None:
        if self._http_client is not None:
            with contextlib.suppress(Exception):
                await self._http_client.aclose()
            self._http_client = None

    def _mask_proxy_secret(self, secret: Optional[str]) -> str:
        """隐藏代理敏感信息，避免在状态页泄露密码或密钥。"""
        if not secret:
            return ""
        if len(secret) <= 4:
            return "*" * len(secret)
        return f"{secret[:4]}***"

    def _build_proxy_display_url(
        self,
        proxy_type: str,
        host: str,
        port: int,
        username: Optional[str] = None,
        password: Optional[str] = None,
        secret: Optional[str] = None,
    ) -> str:
        """生成用于展示的代理地址，敏感字段只显示掩码。"""
        if proxy_type == "mtproxy":
            return f"{host}:{port}:{self._mask_proxy_secret(secret)}"

        if username and password:
            return f"{host}:{port}:{username}:******"

        return f"{host}:{port}"

    def _parse_standard_proxy(self, proxy_type: str, proxy_url: str, source: str = "manual") -> Dict:
        """解析 Socks5/HTTP 代理。"""
        if not proxy_url:
            raise ValueError("代理地址不能为空")

        username = None
        password = None

        if "://" in proxy_url:
            parsed = urlparse(proxy_url)
            host = parsed.hostname
            port = parsed.port
            username = parsed.username
            password = parsed.password
        else:
            parts = proxy_url.split(":")
            if len(parts) == 2:
                host, port = parts
            elif len(parts) == 4:
                host, port, username, password = parts
            else:
                raise ValueError("代理地址格式错误")

        if not host or not port:
            raise ValueError("代理地址缺少主机或端口")

        normalized = {
            'type': proxy_type,
            'url': self._build_proxy_display_url(proxy_type, host, int(port), username, password),
            'host': host,
            'port': int(port),
            'username': username or None,
            'password': password or None,
            'source': source,
        }
        return normalized

    def _parse_mtproxy(self, proxy_url: str, source: str = "manual") -> Dict:
        """解析 MTProxy 链接或 server:port:secret 形式。"""
        if not proxy_url:
            raise ValueError("MTProxy 地址不能为空")

        if proxy_url.startswith(("https://t.me/proxy?", "http://t.me/proxy?", "tg://proxy?")):
            parsed = urlparse(proxy_url)
            params = parse_qs(parsed.query)
            server = params.get('server', [None])[0]
            port = params.get('port', [None])[0]
            secret = params.get('secret', [None])[0]
        else:
            parts = proxy_url.split(":", 2)
            if len(parts) != 3:
                raise ValueError("MTProxy 地址格式错误")
            server, port, secret = parts

        if not server or not port or not secret:
            raise ValueError("MTProxy 配置不完整")

        normalized = {
            'type': 'mtproxy',
            'url': self._build_proxy_display_url('mtproxy', server, int(port), secret=secret),
            'server': server,
            'port': int(port),
            'secret': secret,
            'source': source,
        }
        return normalized

    def _normalize_proxy_config(
        self,
        proxy_type: str,
        proxy_url: str = None,
        existing_config: Optional[Dict] = None,
        source: str = "manual",
    ) -> Dict:
        """归一化代理配置，兼容旧配置和环境变量配置。"""
        proxy_type = (proxy_type or 'none').lower()
        existing_config = existing_config or {}

        if proxy_type == 'none':
            return {'type': 'none', 'url': None, 'source': source}

        if proxy_type in {'socks5', 'http'}:
            if existing_config.get('host') and existing_config.get('port'):
                return {
                    'type': proxy_type,
                    'url': existing_config.get('url') or self._build_proxy_display_url(
                        proxy_type,
                        existing_config['host'],
                        int(existing_config['port']),
                        existing_config.get('username'),
                        existing_config.get('password'),
                    ),
                    'host': existing_config['host'],
                    'port': int(existing_config['port']),
                    'username': existing_config.get('username') or None,
                    'password': existing_config.get('password') or None,
                    'source': existing_config.get('source', source),
                }
            return self._parse_standard_proxy(proxy_type, proxy_url or existing_config.get('url'), source)

        if proxy_type == 'mtproxy':
            if existing_config.get('server') and existing_config.get('port') and existing_config.get('secret'):
                return {
                    'type': 'mtproxy',
                    'url': existing_config.get('url') or self._build_proxy_display_url(
                        'mtproxy',
                        existing_config['server'],
                        int(existing_config['port']),
                        secret=existing_config.get('secret'),
                    ),
                    'server': existing_config['server'],
                    'port': int(existing_config['port']),
                    'secret': existing_config['secret'],
                    'source': existing_config.get('source', source),
                }
            return self._parse_mtproxy(proxy_url or existing_config.get('url'), source)

        raise ValueError(f"不支持的代理类型: {proxy_type}")

    def _get_env_proxy_config(self) -> Dict:
        """从环境变量读取代理配置，供无数据库配置时兜底。"""
        proxy_type = config('PROXY_TYPE', default='none').lower()

        if proxy_type == 'none':
            return {'type': 'none', 'url': None, 'source': 'env'}

        if proxy_type in {'socks5', 'http'}:
            host = config('PROXY_HOST', default=None)
            port = config('PROXY_PORT', default=None)
            username = config('PROXY_USERNAME', default=None)
            password = config('PROXY_PASSWORD', default=None)

            if not host or not port:
                raise ValueError("环境变量代理配置缺少 PROXY_HOST 或 PROXY_PORT")

            proxy_url = f"{host}:{port}"
            if username and password:
                proxy_url = f"{proxy_url}:{username}:{password}"

            return self._parse_standard_proxy(proxy_type, proxy_url, source='env')

        if proxy_type == 'mtproxy':
            server = config('PROXY_HOST', default=None)
            port = config('PROXY_PORT', default=None)
            secret = config('PROXY_SECRET', default=None)

            if not server or not port or not secret:
                raise ValueError("环境变量 MTProxy 配置缺少 PROXY_HOST、PROXY_PORT 或 PROXY_SECRET")

            return self._parse_mtproxy(f"{server}:{port}:{secret}", source='env')

        raise ValueError(f"不支持的环境变量代理类型: {proxy_type}")

    def _build_telethon_proxy_settings(self, proxy_config: Dict) -> Dict:
        """将归一化配置转换成 Telethon 需要的 connection/proxy 参数。"""
        proxy_type = proxy_config.get('type', 'none')

        if proxy_type == 'none':
            return {}

        if proxy_type in {'socks5', 'http'}:
            proxy = (
                proxy_type,
                proxy_config['host'],
                int(proxy_config['port']),
                True,
                proxy_config.get('username'),
                proxy_config.get('password'),
            )
            return {'proxy': proxy}

        if proxy_type == 'mtproxy':
            secret = proxy_config['secret']
            connection = (
                ConnectionTcpMTProxyRandomizedIntermediate
                if secret.lower().startswith('dd')
                else ConnectionTcpMTProxyIntermediate
            )
            proxy = (
                proxy_config['server'],
                int(proxy_config['port']),
                secret,
            )
            return {
                'connection': connection,
                'proxy': proxy,
            }

        raise ValueError(f"不支持的代理类型: {proxy_type}")

    async def create_client(self, phone: str) -> TelegramClient:
        """创建Telegram客户端"""
        session_file = self.session_path / f"{phone.replace('+', '')}.session"
        
        # 获取或创建设备指纹（持久化）
        fingerprint = self.device_fingerprint.get_or_create()
        
        logger.info(f"使用设备: {fingerprint.get('device_model')} | "
                   f"系统: {fingerprint.get('system_version')} | "
                   f"TG版本: {fingerprint.get('app_version')}")

        proxy_config = await self.get_proxy_config()
        proxy_settings = self._build_telethon_proxy_settings(proxy_config)
        if proxy_config.get('type') != 'none':
            logger.info(
                f"应用代理配置: {proxy_config.get('type')} | "
                f"{proxy_config.get('url')} | 来源: {proxy_config.get('source', 'manual')}"
            )
        
        self.client = TelegramClient(
            str(session_file),
            self.api_id,
            self.api_hash,
            device_model=fingerprint.get('device_model', 'Unknown Device'),
            system_version=fingerprint.get('system_version', 'Unknown'),
            app_version=fingerprint.get('app_version', '10.0.0'),
            lang_code=fingerprint.get('lang_code', 'en'),
            system_lang_code=fingerprint.get('system_lang_code', 'en-US'),
            catch_up=True,
            **proxy_settings,
        )
        
        return self.client
    
    async def login_with_phone(self, phone: str) -> Tuple[bool, str]:
        """
        使用手机号登录
        返回: (是否需要验证码, 消息)
        """
        try:
            if not self.client:
                await self.create_client(phone)
            
            await self.client.connect()
            
            if await self.client.is_user_authorized():
                await self.load_dialogs()
                await set_config("telegram_phone", phone)
                return True, "登录成功"
            
            # 发送验证码
            await self.client.send_code_request(phone)
            await set_config("telegram_phone", phone)
            return False, "验证码已发送，请输入验证码"
            
        except Exception as e:
            logger.error(f"登录失败: {e}")
            return False, f"登录失败: {str(e)}"
    
    async def verify_code(self, phone: str, code: str) -> Tuple[bool, str]:
        """
        验证验证码
        返回: (是否需要密码, 消息)
        """
        try:
            code = normalize_login_code(code)
            if not code:
                return False, "验证码格式错误，请输入数字验证码"

            if not self.client:
                await self.create_client(phone)
                await self.client.connect()
            
            await self.client.sign_in(phone, code)
            
            if await self.client.is_user_authorized():
                await self.load_dialogs()
                return True, "登录成功"
            
            return False, "登录失败，请检查验证码"
            
        except EmailUnconfirmedError as e:
            return False, "需要输入邮箱验证码"
        except SessionPasswordNeededError:
            return False, "需要输入两步验证密码"
        except PhoneCodeExpiredError:
            return False, "验证码已失效，请重新获取验证码"
        except PhoneCodeInvalidError:
            return False, "验证码无效，请重新输入"
        except Exception as e:
            logger.error(f"验证码验证失败: {e}")
            return False, f"验证失败: {str(e)}"
    
    async def verify_email_code(self, email_code: str) -> Tuple[bool, str]:
        """验证邮箱验证码"""
        try:
            await self.client.sign_in(email_code=email_code)
            
            if await self.client.is_user_authorized():
                await self.load_dialogs()
                return True, "登录成功"
            
            return False, "登录失败，请检查邮箱验证码"
            
        except SessionPasswordNeededError:
            return False, "需要输入两步验证密码"
        except Exception as e:
            logger.error(f"邮箱验证失败: {e}")
            return False, f"验证失败: {str(e)}"
    
    async def verify_password(self, password: str) -> Tuple[bool, str]:
        """验证两步验证密码"""
        try:
            await self.client.sign_in(password=password)
            
            if await self.client.is_user_authorized():
                await self.load_dialogs()
                return True, "登录成功"
            
            return False, "登录失败"
            
        except PasswordHashInvalidError:
            return False, "密码错误，请重新输入"
        except Exception as e:
            logger.error(f"密码验证失败: {e}")
            return False, f"验证失败: {str(e)}"
    
    async def is_logged_in(self) -> bool:
        """检查是否已登录"""
        try:
            if not self.client:
                phone = await get_config("telegram_phone")
                if phone:
                    await self.create_client(phone)
                    await self.client.connect()
                else:
                    return False
            
            if not self.client.is_connected():
                await self.client.connect()
            
            return await self.client.is_user_authorized()
        except:
            return False
    
    async def logout(self) -> bool:
        """退出登录"""
        try:
            await self.stop_monitoring()
            if self.client:
                await self.client.log_out()
                await self.client.disconnect()
                self.client = None
            
            # 清除配置
            await set_config("telegram_phone", "")
            await set_config("target_chat_id", "")
            
            return True
        except Exception as e:
            logger.error(f"退出登录失败: {e}")
            return False
    
    async def load_dialogs(self):
        """加载对话列表"""
        try:
            if not await self.is_logged_in():
                return
            
            dialogs = await self.client.get_dialogs()
            
            for dialog in dialogs:
                entity = dialog.entity
                if isinstance(entity, User):
                    self.users[entity.id] = entity
                elif isinstance(entity, (Chat, Channel)):
                    self.chats[entity.id] = entity
            
            logger.info(f"加载了 {len(self.users)} 个用户和 {len(self.chats)} 个聊天")
            
        except Exception as e:
            logger.error(f"加载对话失败: {e}")
    
    async def get_available_chats(self) -> List[Dict]:
        """获取可作为转发目标的聊天列表（当前账号可管理/可发帖）。"""
        if not await self.is_logged_in():
            return []
        
        available_chats = []
        
        try:
            dialogs = await self.client.get_dialogs()
            
            for dialog in dialogs:
                entity = dialog.entity

                if isinstance(entity, Channel):
                    chat_info = build_target_chat_info(entity, "channel")
                elif isinstance(entity, Chat):
                    chat_info = build_target_chat_info(entity, "chat")
                else:
                    chat_info = None

                if chat_info:
                    available_chats.append(chat_info)
        
        except Exception as e:
            logger.error(f"获取聊天列表失败: {e}")
        
        return available_chats
    
    async def set_target_chat(self, chat_id: int) -> bool:
        """设置目标聊天"""
        try:
            await set_config("target_chat_id", str(chat_id))
            self.target_chat_id = chat_id
            return True
        except Exception as e:
            logger.error(f"设置目标聊天失败: {e}")
            return False
    
    async def get_target_chat(self) -> Optional[Dict]:
        """获取目标聊天信息"""
        try:
            chat_id_str = await get_config("target_chat_id")
            if not chat_id_str:
                return None
            
            chat_id = int(chat_id_str)
            self.target_chat_id = chat_id
            
            # 从缓存中获取聊天信息
            if chat_id in self.chats:
                entity = self.chats[chat_id]
                return {
                    'id': entity.id,
                    'title': entity.title,
                    'username': getattr(entity, 'username', None)
                }
            
            # 如果缓存中没有，尝试从Telegram获取
            if self.client and await self.is_logged_in():
                try:
                    entity = await self.client.get_entity(chat_id)
                    # 更新缓存
                    self.chats[chat_id] = entity
                    return {
                        'id': entity.id,
                        'title': getattr(entity, 'title', f'Chat {chat_id}'),
                        'username': getattr(entity, 'username', None)
                    }
                except Exception as e:
                    logger.warning(f"无法获取聊天实体 {chat_id}: {e}")
            
            return {'id': chat_id, 'title': f'Chat {chat_id}'}
            
        except Exception as e:
            logger.error(f"获取目标聊天失败: {e}")
            return None
    
    async def start_monitoring(self, keyword_matcher) -> bool:
        """开始监控"""
        try:
            logger.info("=== 开始监控流程 ===")

            if self.is_monitoring and self._message_handler:
                logger.info("监控已在运行中，跳过重复注册监听器")
                return True

            if not await self.is_logged_in():
                logger.warning("监控失败：用户未登录")
                return False

            logger.info("✓ 用户已登录")

            if not self.target_chat_id:
                target_chat = await self.get_target_chat()
                if not target_chat:
                    logger.warning("监控失败：未设置目标聊天")
                    return False
                self.target_chat_id = target_chat["id"]

            logger.info(f"✓ 目标聊天ID: {self.target_chat_id}")

            async with self._processed_messages_lock:
                self._processed_messages.clear()

            self._monitor_started_at = datetime.now(timezone.utc)

            self._ensure_message_queue()
            self._start_message_workers(keyword_matcher)

            # 添加消息处理器。这里仅入队，避免大群高频消息被重处理链路拖慢。
            async def message_handler(event):
                await self._enqueue_message_event(event, keyword_matcher)

            self.client.add_event_handler(message_handler, events.NewMessage)
            self._message_handler = message_handler

            self.is_monitoring = True
            try:
                await self.client.catch_up()
            except Exception as e:
                logger.warning(f"监听启动后 catch-up 失败，将继续实时监听: {e}")
            logger.info("✓ 消息处理器已注册，开始监控所有群组消息")
            logger.info("=== 监控启动成功 ===")
            return True

        except Exception as e:
            logger.error(f"开始监控失败: {e}", exc_info=True)
            return False
    
    async def stop_monitoring(self) -> bool:
        """停止监控"""
        try:
            if self.client and self._message_handler:
                self.client.remove_event_handler(self._message_handler, events.NewMessage)
                self._message_handler = None

            async with self._processed_messages_lock:
                self._processed_messages.clear()

            await self._stop_message_workers()
            await self._close_http_client()
            
            self.is_monitoring = False
            self._monitor_started_at = None
            logger.info("停止监控消息")
            return True
            
        except Exception as e:
            logger.error(f"停止监控失败: {e}")
            return False
    
    async def _handle_new_message(self, event, keyword_matcher):
        """处理新消息"""
        try:
            logger.debug(f">>> 收到新消息事件")
            message = event.message
            
            # 记录消息基本信息
            chat_id = message.chat_id if message.chat_id else "Unknown"
            sender_id = message.sender_id if message.sender_id else "Unknown"
            has_text = bool(message.text)

            if is_same_telegram_chat(message.chat_id, self.target_chat_id):
                logger.debug(f"跳过目标群消息，避免转发自循环: chat_id={chat_id}")
                return

            if should_skip_message_date(message.date, self._monitor_started_at):
                logger.debug(f"跳过监控启动前的历史消息: chat_id={chat_id}, message_id={message.id}")
                return

            if await self._is_duplicate_message(message.chat_id, message.id):
                logger.debug(
                    f"跳过重复消息: chat_id={message.chat_id}, message_id={message.id}, sender_id={sender_id}"
                )
                return
            
            logger.debug(f"📨 新消息 | 群组ID: {chat_id} | 发送者ID: {sender_id} | 有文本: {has_text}")

            sender = await message.get_sender()
            if should_skip_bot_sender(sender):
                logger.debug(f"跳过 Bot 消息: chat_id={chat_id}, message_id={message.id}, sender_id={sender_id}")
                return
            
            # 检查黑名单
            from services.blacklist_service import BlacklistService
            blacklist_service = BlacklistService()
            if await blacklist_service.is_blacklisted(user_id=sender_id, chat_id=chat_id):
                logger.debug(f"🚫 跳过：用户或群组在黑名单中")
                return
            
            # 跳过空消息
            if not message.text:
                logger.debug(f"⊘ 跳过：消息无文本内容")
                return
            
            logger.debug(f"消息内容预览: {message.text[:50]}...")
            
            # 检查关键词匹配
            logger.debug(f"开始关键词匹配...")
            matched_keywords = await keyword_matcher.match_message(
                message.text,
                message.sender_id,
                message.chat_id
            )
            
            if not matched_keywords:
                logger.debug(f"⊘ 跳过：未匹配任何关键词")
                return
            
            logger.info(f"✓ 匹配到关键词: {[kw.content for kw in matched_keywords]}")
            
            # 格式化消息
            logger.debug(f"开始格式化消息...")
            formatted_message = await self._format_message(message, matched_keywords)
            
            # 使用 Bot API 发送消息
            logger.info(f"📤 准备通过Bot转发到目标群组: {self.target_chat_id}")
            await self._send_via_bot(formatted_message, sender_id, chat_id, message.id)
            
            logger.info(f"✅ 消息转发成功！")
            
        except Exception as e:
            logger.error(f"❌ 处理消息失败: {e}", exc_info=True)

    async def _is_duplicate_message(self, chat_id: Optional[int], message_id: Optional[int]) -> bool:
        """使用 chat_id + message_id 做短时间去重，避免同一条消息被重复处理。"""
        if chat_id is None or message_id is None:
            return False

        message_key = (chat_id, message_id)
        now = monotonic()

        async with self._processed_messages_lock:
            expired_keys = [
                key for key, processed_at in self._processed_messages.items()
                if now - processed_at > 120
            ]
            for key in expired_keys:
                self._processed_messages.pop(key, None)

            if message_key in self._processed_messages:
                return True

            self._processed_messages[message_key] = now
            return False
    
    async def _send_via_bot(self, text: str, sender_id: int, source_chat_id: int, message_id: int):
        """通过 Bot API 发送消息"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        bot_token = config('BOT_TOKEN')
        
        # 构建按钮
        keyboard = []
        
        # 第一行：历史、屏蔽此人、屏蔽此群
        row1 = []
        if source_chat_id and source_chat_id < 0:
            history_link = private_message_link(source_chat_id, message_id)
            if history_link:
                row1.append(InlineKeyboardButton("👀 查看", url=history_link))
        if sender_id:
            row1.append(InlineKeyboardButton("🚫 屏蔽此人", callback_data=f"block_user_{sender_id}"))
        if source_chat_id:
            row1.append(InlineKeyboardButton("🚫 屏蔽此群", callback_data=f"block_chat_{source_chat_id}"))
        if row1:
            keyboard.append(row1)
        
        # 第二行：广告按钮
        try:
            from core.ad_integration import get_ad_buttons
            ad_button_configs = get_ad_buttons()
            if ad_button_configs:
                ad_row = [
                    InlineKeyboardButton(btn["text"], url=btn["url"])
                    for btn in ad_button_configs
                ]
                keyboard.append(ad_row)
        except Exception as e:
            logger.warning(f"获取广告按钮失败: {e}")
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        client = await self._get_http_client()
        last_error = "Unknown error"

        for target_id in bot_api_chat_id_candidates(self.target_chat_id):
            logger.info(f"Bot API 目标ID: {target_id}")

            payload = {
                "chat_id": target_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }

            if reply_markup:
                payload["reply_markup"] = reply_markup.to_json()

            response = await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json=payload,
            )

            if response.status_code == 200:
                if target_id != self.target_chat_id:
                    self.target_chat_id = target_id
                    await set_config("target_chat_id", str(target_id))
                return

            result = response.json()
            last_error = result.get("description", "Unknown error")
            logger.error(f"Bot API 发送失败: {result}")

            if "chat not found" not in last_error.lower():
                break

        raise Exception(f"Bot API error: {last_error}")
    
    async def _format_message(self, message, matched_keywords) -> str:
        """格式化消息"""
        try:
            # 获取发送者信息
            sender = await message.get_sender()
            sender_name = getattr(sender, 'first_name', '') or getattr(sender, 'title', 'Unknown')
            sender_username = getattr(sender, 'username', None)
            sender_id = message.sender_id

            if sender_id and not sender_username and self.client:
                try:
                    full_sender = await self.client.get_entity(sender_id)
                    sender_name = (
                        getattr(full_sender, 'first_name', '')
                        or getattr(full_sender, 'title', '')
                        or sender_name
                    )
                    sender_username = getattr(full_sender, 'username', None) or sender_username
                except Exception as e:
                    logger.debug(
                        "无法补全发送者信息: sender_id=%s, error=%s",
                        mask_sensitive_id(sender_id),
                        e,
                    )
            
            # 获取聊天信息
            chat = await message.get_chat()
            chat_name = getattr(chat, 'title', 'Private Chat')
            chat_id = message.chat_id
            chat_username = getattr(chat, 'username', None)
            
            # 构建用户链接
            user_link = build_telegram_user_html_link(
                sender_name,
                username=sender_username,
                user_id=sender_id,
            )
            
            # 构建群组链接
            if chat_username:
                chat_link = build_telegram_html_link(chat_name, f"https://t.me/{chat_username}")
            elif chat_id < 0:
                source_link = private_message_link(chat_id, message.id)
                chat_link = build_telegram_html_link(chat_name, source_link) if source_link else escape_html_text(chat_name)
            else:
                chat_link = escape_html_text(chat_name)
            
            # 构建消息链接
            if chat_username:
                msg_link = f"https://t.me/{chat_username}/{message.id}"
            elif chat_id < 0:
                msg_link = private_message_link(chat_id, message.id)
            else:
                msg_link = None
            
            styled_text = escape_html_text(message.text)
            
            # 获取广告配置
            header_title = "📨 实时精准获客"
            header_author = ""
            
            try:
                from core.ad_integration import get_ad_header
                header = get_ad_header()
                if header:
                    header_title = header.get('title', header_title)
                    header_author = header.get('author', '')
            except Exception as e:
                logger.warning(f"获取header配置失败: {e}")
            
            # 构建标题
            title = escape_html_text(header_title)
            if header_author:
                title += f" {escape_html_text(header_author)}"
            
            # 格式化消息
            formatted = f"""{title}

用户: {user_link}
来源: 🔍 {chat_link}
内容: {styled_text}
{f"原文: {build_telegram_html_link('查看消息', msg_link)}" if msg_link else ""}
时间: {format_datetime(message.date)}
命中关键词: {escape_html_text(', '.join([kw.content for kw in matched_keywords]))}
"""
            
            # 添加消息内广告链接（使用 ads 配置）
            try:
                from core.ad_integration import get_ad_links
                ads = get_ad_links()
                if ads:
                    formatted += "\n"
                    for ad in ads:
                        formatted += f"🔗 {build_telegram_html_link(ad['title'], ad['url'])}\n"
            except Exception as e:
                logger.warning(f"获取广告链接失败: {e}")
            
            formatted += "\n---"
            
            return formatted
            
        except Exception as e:
            logger.error(f"格式化消息失败: {e}")
            return message.text
    
    async def set_proxy(self, proxy_type: str, proxy_url: str = None) -> bool:
        """设置代理"""
        try:
            proxy_config = self._normalize_proxy_config(proxy_type, proxy_url, source='manual')
            
            await set_config("proxy_config", json.dumps(proxy_config))
            
            # 代理配置变更后，销毁当前客户端实例，确保下次连接按新代理重建。
            if self.client:
                await self.stop_monitoring()
                if self.client.is_connected():
                    await self.client.disconnect()
                self.client = None
            
            return True
            
        except Exception as e:
            logger.error(f"设置代理失败: {e}")
            return False
    
    async def get_proxy_config(self) -> Dict:
        """获取代理配置"""
        try:
            config_str = await get_config("proxy_config", "{}")
            stored_config = json.loads(config_str) if config_str else {}

            if stored_config and stored_config.get('type'):
                return self._normalize_proxy_config(
                    stored_config.get('type'),
                    stored_config.get('url'),
                    existing_config=stored_config,
                    source=stored_config.get('source', 'manual'),
                )

            return self._get_env_proxy_config()
        except Exception as e:
            logger.warning(f"读取代理配置失败，已回退为无代理: {e}")
            return {'type': 'none', 'url': None, 'source': 'fallback'}


# 全局客户端管理器实例
telegram_client_manager = TelegramClientManager()
