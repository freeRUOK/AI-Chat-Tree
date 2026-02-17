# --*-- Coding: UTF-8 --*--
#! filename: data_status.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2025-02
# * description: 一个简单的AI LLM聊天程序
# 单独分离UI相关的一些数据
from typing import Any
from queue import Queue
from consts import default_system_prompt
from text_to_speech import TextToSpeechOption
from application import Application
from consts import ContentTag


class DataStatus:
    """
    单独管理和UI相关联的一些状态数据
    """

    def __init__(self):
        self.models: list = []
        self.first_model = ""
        self.second_model = ""
        self.text_to_speech_option = TextToSpeechOption.play
        self.message_queue: Queue = Queue()
        self.current_user_input = ""
        self.line = ""
        self.current_content_tag = ContentTag.empty
        self.current_model_name: str | None = None
        self.system_prompt = default_system_prompt
        self.is_change = False

    def on_begin(self) -> dict[str, Any] | None:
        """
        每次调用模型之前获取前端设定状态
        线程不安全， 后端调用的时候需要枷锁
        """
        if not self.is_change:
            return None

        self.is_change = False
        return {
            "first_model_name": self.first_model,
            "second_model_name": self.second_model,
            "text_to_speech_option": self.text_to_speech_option,
            "system_prompt": self.system_prompt,
        }

    def load_models_status(self, application: Application):
        """
        获取后端模型， 包括所有可用的模型和当前模型和备用模型
        """
        model_info = application.get_model_info(ContentTag.all_model)
        if model_info.content_tag != ContentTag.all_model:
            return

        self.models = model_info.metadata["models"]
        self.first_model = model_info.metadata["first_model"]
        self.second_model = model_info.metadata["second_model"]
        self.text_to_speech_option = model_info.metadata["text_to_speech_option"]

    def set_current_model(self, model_index: int, is_first_model: bool) -> bool:
        """
        修改当前使用的模型
        """
        try:
            if is_first_model:
                self.first_model = self.models[model_index][0]
            else:
                self.second_model = self.models[model_index][0]

            self.is_change = True
            return True
        except IndexError:
            return False

    def on_speech_result(self, result_text: str):
        """
        语音输入结束后调用
        :param result_text: 语音识别到的文本内容
        :type result_text: str
        """
        result_text = result_text.strip()
        if result_text:
            self.current_user_input = result_text
            self.message_queue.put(
                (
                    result_text,
                    None,
                )
            )
