"""
Telegram服务
处理Telegram相关的业务逻辑
"""

import logging
from typing import Dict, List, Optional, Tuple

from core.telegram_client import telegram_client_manager

logger = logging.getLogger(__name__)


class TelegramService:
    """Telegram服务类"""
    
    def __init__(self):
        self.client_manager = telegram_client_manager
    
    async def is_logged_in(self) -> bool:
        """检查是否已登录"""
        return await self.client_manager.is_logged_in()
    
    async def login_with_phone(self, phone: str) -> Tuple[bool, str]:
        """使用手机号登录"""
        return await self.client_manager.login_with_phone(phone)
    
    async def verify_code(self, phone: str, code: str) -> Tuple[bool, str]:
        """验证验证码"""
        return await self.client_manager.verify_code(phone, code)
    
    async def verify_password(self, password: str) -> Tuple[bool, str]:
        """验证两步验证密码"""
        return await self.client_manager.verify_password(password)
    
    async def logout(self) -> bool:
        """退出登录"""
        return await self.client_manager.logout()
    
    async def get_account_status(self) -> Dict:
        """获取账号状态"""
        try:
            is_logged_in = await self.is_logged_in()
            
            if not is_logged_in:
                return {
                    'logged_in': False,
                    'user_info': None,
                    'proxy_status': await self.get_proxy_status()
                }
            
            # 获取用户信息
            client = self.client_manager.client
            if client:
                me = await client.get_me()
                user_info = {
                    'id': me.id,
                    'first_name': me.first_name,
                    'last_name': me.last_name,
                    'username': me.username,
                    'phone': me.phone
                }
            else:
                user_info = None
            
            return {
                'logged_in': True,
                'user_info': user_info,
                'proxy_status': await self.get_proxy_status()
            }
            
        except Exception as e:
            logger.error(f"获取账号状态失败: {e}")
            return {
                'logged_in': False,
                'user_info': None,
                'proxy_status': {'type': 'none', 'status': 'error'}
            }
    
    async def get_available_chats(self) -> List[Dict]:
        """获取可用的聊天列表"""
        return await self.client_manager.get_available_chats()
    
    async def set_target_chat(self, chat_id: int) -> bool:
        """设置目标聊天"""
        return await self.client_manager.set_target_chat(chat_id)
    
    async def get_target_chat(self) -> Optional[Dict]:
        """获取目标聊天信息"""
        return await self.client_manager.get_target_chat()
    
    async def set_proxy(self, proxy_type: str, proxy_url: str = None) -> Tuple[bool, str]:
        """设置代理"""
        try:
            # 验证代理类型
            if proxy_type not in ['none', 'socks5', 'mtproxy']:
                return False, "不支持的代理类型"
            
            # 如果不是无代理，检查URL
            if proxy_type != 'none' and not proxy_url:
                return False, "请提供代理地址"
            
            success = await self.client_manager.set_proxy(proxy_type, proxy_url)
            
            if success:
                return True, "代理设置成功"
            else:
                return False, "代理设置失败"
                
        except Exception as e:
            logger.error(f"设置代理失败: {e}")
            return False, f"设置失败: {str(e)}"
    
    async def get_proxy_status(self) -> Dict:
        """获取代理状态"""
        try:
            config = await self.client_manager.get_proxy_config()
            
            proxy_type = config.get('type', 'none')
            proxy_url = config.get('url')
            
            if proxy_type == 'none':
                return {
                    'type': 'none',
                    'status': '无代理',
                    'url': None
                }
            elif proxy_type == 'socks5':
                return {
                    'type': 'socks5',
                    'status': 'Socks5代理',
                    'url': proxy_url
                }
            elif proxy_type == 'mtproxy':
                return {
                    'type': 'mtproxy',
                    'status': 'MTProxy代理',
                    'url': proxy_url
                }
            else:
                return {
                    'type': 'unknown',
                    'status': '未知代理类型',
                    'url': proxy_url
                }
                
        except Exception as e:
            logger.error(f"获取代理状态失败: {e}")
            return {
                'type': 'error',
                'status': '获取失败',
                'url': None
            }