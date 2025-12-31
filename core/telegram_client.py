"""
Telegram客户端管理
对应原C#项目的TelegramClientManager
"""

import asyncio
import hashlib
import json
import logging
import os
import random
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from decouple import config
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PasswordHashInvalidError, EmailUnconfirmedError
from telethon.tl.types import User, Chat, Channel, Dialog

from core.database import get_config, set_config
from core.utils import format_datetime

logger = logging.getLogger(__name__)


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
        
        # 用户和聊天缓存
        self.users: Dict[int, User] = {}
        self.chats: Dict[int, Chat] = {}
        
        # 设备指纹管理器
        self.device_fingerprint = DeviceFingerprint(self.session_path)
    
    async def create_client(self, phone: str) -> TelegramClient:
        """创建Telegram客户端"""
        session_file = self.session_path / f"{phone.replace('+', '')}.session"
        
        # 获取或创建设备指纹（持久化）
        fingerprint = self.device_fingerprint.get_or_create()
        
        logger.info(f"使用设备: {fingerprint.get('device_model')} | "
                   f"系统: {fingerprint.get('system_version')} | "
                   f"TG版本: {fingerprint.get('app_version')}")
        
        self.client = TelegramClient(
            str(session_file),
            self.api_id,
            self.api_hash,
            device_model=fingerprint.get('device_model', 'Unknown Device'),
            system_version=fingerprint.get('system_version', 'Unknown'),
            app_version=fingerprint.get('app_version', '10.0.0'),
            lang_code=fingerprint.get('lang_code', 'en'),
            system_lang_code=fingerprint.get('system_lang_code', 'en-US'),
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
        """获取可用的聊天列表（可以发送消息的）"""
        if not await self.is_logged_in():
            return []
        
        available_chats = []
        
        try:
            dialogs = await self.client.get_dialogs()
            
            for dialog in dialogs:
                entity = dialog.entity
                
                # 检查是否可以发送消息
                if isinstance(entity, Channel):
                    if entity.broadcast:  # 频道
                        if entity.creator or (hasattr(entity, 'admin_rights') and entity.admin_rights and entity.admin_rights.post_messages):
                            chat_type = "频道"
                        else:
                            continue
                    else:  # 超级群组
                        # 检查是否被禁言
                        if hasattr(entity, 'banned_rights') and entity.banned_rights and entity.banned_rights.send_messages:
                            continue
                        chat_type = "群组"
                elif isinstance(entity, Chat):
                    # 普通群组，检查是否被踢出或限制
                    if hasattr(entity, 'kicked') and entity.kicked:
                        continue
                    if hasattr(entity, 'left') and entity.left:
                        continue
                    chat_type = "群组"
                else:
                    continue  # 跳过私聊
                
                available_chats.append({
                    'id': entity.id,
                    'title': entity.title,
                    'type': chat_type,
                    'username': getattr(entity, 'username', None)
                })
        
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

            # 同步所有未读消息，确保能接收到所有群组的消息
            logger.info("正在同步消息...")
            await self.client.catch_up()
            logger.info("✓ 消息同步完成")

            # 添加消息处理器
            @self.client.on(events.NewMessage)
            async def message_handler(event):
                await self._handle_new_message(event, keyword_matcher)

            self.is_monitoring = True
            logger.info("✓ 消息处理器已注册，开始监控所有群组消息")
            logger.info("=== 监控启动成功 ===")
            return True

        except Exception as e:
            logger.error(f"开始监控失败: {e}", exc_info=True)
            return False
    
    async def stop_monitoring(self) -> bool:
        """停止监控"""
        try:
            if self.client:
                # 移除所有事件处理器
                self.client.remove_event_handler(self._handle_new_message)
            
            self.is_monitoring = False
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
            
            logger.info(f"📨 新消息 | 群组ID: {chat_id} | 发送者ID: {sender_id} | 有文本: {has_text}")
            
            # 检查黑名单
            from services.blacklist_service import BlacklistService
            blacklist_service = BlacklistService()
            if await blacklist_service.is_blacklisted(user_id=sender_id, chat_id=chat_id):
                logger.info(f"🚫 跳过：用户或群组在黑名单中")
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
    
    async def _send_via_bot(self, text: str, sender_id: int, source_chat_id: int, message_id: int):
        """通过 Bot API 发送消息"""
        import httpx
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        bot_token = config('BOT_TOKEN')
        
        # 构建按钮
        keyboard = []
        
        # 第一行：历史、屏蔽此人、屏蔽此群
        row1 = []
        if source_chat_id and source_chat_id < 0:
            # 超级群组ID格式：-100xxxxxxxxxx，需要去掉-100前缀
            chat_id_for_link = str(abs(source_chat_id))
            if chat_id_for_link.startswith("100"):
                chat_id_for_link = chat_id_for_link[3:]  # 去掉100前缀
            history_link = f"https://t.me/c/{chat_id_for_link}/{message_id}"
            row1.append(InlineKeyboardButton("👀 查看", url=history_link))
        if sender_id:
            row1.append(InlineKeyboardButton("🚫 屏蔽此人", callback_data=f"block_user_{sender_id}"))
        if source_chat_id:
            row1.append(InlineKeyboardButton("🚫 屏蔽此群", callback_data=f"block_chat_{source_chat_id}"))
        if row1:
            keyboard.append(row1)
        
        # 第二行：广告按钮
        try:
            from core.ad_integration import get_ad_service
            ad_service = get_ad_service()
            if ad_service and ad_service.manager:
                ad_button_configs = ad_service.manager.get_buttons()
                if ad_button_configs:
                    ad_row = [
                        InlineKeyboardButton(btn["text"], url=btn["url"])
                        for btn in ad_button_configs
                    ]
                    keyboard.append(ad_row)
        except Exception as e:
            logger.warning(f"获取广告按钮失败: {e}")
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        # 调用 Bot API 发送消息
        async with httpx.AsyncClient() as client:
            # 需要将目标群组ID转换为Bot API格式
            # Telethon 返回的超级群组ID是正数，Bot API 需要 -100 前缀
            target_id = self.target_chat_id
            if target_id > 0:
                # Telethon 格式的超级群组ID，需要转换为 Bot API 格式
                target_id = -1000000000000 - target_id
            # 如果已经是负数，保持不变
            
            logger.info(f"Bot API 目标ID: {target_id}")
            
            payload = {
                "chat_id": target_id,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            }
            
            if reply_markup:
                payload["reply_markup"] = reply_markup.to_json()
            
            response = await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json=payload,
                timeout=30.0
            )
            
            if response.status_code != 200:
                result = response.json()
                logger.error(f"Bot API 发送失败: {result}")
                raise Exception(f"Bot API error: {result.get('description', 'Unknown error')}")
    
    async def _format_message(self, message, matched_keywords) -> str:
        """格式化消息"""
        try:
            # 获取发送者信息
            sender = await message.get_sender()
            sender_name = getattr(sender, 'first_name', '') or getattr(sender, 'title', 'Unknown')
            sender_username = getattr(sender, 'username', None)
            sender_id = message.sender_id
            
            # 获取聊天信息
            chat = await message.get_chat()
            chat_name = getattr(chat, 'title', 'Private Chat')
            chat_id = message.chat_id
            chat_username = getattr(chat, 'username', None)
            
            # 构建用户链接
            if sender_username:
                user_link = f"[{sender_name}](https://t.me/{sender_username})"
            else:
                user_link = f"[{sender_name}](tg://user?id={sender_id})"
            
            # 构建群组链接
            if chat_username:
                chat_link = f"[{chat_name}](https://t.me/{chat_username})"
            elif chat_id < 0:
                # 超级群组/频道
                chat_link = f"[{chat_name}](https://t.me/c/{abs(chat_id) % 10000000000}/{message.id})"
            else:
                chat_link = chat_name
            
            # 构建消息链接
            if chat_username:
                msg_link = f"https://t.me/{chat_username}/{message.id}"
            elif chat_id < 0:
                msg_link = f"https://t.me/c/{abs(chat_id) % 10000000000}/{message.id}"
            else:
                msg_link = None
            
            # 应用样式
            styled_text = message.text
            if msg_link:
                styled_text = f"[{message.text}]({msg_link})"
            
            # 获取广告配置
            header_title = "📨 实时精准获客"
            header_author = ""
            
            try:
                from core.ad_integration import get_ad_service
                ad_service = get_ad_service()
                if ad_service and ad_service.manager:
                    header = ad_service.manager.get_header()
                    if header:
                        header_title = header.get('title', header_title)
                        header_author = header.get('author', '')
            except Exception as e:
                logger.warning(f"获取header配置失败: {e}")
            
            # 构建标题
            title = header_title
            if header_author:
                title += f" {header_author}"
            
            # 格式化消息
            formatted = f"""{title}

用户: {user_link}
来源: 🔍 {chat_link}
内容: {styled_text}
时间: {format_datetime(message.date)}
命中关键词: {', '.join([kw.content for kw in matched_keywords])}
"""
            
            # 添加消息内广告链接（使用 ads 配置）
            try:
                from core.ad_integration import get_ad_service
                ad_service = get_ad_service()
                if ad_service and ad_service.manager:
                    ads = ad_service.manager.get_ads()
                    if ads:
                        formatted += "\n"
                        for ad in ads:
                            formatted += f"🔗 [{ad['title']}]({ad['url']})\n"
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
            proxy_config = {
                'type': proxy_type,
                'url': proxy_url
            }
            
            await set_config("proxy_config", json.dumps(proxy_config))
            
            # 如果客户端已连接，需要重新连接以应用代理
            if self.client and self.client.is_connected():
                await self.client.disconnect()
                # 重新创建客户端时会应用新的代理设置
            
            return True
            
        except Exception as e:
            logger.error(f"设置代理失败: {e}")
            return False
    
    async def get_proxy_config(self) -> Dict:
        """获取代理配置"""
        try:
            config_str = await get_config("proxy_config", "{}")
            return json.loads(config_str)
        except:
            return {'type': 'none', 'url': None}


# 全局客户端管理器实例
telegram_client_manager = TelegramClientManager()