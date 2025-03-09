# --*-- Coding: UTF-8 --*--
#! filename: application.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2025-02
# * description: 一个简单的AI LLM聊天程序
# 抽象了一个层简化底层组件的调用
# 简单 灵活 复杂 这都是平衡妥协的产物
from io import BytesIO
from typing import Callable
import threading
import ollama
from config import Config
from consts import default_system_prompt, ContentTag
from chat import Chat
from model import ModelOutput, Model, ModelResult, ModelInfo
from util import debug_log, DEBUG_MODE


class Application(threading.Thread):
    """
    在CLI或GUI中间搭建一个层方便后续扩展
    """

    def __init__(
        self,
        config: Config,
        model_name: str = "deepseek-reasoner",
        second_model_name: str = "deepseek-r1:14b",
        system_prompt: str = default_system_prompt,
        is_speak: bool = True,
        begin_callback: Callable[[], dict] | None = None,
        input_callback: Callable[[], str] | None = None,
        chunk_callback: Callable[[ModelResult], None] | None = None,
        audio_callback: Callable[[BytesIO], None] | None = None,
        finish_callback: Callable[[list], None] | None = None,
    ):
        """
        初始化
        """
        super().__init__()
        self._config = config
        self._model_name = model_name
        self._second_model_name = second_model_name
        self._system_prompt = system_prompt
        self._is_speak = is_speak
        self._begin_callback = begin_callback
        self._input_callback = input_callback
        self._chunk_callback = chunk_callback
        self._audio_callback = audio_callback
        self._finish_callback = finish_callback
        self._lock = threading.Lock()

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

    def get_model_info(self, content_tag: ContentTag) -> ModelInfo:
        """
        首次初始化前端客户端的时候调用加载模型相关信息
        不建议初始化以外的阶段调用
        """
        with self._lock:
            match content_tag:
                case ContentTag.model_status:
                    return ModelInfo(
                        content_tag,
                        metadata={
                            "first_model": self._model_name,
                            "second_model": self._second_model_name,
                            "is_speak": self._is_speak,
                        },
                    )
                case ContentTag.all_model:
                    sub_models = [
                        (
                            sub_model,
                            model["is_online"],
                        )
                        for model in self._models
                        for sub_model in model["sub_models"]
                    ]
                    return ModelInfo(
                        content_tag,
                        metadata={
                            "models": sub_models,
                            "first_model": self._model_name,
                            "second_model": self._second_model_name,
                            "is_speak": self._is_speak,
                        },
                    )
                case _:
                    return ModelInfo(ContentTag.empty, metadata={})

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
            models=self._models,
            second_model=second_model,
            system_prompt=system_prompt,
        )

    def run(self):
        """
        在这个层级启动程序
        """
        try:
            with ModelOutput(
                config=self._config,
                is_speak=self._is_speak,
                chunk_callback=self._chunk_callback,
                audio_callback=self._audio_callback,
                finish_callback=self._finish_callback,
            ) as model_output:
                self._begin(
                    model_output=model_output,
                    first_model_name=self._model_name,
                    second_model_name=self._second_model_name,
                    system_prompt=self._system_prompt,
                )
                if not self._is_begin:
                    raise RuntimeError("调用run方法之前必须正确调用_begin方法")

                self._chat.run(input_callback=self._input_callback)
        except Exception as e:
            debug_log(e)
            if DEBUG_MODE:
                raise e
            else:
                print(f"错误： {e}")

    def load_models(self) -> list:
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
            ollama_models = {}

        models = []
        if result := self._config.get("models"):
            models = result
        if ollama_models:
            models.append(ollama_models)

        return models

    def build_model(
        self, first_model_name, second_model_name: str
    ) -> tuple[Model, Model | None]:
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
