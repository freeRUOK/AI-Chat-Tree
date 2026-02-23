# --*-- Coding: UTF-8 --*--
#! filename: model_tools.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2025-03
# * description: 一个简单的AI LLM聊天程序
# 定义操作Model对象的快捷函数
from copy import deepcopy
import json
from model import Model


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
        self._tool_calls: list = []
        self._current_tool_call = {}
        self._current_index = -1
        self._arguments_str = ""

    def add_chunk(self, toll_calls: dict, is_online: bool) -> Exception | None:
        """
        添加工具调用辕信息， openAI特殊处理， ollama直接提取
        :param toll_calls: LLM返回的调用信息
        :type toll_calls: dict
        :param is_online: 是否为在线模型， 在线模型用OpenAI格式， 否则使用ollama格式
        :type is_online: bool
        :return: 成功返回None, 失败返回对应的错误
        :rtype: Exception | None
        """
        if is_online:
            return self._process_openai_stream(toll_calls)

        else:
            tool_call = {
                "id": toll_calls.id
                if "id" in toll_calls
                else f"call_{len(self._tool_calls)}",
                "name": toll_calls.function.name,
                "arguments": toll_calls.function.arguments,
            }
            self._tool_calls.append(tool_call)

        return None

    def _reset(self, tool_calls: dict | None = None):
        """
        重置全部数据
        :param tool_calls: 如果提供该参数则填充， 否则重置为默认
        :type tool_calls: dict | None
        """
        if tool_calls is not None:
            self._current_index = tool_calls.index
            self._current_tool_call["index"] = tool_calls.index
            self._current_tool_call["id"] = tool_calls.id
            self._current_tool_call["name"] = tool_calls.function.name
            self._arguments_str = tool_calls.function.arguments or ""
        else:
            self._current_index = -1
            self._current_tool_call = {}
            self._arguments_str = ""

    def _process_openai_stream(self, tool_calls: dict) -> Exception | None:
        """
        对OpenAI stream数据流做特殊处理
        因为该API是stream返回工具调用信息的， 所以需要每次返回的时候累积所有片段
        :param tool_calls: LLM返回的调用信息
        :type tool_calls: dict
        :return: 成功返回None； 失败返回对应的错误
        :rtype: Exception | None
        """
        if self._current_index == -1:
            self._reset(tool_calls)

        if tool_calls.index == self._current_index:
            self._arguments_str += tool_calls.function.arguments
            return None
        else:
            self.add_last_tool_call(tool_calls)

    def add_last_tool_call(self, tool_calls: dict | None = None) -> Exception | None:
        """
        添加最后一个滞留的工具调用信息添加到工具调用列表
        调用process_openai_stream方法的时候只有一个工具调用的情况之下else语句不会被执行
        所以在调用all方法的时候必须调用该方法添加最后一个工具调用信息
        :param tool_calls: 在all方法可以留空； 在process_openai_stream方法里必须提供
        :type tool_calls: dict | None
        :return: 成功返回None; 失败返回对应的错误
        :rtype: Exception | None
        """
        try:
            self._current_tool_call["arguments"] = json.loads(self._arguments_str)
            self._current_tool_call["arguments_string"] = self._arguments_str
            self._tool_calls.append(deepcopy(self._current_tool_call))
            self._reset(tool_calls=tool_calls)
        except json.decoder.JSONDecodeError as e:
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
        self._tool_calls = []
        return result


def find_model_group_index(model_list: list, name: str | None = None) -> int:
    """
    根据子模型查询模型组的索引
    """
    if name is None:
        return -1

    for index, model in enumerate(model_list):
        for sub_model in model["sub_models"]:
            if name in sub_model:
                return index

    return -1


def create_or_switch_model(
    model_list: list, model_name: str | None, model: Model | None = None
) -> Model | None:
    """
    根据条件切换或者创建模型
    如果新的子模型在当前模型组之内则简单切换
    如果子模型不在当前模型组则重新创建模型组
    """
    index = find_model_group_index(model_list, model_name)

    if index == -1:
        return None

    if model and model_name in model.sub_models:
        model.current_model = model_name
        return model
    else:
        model_list[index].update({"current_model": model_name})
        new_model = Model.from_dict(model_list[index])
        return new_model
