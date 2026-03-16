# --*-- Coding: UTF-8 --*--
#! filename: error_handling.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2026-03
# * description: 一个简单的AI LLM聊天程序
# 这里提供了日志文件的配置和错误处理
from enum import Enum
from dataclasses import dataclass
import os
from loguru import logger
from typing import Callable
import ollama
from openai import APIStatusError, RateLimitError, APIConnectionError
from httpx import ReadTimeout as OpenAIReadTimeout

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

_DEBUG_MODE = os.getenv("DEBUG_MODE", None)


class Level(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"


@dataclass
class Error:
    msg: str
    level: Level = Level.ERROR
    exception: Exception | None = None
    hint: str = ""
    retry: bool = False
    call_count: int = 0

    def __str__(self) -> str:
        if self.hint:
            return f"{self.msg}\n提示： {self.hint}"

        return self.msg


_on_error: (
    Callable[
        [
            Error,
        ],
        None,
    ]
    | None
) = None


def set_error_handler(
    on_error: Callable[
        [
            Error,
        ],
        None,
    ]
    | None = None,
):
    global _on_error
    _on_error = on_error


def emit_error(
    msg: str,
    level: Level = Level.ERROR,
    hint: str = "",
    exception: Exception | None = None,
    retry: bool = False,
    call_count: int = 0,
):
    global _on_error
    err = Error(msg, level, exception, hint, retry, call_count)
    if _on_error:
        _on_error(err)

    _log(err)


def _log(err: Error):
    if err.msg:
        logger.info(str(err))

    if err.exception:
        logger.exception(str(err.exception))

    if (
        err.exception is not None
        and _DEBUG_MODE
        and err.level in [Level.ERROR, Level.FATAL]
    ):
        raise err.exception
    else:
        print(f"{err}\nException:\n{err.exception}")


def handle_api_error(
    err: Exception,
    call_count: int,
    messages: list,
    output_done_callback: Callable | None = None,
    pop_message: bool = True,
) -> bool:
    """
     处理发送聊天信息期间的错误
    返回True暂时故障，
    返回False不可恢复错误， 可能是程序bug或者配置错误
    """
    err_code = -1
    msg = ""

    if isinstance(err, APIStatusError):
        msg = f"错误： {err.message}"
        err_code = err.status_code
    elif isinstance(err, OpenAIReadTimeout):
        err_code = 600
        msg = "读取超时"
    elif isinstance(err, RateLimitError):
        err_code = 429
        msg = "请求过于频繁"
    elif isinstance(err, APIConnectionError):
        err_code = 599
        msg = "API连接错误"
    elif isinstance(err, ollama.ResponseError):
        msg = f"错误： Error Code {err.status_code} {err}"
        err_code = err.status_code
    else:
        msg = f"错误： {err}"

    is_failed = err_code >= 500 and call_count >= 3
    emit_error(msg=msg, exception=err, level=Level.FATAL)

    if not is_failed:
        return True

    if pop_message:
        messages.pop(-1)

    if output_done_callback:
        output_done_callback()

    return False
