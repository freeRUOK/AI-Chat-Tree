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
from config import Config
from consts import default_system_prompt, ContentTag
from chat import Chat
from model import ModelOutput, ModelResult, ModelInfo
from model_manager import get_model_manager
from error_handling import emit_error, set_error_handler, Error
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
        error_callback: Callable[
            [
                Error,
            ],
            None,
        ]
        | None = None,
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
        set_error_handler(on_error=error_callback)
        self._begin_callback = begin_callback
        self._input_callback = input_callback
        self._chunk_callback = chunk_callback
        self._audio_callback = audio_callback
        self._finish_callback = finish_callback
        self._lock = threading.Lock()

        self._model_manager = get_model_manager(config=self._config)
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

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        with自动管理上下文， 语句块的结束部分运行
        这里可以保存状态或清理资源
        """
        self.voice_input_manager.stop()
        if exc_type:
            emit_error(msg=str(exc_val), exception=exc_val)

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
                        for model in self._model_manager.copy_models()
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
            first_model, second_model = self._model_manager.build_model(
                first_model_name=first_model_name, second_model_name=second_model_name
            )

            self._is_begin = True
        except ValueError as e:
            emit_error(msg=str(e), exception=e)
            return

        self._chat = Chat(
            first_model=first_model,
            model_output=model_output,
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
            emit_error(msg=str(e), exception=e)
