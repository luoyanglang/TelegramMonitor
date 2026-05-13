"""
Bot键盘菜单定义
所有菜单都包含🔙返回和❌取消按钮
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    """主菜单 - 4个核心功能"""
    keyboard = [
        [
            InlineKeyboardButton("📱 账号管理", callback_data="account_menu"),
            InlineKeyboardButton("🔍 关键词管理", callback_data="keyword_menu")
        ],
        [
            InlineKeyboardButton("⚙️ 监控控制", callback_data="monitor_menu"),
            InlineKeyboardButton("🚫 黑名单", callback_data="blacklist_menu")
        ],
        [
            InlineKeyboardButton("ℹ️ 帮助信息", callback_data="help_info")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def account_menu() -> InlineKeyboardMarkup:
    """账号管理菜单"""
    keyboard = [
        [
            InlineKeyboardButton("🔑 登录账号", callback_data="login_account"),
            InlineKeyboardButton("🌐 代理设置", callback_data="proxy_settings")
        ],
        [
            InlineKeyboardButton("📊 账号状态", callback_data="account_status"),
            InlineKeyboardButton("🚪 退出账号", callback_data="logout_account")
        ],
        [
            InlineKeyboardButton("🔙 返回主菜单", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def keyword_menu() -> InlineKeyboardMarkup:
    """关键词管理菜单"""
    keyboard = [
        [
            InlineKeyboardButton("➕ 添加关键词", callback_data="add_keyword"),
            InlineKeyboardButton("📋 查看列表", callback_data="list_keywords")
        ],
        [
            InlineKeyboardButton("📥 批量导入", callback_data="import_keywords"),
            InlineKeyboardButton("📤 批量导出", callback_data="export_keywords")
        ],
        [
            InlineKeyboardButton("🔙 返回主菜单", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def monitor_menu() -> InlineKeyboardMarkup:
    """监控控制菜单"""
    keyboard = [
        [
            InlineKeyboardButton("🎯 设置目标", callback_data="set_target"),
            InlineKeyboardButton("📊 监控状态", callback_data="monitor_status")
        ],
        [
            InlineKeyboardButton("▶️ 开始监控", callback_data="start_monitor"),
            InlineKeyboardButton("⏹️ 停止监控", callback_data="stop_monitor")
        ],
        [
            InlineKeyboardButton("🔙 返回主菜单", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def proxy_type_menu() -> InlineKeyboardMarkup:
    """代理类型选择菜单"""
    keyboard = [
        [
            InlineKeyboardButton("🚫 无代理", callback_data="proxy_none"),
            InlineKeyboardButton("🧦 Socks5", callback_data="proxy_socks5")
        ],
        [
            InlineKeyboardButton("🔗 MTProxy", callback_data="proxy_mtproxy")
        ],
        [
            InlineKeyboardButton("🔙 返回", callback_data="account_menu"),
            InlineKeyboardButton("❌ 取消", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def keyword_type_menu() -> InlineKeyboardMarkup:
    """关键词类型选择菜单"""
    keyboard = [
        [
            InlineKeyboardButton("🎯 全字匹配", callback_data="kw_type_0"),
            InlineKeyboardButton("📝 包含匹配", callback_data="kw_type_1")
        ],
        [
            InlineKeyboardButton("🔍 正则表达式", callback_data="kw_type_2"),
            InlineKeyboardButton("🌟 模糊匹配", callback_data="kw_type_3")
        ],
        [
            InlineKeyboardButton("👤 用户匹配", callback_data="kw_type_4")
        ],
        [
            InlineKeyboardButton("🔙 返回", callback_data="keyword_menu"),
            InlineKeyboardButton("❌ 取消", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def keyword_action_menu() -> InlineKeyboardMarkup:
    """关键词动作选择菜单"""
    keyboard = [
        [
            InlineKeyboardButton("✅ 监控", callback_data="kw_action_1"),
            InlineKeyboardButton("🚫 排除", callback_data="kw_action_0")
        ],
        [
            InlineKeyboardButton("🔙 返回", callback_data="keyword_menu"),
            InlineKeyboardButton("❌ 取消", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def keyword_style_menu() -> InlineKeyboardMarkup:
    """关键词样式设置菜单"""
    keyboard = [
        [
            InlineKeyboardButton("🔤 区分大小写", callback_data="style_case"),
            InlineKeyboardButton("**粗体**", callback_data="style_bold")
        ],
        [
            InlineKeyboardButton("*斜体*", callback_data="style_italic"),
            InlineKeyboardButton("__下划线__", callback_data="style_underline")
        ],
        [
            InlineKeyboardButton("~~删除线~~", callback_data="style_strike"),
            InlineKeyboardButton("❝引用❞", callback_data="style_quote")
        ],
        [
            InlineKeyboardButton("`等宽字体`", callback_data="style_mono"),
            InlineKeyboardButton("||剧透||", callback_data="style_spoiler")
        ],
        [
            InlineKeyboardButton("✅ 完成设置", callback_data="style_done")
        ],
        [
            InlineKeyboardButton("🔙 返回", callback_data="keyword_menu"),
            InlineKeyboardButton("❌ 取消", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def confirm_menu(confirm_data: str, cancel_data: str = "main_menu") -> InlineKeyboardMarkup:
    """确认操作菜单"""
    keyboard = [
        [
            InlineKeyboardButton("✅ 确认", callback_data=confirm_data),
            InlineKeyboardButton("❌ 取消", callback_data=cancel_data)
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def back_cancel_menu(back_data: str, cancel_data: str = "main_menu") -> InlineKeyboardMarkup:
    """返回和取消菜单"""
    keyboard = [
        [
            InlineKeyboardButton("🔙 返回", callback_data=back_data),
            InlineKeyboardButton("❌ 取消", callback_data=cancel_data)
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def pagination_menu(page: int, total_pages: int, prefix: str, back_data: str = "main_menu") -> InlineKeyboardMarkup:
    """分页菜单"""
    keyboard = []
    
    # 分页按钮
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ 上页", callback_data=f"{prefix}_page_{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("➡️ 下页", callback_data=f"{prefix}_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # 页码信息
    keyboard.append([InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="noop")])
    
    # 返回按钮
    keyboard.append([
        InlineKeyboardButton("🔙 返回", callback_data=back_data),
        InlineKeyboardButton("❌ 取消", callback_data="main_menu")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def verification_code_keyboard() -> InlineKeyboardMarkup:
    """Telegram login code keypad."""
    keyboard = [
        [
            InlineKeyboardButton("1", callback_data="code_digit_1"),
            InlineKeyboardButton("2", callback_data="code_digit_2"),
            InlineKeyboardButton("3", callback_data="code_digit_3"),
        ],
        [
            InlineKeyboardButton("4", callback_data="code_digit_4"),
            InlineKeyboardButton("5", callback_data="code_digit_5"),
            InlineKeyboardButton("6", callback_data="code_digit_6"),
        ],
        [
            InlineKeyboardButton("7", callback_data="code_digit_7"),
            InlineKeyboardButton("8", callback_data="code_digit_8"),
            InlineKeyboardButton("9", callback_data="code_digit_9"),
        ],
        [
            InlineKeyboardButton("⌫", callback_data="code_delete"),
            InlineKeyboardButton("0", callback_data="code_digit_0"),
            InlineKeyboardButton("✅", callback_data="code_submit"),
        ],
        [
            InlineKeyboardButton("🔙 返回", callback_data="account_menu"),
            InlineKeyboardButton("❌ 取消", callback_data="main_menu"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)



def blacklist_menu() -> InlineKeyboardMarkup:
    """黑名单管理菜单"""
    keyboard = [
        [
            InlineKeyboardButton("👤 屏蔽用户", callback_data="add_blacklist_user"),
            InlineKeyboardButton("👥 屏蔽群组", callback_data="add_blacklist_group")
        ],
        [
            InlineKeyboardButton("📋 查看黑名单", callback_data="list_blacklist")
        ],
        [
            InlineKeyboardButton("🔙 返回主菜单", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def blacklist_type_menu() -> InlineKeyboardMarkup:
    """黑名单类型选择"""
    keyboard = [
        [
            InlineKeyboardButton("👤 用户黑名单", callback_data="list_blacklist_user"),
            InlineKeyboardButton("👥 群组黑名单", callback_data="list_blacklist_group")
        ],
        [
            InlineKeyboardButton("📋 全部黑名单", callback_data="list_blacklist_all")
        ],
        [
            InlineKeyboardButton("🔙 返回", callback_data="blacklist_menu"),
            InlineKeyboardButton("❌ 取消", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
