# --*-- Encoding: UTF-8 --*--
#! filename: /tools/todo_tool.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2026-03
# * description: 一个简单的AI LLM聊天程序
"""
todo待办计划工具
把复杂的任务拆分为多个待办列表
如果LLM不更新待办列表的话强制提醒
"""

from typing import Literal
from threading import Lock
from pydantic import BaseModel, Field
from tools import get_tool_registry
from tools.result import Result


class TodoItem(BaseModel):
    """
    待办项目
    """

    status: Literal["pending", "in_progress", "completed"] = Field(
        description="待办状态： pending; in_progress(列表当中同时允许一个)； completed"
    )
    id: str = Field(
        default="",
        description="待办id",
    )
    text: str = Field(description="待办具体内容")


class TodoInputModel(BaseModel):
    """
    todo工具的输入参数
    """

    items: list[TodoItem] = Field(description="待办列表，", min_length=1, max_length=12)


class _TodoManager:
    def __init__(self):
        """
        初始化
        """
        self.__items = []
        self.__initialized = False

    def is_active(self) -> bool:
        """
        :return: 待办列表是否活跃
        :rtype: bool
        """
        if not self.__initialized:
            return False

        return not all(item.status == "completed" for item in self.__items)

    def update(self, items: list[TodoItem]) -> str:
        """
        更新待办列表
        :param items: 需要更新的待办列表
        :type items: list[TodoItem]
        :return: 人类和LLM可读的待办列表文本
        :rtype: str
        """
        if len(list(filter(lambda it: it.status == "in_progress", items))) > 1:
            raise ValueError("todo列表中只能有一个status: in_progress的项目")

        self.__items = items
        self.__initialized = True
        return self.render()

    def render(self) -> str:
        """
        :return: 人类和LLM可读的待办列表文本
        :rtype: str
        """
        if not self.__items:
            return "暂无待办"

        lines = []
        for item in self.__items:
            marker = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}[
                item.status
            ]
            lines.append(f"{marker} #{item.id}: {item.text}")

        done = sum(1 for t in self.__items if t.status == "completed")
        lines.append(f"\n进度： {done}/{len(self.__items)}")

        return "\n".join(lines)


registry = get_tool_registry()
_todo_manager: _TodoManager | None = None
_lock = Lock()


def get_todo_manager() -> "_TodoManager":
    """
    单例返回
    """
    global _todo_manager
    if _todo_manager is None:
        with _lock:
            if _todo_manager is None:
                _todo_manager = _TodoManager()

    return _todo_manager


@registry.register
def todo_write(p: TodoInputModel) -> Result:
    """
    生成清晰的待办列表
    最多只能有12个待办
    一个待办列表只能存在一个status： in_progress
    """
    todo_manager = get_todo_manager()
    try:
        return Result(result=todo_manager.update(p.items))
    except Exception as e:
        return Result(error=e, result={})
