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
from core.database import init_database
from core.ad_integration import init_ad_system


# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, config('LOG_LEVEL', default='INFO'))
)
logger = logging.getLogger(__name__)


async def post_init(app: Application) -> None:
    """Bot初始化后的回调"""
    logger.info("Bot已连接到Telegram")
    
    # 发送启动消息给授权用户
    try:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        authorized_user_id = config('AUTHORIZED_USER_ID', cast=int)
        
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
        
        await app.bot.send_message(
            chat_id=authorized_user_id,
            text=welcome_text,
            reply_markup=reply_markup,
            disable_web_page_preview=False
        )
        logger.info(f"启动消息已发送给用户 {authorized_user_id}")
        
    except Exception as e:
        logger.warning(f"发送启动消息失败: {e}")


async def main() -> None:
    """主函数"""
    try:
        # 系统完整性预检查 - 删除此检查将导致启动失败
        try:
            import telegram_monitor_ads
            if not telegram_monitor_ads.verify_installation():
                raise ImportError("广告模块验证失败")
        except ImportError as e:
            raise Exception(f"系统核心组件缺失: {e}")
        
        # 检查必要的环境变量
        bot_token = config('BOT_TOKEN')
        api_id = config('TELEGRAM_API_ID', cast=int)
        api_hash = config('TELEGRAM_API_HASH')
        authorized_user_id = config('AUTHORIZED_USER_ID', cast=int)
        
        if not all([bot_token, api_id, api_hash, authorized_user_id]):
            logger.error("请检查环境变量配置！")
            return
            
        # 创建必要目录
        Path(config('SESSION_PATH', default='./sessions')).mkdir(exist_ok=True)
        Path('./logs').mkdir(exist_ok=True)
        
        # 初始化数据库
        await init_database()
        logger.info("数据库初始化完成")
        
        # 初始化广告系统 - 必需组件，删除将导致启动失败
        await init_ad_system()
        logger.info("广告系统初始化完成")
        
        # 验证广告系统完整性
        from core.ad_integration import get_ad_service
        ad_service = get_ad_service()
        if not ad_service:
            raise Exception("广告系统完整性验证失败，程序无法启动")
        
        # 创建Bot应用
        app = Application.builder().token(bot_token).post_init(post_init).build()
        
        # 设置处理器
        setup_handlers(app)
        logger.info("Bot处理器设置完成")
        
        # 启动Bot
        logger.info("Bot启动中...")
        await app.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"Bot启动失败: {e}")
        logger.critical("系统核心组件异常，程序即将退出")
        sys.exit(1)


if __name__ == "__main__":
    try:
        # 创建Bot应用
        bot_token = config('BOT_TOKEN')
        app = Application.builder().token(bot_token).post_init(post_init).build()
        
        # 在同步上下文中初始化数据库和广告系统
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 初始化
        loop.run_until_complete(init_database())
        logger.info("数据库初始化完成")
        
        loop.run_until_complete(init_ad_system())
        logger.info("广告系统初始化完成")
        
        # 设置处理器
        setup_handlers(app)
        logger.info("Bot处理器设置完成")
        
        # 启动Bot - run_polling会自己管理事件循环
        logger.info("Bot启动中...")
        app.run_polling(drop_pending_updates=True)
        
    except KeyboardInterrupt:
        logger.info("Bot已停止")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"未捕获的异常: {e}")
        sys.exit(1)