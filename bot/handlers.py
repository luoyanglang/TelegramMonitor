"""
Bot消息处理器
处理所有用户交互，优先使用消息编辑
"""

import json
import logging
from typing import Dict, Any, Tuple

from decouple import config
from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler, 
    ContextTypes, MessageHandler, filters
)

from bot.keyboards import *
from core.database import get_user_state, set_user_state
from services.keyword_service import KeywordService
from services.telegram_service import TelegramService
from services.monitor_service import MonitorService
from services.blacklist_service import BlacklistService

logger = logging.getLogger(__name__)

# 授权用户ID
AUTHORIZED_USER_ID = config('AUTHORIZED_USER_ID', cast=int)

# 服务实例
keyword_service = KeywordService()
telegram_service = TelegramService()
monitor_service = MonitorService()
blacklist_service = BlacklistService()


def check_authorization(func):
    """检查用户授权装饰器"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id != AUTHORIZED_USER_ID:
            await update.message.reply_text("❌ 您没有权限使用此Bot")
            return
        return await func(update, context)
    return wrapper


async def safe_edit_message(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                          text: str, reply_markup=None, parse_mode=ParseMode.MARKDOWN):
    """安全的消息编辑，失败时删除原消息并发送新消息"""
    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=text, 
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        else:
            # 获取用户状态中的最后消息ID
            user_state = await get_user_state(update.effective_user.id)
            if user_state.last_message_id:
                try:
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=user_state.last_message_id,
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode=parse_mode
                    )
                    return
                except BadRequest:
                    # 编辑失败，删除原消息
                    try:
                        await context.bot.delete_message(
                            chat_id=update.effective_chat.id,
                            message_id=user_state.last_message_id
                        )
                    except:
                        pass
            
            # 发送新消息
            message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
            # 保存消息ID
            await set_user_state(update.effective_user.id, "idle", message_id=message.message_id)
            
    except BadRequest as e:
        logger.warning(f"消息编辑失败: {e}")
        # 删除原消息并发送新消息
        if update.callback_query:
            try:
                await update.callback_query.message.delete()
            except:
                pass
        
        message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        await set_user_state(update.effective_user.id, "idle", message_id=message.message_id)


@check_authorization
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """开始命令"""
    welcome_text = """
🤖 **Telegram Monitor Bot**

欢迎使用Telegram消息监控Bot！

**功能介绍：**
📱 **账号管理** - 登录Telegram账号，设置代理
🔍 **关键词管理** - 添加监控关键词规则
⚙️ **监控控制** - 设置目标群组，控制监控开关
ℹ️ **帮助信息** - 查看详细使用说明

