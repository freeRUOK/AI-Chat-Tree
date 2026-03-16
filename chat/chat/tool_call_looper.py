# --*-- Coding: UTF-8 --*--
#! filename: tool_call_looper.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2026-03
# * description: 一个简单的AI LLM聊天程序
# 实现一个主Agent和子Agent共用的工具调用循环
from typing import Callable
from error_handling import emit_error

from tools import get_tool_registry
from model import Model


class ToolCallLooper:
    """
    定义一个工具调用循环
    """

    def __init__(
        self,
        enable_tools: bool = True,
    ):
        """ """

        self._enable_tools = enable_tools
        self._tool_registry = get_tool_registry() if self._enable_tools else None

    def run(
        self,
        model: Model,
        messages: list[dict],
        is_online: bool,
        exclude_tools: set | None = None,
        max_iterations: int = 9,
        stream_handler: Callable | None = None,
        on_iteration: Callable | None = None,
    ) -> list[dict]:
        if not self._enable_tools or self._tool_registry is None:
            tools = None
        else:
            tools = self._tool_registry.to_call_tools(exclude=exclude_tools)

        for iteration in range(max_iterations):
            if on_iteration:
                on_iteration(iteration)

            response = model.chat(
                messages=messages, tools=tools, stream=stream_handler is not None
            )
            if stream_handler is not None:
                pending_calls = stream_handler(response)
            else:
                pending_calls = model.response_handler(response, messages=messages)

            if not pending_calls:
                break

            self._execute_and_append(messages, pending_calls, is_online)

        return messages

    def _execute_and_append(self, messages: list, pending_calls: list, is_online: bool):
        tool_results = self._execute_all_tool_call(pending_tool_calls=pending_calls)
        if not tool_results:
            return

        tool_messages = self._build_tool_call_messages(tool_results, is_online)
        messages.extend(tool_messages)

    def _execute_all_tool_call(self, pending_tool_calls: list) -> list[dict]:
        """
        一次性执行所有工具调用
        :param pending_tool_calls: 需要执行的工具列表
        :type pending_tool_calls: list
        :return: 返回工具执行结果
        :rtype: list[Result]
        """
        if self._tool_registry is None:
            return []

        tool_results = []
        for tc in pending_tool_calls:
            print(f"\n\nTool Calling: {tc['name']} Arguments: {tc['arguments']}")
            result = self._tool_registry.execute(
                name=tc["name"], arguments=tc["arguments"]
            )
            print(f"Tool Calling: {tc['name']} Done. Return Result: {result}")
            if result.error:
                emit_error(msg=str(result.error), exception=result.error)

            tool_results.append({"tool_call": tc, "result": result})

        return tool_results

    def _build_openai_tool_calls(self, tool_calls: list) -> dict:
        """
        添加openai格式的工具调用消息
        :param tool_calls: 工具调用列表
        :type tool_calls: list
        :return: OpenAI工具调用消息
        :rtype: dict
        """
        tool_message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": tc["arguments_string"],
                    },
                }
                for tc in tool_calls
            ],
        }

        return tool_message

    def _build_tool_call_messages(self, tool_results: list, is_online: bool) -> list:
        """
        把工具调用所有消息添加到聊天队列
        :param tool_results: 工具调用结果
        :type tool_results: list
        :param is_online: 是否在线模型
        :type is_online: bool
        """
        tool_messages = []
        if is_online:
            tool_message = self._build_openai_tool_calls(
                [tr["tool_call"] for tr in tool_results]
            )
            tool_messages.append(tool_message)

        for tr in tool_results:
            tool_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tr["tool_call"]["id"],
                    "content": str(tr["result"]),
                }
            )

        return tool_messages
