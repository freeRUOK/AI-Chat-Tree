# --*-- Encoding: UTF-8 --*--
#! filename: tools/__init__.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2026-02
# * description: 一个简单的AI LLM聊天程序
# 自动发现和注册工具

from typing_extensions import Any, Callable
from threading import Lock
import inspect
import os
import sys
import importlib
from pathlib import Path
from pydantic import BaseModel, Field
from tools.result import Result


class _ToolRegistry:
    """
    工具注册中心
    统一集中发现注册和管理所有工具
    """

    def __init__(self):
        """
        初始化
        """
        self._tools: dict[str, dict] = {}

    def register(self, fun: Callable[[BaseModel], Result]):
        """
        注册工具
        工具函数的参数必须是pydantic.BaseModel的子类型， 返回值应当是result.Result类型
        :param fun: 工具函数
        :type fun: Callable[[BaseModel], Result]
        """
        if fun.__name__ in self._tools:
            raise ValueError(
                f"工具： {fun.__name__} 已经被注册， 请检查工具名称是否有误。"
            )

        # 获取函数签名
        sig = inspect.signature(fun)
        params = list(sig.parameters.values())
        if not params:
            raise ValueError("工具函数必须有参数输入模型")

        input_model = params[0].annotation
        if not (isinstance(input_model, type) and issubclass(input_model, BaseModel)):
            raise ValueError("工具函数的第一个参数必须是pydantic.BaseModel的子类型")
        # LLM需要的工具函数数据结构
        tool_def = {
            "type": "function",
            "function": {
                "name": fun.__name__,
                "description": fun.__doc__ or "",
                "parameters": input_model.model_json_schema(),
            },
        }
        self._tools[fun.__name__] = {
            "fun": fun,
            "input_model": input_model,
            "tool_def": tool_def,
        }
        return fun

    def get(self, name: str) -> dict | None:
        """
        通过名称获取工具
        :param name: 工具名称
        :type name: str
        :return: 工具的详细定义
        :rtype: dict | None
        """
        return self._tools.get(name)

    def to_ollama_tools(self) -> list[dict]:
        """
        获取ollama格式的全部工具， 以便调用
        :return: 返回所有工具列表
        :rtype: list[dict]
        """
        return [info["tool_def"] for info in self._tools.values()]

    def execute(self, name: str, arguments: dict) -> Result:
        """
        验证参数之后执行工具
        :param name: 工具名称
        :type name: str
        :param arguments: 工具的参数和该工具的input_model参数关联， 而input_model是用pydantic.BaseModel上定义的
        :type arguments: dict
        :return: 工具执行结果
        :rtype: Result
        """
        info = self.get(name=name)
        if not info:
            return Result(result={}, error=RuntimeError(f"找不到工具： {name}"))

        try:
            args = info["input_model"](**arguments)
            result = info["fun"](args)
            return result
        except Exception as e:
            return Result(result={}, error=e)


def _setup_import_hack():
    """
    修改sys.path 直接导入 chat.util模块
    比较脆弱， 后续需要重构
    """
    chat_dir = Path(__file__).parent.parent
    if "chat.util" not in sys.modules:
        if str(chat_dir.parent) in sys.path:
            sys.path.insert(0, str(chat_dir.parent))
        importlib.import_module("chat.util")

    if "util" not in sys.modules:
        sys.modules["util"] = sys.modules["chat.util"]


def _auto_discover_tools():
    """
    自动发现并注册所有 tools/*_tool.py 工具模块
    """
    tools_dir = Path(__file__).parent
    for file in tools_dir.glob("*_tool.py"):
        module_name = f"tools.{file.stem}"
        try:
            importlib.import_module(module_name)

        except Exception as e:
            raise e


_tool_registry_instance: _ToolRegistry | None = None
_instance_lock = Lock()


def get_tool_registry() -> _ToolRegistry:
    """
    全局唯一获取单例
    :return: 单例
    :rtype: _ToolRegistry
    """
    global _tool_registry_instance
    if _tool_registry_instance is None:
        with _instance_lock:
            if _tool_registry_instance is None:
                _tool_registry_instance = _ToolRegistry()
                _auto_discover_tools()

    return _tool_registry_instance
