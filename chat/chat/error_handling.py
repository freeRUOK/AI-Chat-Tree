# --*-- Coding: UTF-8 --*--
#! filename: error_handling.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2026-03
# * description: 一个简单的AI LLM聊天程序
# 这里提供了日志文件的配置和错误处理
import os
from loguru import logger

# 配置日志记录
logger.remove()
logger.add(
    "logs/debug.log",
    format="{line} | {message} | {time:YYYY-MM-DD HH:mm:ss}",
    rotation="1 MB",
    compression="zip",
    backtrace=True,
    diagnose=True,
    enqueue=True,
)
debug_logger = logger
DEBUG_MODE = os.getenv("DEBUG_MODE", None)


def debug_log(err: Exception):
    """
    记录错误和调用堆栈
    """
    if DEBUG_MODE:
        logger.exception(f"Error: {err}")