请选择要使用的功能：
"""
    
    message = await update.message.reply_text(
        welcome_text, 
        reply_markup=main_menu(),
        parse_mode=ParseMode.MARKDOWN
    )
    await set_user_state(update.effective_user.id, "idle", message_id=message.message_id)


@check_authorization
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """按钮回调处理器"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    # 主菜单
    if data == "main_menu":
        await show_main_menu(update, context)
    
    # 账号管理
    elif data == "account_menu":
        await show_account_menu(update, context)
    elif data == "login_account":
        await start_login_process(update, context)
    elif data == "proxy_settings":
        await show_proxy_menu(update, context)
    elif data == "account_status":
        await show_account_status(update, context)
    elif data == "logout_account":
        await logout_account(update, context)
    
    # 代理设置
    elif data.startswith("proxy_"):
        await handle_proxy_setting(update, context, data)
    
    # 关键词管理
    elif data == "keyword_menu":
        await show_keyword_menu(update, context)
    elif data == "add_keyword":
        await start_add_keyword(update, context)
    elif data == "list_keywords":
        await show_keyword_list(update, context)
    elif data == "import_keywords":
        await import_keywords(update, context)
    elif data == "export_keywords":
        await export_keywords(update, context)
    
    # 关键词类型和动作
    elif data.startswith("kw_type_"):
        await handle_keyword_type(update, context, data)
    elif data.startswith("kw_action_"):
        await handle_keyword_action(update, context, data)
    elif data.startswith("style_"):
        await handle_keyword_style(update, context, data)
    
    # 监控控制
    elif data == "monitor_menu":
        await show_monitor_menu(update, context)
    elif data == "set_target":
        await show_target_selection(update, context)
    elif data == "monitor_status":
        await show_monitor_status(update, context)
    elif data == "start_monitor":
        await start_monitoring(update, context)
    elif data == "stop_monitor":
        await stop_monitoring(update, context)
    elif data.startswith("set_target_"):
        chat_id = int(data.split('_')[-1])
        success, message = await monitor_service.set_target_chat(chat_id)
        text = f"{'✅' if success else '❌'} {message}"
        await safe_edit_message(update, context, text, back_cancel_menu("monitor_menu"))
    
    # 关键词列表相关
    elif data.startswith("kw_list_page_"):
        page = int(data.split('_')[-1])
        await show_keyword_list(update, context, page)
    elif data.startswith("edit_kw_"):
        keyword_id = int(data.split('_')[-1])
        await edit_keyword(update, context, keyword_id)
    elif data.startswith("del_kw_"):
        keyword_id = int(data.split('_')[-1])
        await delete_keyword_confirm(update, context, keyword_id)
    elif data.startswith("confirm_del_kw_"):
        keyword_id = int(data.split('_')[-1])
        await delete_keyword(update, context, keyword_id)
    
    # 确认操作
    elif data == "confirm_logout":
        success = await telegram_service.logout()
        text = f"{'✅' if success else '❌'} {'退出成功' if success else '退出失败'}"
        await safe_edit_message(update, context, text, back_cancel_menu("account_menu"))
    
    # 帮助信息
    elif data == "help_info":
        await show_help_info(update, context)
    
    # 黑名单管理
    elif data == "blacklist_menu":
        await show_blacklist_menu(update, context)
    elif data == "add_blacklist_user":
        await start_add_blacklist(update, context, 0)
    elif data == "add_blacklist_group":
        await start_add_blacklist(update, context, 1)
    elif data == "list_blacklist":
        await show_blacklist_type_menu(update, context)
    elif data == "list_blacklist_user":
        await show_blacklist_list(update, context, target_type=0)
    elif data == "list_blacklist_group":
        await show_blacklist_list(update, context, target_type=1)
    elif data == "list_blacklist_all":
        await show_blacklist_list(update, context)
    elif data.startswith("bl_list_page_"):
        parts = data.split('_')
        page = int(parts[-1])
        target_type = int(parts[-2]) if parts[-2] != 'all' else None
        await show_blacklist_list(update, context, target_type=target_type, page=page)
    elif data.startswith("del_bl_"):
        bl_id = int(data.split('_')[-1])
        await delete_blacklist_confirm(update, context, bl_id)
    elif data.startswith("confirm_del_bl_"):
        bl_id = int(data.split('_')[-1])
        await delete_blacklist(update, context, bl_id)
    
    # 快捷屏蔽（从转发消息的按钮触发）
    elif data.startswith("block_user_"):
        user_id = data.replace("block_user_", "")
        success, message = await blacklist_service.add_to_blacklist(user_id, target_type=0)
        if success:
            await query.answer("✅ 已屏蔽此用户", show_alert=True)
            # 更新按钮状态
            await update_block_button(update, context, "user", user_id, blocked=True)
        else:
            await query.answer(message, show_alert=True)
    elif data.startswith("block_chat_"):
        chat_id = data.replace("block_chat_", "")
        success, message = await blacklist_service.add_to_blacklist(chat_id, target_type=1)
        if success:
            await query.answer("✅ 已屏蔽此群组", show_alert=True)
            # 更新按钮状态
            await update_block_button(update, context, "chat", chat_id, blocked=True)
        else:
            await query.answer(message, show_alert=True)
    
    # 解除屏蔽
    elif data.startswith("unblock_user_"):
        user_id = data.replace("unblock_user_", "")
        # 查找并删除黑名单记录
        items = await blacklist_service.get_blacklist(target_type=0, per_page=0)
        for item in items:
            if item['target_id'] == user_id:
                await blacklist_service.remove_from_blacklist(item['id'])
                break
        await query.answer("✅ 已解除屏蔽", show_alert=True)
        await update_block_button(update, context, "user", user_id, blocked=False)
    elif data.startswith("unblock_chat_"):
        chat_id = data.replace("unblock_chat_", "")
        items = await blacklist_service.get_blacklist(target_type=1, per_page=0)
        for item in items:
            if item['target_id'] == chat_id:
                await blacklist_service.remove_from_blacklist(item['id'])
                break
        await query.answer("✅ 已解除屏蔽", show_alert=True)
        await update_block_button(update, context, "chat", chat_id, blocked=False)
    
    # 无操作（用于页码显示等）
    elif data == "noop":
        pass
    
    else:
        logger.warning(f"未处理的回调数据: {data}")


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示主菜单"""
    text = """
🤖 **Telegram Monitor Bot**

请选择要使用的功能：

📱 **账号管理** - 登录账号、设置代理
🔍 **关键词管理** - 管理监控关键词
⚙️ **监控控制** - 控制监控开关
🚫 **黑名单** - 屏蔽用户或群组
ℹ️ **帮助信息** - 查看使用说明
"""
    await safe_edit_message(update, context, text, main_menu())


async def show_account_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示账号管理菜单"""
    # 获取账号状态
    is_logged_in = await telegram_service.is_logged_in()
    status_text = "✅ 已登录" if is_logged_in else "❌ 未登录"
    
    text = f"""
📱 **账号管理**

当前状态: {status_text}

🔑 **登录账号** - 使用手机号登录Telegram
🌐 **代理设置** - 配置网络代理
📊 **账号状态** - 查看详细状态信息
🚪 **退出账号** - 退出当前登录
"""
    await safe_edit_message(update, context, text, account_menu())


async def show_keyword_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示关键词管理菜单"""
    # 获取关键词统计
    total_keywords = await keyword_service.get_keyword_count()
    monitor_count = await keyword_service.get_keyword_count(action=1)
    exclude_count = await keyword_service.get_keyword_count(action=0)
    
    text = f"""
🔍 **关键词管理**

当前统计:
📊 总关键词: {total_keywords}
✅ 监控规则: {monitor_count}
🚫 排除规则: {exclude_count}

➕ **添加关键词** - 添加新的监控规则
📋 **查看列表** - 查看和编辑现有关键词
📥 **批量导入** - 从文件导入关键词
📤 **批量导出** - 导出关键词到文件
"""
    await safe_edit_message(update, context, text, keyword_menu())


async def show_monitor_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示监控控制菜单"""
    # 获取监控状态
    is_monitoring = await monitor_service.is_monitoring()
    target_chat = await monitor_service.get_target_chat()
    
    status_text = "🟢 监控中" if is_monitoring else "🔴 已停止"
    target_text = target_chat.get('title', '未设置') if target_chat else '未设置'
    
    text = f"""
⚙️ **监控控制**

当前状态: {status_text}
目标群组: {target_text}

🎯 **设置目标** - 选择转发目标群组
📊 **监控状态** - 查看详细监控信息
▶️ **开始监控** - 启动消息监控
⏹️ **停止监控** - 停止消息监控
"""
    await safe_edit_message(update, context, text, monitor_menu())


async def show_help_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示帮助信息"""
    text = """
