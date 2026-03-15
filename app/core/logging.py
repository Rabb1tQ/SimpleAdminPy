"""
日志配置
"""
import sys
from loguru import logger

from app.core.config import settings


def setup_logging():
    """配置日志"""
    # 移除默认处理器
    logger.remove()

    # 控制台输出
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # 开发环境：彩色输出到控制台
    if settings.is_development:
        logger.add(
            sys.stdout,
            format=log_format,
            level="DEBUG",
            colorize=True,
            backtrace=True,
            diagnose=True,
        )
    else:
        # 生产环境：输出到文件
        logger.add(
            "logs/app_{time:YYYY-MM-DD}.log",
            rotation="00:00",
            retention="30 days",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
            level="INFO",
            encoding="utf-8",
        )
        # 同时输出到控制台（简化格式）
        logger.add(
            sys.stdout,
            format=log_format,
            level="INFO",
            colorize=True,
        )

    return logger
