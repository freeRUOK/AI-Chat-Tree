# --*-- Coding: UTF-8 --*--
#! filename: ./tools/tool_call_accumuator.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2026-03
# * description: 一个简单的AI LLM聊天程序
# 收集工具调用
from typing_extensions import Any
from copy import deepcopy
import json
from error_handling import emit_error


class ToolCallAccumulator:
    """
    收集工具调用信息
    解决旧的OpenAI API流式输出tool_calls的问题
    ollama API一次性输出工具调用的所有信息， 而OpenAI需要累积之后在调用工具
    """

    def __init__(self):
        """
        初始化
        """
        self._do_init()

    def _do_init(self):
        """
        初始化和重置的重复代码放在一起
        """
        self._tool_calls: list = []
        self._current_tool_call = {
            "id": None,
            "index": -1,
            "name": None,
            "arguments": "",
        }
        self._arguments_string = ""

    def add_chunk(self, tool_calls: Any, is_online: bool = False) -> Exception | None:
        """
        添加工具调用辕信息， openAI特殊处理， ollama直接提取
        :param tool_calls: LLM返回的调用信息
        :type tool_calls: dict
        :param is_online: 是否为在线模型， 在线模型用OpenAI格式， 否则使用ollama格式
        :type is_online: bool
        :return: 成功返回None, 失败返回对应的错误
        :rtype: Exception | None
        """
        if is_online:
            return self._process_openai_stream(tool_calls)

        else:
            tool_call = {
                "id": tool_calls.id
                if "id" in tool_calls
                else f"call_{len(self._tool_calls)}",
                "name": tool_calls.function.name,
                "arguments": tool_calls.function.arguments,
            }
            self._tool_calls.append(tool_call)

        return None

    def _process_openai_stream(self, tool_calls: Any) -> Exception | None:
        """
        对OpenAI stream数据流做特殊处理
        因为该API是stream返回工具调用信息的， 所以需要每次返回的时候累积所有片段
        :param tool_calls: LLM返回的调用信息
        :type tool_calls: dict
        :return: 成功返回None； 失败返回对应的错误
        :rtype: Exception | None
        """
        if self._current_tool_call["index"] == tool_calls.index:
            self._current_tool_call["id"] = (
                tool_calls.id or self._current_tool_call["id"]
            )
            self._current_tool_call["name"] = (
                tool_calls.function.name or self._current_tool_call["name"]
            )
            self._arguments_string += tool_calls.function.arguments or ""
        else:
            if self._current_tool_call["index"] != -1:
                if err := self.add_last_tool_call():
                    return err

            self._current_tool_call = {
                "index": tool_calls.index,
                "id": tool_calls.id,
                "name": tool_calls.function.name,
                "arguments": "",
            }
            self._arguments_string = tool_calls.function.arguments or ""

        return None

    def add_last_tool_call(self) -> Exception | None:
        """
        添加最后一个滞留的工具调用信息添加到工具调用列表
        所以在调用all方法的时候必须调用该方法添加最后一个工具调用信息
        :return: 成功返回None; 失败返回对应的错误
        :rtype: Exception | None
        """
        if not self._current_tool_call.get("name"):
            return ValueError("current_tool_call.name  name not found.")

        try:
            arguments_string = self._arguments_string.strip()
            arguments_string = arguments_string if arguments_string else "{}"
            self._current_tool_call["arguments"] = json.loads(arguments_string)
            self._current_tool_call["arguments_string"] = arguments_string
            self._tool_calls.append(deepcopy(self._current_tool_call))
        except json.decoder.JSONDecodeError as e:
            emit_error(msg=str(e), exception=e)
            return e

        return None

    def all(self) -> list:
        """
        清空并返回所有工具调用
        :return: 全部工具调用
        :rtype: list
        """
        self.add_last_tool_call()
        result = deepcopy(self._tool_calls)
        self._do_init()
        return result
