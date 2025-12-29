"""
数据库模型和初始化
完全对应原C#项目的数据结构
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from decouple import config
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class Keyword(Base):
    """关键词配置表 - 完全对应原项目KeywordConfig"""
    __tablename__ = "keywords"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(String(500), nullable=False, comment="关键词内容")
    type = Column(Integer, default=1, comment="匹配类型: 0=全字,1=包含,2=正则,3=模糊,4=用户")
    action = Column(Integer, default=1, comment="执行动作: 0=排除,1=监控")
    
    # 样式设置 - 对应原项目的样式字段
    is_case_sensitive = Column(Boolean, default=False, comment="是否区分大小写")
    is_bold = Column(Boolean, default=False, comment="是否粗体")
    is_italic = Column(Boolean, default=False, comment="是否斜体")
    is_underline = Column(Boolean, default=False, comment="是否下划线")
    is_strikethrough = Column(Boolean, default=False, comment="是否删除线")
    is_quote = Column(Boolean, default=False, comment="是否引用样式")
    is_monospace = Column(Boolean, default=False, comment="是否等宽字体")
    is_spoiler = Column(Boolean, default=False, comment="是否剧透内容")
    
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")


class SystemConfig(Base):
    """系统配置表"""
    __tablename__ = "system_config"
    
    key = Column(String(100), primary_key=True, comment="配置键")
    value = Column(Text, comment="配置值")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")


class UserState(Base):
    """用户状态表 - Bot交互状态管理"""
    __tablename__ = "user_states"
    
    user_id = Column(Integer, primary_key=True, comment="用户ID")
    current_state = Column(String(50), default="idle", comment="当前状态")
    temp_data = Column(Text, comment="临时数据")
    last_message_id = Column(Integer, comment="最后消息ID")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")


class Blacklist(Base):
    """黑名单表 - 屏蔽用户或群组"""
    __tablename__ = "blacklist"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    target_id = Column(String(50), nullable=False, comment="目标ID（用户ID或群组ID）")
    target_type = Column(Integer, default=0, comment="类型: 0=用户, 1=群组")
    name = Column(String(200), comment="名称备注")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")


# 数据库引擎和会话
DATABASE_PATH = config('DATABASE_PATH', default='./telegram_monitor.db')
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_database():
    """初始化数据库"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db_session() -> AsyncSession:
    """获取数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# 数据库操作辅助函数
async def get_config(key: str, default: Optional[str] = None) -> Optional[str]:
    """获取系统配置"""
    async with AsyncSessionLocal() as session:
        result = await session.get(SystemConfig, key)
        return result.value if result else default


async def set_config(key: str, value: str):
    """设置系统配置"""
    async with AsyncSessionLocal() as session:
        config_item = await session.get(SystemConfig, key)
        if config_item:
            config_item.value = value
            config_item.updated_at = datetime.now()
        else:
            config_item = SystemConfig(key=key, value=value)
            session.add(config_item)
        await session.commit()


async def get_user_state(user_id: int) -> UserState:
    """获取用户状态"""
    async with AsyncSessionLocal() as session:
        state = await session.get(UserState, user_id)
        if not state:
            state = UserState(user_id=user_id)
            session.add(state)
            await session.commit()
        return state


async def set_user_state(user_id: int, state: str, temp_data: str = None, message_id: int = None):
    """设置用户状态"""
    async with AsyncSessionLocal() as session:
        user_state = await session.get(UserState, user_id)
        if not user_state:
            user_state = UserState(user_id=user_id)
            session.add(user_state)
        
        user_state.current_state = state
        if temp_data is not None:
            user_state.temp_data = temp_data
        if message_id is not None:
            user_state.last_message_id = message_id
        user_state.updated_at = datetime.now()
        
        await session.commit()