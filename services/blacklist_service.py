"""
黑名单服务
管理用户和群组黑名单
"""

import logging
from typing import List, Optional, Dict, Tuple

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import AsyncSessionLocal, Blacklist

logger = logging.getLogger(__name__)


class BlacklistService:
    """黑名单服务类"""
    
    # 类型映射
    TYPE_NAMES = {
        0: "用户",
        1: "群组"
    }
    
    async def add_to_blacklist(self, target_id: str, target_type: int = 0, name: str = None) -> Tuple[bool, str]:
        """添加到黑名单"""
        try:
            if not target_id.strip():
                return False, "ID不能为空"
            
            # 检查是否已存在
            async with AsyncSessionLocal() as session:
                query = select(Blacklist).where(
                    Blacklist.target_id == target_id.strip(),
                    Blacklist.target_type == target_type
                )
                result = await session.execute(query)
                existing = result.scalar_one_or_none()
                
                if existing:
                    return False, "该目标已在黑名单中"
                
                # 添加新记录
                blacklist_item = Blacklist(
                    target_id=target_id.strip(),
                    target_type=target_type,
                    name=name
                )
                session.add(blacklist_item)
                await session.commit()
                
            type_name = self.TYPE_NAMES.get(target_type, "未知")
            return True, f"已将{type_name} {target_id} 添加到黑名单"
            
        except Exception as e:
            logger.error(f"添加黑名单失败: {e}")
            return False, f"添加失败: {str(e)}"
    
    async def remove_from_blacklist(self, blacklist_id: int) -> Tuple[bool, str]:
        """从黑名单移除"""
        try:
            async with AsyncSessionLocal() as session:
                item = await session.get(Blacklist, blacklist_id)
                if not item:
                    return False, "记录不存在"
                
                await session.delete(item)
                await session.commit()
                
            return True, "已从黑名单移除"
            
        except Exception as e:
            logger.error(f"移除黑名单失败: {e}")
            return False, f"移除失败: {str(e)}"
    
    async def get_blacklist(self, target_type: Optional[int] = None, page: int = 0, per_page: int = 10) -> List[Dict]:
        """获取黑名单列表"""
        try:
            async with AsyncSessionLocal() as session:
                query = select(Blacklist)
                
                if target_type is not None:
                    query = query.where(Blacklist.target_type == target_type)
                
                query = query.order_by(Blacklist.id.desc())
                if per_page > 0:
                    query = query.offset(page * per_page).limit(per_page)
                
                result = await session.execute(query)
                items = result.scalars().all()
                
                return [
                    {
                        'id': item.id,
                        'target_id': item.target_id,
                        'target_type': item.target_type,
                        'type_name': self.TYPE_NAMES.get(item.target_type, '未知'),
                        'name': item.name or '',
                        'created_at': item.created_at.strftime('%Y-%m-%d %H:%M:%S')
                    }
                    for item in items
                ]
                
        except Exception as e:
            logger.error(f"获取黑名单失败: {e}")
            return []
    
    async def get_blacklist_count(self, target_type: Optional[int] = None) -> int:
        """获取黑名单数量"""
        try:
            async with AsyncSessionLocal() as session:
                query = select(func.count(Blacklist.id))
                
                if target_type is not None:
                    query = query.where(Blacklist.target_type == target_type)
                
                result = await session.execute(query)
                return result.scalar() or 0
                
        except Exception as e:
            logger.error(f"获取黑名单数量失败: {e}")
            return 0
    
    async def is_blacklisted(self, user_id: int = None, chat_id: int = None) -> bool:
        """检查是否在黑名单中"""
        try:
            async with AsyncSessionLocal() as session:
                # 检查用户黑名单
                if user_id:
                    query = select(Blacklist).where(
                        Blacklist.target_id == str(user_id),
                        Blacklist.target_type == 0
                    )
                    result = await session.execute(query)
                    if result.scalar_one_or_none():
                        return True
                
                # 检查群组黑名单
                if chat_id:
                    query = select(Blacklist).where(
                        Blacklist.target_id == str(chat_id),
                        Blacklist.target_type == 1
                    )
                    result = await session.execute(query)
                    if result.scalar_one_or_none():
                        return True
                
                return False
                
        except Exception as e:
            logger.error(f"检查黑名单失败: {e}")
            return False
