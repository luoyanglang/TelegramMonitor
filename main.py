#!/usr/bin/env python3
"""
Telegram Monitor Bot - 简化版
完全仿照原C#项目功能的Python Bot版本
"""

import asyncio
import logging
import sys
from pathlib import Path

from decouple import config
from telegram.ext import Application

from bot.handlers import setup_handlers
from core.auth import load_authorized_user_ids
from core.database import init_database
from core.ad_integration import init_ad_system, shutdown_ad_system
from core.utils import mask_sensitive_id, redact_sensitive_text


# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, config('LOG_LEVEL', default='INFO'))
)
logger = logging.getLogger(__name__)

# Avoid leaking bot tokens in HTTP client request URLs at INFO level.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def redact_log_text(text: object) -> str:
    """Remove configured secrets from log messages."""
    return redact_sensitive_text(
        text,
        [
            config('BOT_TOKEN', default=''),
            config('TELEGRAM_API_HASH', default=''),
        ],
    )


async def post_init(app: Application) -> None:
    """Bot初始化后的回调"""
    logger.info("Bot已连接到Telegram")
    
    # 发送启动消息给授权用户
    try:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        welcome_text = """👋 欢迎使用 Telegram Monitor Bot，一款更好用的个人群组/频道/私聊关键词监听系统，如果您看到此消息，说明机器人已经启动成功！

📌 当前版本：2.0.0
📝 发送命令 /start 可以开始使用
🎉 开源地址 https://github.com/luoyanglang/TelegramMonitor
---"""
        
        keyboard = [
            [
                InlineKeyboardButton("📢 关注频道", url="https://t.me/langgefabu"),
                InlineKeyboardButton("💬 社区交流", url="https://t.me/langgepython"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        for authorized_user_id in sorted(load_authorized_user_ids()):
            await app.bot.send_message(
                chat_id=authorized_user_id,
                text=welcome_text,
                reply_markup=reply_markup,
                disable_web_page_preview=False
            )
            logger.info(f"启动消息已发送给用户 {mask_sensitive_id(authorized_user_id)}")
        
    except Exception as e:
        logger.warning(f"发送启动消息失败: {redact_log_text(e)}")


async def post_shutdown(app: Application) -> None:
    """Bot关闭后的清理回调"""
    await shutdown_ad_system()


def build_application(bot_token: str) -> Application:
    """创建 Telegram Bot 应用并注册生命周期回调。"""
    return (
        Application.builder()
        .token(bot_token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )


def validate_required_config() -> str:
    """读取并校验启动必需配置，返回 Bot token。"""
    bot_token = config('BOT_TOKEN')
    api_id = config('TELEGRAM_API_ID', cast=int)
    api_hash = config('TELEGRAM_API_HASH')
    authorized_user_ids = load_authorized_user_ids()

    if not all([bot_token, api_id, api_hash, authorized_user_ids]):
        raise Exception("请检查环境变量配置！")

    return bot_token


async def initialize_runtime() -> None:
    """初始化数据库、广告系统和本地运行目录。"""
    try:
        import telegram_monitor_ads
        if not telegram_monitor_ads.verify_installation():
            raise ImportError("广告模块验证失败")
    except ImportError as e:
        raise Exception(f"系统核心组件缺失: {e}")

    Path(config('SESSION_PATH', default='./sessions')).mkdir(exist_ok=True)
    Path('./logs').mkdir(exist_ok=True)

    await init_database()
    logger.info("数据库初始化完成")

    await init_ad_system()
    logger.info("广告系统初始化完成")

    from core.ad_integration import get_ad_service
    ad_service = get_ad_service()
    if not ad_service:
        raise Exception("广告系统完整性验证失败，程序无法启动")


def run() -> int:
    """单一启动入口。"""
    loop = None

    try:
        bot_token = validate_required_config()
        app = build_application(bot_token)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(initialize_runtime())

        setup_handlers(app)
        logger.info("Bot处理器设置完成")

        logger.info("Bot启动中...")
        app.run_polling(drop_pending_updates=True)
        return 0

    except KeyboardInterrupt:
        logger.info("Bot已停止")
        return 0
    except Exception as e:
        logger.critical(f"未捕获的异常: {redact_log_text(e)}")
        if loop is not None and not loop.is_closed():
            loop.run_until_complete(shutdown_ad_system())
        return 1


if __name__ == "__main__":
    sys.exit(run())