ℹ️ **使用帮助**

**基本流程：**
1️⃣ 账号管理 → 登录Telegram账号
2️⃣ 关键词管理 → 添加监控关键词
3️⃣ 监控控制 → 设置目标群组
4️⃣ 监控控制 → 开始监控

**关键词类型：**
🎯 **全字匹配** - 完全匹配关键词
📝 **包含匹配** - 消息包含关键词即匹配
🔍 **正则表达式** - 使用正则表达式匹配
🌟 **模糊匹配** - 多个关键词用?分隔
👤 **用户匹配** - 匹配特定用户ID或用户名

**关键词动作：**
✅ **监控** - 匹配时转发消息到目标群组
🚫 **排除** - 匹配时忽略该消息

**注意事项：**
• 本程序仅监听您已加入的群组和频道
• 请遵守相关法律法规和群组规则
• 建议在VPS上运行以保持稳定监控
"""
    
    keyboard = [[InlineKeyboardButton("🔙 返回主菜单", callback_data="main_menu")]]
    await safe_edit_message(update, context, text, InlineKeyboardMarkup(keyboard))


# 消息处理器（用于接收用户输入）
@check_authorization
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理用户发送的消息"""
    user_id = update.effective_user.id
    user_state = await get_user_state(user_id)
    message_text = update.message.text
    
    # 删除用户发送的消息，保持界面整洁
    try:
        await update.message.delete()
    except:
        pass
    
    # 根据用户状态处理消息
    if user_state.current_state == "waiting_phone":
        await handle_phone_input(update, context, message_text)
    elif user_state.current_state == "waiting_verification":
        await handle_verification_input(update, context, message_text)
    elif user_state.current_state == "waiting_password":
        await handle_password_input(update, context, message_text)
    elif user_state.current_state == "waiting_proxy_url":
        await handle_proxy_url_input(update, context, message_text)
    elif user_state.current_state == "waiting_keyword_content":
        await handle_keyword_content_input(update, context, message_text)
    elif user_state.current_state == "waiting_import_file":
        await handle_import_keywords_input(update, context, message_text)
    elif user_state.current_state == "waiting_blacklist_id":
        await handle_blacklist_input(update, context, message_text)
    else:
        # 未知状态，返回主菜单
        await show_main_menu(update, context)


def setup_handlers(app: Application):
    """设置所有处理器"""
    # 命令处理器
    app.add_handler(CommandHandler("start", start_command))
    
    # 回调查询处理器
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # 消息处理器
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    logger.info("所有处理器设置完成")


async def start_login_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """开始登录流程"""
    text = """
🔑 **账号登录**

请发送您的手机号码（包含国家代码）

示例: +8613812345678

⚠️ 注意: 发送后消息会自动删除以保护隐私
"""
    await safe_edit_message(update, context, text, back_cancel_menu("account_menu"))
    await set_user_state(update.effective_user.id, "waiting_phone")


async def handle_phone_input(update: Update, context: ContextTypes.DEFAULT_TYPE, phone: str):
    """处理手机号输入"""
    user_id = update.effective_user.id
    
    # 验证手机号格式
    if not phone.startswith('+') or len(phone) < 10:
        text = """
❌ **手机号格式错误**

请发送正确的手机号码（包含国家代码）

示例: +8613812345678
"""
        await safe_edit_message(update, context, text, back_cancel_menu("account_menu"))
        return
    
    # 尝试登录
    success, message = await telegram_service.login_with_phone(phone)
    
    if success:
        # 登录成功
        text = f"""
✅ **登录成功**

{message}

账号已成功登录！
"""
        await safe_edit_message(update, context, text, back_cancel_menu("account_menu"))
        await set_user_state(user_id, "idle")
    else:
        # 需要验证码
        if "验证码" in message:
            text = f"""
📱 **验证码验证**

{message}

请输入收到的验证码:
"""
            await safe_edit_message(update, context, text, back_cancel_menu("account_menu"))
            await set_user_state(user_id, "waiting_verification", phone)
        else:
            # 登录失败
            text = f"""
❌ **登录失败**

{message}

请重试或检查网络连接。
"""
            await safe_edit_message(update, context, text, back_cancel_menu("account_menu"))
            await set_user_state(user_id, "idle")


async def handle_verification_input(update: Update, context: ContextTypes.DEFAULT_TYPE, code: str):
    """处理验证码输入"""
    user_id = update.effective_user.id
    user_state = await get_user_state(user_id)
    phone = user_state.temp_data
    
    if not phone:
        await show_account_menu(update, context)
        return
    
    # 验证验证码
    success, message = await telegram_service.verify_code(phone, code)
    
    if success:
        # 验证成功
        text = f"""
✅ **验证成功**

{message}

账号已成功登录！
"""
        await safe_edit_message(update, context, text, back_cancel_menu("account_menu"))
        await set_user_state(user_id, "idle")
    else:
        if "密码" in message:
            # 需要两步验证密码
            text = f"""
🔐 **两步验证**

{message}

请输入您的两步验证密码:
"""
            await safe_edit_message(update, context, text, back_cancel_menu("account_menu"))
            await set_user_state(user_id, "waiting_password", phone)
        else:
            # 验证失败
            text = f"""
❌ **验证失败**

{message}

请重新输入验证码:
"""
            await safe_edit_message(update, context, text, back_cancel_menu("account_menu"))


async def handle_password_input(update: Update, context: ContextTypes.DEFAULT_TYPE, password: str):
    """处理密码输入"""
    user_id = update.effective_user.id
    
    # 验证密码
    success, message = await telegram_service.verify_password(password)
    
    if success:
        text = f"""
✅ **登录成功**

{message}

账号已成功登录！
"""
        await safe_edit_message(update, context, text, back_cancel_menu("account_menu"))
        await set_user_state(user_id, "idle")
    else:
        text = f"""
❌ **密码错误**

{message}

请重新输入两步验证密码:
"""
        await safe_edit_message(update, context, text, back_cancel_menu("account_menu"))


