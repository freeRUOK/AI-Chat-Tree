# --*-- Encoding: UTF-8 --*--
#! filename: /tools/task_tool.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2026-03
# * description: 一个简单的AI LLM聊天程序
"""
实现了一个Sub Agent
该Agent拥有自己的消息列表， 不污染主消息列表
完成后返回最后的总结内容， 其他历史消息直接丢弃
"""

from pydantic import BaseModel, Field
from tools import get_tool_registry
from tools.result import Result
from model_manager import get_model_manager
from tool_call_looper import ToolCallLooper
from error_handling import handle_api_error


registry = get_tool_registry()


class SubAgentInput(BaseModel):
    prompt: str = Field(description="Prompt： 委派给子agent的任务内容")


def get_last_message(messages: list) -> str:
    """
    获取task工具LLM输出的最后一条消息
    :param messages: 消息列表
    :type messages: list
    :rtype: str
    """
    for i in range(len(messages), -1, -1):
        if messages[i]["role"] == "assistant":
            return messages[i]["content"]

    return "没有总结内容"


@registry.register
def task(p: SubAgentInput) -> Result:
    """
    Sub Agent， 协助主agent完成任务
    拥有自己的消息列表，不会污染主消息列表
    完成后返回最终结果，历史消息全部丢弃
    """
    messages = [
        {
            "role": "system",
            "content": "你是一个子agent，帮助主agent探索任务，最后总结,主agent需要最后的总结内容，其他的消息列表直接废弃，所以最后的消息必须有内容而且是最终结果",
        },
        {"role": "user", "content": p.prompt},
    ]
    model = get_model_manager().create_or_switch(model_name="qwen3.5:4b")
    if model is None:
        raise ValueError("模型创建失败，请替换一个模型。")

    model.max_tokens = 8000

    model.tools = get_tool_registry().to_call_tools(exclude={"task"})
    looper = ToolCallLooper(enable_tools=True)
    tool_result = {}
    for i in range(3):
        try:
            messages = looper.run(
                model=model, messages=messages, is_online=model.is_online
            )
            tool_result["last_message"] = get_last_message(messages=messages)

        except Exception as e:
            if not handle_api_error(
                err=e, messages=messages, call_count=i, pop_message=True
            ):
                return Result(error=e, result={})

    return Result(result=tool_result)
