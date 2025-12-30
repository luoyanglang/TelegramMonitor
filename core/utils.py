"""
工具函数模块
提供全项目通用的工具函数
"""

from datetime import datetime
from typing import Optional
import pytz


def get_current_time(timezone: str = 'Asia/Shanghai', format: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    获取当前时间
    
    Args:
        timezone: 时区，默认为上海时区
        format: 时间格式，默认为 'YYYY-MM-DD HH:MM:SS'
        
    Returns:
        格式化后的时间字符串
    """
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)
    return now.strftime(format)


def format_timestamp(timestamp: float, timezone: str = 'Asia/Shanghai', format: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    格式化时间戳
    
    Args:
        timestamp: Unix 时间戳
        timezone: 时区，默认为上海时区
        format: 时间格式，默认为 'YYYY-MM-DD HH:MM:SS'
        
    Returns:
        格式化后的时间字符串
    """
    tz = pytz.timezone(timezone)
    dt = datetime.fromtimestamp(timestamp, tz)
    return dt.strftime(format)


def format_datetime(dt: datetime, timezone: str = 'Asia/Shanghai', format: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    格式化 datetime 对象
    
    Args:
        dt: datetime 对象
        timezone: 时区，默认为上海时区
        format: 时间格式，默认为 'YYYY-MM-DD HH:MM:SS'
        
    Returns:
        格式化后的时间字符串
    """
    if dt.tzinfo is None:
        # 如果没有时区信息，假设为 UTC
        dt = pytz.utc.localize(dt)
    
    tz = pytz.timezone(timezone)
    dt_local = dt.astimezone(tz)
    return dt_local.strftime(format)


def get_relative_time(dt: datetime) -> str:
    """
    获取相对时间描述
    
    Args:
        dt: datetime 对象
        
    Returns:
        相对时间描述，如 "刚刚"、"5分钟前"、"2小时前"
    """
    now = datetime.now(pytz.utc)
    
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    
    diff = now - dt
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "刚刚"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes}分钟前"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours}小时前"
    elif seconds < 2592000:  # 30天
        days = int(seconds / 86400)
        return f"{days}天前"
    else:
        return format_datetime(dt, format='%Y-%m-%d')