async def show_account_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示账号状态"""
    status = await telegram_service.get_account_status()
    
    if status['logged_in']:
        user_info = status['user_info']
        proxy_status = status['proxy_status']
        
        # 构建姓名显示
        name_parts = []
        if user_info.get('first_name'):
            name_parts.append(user_info['first_name'])
        if user_info.get('last_name'):
            name_parts.append(user_info['last_name'])
        full_name = ' '.join(name_parts) if name_parts else '未设置'
        
        text = f"""
📊 **账号状态**

✅ **登录状态:** 已登录

👤 **用户信息:**
• 姓名: {full_name}
• 用户名: @{user_info.get('username', '无')}
• 手机号: {user_info.get('phone', '未知')}
• 用户ID: {user_info.get('id', '未知')}

🌐 **代理状态:** {proxy_status.get('status', '未知')}
"""
    else:
        text = """
📊 **账号状态**

❌ **登录状态:** 未登录

请先登录Telegram账号。
"""
    
    await safe_edit_message(update, context, text, back_cancel_menu("account_menu"))


async def logout_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """退出账号"""
    text = """
🚪 **退出账号**

确认要退出当前登录的Telegram账号吗？

⚠️ 退出后需要重新登录才能使用监控功能。
"""
    
    keyboard = [
        [
            InlineKeyboardButton("✅ 确认退出", callback_data="confirm_logout"),
            InlineKeyboardButton("❌ 取消", callback_data="account_menu")
        ]
    ]
    await safe_edit_message(update, context, text, InlineKeyboardMarkup(keyboard))


async def show_proxy_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示代理设置菜单"""
    proxy_status = await telegram_service.get_proxy_status()
    
    text = f"""
🌐 **代理设置**

当前状态: {proxy_status.get('status', '未知')}
"""
    
    if proxy_status.get('url'):
        text += f"代理地址: {proxy_status['url']}"
    
    text += """

请选择代理类型:

🚫 **无代理** - 直接连接
🧦 **Socks5** - Socks5代理
🔗 **MTProxy** - Telegram MTProxy
"""
    
    await safe_edit_message(update, context, text, proxy_type_menu())


