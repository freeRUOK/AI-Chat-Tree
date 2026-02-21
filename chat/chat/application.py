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
from model_tools import create_or_switch_model
from util import debug_log, DEBUG_MODE
from text_to_speech import TextToSpeechOption
from voice_input_manager import VoiceInputManager


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
        text_to_speech_option: TextToSpeechOption = TextToSpeechOption.off,
        error_callback: Callable[[Exception, bool], None] | None = None,
        begin_callback: Callable[[], dict | None] | None = None,
        input_callback: Callable[[], tuple[str, str | None]] | None = None,
        chunk_callback: Callable[[ModelResult], None] | None = None,
        audio_callback: Callable[[BytesIO], None] | None = None,
        finish_callback: Callable[[list], None] | None = None,
        voice_input_callback: Callable[[str], None] | None = None,
        enable_tools: bool = True,
    ):
        """
        初始化
        """
        super().__init__(daemon=True)
        self._config = config
        self._model_name = model_name
        self._second_model_name = second_model_name
        self._system_prompt = system_prompt
        self._text_to_speech_option = text_to_speech_option
        self._error_callback = error_callback
        self._begin_callback = begin_callback
        self._input_callback = input_callback
        self._chunk_callback = chunk_callback
        self._audio_callback = audio_callback
        self._finish_callback = finish_callback
        self._lock = threading.Lock()

        self._models = self.load_models()
        self._chat: Chat
        self._is_begin = False
        self.voice_input_manager = VoiceInputManager(
            config=self._config, stt_callback=voice_input_callback
        )
        self._enable_tools = enable_tools

    def __enter__(self):
        """
        with自动管理上下文， 语句块的开头部分运行
        """
        self.voice_input_manager.start()
        return self

    def __exit__(self, exc_typ, exc_val, exc_tb):
        """
        with自动管理上下文， 语句块的结束部分运行
        这里可以保存状态或清理资源
        """
        self.voice_input_manager.stop()
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
                            "text_to_speech_option": self._text_to_speech_option,
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
                            "text_to_speech_option": self._text_to_speech_option,
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
            if self._error_callback:
                self._error_callback(e, True)
            else:
                print(f"错误： {e}")

            debug_log(e)
            return

        self._chat = Chat(
            first_model=first_model,
            model_output=model_output,
            models=self._models,
            second_model=second_model,
            system_prompt=system_prompt,
            begin_callback=self._begin_callback,
            enable_tools=self._enable_tools,
        )

    def run(self):
        """
        在这个层级启动程序
        """
        try:
            with ModelOutput(
                config=self._config,
                text_to_speech_option=self._text_to_speech_option,
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
                    return

                self._chat.run(input_callback=self._input_callback)
        except Exception as e:
            debug_log(e)
            if DEBUG_MODE:
                raise e
            else:
                if self._error_callback:
                    self._error_callback(e, True)
                else:
                    print(f"错误： {e}")

    def _load_ollama_models(self, is_online: bool) -> dict:
        """
        获取ollama提供的所有可用的模型
        如果 is_online == True 则尝试获取ollama云端模型
        """
        if is_online:
            ollama_host = "https://ollama.com"
        elif host := self._config.get("usage.ollama_host"):
            ollama_host = host
        else:
            ollama_host = "http://127.0.0.1:11434"
        ollama_models = {
            "group_name": "ollama_local" if is_online else "ollama_cloud",
            "show_reasoning": True,
            "is_online": is_online,
            "base_url": ollama_host,
            "api_key": self._config.get("usage.ollama_api_key"),
        }
        try:
            # ollama没有运行或者没有安装， 所以这里需要提醒用户
            ollama_sub_models = [
                f"{item.model}{'-cloud' if is_online else ''}"
                for item in ollama.Client(host=ollama_host).list().models
                if item.model and "cloud" not in item.model
            ]
        except ollama.ResponseError as e:
            ollama_sub_models = []
            debug_log(e)
            error_prompt = "加载ollama模型失败， 请检查ollama服务是否正在运行或者建议安装配置ollama服务。。"
            if self._error_callback:
                self._error_callback(ValueError(error_prompt), False)
            else:
                print(error_prompt)

        if ollama_sub_models:
            ollama_models["sub_models"] = ollama_sub_models
        else:
            ollama_models = {}

        return ollama_models

    def load_models(self) -> list:
        """
        获取配置文件里的和本地ollama的模型元数据
        :param self: Description
        :return: 返回所有的ollama模型
        :rtype: list
        """
        models = []
        if result := self._config.get("models"):
            models = result

        models.append(self._load_ollama_models(is_online=True))
        models.append(self._load_ollama_models(is_online=False))

        return models

    def build_model(
        self, first_model_name: str, second_model_name: str | None
    ) -> tuple[Model, Model | None]:
        """
        通过sub_model_name查询创建主要模型和备用模型
        # 真正加载模型， 必须有一个主要模型， 备用模型可选
        # 如果主要模型出现问题就切换到备用模型
        """
        if len(self._models) == 0:
            raise ValueError("没有可用的模型, 请安装ollama或者添加在线模型。")

        first_model = create_or_switch_model(self._models, first_model_name)
        second_model = create_or_switch_model(self._models, second_model_name)
        if first_model is None:
            raise ValueError(f"没有找到子模型： {first_model_name}")

        return (
            first_model,
            second_model,
        )
