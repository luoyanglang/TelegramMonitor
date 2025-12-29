"""
关键词服务
处理关键词管理和匹配逻辑
"""

import json
import re
import logging
from typing import List, Optional, Dict, Any, Tuple

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import AsyncSessionLocal, Keyword

logger = logging.getLogger(__name__)


class KeywordService:
    """关键词服务类"""
    
    # 关键词类型映射
    TYPE_NAMES = {
        0: "全字匹配",
        1: "包含匹配", 
        2: "正则表达式",
        3: "模糊匹配",
        4: "用户匹配"
    }
    
    # 动作类型映射
    ACTION_NAMES = {
        0: "排除",
        1: "监控"
    }
    
    async def add_keyword(self, content: str, kw_type: int = 1, action: int = 1, 
                         styles: Dict[str, bool] = None) -> Tuple[bool, str]:
        """添加关键词"""
        try:
            if not content.strip():
                return False, "关键词内容不能为空"
            
            # 验证关键词类型
            if kw_type not in range(5):
                return False, "无效的关键词类型"
            
            # 验证动作类型
            if action not in [0, 1]:
                return False, "无效的动作类型"
            
            # 如果是正则表达式，验证语法
            if kw_type == 2:
                try:
                    re.compile(content)
                except re.error as e:
                    return False, f"正则表达式语法错误: {str(e)}"
            
            # 创建关键词对象
            keyword = Keyword(
                content=content.strip(),
                type=kw_type,
                action=action
            )
            
            # 设置样式
            if styles:
                keyword.is_case_sensitive = styles.get('case_sensitive', False)
                keyword.is_bold = styles.get('bold', False)
                keyword.is_italic = styles.get('italic', False)
                keyword.is_underline = styles.get('underline', False)
                keyword.is_strikethrough = styles.get('strikethrough', False)
                keyword.is_quote = styles.get('quote', False)
                keyword.is_monospace = styles.get('monospace', False)
                keyword.is_spoiler = styles.get('spoiler', False)
            
            # 保存到数据库
            async with AsyncSessionLocal() as session:
                session.add(keyword)
                await session.commit()
            
            return True, "关键词添加成功"
            
        except Exception as e:
            logger.error(f"添加关键词失败: {e}")
            return False, f"添加失败: {str(e)}"
    
    async def get_keywords(self, page: int = 0, per_page: int = 10, 
                          action: Optional[int] = None) -> List[Dict]:
        """获取关键词列表"""
        try:
            async with AsyncSessionLocal() as session:
                query = select(Keyword)
                
                # 按动作过滤
                if action is not None:
                    query = query.where(Keyword.action == action)
                
                # 排序和分页
                query = query.order_by(Keyword.id.desc())
                if per_page > 0:
                    query = query.offset(page * per_page).limit(per_page)
                
                result = await session.execute(query)
                keywords = result.scalars().all()
                
                # 转换为字典格式
                keyword_list = []
                for kw in keywords:
                    keyword_dict = {
                        'id': kw.id,
                        'content': kw.content,
                        'type': kw.type,
                        'type_name': self.TYPE_NAMES.get(kw.type, '未知'),
                        'action': kw.action,
                        'action_name': self.ACTION_NAMES.get(kw.action, '未知'),
                        'styles': {
                            'case_sensitive': kw.is_case_sensitive,
                            'bold': kw.is_bold,
                            'italic': kw.is_italic,
                            'underline': kw.is_underline,
                            'strikethrough': kw.is_strikethrough,
                            'quote': kw.is_quote,
                            'monospace': kw.is_monospace,
                            'spoiler': kw.is_spoiler
                        },
                        'created_at': kw.created_at.strftime('%Y-%m-%d %H:%M:%S')
                    }
                    keyword_list.append(keyword_dict)
                
                return keyword_list
                
        except Exception as e:
            logger.error(f"获取关键词列表失败: {e}")
            return []
    
    async def get_keyword_count(self, action: Optional[int] = None) -> int:
        """获取关键词数量"""
        try:
            async with AsyncSessionLocal() as session:
                query = select(func.count(Keyword.id))
                
                if action is not None:
                    query = query.where(Keyword.action == action)
                
                result = await session.execute(query)
                return result.scalar() or 0
                
        except Exception as e:
            logger.error(f"获取关键词数量失败: {e}")
            return 0
    
    async def get_keyword_by_id(self, keyword_id: int) -> Optional[Dict]:
        """根据ID获取关键词"""
        try:
            async with AsyncSessionLocal() as session:
                result = await session.get(Keyword, keyword_id)
                
                if not result:
                    return None
                
                return {
                    'id': result.id,
                    'content': result.content,
                    'type': result.type,
                    'type_name': self.TYPE_NAMES.get(result.type, '未知'),
                    'action': result.action,
                    'action_name': self.ACTION_NAMES.get(result.action, '未知'),
                    'styles': {
                        'case_sensitive': result.is_case_sensitive,
                        'bold': result.is_bold,
                        'italic': result.is_italic,
                        'underline': result.is_underline,
                        'strikethrough': result.is_strikethrough,
                        'quote': result.is_quote,
                        'monospace': result.is_monospace,
                        'spoiler': result.is_spoiler
                    }
                }
                
        except Exception as e:
            logger.error(f"获取关键词失败: {e}")
            return None
    
    async def update_keyword(self, keyword_id: int, content: str = None, 
                           kw_type: int = None, action: int = None,
                           styles: Dict[str, bool] = None) -> Tuple[bool, str]:
        """更新关键词"""
        try:
            async with AsyncSessionLocal() as session:
                keyword = await session.get(Keyword, keyword_id)
                
                if not keyword:
                    return False, "关键词不存在"
                
                # 更新内容
                if content is not None:
                    if not content.strip():
                        return False, "关键词内容不能为空"
                    keyword.content = content.strip()
                
                # 更新类型
                if kw_type is not None:
                    if kw_type not in range(5):
                        return False, "无效的关键词类型"
                    keyword.type = kw_type
                
                # 更新动作
                if action is not None:
                    if action not in [0, 1]:
                        return False, "无效的动作类型"
                    keyword.action = action
                
                # 更新样式
                if styles:
                    keyword.is_case_sensitive = styles.get('case_sensitive', keyword.is_case_sensitive)
                    keyword.is_bold = styles.get('bold', keyword.is_bold)
                    keyword.is_italic = styles.get('italic', keyword.is_italic)
                    keyword.is_underline = styles.get('underline', keyword.is_underline)
                    keyword.is_strikethrough = styles.get('strikethrough', keyword.is_strikethrough)
                    keyword.is_quote = styles.get('quote', keyword.is_quote)
                    keyword.is_monospace = styles.get('monospace', keyword.is_monospace)
                    keyword.is_spoiler = styles.get('spoiler', keyword.is_spoiler)
                
                await session.commit()
                return True, "关键词更新成功"
                
        except Exception as e:
            logger.error(f"更新关键词失败: {e}")
            return False, f"更新失败: {str(e)}"
    
    async def delete_keyword(self, keyword_id: int) -> Tuple[bool, str]:
        """删除关键词"""
        try:
            async with AsyncSessionLocal() as session:
                keyword = await session.get(Keyword, keyword_id)
                
                if not keyword:
                    return False, "关键词不存在"
                
                await session.delete(keyword)
                await session.commit()
                
                return True, "关键词删除成功"
                
        except Exception as e:
            logger.error(f"删除关键词失败: {e}")
            return False, f"删除失败: {str(e)}"
    
    async def batch_add_keywords(self, keywords_data: List[Dict]) -> Tuple[bool, str]:
        """批量添加关键词"""
        try:
            if not keywords_data:
                return False, "没有要添加的关键词"
            
            keywords = []
            for data in keywords_data:
                content = data.get('content', '').strip()
                if not content:
                    continue
                
                keyword = Keyword(
                    content=content,
                    type=data.get('type', 1),
                    action=data.get('action', 1),
                    is_case_sensitive=data.get('case_sensitive', False),
                    is_bold=data.get('bold', False),
                    is_italic=data.get('italic', False),
                    is_underline=data.get('underline', False),
                    is_strikethrough=data.get('strikethrough', False),
                    is_quote=data.get('quote', False),
                    is_monospace=data.get('monospace', False),
                    is_spoiler=data.get('spoiler', False)
                )
                keywords.append(keyword)
            
            if not keywords:
                return False, "没有有效的关键词"
            
            async with AsyncSessionLocal() as session:
                session.add_all(keywords)
                await session.commit()
            
            return True, f"成功添加 {len(keywords)} 个关键词"
            
        except Exception as e:
            logger.error(f"批量添加关键词失败: {e}")
            return False, f"批量添加失败: {str(e)}"
    
    async def export_keywords(self) -> str:
        """导出关键词为JSON格式"""
        try:
            keywords = await self.get_keywords(per_page=0)  # 获取所有关键词
            return json.dumps(keywords, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"导出关键词失败: {e}")
            return ""
    
    async def match_message(self, message_text: str, sender_id: int, 
                          chat_id: int) -> List[Keyword]:
        """匹配消息中的关键词"""
        try:
            # 获取所有关键词
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(Keyword))
                all_keywords = result.scalars().all()
            
            matched_keywords = []
            
            for keyword in all_keywords:
                is_match = False
                
                # 根据类型进行匹配
                if keyword.type == 0:  # 全字匹配
                    is_match = self._full_word_match(keyword.content, message_text, keyword.is_case_sensitive)
                elif keyword.type == 1:  # 包含匹配
                    is_match = self._contains_match(keyword.content, message_text, keyword.is_case_sensitive)
                elif keyword.type == 2:  # 正则表达式
                    is_match = self._regex_match(keyword.content, message_text, keyword.is_case_sensitive)
                elif keyword.type == 3:  # 模糊匹配
                    is_match = self._fuzzy_match(keyword.content, message_text, keyword.is_case_sensitive)
                elif keyword.type == 4:  # 用户匹配
                    is_match = self._user_match(keyword.content, sender_id)
                
                if is_match:
                    matched_keywords.append(keyword)
            
            # 处理排除规则
            exclude_keywords = [kw for kw in matched_keywords if kw.action == 0]
            if exclude_keywords:
                return []  # 如果有排除规则匹配，则不转发消息
            
            # 返回监控规则
            monitor_keywords = [kw for kw in matched_keywords if kw.action == 1]
            return monitor_keywords
            
        except Exception as e:
            logger.error(f"匹配关键词失败: {e}")
            return []
    
    def _full_word_match(self, keyword: str, text: str, case_sensitive: bool) -> bool:
        """全字匹配"""
        if not case_sensitive:
            return keyword.lower() == text.lower()
        return keyword == text
    
    def _contains_match(self, keyword: str, text: str, case_sensitive: bool) -> bool:
        """包含匹配"""
        if not case_sensitive:
            return keyword.lower() in text.lower()
        return keyword in text
    
    def _regex_match(self, pattern: str, text: str, case_sensitive: bool) -> bool:
        """正则表达式匹配"""
        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            return bool(re.search(pattern, text, flags))
        except re.error:
            return False
    
    def _fuzzy_match(self, keyword: str, text: str, case_sensitive: bool) -> bool:
        """模糊匹配（多个关键词用?分隔）"""
        keywords = [kw.strip() for kw in keyword.split('?') if kw.strip()]
        if not keywords:
            return False
        
        text_to_match = text if case_sensitive else text.lower()
        
        for kw in keywords:
            kw_to_match = kw if case_sensitive else kw.lower()
            if kw_to_match not in text_to_match:
                return False
        
        return True
    
    def _user_match(self, keyword: str, sender_id: int) -> bool:
        """用户匹配"""
        # 移除@符号
        keyword = keyword.lstrip('@')
        
        # 检查是否是用户ID
        try:
            if int(keyword) == sender_id:
                return True
        except ValueError:
            pass
        
        # TODO: 检查用户名匹配（需要从Telegram客户端获取用户信息）
        
        return False