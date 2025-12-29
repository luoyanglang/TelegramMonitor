"""
监控服务
处理消息监控相关的业务逻辑
"""

import logging
from typing import Dict, Optional, Tuple

from core.telegram_client import telegram_client_manager
from services.keyword_service import KeywordService

logger = logging.getLogger(__name__)


class MonitorService:
    """监控服务类"""
    
    def __init__(self):
        self.client_manager = telegram_client_manager
        self.keyword_service = KeywordService()
    
    async def is_monitoring(self) -> bool:
        """检查是否正在监控"""
        return self.client_manager.is_monitoring
    
    async def get_target_chat(self) -> Optional[Dict]:
        """获取目标聊天信息"""
        return await self.client_manager.get_target_chat()
    
    async def set_target_chat(self, chat_id: int) -> Tuple[bool, str]:
        """设置目标聊天"""
        try:
            success = await self.client_manager.set_target_chat(chat_id)
            if success:
                return True, "目标聊天设置成功"
            else:
                return False, "目标聊天设置失败"
        except Exception as e:
            logger.error(f"设置目标聊天失败: {e}")
            return False, f"设置失败: {str(e)}"
    
    async def start_monitoring(self) -> Tuple[bool, str]:
        """开始监控"""
        try:
            # 检查是否已登录
            if not await self.client_manager.is_logged_in():
                return False, "请先登录Telegram账号"
            
            # 检查是否设置了目标聊天
            target_chat = await self.get_target_chat()
            if not target_chat:
                return False, "请先设置目标聊天"
            
            # 检查是否有关键词
            keyword_count = await self.keyword_service.get_keyword_count(action=1)
            if keyword_count == 0:
                return False, "请先添加监控关键词"
            
            # 开始监控
            success = await self.client_manager.start_monitoring(self.keyword_service)
            
            if success:
                return True, "监控已启动"
            else:
                return False, "监控启动失败"
                
        except Exception as e:
            logger.error(f"启动监控失败: {e}")
            return False, f"启动失败: {str(e)}"
    
    async def stop_monitoring(self) -> Tuple[bool, str]:
        """停止监控"""
        try:
            success = await self.client_manager.stop_monitoring()
            
            if success:
                return True, "监控已停止"
            else:
                return False, "监控停止失败"
                
        except Exception as e:
            logger.error(f"停止监控失败: {e}")
            return False, f"停止失败: {str(e)}"
    
    async def get_monitor_status(self) -> Dict:
        """获取监控状态"""
        try:
            is_monitoring = await self.is_monitoring()
            target_chat = await self.get_target_chat()
            
            # 获取关键词统计
            total_keywords = await self.keyword_service.get_keyword_count()
            monitor_keywords = await self.keyword_service.get_keyword_count(action=1)
            exclude_keywords = await self.keyword_service.get_keyword_count(action=0)
            
            # 获取账号状态
            is_logged_in = await self.client_manager.is_logged_in()
            
            return {
                'is_monitoring': is_monitoring,
                'is_logged_in': is_logged_in,
                'target_chat': target_chat,
                'keyword_stats': {
                    'total': total_keywords,
                    'monitor': monitor_keywords,
                    'exclude': exclude_keywords
                },
                'status_text': self._get_status_text(is_monitoring, is_logged_in, target_chat, monitor_keywords)
            }
            
        except Exception as e:
            logger.error(f"获取监控状态失败: {e}")
            return {
                'is_monitoring': False,
                'is_logged_in': False,
                'target_chat': None,
                'keyword_stats': {'total': 0, 'monitor': 0, 'exclude': 0},
                'status_text': '状态获取失败'
            }
    
    def _get_status_text(self, is_monitoring: bool, is_logged_in: bool, 
                        target_chat: Optional[Dict], monitor_keywords: int) -> str:
        """生成状态文本"""
        if not is_logged_in:
            return "❌ 未登录Telegram账号"
        
        if not target_chat:
            return "⚠️ 未设置目标聊天"
        
        if monitor_keywords == 0:
            return "⚠️ 未设置监控关键词"
        
        if is_monitoring:
            return "🟢 监控运行中"
        else:
            return "🔴 监控已停止"