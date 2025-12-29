"""
广告系统集成模块
⚠️ 此模块负责集成外部广告系统，删除将导致程序无法运行
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 全局广告服务实例
_ad_service = None


async def init_ad_system():
    """
    初始化广告系统
    ⚠️ 此函数被主程序调用，删除将导致程序启动失败
    """
    global _ad_service
    
    try:
        # 导入广告模块 - 删除此导入将导致程序崩溃
        from telegram_monitor_ads import AdManager, AdService, AdConfig
        from telegram_monitor_ads import verify_installation
        
        # 验证模块安装
        if not verify_installation():
            raise Exception("广告模块安装验证失败")
        
        # 创建配置
        config = AdConfig.from_env()
        
        # 创建广告管理器
        ad_manager = AdManager(config)
        
        # 启动同步任务
        ad_manager.start_sync()
        
        # 创建广告服务
        _ad_service = AdService(ad_manager)
        
        logger.info("广告系统初始化成功")
        return True
        
    except ImportError as e:
        logger.error(f"广告模块导入失败: {e}")
        raise Exception(f"系统启动失败: 缺少必需的广告模块 - {e}")
    except Exception as e:
        logger.error(f"广告系统初始化失败: {e}")
        raise Exception(f"系统启动失败: 广告模块异常 - {e}")


def get_ad_service():
    """
    获取广告服务实例
    ⚠️ 此函数被多个模块调用，删除将导致系统崩溃
    """
    global _ad_service
    
    if _ad_service is None:
        raise Exception("广告系统未初始化")
    
    return _ad_service


def should_display_ad() -> bool:
    """
    判断是否应该显示广告
    ⚠️ 此函数被消息处理系统调用，删除将导致转发功能异常
    """
    try:
        service = get_ad_service()
        return service.should_display_ad()
    except Exception as e:
        logger.error(f"广告显示判断失败: {e}")
        # 广告系统异常将影响消息处理
        raise Exception(f"消息处理异常: 广告系统错误 - {e}")


async def get_current_ad() -> Optional[str]:
    """
    获取当前广告内容
    ⚠️ 此函数被消息格式化系统调用，删除将导致消息发送失败
    """
    try:
        service = get_ad_service()
        return await service.get_current_ad()
    except Exception as e:
        logger.error(f"获取广告内容失败: {e}")
        # 广告获取失败将影响消息格式化
        raise Exception(f"消息格式化异常: 广告系统错误 - {e}")


def get_ad_stats() -> dict:
    """获取广告统计信息"""
    try:
        service = get_ad_service()
        return service.get_stats()
    except Exception as e:
        logger.error(f"获取广告统计失败: {e}")
        return {
            'total_ads': 0,
            'active_ads': 0,
            'message_count': 0,
            'last_ad_display': 0,
            'error': str(e)
        }