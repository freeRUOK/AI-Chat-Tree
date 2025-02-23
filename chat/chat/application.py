# --*-- Coding: UTF-8 --*--
#! filename: application.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2025-02
# * description: 一个简单的AI LLM聊天程序
# 抽象了一个层简化底层组件的调用
# 简单 灵活 复杂 这都是平衡妥协的产物
from typing import Any
import ollama
from config import Config
from chat import Chat
from model import ModelOutput, Model
from util import debug_log


class Application:
    """
    在CLI或GUI中间搭建一个层方便后续扩展
    """

    def __init__(
        self,
        config: Config,
    ):
        """
        初始化
        """
        self._config = config

        self._models = self.load_models()
        self._chat: Chat
        self._is_begin = False

    def __enter__(self):
        """
        with自动管理上下文， 语句块的开头部分运行
        """
        return self

    def __exit__(self, exc_typ, exc_val, exc_tb):
        """
        with自动管理上下文， 语句块的结束部分运行
        这里可以保存状态或清理资源
        """
        if exc_typ:
            debug_log(exc_val)

    def _begin(
        self,
        model_output: ModelOutput,
        first_model_name: str,
        second_model_name: str,
        system_prompt: str,
    ):
        """
        运行聊天之前的准备， 真正加载模型
        # 很多时候不会真正运行模型， 仅仅是查看相关配置信息
        """
        try:
            first_model, second_model = self.build_model(
                first_model_name=first_model_name, second_model_name=second_model_name
            )

            self._is_begin = True
        except ValueError as e:
            print(f"错误： {e}")
            debug_log(e)

        self._chat = Chat(
            first_model=first_model,
            model_output=model_output,
            second_model=second_model,
            system_prompt=system_prompt,
        )

    def run(self, input_callback=None):
        """
        在这个层级启动程序
        """
        if not self._is_begin:
            raise RuntimeError("调用run方法之前必须正确调用_begin方法")

        self._chat.run(input_callback=input_callback)

    def load_models(self) -> dict[str, Any]:
        """
        获取配置文件里的和本地ollama的模型元数据
        """
        if host := self._config.get("usage.ollama_host"):
            ollama_host = host
        else:
            ollama_host = "http://127.0.0.1:11434"
        ollama_models = {
            "group_name": "ollama",
            "show_reasoning": True,
            "is_online": False,
            "base_url": ollama_host,
            "api_key": "ollama",
        }
        try:
            # ollama没有运行或者没有安装， 所以这里需要提醒用户
            ollama_sub_models = [
                item.model for item in ollama.Client(host=ollama_host).list().models
            ]
        except ollama.ResponseError as e:
            ollama_sub_models = []
            debug_log(e)
            print("加载ollama模型失败， 检查是否在运行或者建议安装。")

        if ollama_sub_models:
            ollama_models["sub_models"] = ollama_sub_models
        else:
            ollama_models = None

        models = []
        if result := self._config.get("models"):
            models = result
        if ollama_models:
            models.append(ollama_models)

        return models

    def build_model(
        self, first_model_name, second_model_name: str
    ) -> tuple[Model, Model]:
        """
        通过sub_model_name查询创建主要模型和备用模型
        # 真正加载模型， 必须有一个主要模型， 备用模型可选
        # 如果主要模型出现问题就切换到备用模型
        """
        if len(self._models) == 0:
            raise ValueError("没有可用的模型, 请安装ollama或者添加在线模型。")

        first_model, second_model = None, None
        for model in self._models:
            if first_model_name in model["sub_models"]:
                model.update({"current_model": first_model_name})
                first_model = Model.from_dict(model)
            if second_model_name in model["sub_models"]:
                model.update({"current_model": second_model_name})
                second_model = Model.from_dict(model)

        if first_model is None:
            raise ValueError(f"没有找到子模型： {first_model_name}")

        return (
            first_model,
            second_model,
        )