async def handle_proxy_setting(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """处理代理设置"""
    user_id = update.effective_user.id
    
    if data == "proxy_none":
        # 设置无代理
        success, message = await telegram_service.set_proxy("none")
        text = f"""
🚫 **无代理设置**

{message}
"""
        await safe_edit_message(update, context, text, back_cancel_menu("account_menu"))
        
    elif data == "proxy_socks5":
        # 设置Socks5代理
        text = """
🧦 **Socks5代理设置**

请发送Socks5代理地址

格式1: host:port
格式2: host:port:username:password

示例: 127.0.0.1:1080
"""
        await safe_edit_message(update, context, text, back_cancel_menu("account_menu"))
        await set_user_state(user_id, "waiting_proxy_url", "socks5")
        
    elif data == "proxy_mtproxy":
        # 设置MTProxy
        text = """
🔗 **MTProxy设置**

请发送MTProxy链接

格式: https://t.me/proxy?server=...

或直接发送代理参数:
server:port:secret
"""
        await safe_edit_message(update, context, text, back_cancel_menu("account_menu"))
        await set_user_state(user_id, "waiting_proxy_url", "mtproxy")


async def handle_proxy_url_input(update: Update, context: ContextTypes.DEFAULT_TYPE, proxy_url: str):
    """处理代理地址输入"""
    user_id = update.effective_user.id
    user_state = await get_user_state(user_id)
    proxy_type = user_state.temp_data
    
    if not proxy_type:
        await show_proxy_menu(update, context)
        return
    
    # 设置代理
    success, message = await telegram_service.set_proxy(proxy_type, proxy_url)
    
    text = f"""
{'✅' if success else '❌'} **代理设置结果**

{message}
"""
    
    await safe_edit_message(update, context, text, back_cancel_menu("account_menu"))
    await set_user_state(user_id, "idle")


async def start_add_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """开始添加关键词"""
    text = """
➕ **添加关键词**

请发送要监控的关键词内容:

⚠️ 注意: 发送后消息会自动删除
"""
    await safe_edit_message(update, context, text, back_cancel_menu("keyword_menu"))
    await set_user_state(update.effective_user.id, "waiting_keyword_content")


async def handle_keyword_content_input(update: Update, context: ContextTypes.DEFAULT_TYPE, content: str):
    """处理关键词内容输入"""
    user_id = update.effective_user.id
    
    if not content.strip():
        text = """
❌ **关键词不能为空**

请重新发送关键词内容:
"""
        await safe_edit_message(update, context, text, back_cancel_menu("keyword_menu"))
        return
    
    # 保存关键词内容，进入类型选择
    await set_user_state(user_id, "selecting_keyword_type", content.strip())
    
    text = f"""
🔍 **选择匹配类型**

关键词: `{content.strip()}`

请选择匹配类型:

🎯 **全字匹配** - 完全匹配关键词
📝 **包含匹配** - 消息包含关键词即匹配
🔍 **正则表达式** - 使用正则表达式匹配
🌟 **模糊匹配** - 多个关键词用?分隔
👤 **用户匹配** - 匹配特定用户ID或用户名
"""
    
    await safe_edit_message(update, context, text, keyword_type_menu())


async def handle_keyword_type(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """处理关键词类型选择"""
    user_id = update.effective_user.id
    user_state = await get_user_state(user_id)
    content = user_state.temp_data
    
    if not content:
        await show_keyword_menu(update, context)
        return
    
    # 提取类型
    kw_type = int(data.split('_')[-1])
    type_names = {0: "全字匹配", 1: "包含匹配", 2: "正则表达式", 3: "模糊匹配", 4: "用户匹配"}
    
    # 保存类型，进入动作选择
    temp_data = json.dumps({"content": content, "type": kw_type})
    await set_user_state(user_id, "selecting_keyword_action", temp_data)
    
    text = f"""
✅ **选择执行动作**

关键词: `{content}`
类型: {type_names.get(kw_type, '未知')}

请选择执行动作:

✅ **监控** - 匹配时转发消息到目标群组
🚫 **排除** - 匹配时忽略该消息
"""
    
    await safe_edit_message(update, context, text, keyword_action_menu())


async def handle_keyword_action(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """处理关键词动作选择"""
    user_id = update.effective_user.id
    user_state = await get_user_state(user_id)
    
    try:
        temp_data = json.loads(user_state.temp_data)
    except:
        await show_keyword_menu(update, context)
        return
    
    # 提取动作
    action = int(data.split('_')[-1])
    temp_data["action"] = action
    
    action_names = {0: "排除", 1: "监控"}
    
    # 保存动作，进入样式选择
    await set_user_state(user_id, "selecting_keyword_style", json.dumps(temp_data))
    
    text = f"""
🎨 **设置文本样式**

关键词: `{temp_data['content']}`
类型: {keyword_service.TYPE_NAMES.get(temp_data['type'], '未知')}
动作: {action_names.get(action, '未知')}

请选择要应用的文本样式（可多选）:

当前样式: 无
"""
    
    await safe_edit_message(update, context, text, keyword_style_menu())


async def handle_keyword_style(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """处理关键词样式选择"""
    user_id = update.effective_user.id
    user_state = await get_user_state(user_id)
    
    try:
        temp_data = json.loads(user_state.temp_data)
    except:
        await show_keyword_menu(update, context)
        return
    
    if data == "style_done":
        # 完成样式设置，保存关键词
        styles = temp_data.get("styles", {})
        
        success, message = await keyword_service.add_keyword(
            content=temp_data["content"],
            kw_type=temp_data["type"],
            action=temp_data["action"],
            styles=styles
        )
        
        text = f"""
{'✅' if success else '❌'} **关键词添加结果**

{message}
"""
        
        await safe_edit_message(update, context, text, back_cancel_menu("keyword_menu"))
        await set_user_state(user_id, "idle")
        
    else:
        # 切换样式选项
        style_key = data.replace("style_", "")
        style_map = {
            "case": "case_sensitive",
            "bold": "bold", 
            "italic": "italic",
            "underline": "underline",
            "strike": "strikethrough",
            "quote": "quote",
            "mono": "monospace",
            "spoiler": "spoiler"
        }
        
        if style_key in style_map:
            if "styles" not in temp_data:
                temp_data["styles"] = {}
            
            style_name = style_map[style_key]
            temp_data["styles"][style_name] = not temp_data["styles"].get(style_name, False)
            
            # 更新状态
            await set_user_state(user_id, "selecting_keyword_style", json.dumps(temp_data))
            
            # 生成当前样式显示
            current_styles = []
            for key, value in temp_data["styles"].items():
                if value:
                    style_names = {
                        "case_sensitive": "区分大小写",
                        "bold": "粗体",
                        "italic": "斜体", 
                        "underline": "下划线",
                        "strikethrough": "删除线",
                        "quote": "引用",
                        "monospace": "等宽",
                        "spoiler": "剧透"
                    }
                    current_styles.append(style_names.get(key, key))
            
            style_text = ", ".join(current_styles) if current_styles else "无"
            
            text = f"""
🎨 **设置文本样式**

关键词: `{temp_data['content']}`
类型: {keyword_service.TYPE_NAMES.get(temp_data['type'], '未知')}
动作: {keyword_service.ACTION_NAMES.get(temp_data['action'], '未知')}

请选择要应用的文本样式（可多选）:

当前样式: {style_text}
"""
            
            await safe_edit_message(update, context, text, keyword_style_menu())


async def show_keyword_list(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    """显示关键词列表"""
    keywords = await keyword_service.get_keywords(page=page, per_page=5)
    total_count = await keyword_service.get_keyword_count()
    total_pages = (total_count + 4) // 5  # 每页5个
    
    if not keywords:
        text = """
📋 **关键词列表**

暂无关键词，请先添加关键词。
"""
        await safe_edit_message(update, context, text, back_cancel_menu("keyword_menu"))
        return
    
    text = f"""
📋 **关键词列表** (第{page+1}页/共{total_pages}页)

"""
    
    keyboard = []
    for kw in keywords:
        # 生成样式标识
        styles = []
        if kw['styles']['bold']: styles.append('B')
        if kw['styles']['italic']: styles.append('I')
        if kw['styles']['underline']: styles.append('U')
        style_text = f"[{''.join(styles)}]" if styles else ""
        
        # 添加关键词信息
        action_emoji = "✅" if kw['action'] == 1 else "🚫"
        text += f"{action_emoji} `{kw['content'][:20]}{'...' if len(kw['content']) > 20 else ''}` {style_text}\n"
        text += f"   类型: {kw['type_name']} | 动作: {kw['action_name']}\n\n"
        
        # 添加编辑和删除按钮
        keyboard.append([
            InlineKeyboardButton(f"✏️ 编辑 {kw['id']}", callback_data=f"edit_kw_{kw['id']}"),
            InlineKeyboardButton(f"🗑️ 删除 {kw['id']}", callback_data=f"del_kw_{kw['id']}")
        ])
    
    # 添加分页按钮
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ 上页", callback_data=f"kw_list_page_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("➡️ 下页", callback_data=f"kw_list_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # 添加返回按钮
    keyboard.append([
        InlineKeyboardButton("🔙 返回", callback_data="keyword_menu"),
        InlineKeyboardButton("❌ 取消", callback_data="main_menu")
    ])
    
    await safe_edit_message(update, context, text, InlineKeyboardMarkup(keyboard))


async def show_target_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示目标群组选择"""
    # 检查是否已登录
    if not await telegram_service.is_logged_in():
        text = """
❌ **未登录**

请先登录Telegram账号才能设置目标群组。
"""
        await safe_edit_message(update, context, text, back_cancel_menu("monitor_menu"))
        return
    
    # 获取可用聊天列表
    chats = await telegram_service.get_available_chats()
    
    if not chats:
        text = """
⚠️ **无可用群组**

未找到可发送消息的群组或频道。

请确保：
1. 您已加入相关群组/频道
2. 在群组中有发送消息的权限
3. 在频道中有管理员权限
"""
        await safe_edit_message(update, context, text, back_cancel_menu("monitor_menu"))
        return
    
    text = """
🎯 **选择目标群组**

请选择要转发消息的目标群组或频道:

"""
    
    keyboard = []
    for chat in chats[:10]:  # 限制显示前10个
        chat_emoji = "📢" if chat['type'] == '频道' else "👥"
        button_text = f"{chat_emoji} {chat['title'][:20]}{'...' if len(chat['title']) > 20 else ''}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"set_target_{chat['id']}")])
    
    keyboard.append([
        InlineKeyboardButton("🔙 返回", callback_data="monitor_menu"),
        InlineKeyboardButton("❌ 取消", callback_data="main_menu")
    ])
    
    await safe_edit_message(update, context, text, InlineKeyboardMarkup(keyboard))


async def show_monitor_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示监控状态"""
    status = await monitor_service.get_monitor_status()
    
    # 状态图标
    login_icon = "✅" if status['is_logged_in'] else "❌"
    monitor_icon = "🟢" if status['is_monitoring'] else "🔴"
    
    # 目标群组信息
    target_text = "未设置"
    if status['target_chat']:
        target_text = status['target_chat']['title']
    
    text = f"""
📊 **监控状态详情**

{login_icon} **账号状态:** {'已登录' if status['is_logged_in'] else '未登录'}
{monitor_icon} **监控状态:** {'运行中' if status['is_monitoring'] else '已停止'}

🎯 **目标群组:** {target_text}

📊 **关键词统计:**
• 总关键词: {status['keyword_stats']['total']}
• 监控规则: {status['keyword_stats']['monitor']}
• 排除规则: {status['keyword_stats']['exclude']}

💡 **状态说明:** {status['status_text']}
"""
    
    await safe_edit_message(update, context, text, back_cancel_menu("monitor_menu"))


async def start_monitoring(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """开始监控"""
    success, message = await monitor_service.start_monitoring()
    
    text = f"""
{'✅' if success else '❌'} **监控启动结果**

{message}
"""
    
    if success:
        text += """

🟢 监控已启动，开始监听消息...

💡 提示: 
• 监控将在后台持续运行
• 匹配的消息会自动转发到目标群组
• 可随时停止监控
"""
    
    await safe_edit_message(update, context, text, back_cancel_menu("monitor_menu"))


async def stop_monitoring(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """停止监控"""
    success, message = await monitor_service.stop_monitoring()
    
    text = f"""
{'✅' if success else '❌'} **监控停止结果**

{message}
"""
    
    if success:
        text += """

🔴 监控已停止

💡 可随时重新启动监控
"""
    
    await safe_edit_message(update, context, text, back_cancel_menu("monitor_menu"))


async def edit_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE, keyword_id: int):
    """编辑关键词"""
    keyword = await keyword_service.get_keyword_by_id(keyword_id)
    
    if not keyword:
        text = "❌ 关键词不存在"
        await safe_edit_message(update, context, text, back_cancel_menu("keyword_menu"))
        return
    
    # 生成样式显示
    styles = []
    for key, value in keyword['styles'].items():
        if value:
            style_names = {
                'case_sensitive': '区分大小写',
                'bold': '粗体',
                'italic': '斜体',
                'underline': '下划线',
                'strikethrough': '删除线',
                'quote': '引用',
                'monospace': '等宽',
                'spoiler': '剧透'
            }
            styles.append(style_names.get(key, key))
    
    style_text = ', '.join(styles) if styles else '无'
    
    text = f"""
✏️ **编辑关键词**

**ID:** {keyword['id']}
**内容:** `{keyword['content']}`
**类型:** {keyword['type_name']}
**动作:** {keyword['action_name']}
**样式:** {style_text}

暂不支持编辑功能，请删除后重新添加。
"""
    
    keyboard = [
        [InlineKeyboardButton("🗑️ 删除此关键词", callback_data=f"del_kw_{keyword_id}")],
        [
            InlineKeyboardButton("🔙 返回列表", callback_data="list_keywords"),
            InlineKeyboardButton("❌ 取消", callback_data="main_menu")
        ]
    ]
    
    await safe_edit_message(update, context, text, InlineKeyboardMarkup(keyboard))


async def delete_keyword_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, keyword_id: int):
    """确认删除关键词"""
    keyword = await keyword_service.get_keyword_by_id(keyword_id)
    
    if not keyword:
        text = "❌ 关键词不存在"
        await safe_edit_message(update, context, text, back_cancel_menu("keyword_menu"))
        return
    
    text = f"""
🗑️ **确认删除**

确定要删除以下关键词吗？

**内容:** `{keyword['content']}`
**类型:** {keyword['type_name']}
**动作:** {keyword['action_name']}

⚠️ 此操作不可撤销！
"""
    
    keyboard = [
        [
            InlineKeyboardButton("✅ 确认删除", callback_data=f"confirm_del_kw_{keyword_id}"),
            InlineKeyboardButton("❌ 取消", callback_data="list_keywords")
        ]
    ]
    
    await safe_edit_message(update, context, text, InlineKeyboardMarkup(keyboard))


async def delete_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE, keyword_id: int):
    """删除关键词"""
    success, message = await keyword_service.delete_keyword(keyword_id)
    
    text = f"""
{'✅' if success else '❌'} **删除结果**

{message}
"""
    
    await safe_edit_message(update, context, text, back_cancel_menu("keyword_menu"))


async def import_keywords(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """导入关键词"""
    text = """
📥 **批量导入关键词**

请发送包含关键词的文本，每行一个关键词。

示例:
```
关键词1
关键词2
关键词3
```

⚠️ 注意: 发送后消息会自动删除
"""
    
    await safe_edit_message(update, context, text, back_cancel_menu("keyword_menu"))
    await set_user_state(update.effective_user.id, "waiting_import_file")


async def handle_import_keywords_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """处理批量导入关键词输入"""
    user_id = update.effective_user.id
    
    if not text.strip():
        result_text = """
❌ **导入失败**

内容不能为空，请重新发送关键词列表。
"""
        await safe_edit_message(update, context, result_text, back_cancel_menu("keyword_menu"))
        return
    
    # 解析关键词（每行一个）
    lines = text.strip().split('\n')
    keywords_data = []
    
    for line in lines:
        keyword = line.strip()
        if keyword:
            keywords_data.append({
                'content': keyword,
                'type': 1,  # 默认包含匹配
                'action': 1,  # 默认监控
            })
    
    if not keywords_data:
        result_text = """
❌ **导入失败**

未找到有效的关键词，请检查格式后重试。
"""
        await safe_edit_message(update, context, result_text, back_cancel_menu("keyword_menu"))
        await set_user_state(user_id, "idle")
        return
    
    # 批量添加关键词
    success, message = await keyword_service.batch_add_keywords(keywords_data)
    
    result_text = f"""
{'✅' if success else '❌'} **批量导入结果**

{message}

共解析 {len(keywords_data)} 个关键词
"""
    
    await safe_edit_message(update, context, result_text, back_cancel_menu("keyword_menu"))
    await set_user_state(user_id, "idle")


async def export_keywords(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """导出关键词"""
    keywords_json = await keyword_service.export_keywords()
    
    if not keywords_json:
        text = """
❌ **导出失败**

没有可导出的关键词或导出过程中出现错误。
"""
        await safe_edit_message(update, context, text, back_cancel_menu("keyword_menu"))
        return
    
    # 发送文件
    try:
        import io
        file_content = io.BytesIO(keywords_json.encode('utf-8'))
        file_content.name = 'keywords_export.json'
        
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=file_content,
            filename='keywords_export.json',
            caption='📤 关键词导出文件'
        )
        
        text = """
✅ **导出成功**

关键词已导出为JSON文件。
"""
        
    except Exception as e:
        logger.error(f"导出文件失败: {e}")
        text = f"""
❌ **导出失败**

{str(e)}

以下是导出内容:

```json
{keywords_json[:1000]}{'...' if len(keywords_json) > 1000 else ''}
```
"""
    
    await safe_edit_message(update, context, text, back_cancel_menu("keyword_menu"))


# ==================== 黑名单管理 ====================

async def show_blacklist_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示黑名单管理菜单"""
    user_count = await blacklist_service.get_blacklist_count(target_type=0)
    group_count = await blacklist_service.get_blacklist_count(target_type=1)
    
    text = f"""
🚫 **黑名单管理**

当前统计:
👤 屏蔽用户: {user_count}
👥 屏蔽群组: {group_count}

**功能说明:**
• 被屏蔽的用户发送的消息不会被转发
• 被屏蔽的群组中的消息不会被转发
"""
    await safe_edit_message(update, context, text, blacklist_menu())


async def start_add_blacklist(update: Update, context: ContextTypes.DEFAULT_TYPE, target_type: int):
    """开始添加黑名单"""
    type_name = "用户" if target_type == 0 else "群组"
    
    text = f"""
🚫 **添加{type_name}黑名单**

请发送要屏蔽的{type_name}ID:

示例: 
• 用户ID: 123456789
• 群组ID: -1001234567890

💡 提示: 可以从转发的消息中获取ID
"""
    await safe_edit_message(update, context, text, back_cancel_menu("blacklist_menu"))
    await set_user_state(update.effective_user.id, "waiting_blacklist_id", str(target_type))


async def handle_blacklist_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """处理黑名单ID输入"""
    user_id = update.effective_user.id
    user_state = await get_user_state(user_id)
    target_type = int(user_state.temp_data) if user_state.temp_data else 0
    
    # 清理输入
    target_id = text.strip()
    
    # 验证ID格式
    try:
        int(target_id)
    except ValueError:
        result_text = """
❌ **ID格式错误**

请输入有效的数字ID。
"""
        await safe_edit_message(update, context, result_text, back_cancel_menu("blacklist_menu"))
        return
    
    # 添加到黑名单
    success, message = await blacklist_service.add_to_blacklist(target_id, target_type)
    
    result_text = f"""
{'✅' if success else '❌'} **添加结果**

{message}
"""
    await safe_edit_message(update, context, result_text, back_cancel_menu("blacklist_menu"))
    await set_user_state(user_id, "idle")


async def show_blacklist_type_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示黑名单类型选择"""
    text = """
📋 **查看黑名单**

请选择要查看的黑名单类型:
"""
    await safe_edit_message(update, context, text, blacklist_type_menu())


async def show_blacklist_list(update: Update, context: ContextTypes.DEFAULT_TYPE, target_type: int = None, page: int = 0):
    """显示黑名单列表"""
    items = await blacklist_service.get_blacklist(target_type=target_type, page=page, per_page=5)
    total_count = await blacklist_service.get_blacklist_count(target_type=target_type)
    total_pages = max(1, (total_count + 4) // 5)
    
    type_text = "全部" if target_type is None else ("用户" if target_type == 0 else "群组")
    
    if not items:
        text = f"""
📋 **{type_text}黑名单**

暂无记录
"""
        await safe_edit_message(update, context, text, back_cancel_menu("blacklist_menu"))
        return
    
    text = f"""
📋 **{type_text}黑名单** (第{page+1}页/共{total_pages}页)

"""
    
    keyboard = []
    for item in items:
        type_emoji = "👤" if item['target_type'] == 0 else "👥"
        name_text = f" ({item['name']})" if item['name'] else ""
        text += f"{type_emoji} `{item['target_id']}`{name_text}\n"
        text += f"   添加时间: {item['created_at']}\n\n"
        
        keyboard.append([
            InlineKeyboardButton(f"🗑️ 移除 {item['target_id'][:10]}", callback_data=f"del_bl_{item['id']}")
        ])
    
    # 分页按钮
    nav_buttons = []
    type_str = str(target_type) if target_type is not None else 'all'
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ 上页", callback_data=f"bl_list_page_{type_str}_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("➡️ 下页", callback_data=f"bl_list_page_{type_str}_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([
        InlineKeyboardButton("🔙 返回", callback_data="blacklist_menu"),
        InlineKeyboardButton("❌ 取消", callback_data="main_menu")
    ])
    
    await safe_edit_message(update, context, text, InlineKeyboardMarkup(keyboard))


async def delete_blacklist_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, bl_id: int):
    """确认删除黑名单"""
    items = await blacklist_service.get_blacklist()
    item = next((i for i in items if i['id'] == bl_id), None)
    
    if not item:
        text = "❌ 记录不存在"
        await safe_edit_message(update, context, text, back_cancel_menu("blacklist_menu"))
        return
    
    type_name = "用户" if item['target_type'] == 0 else "群组"
    
    text = f"""
🗑️ **确认移除**

确定要从黑名单移除以下{type_name}吗？

**ID:** `{item['target_id']}`
**类型:** {type_name}

⚠️ 移除后该{type_name}的消息将可以被转发
"""
    
    keyboard = [
        [
            InlineKeyboardButton("✅ 确认移除", callback_data=f"confirm_del_bl_{bl_id}"),
            InlineKeyboardButton("❌ 取消", callback_data="list_blacklist")
        ]
    ]
    
    await safe_edit_message(update, context, text, InlineKeyboardMarkup(keyboard))


async def delete_blacklist(update: Update, context: ContextTypes.DEFAULT_TYPE, bl_id: int):
    """删除黑名单"""
    success, message = await blacklist_service.remove_from_blacklist(bl_id)
    
    text = f"""
{'✅' if success else '❌'} **移除结果**

{message}
"""
    
    await safe_edit_message(update, context, text, back_cancel_menu("blacklist_menu"))



async def update_block_button(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                              block_type: str, target_id: str, blocked: bool):
    """更新屏蔽按钮状态"""
    try:
        message = update.callback_query.message
        if not message or not message.reply_markup:
            return
        
        # 获取当前键盘
        old_keyboard = message.reply_markup.inline_keyboard
        new_keyboard = []
        
        for row in old_keyboard:
            new_row = []
            for button in row:
                if button.callback_data:
                    # 检查是否是需要更新的按钮
                    if block_type == "user" and f"block_user_{target_id}" in button.callback_data:
                        if blocked:
                            new_row.append(InlineKeyboardButton(
                                "✅ 已屏蔽此人", 
                                callback_data=f"unblock_user_{target_id}"
                            ))
                        else:
                            new_row.append(InlineKeyboardButton(
                                "🚫 屏蔽此人", 
                                callback_data=f"block_user_{target_id}"
                            ))
                    elif block_type == "user" and f"unblock_user_{target_id}" in button.callback_data:
                        if blocked:
                            new_row.append(InlineKeyboardButton(
                                "✅ 已屏蔽此人", 
                                callback_data=f"unblock_user_{target_id}"
                            ))
                        else:
                            new_row.append(InlineKeyboardButton(
                                "🚫 屏蔽此人", 
                                callback_data=f"block_user_{target_id}"
                            ))
                    elif block_type == "chat" and f"block_chat_{target_id}" in button.callback_data:
                        if blocked:
                            new_row.append(InlineKeyboardButton(
                                "✅ 已屏蔽此群", 
                                callback_data=f"unblock_chat_{target_id}"
                            ))
                        else:
                            new_row.append(InlineKeyboardButton(
                                "🚫 屏蔽此群", 
                                callback_data=f"block_chat_{target_id}"
                            ))
                    elif block_type == "chat" and f"unblock_chat_{target_id}" in button.callback_data:
                        if blocked:
                            new_row.append(InlineKeyboardButton(
                                "✅ 已屏蔽此群", 
                                callback_data=f"unblock_chat_{target_id}"
                            ))
                        else:
                            new_row.append(InlineKeyboardButton(
                                "🚫 屏蔽此群", 
                                callback_data=f"block_chat_{target_id}"
                            ))
                    else:
                        new_row.append(button)
                else:
                    new_row.append(button)
            new_keyboard.append(new_row)
        
        # 更新消息的键盘
        await message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(new_keyboard))
        
    except Exception as e:
        logger.warning(f"更新按钮状态失败: {e}")
