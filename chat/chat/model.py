# --*-- Coding: UTF-8 --*--
#! filename: model.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2025-02
# * description: 一个简单的AI LLM聊天程序
# 定义了关于模型
# Model表示一个模型组， 这些模型组有一些共同的属性, 有若干子模型
# 比如deepseek的调用URL， 密钥都是相同的， 只是提供了两个子模型 deepseek-chat 普通的v3， 和deepseek-reasoner 具有深度思考的r1模型
from io import BytesIO
from typing import Any, Callable
from datetime import datetime
from pathlib import Path
import ollama
from openai import OpenAI
from consts import ContentTag
from util import validate_values, debug_log
from text_to_speech import TextToSpeech, TextToSpeechOption
from config import Config


class ModelResult:
    """
    标记模型输出的内容
    reasoning_content or chunk
    """

    def __init__(self, content: str, tag: ContentTag, model_name: str | None = None):
        self.content = content
        self.tag = tag
        self.model_name = model_name

    def to_dict(self) -> dict[str, str | None]:
        """
        转换到dict类型
        """
        return {
            "content": self.content,
            "tag": self.tag.value,
            "model_name": self.model_name,
        }


class ModelInfo:
    """
    表示模型的状态, 主要模型， 备用模型， 是否tts朗读， 可用模型列表
    """

    def __init__(self, tag: ContentTag, metadata: dict):
        self.content_tag = tag
        self.metadata = metadata


class Model:
    """
    定义某个llm模型组
    包括若干子模型和相关重要参数
    并且提供和当前模型组交互的chat方法
    ----------
    api_key铭文保存在配置文件里
    目前在本地环境运行， 所以这样做没有什么问题，
    如果在相对暴露环境下运行或者api_key价值比较高必须采取额外的安全措施
    ----------
    """

    def __init__(
        self,
        group_name: str,
        is_online: bool,
        show_reasoning: bool,
        base_url: str,
        api_key: str,
        sub_models: list[str],
        current_model: str | None = None,
        max_tokens: int = 5120,
        context_length: int = 131072,
    ):
        validate_values(
            [
                group_name,
                (
                    base_url,
                    r"^http\S+$",
                ),
                api_key,
            ]
        )

        self.group_name = group_name
        self.api_key = api_key
        self.base_url = base_url if "ollama.com" not in base_url else f"{base_url}/v1"

        self.sub_models = validate_values(sub_models)

        self.max_tokens = max_tokens
        self.context_length = context_length
        self.is_online = is_online
        self.show_reasoning = show_reasoning

        self.current_model = current_model
        if self.current_model is None:
            self.current_model = self.sub_models[0]

        self._openAIClient: OpenAI
        self._ollamaClient: ollama.Client
        if self.is_online:
            self._openAIClient = OpenAI(
                base_url=self.base_url, api_key=self.api_key, timeout=16
            )
        else:
            self._ollamaClient = ollama.Client(host=self.base_url)

    def chat(self, messages: list):
        """
        给模型发送消息
        """
        if self.current_model is None:
            raise ValueError("必须提供模型名称。")

        if self.is_online:
            return self._openAIClient.chat.completions.create(
                model=self.current_model,
                messages=messages,
                stream=True,
            )
        else:
            return self._ollamaClient.chat(
                model=self.current_model, messages=messages, stream=True
            )

    def to_dict(
        self,
        includes=[
            "group_name",
            "max_tokens",
            "context_length",
            "is_online",
            "show_reasoning",
            "api_key",
            "base_url",
            "sub_models",
            "current_model",
        ],
    ) -> dict[str, Any]:
        """
        把模型的参数转换到dict以便后续保存到配置文件
        """
        return {name: getattr(self, name) for name in includes if hasattr(self, name)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Model":
        """
        从配置dict创建模型对象
        """
        return cls(**data)


class ModelOutput:
    """
    处理大模型最后输出的内容
    默认情况下内容被tts朗读并且输出到标准输出
    如果需要输出到其他目的， 应当传递 chunk_callback & finish_callback两个函数
    chunk_callback流逝处理ModelResult类型的数据
    finish_callback当本次输出完成后被调用
    比如GUI可以通过这两个接口获取模型的输出， 需要实现线程安全的接口
    web也是一样的道理， 用户输入参考Chat.run方法的参数
    三个回调函数组成了模型的全部交互
    """

    def __init__(
        self,
        config: Config,
        text_to_speech_option: TextToSpeechOption = TextToSpeechOption.play,
        chunk_callback: Callable[[ModelResult], None] | None = None,
        audio_callback: Callable[[BytesIO], None] | None = None,
        finish_callback: Callable[[list], None] | None = None,
    ):
        self._config = config
        self._text_to_speech_option = text_to_speech_option
        self._chunk_callback = chunk_callback
        self._audio_callback = audio_callback
        self._finish_callback = finish_callback
        self._text_to_speech: TextToSpeech | None = None
        self.start_text_to_speech()
        self._tts_content = ""

        # 这里简单计算字符数量
        # 更精细的计算是以后工作的目标了
        self._total_char_length = 0
        self._max_total_char_length = 128 * 1024

    def __enter__(self):
        """
        with语句自动管理
        """
        return self

    def __exit__(self, exc_typ, exc_val, exc_tb):
        """
        with语句自动管理
        """
        self.stop_text_to_speech()

    def set_text_to_text_option(self, new_option: TextToSpeechOption):
        """
        设置语音朗读选项
        """
        self._text_to_speech_option = new_option
        if self._text_to_speech:
            self._text_to_speech.option = new_option
            if new_option == TextToSpeechOption.off:
                self.stop_text_to_speech()

    def stop_text_to_speech(self):
        """
        结束tts线程
        """
        self._tts_content = ""
        if self._text_to_speech:
            self._text_to_speech.stop()
            self._text_to_speech = None

    def start_text_to_speech(self):
        """
        运行TTS语音朗读引擎
        如果没有创建或没有运行则重新创建
        """
        if (
            self._text_to_speech_option == TextToSpeechOption.off
            or self._text_to_speech is not None
            and self._text_to_speech.is_alive()
        ):
            return

        self.stop_text_to_speech()

        tts_config = self._config.get("text_to_speech")
        if tts_config is None:
            tts_config = {
                "voice": "Microsoft Server Speech Text to Speech Voice (zh-CN, XiaoxiaoNeural)",
                "rate": "+80%",
                "volume": "+20%",
            }
        try:
            self._text_to_speech = TextToSpeech(
                option=self._text_to_speech_option,
                process_callback=self._audio_callback,
                voice=tts_config["voice"],
                rate=tts_config["rate"],
                volume=tts_config["volume"],
            )
            self._text_to_speech.start()
        except Exception as e:
            self._text_to_speech_option = TextToSpeechOption.off
            debug_log(e)
            return None

    def output_done(self, messages: list):
        """
        当一轮对话的内容输出完成后调用
        这个时候可以根据情况修剪对话内容
        也可以保存内容， 默认把最后的用户输入和模型输出保存到文件里
        """
        if self._finish_callback:
            self._finish_callback(messages)

        root_dir = Path("ai-chat-collections")
        if not root_dir.exists():
            root_dir.mkdir()
        filename = f"{datetime.now().strftime('%Y-%m-%dt%H-%M-%S')}.txt"
        file_content = "\n\n".join(
            f"{it['role']}: {it['content']}" for it in messages[-2:]
        )

        self._total_char_length += len(file_content)
        if self._total_char_length >= self._max_total_char_length:
            self.trim(messages=messages)
        try:
            (root_dir / Path(filename)).write_text(data=file_content, encoding="UTF-8")
        except Exception as e:
            debug_log(e)

    def trim(self, messages: list):
        """
        修剪整个对话队列， 适应模型后端长度的要求
        """
        system_prompt = messages.pop()
        current_len = 0
        remove_len = self._max_total_char_length // 5
        while current_len <= remove_len:
            current_len += len(messages.pop())

        messages.insert(0, system_prompt)

    def output_chunk(
        self,
        model_result: ModelResult,
        show_reasoning: bool,
        finish_reason: str = "",
    ):
        """
        输出内容， 如果没有传递chunk_callback接口直接在标准输出上输出， 如果提供了接口执行接口定义的逻辑
        """
        if model_result.tag == ContentTag.reasoning_content:
            if show_reasoning:
                self._tts_content += model_result.content
                if self._chunk_callback:
                    self._chunk_callback(model_result)
                else:
                    print(model_result.content, end="", flush=True)

        else:
            self._tts_content += model_result.content
            if self._chunk_callback:
                self._chunk_callback(model_result)
            else:
                print(model_result.content, end="", flush=True)

        if finish_reason == "stop":
            print()

        self.speak(is_last=finish_reason == "stop")

    def speak(self, is_last: bool = False):
        """
        如果可用, 语音朗读llm内容
        """

        if (
            self._text_to_speech
            or self._text_to_speech_option != TextToSpeechOption.off
        ):
            if self._tts_content[-1:] == "\n" or is_last:
                self.start_text_to_speech()
                if self._text_to_speech:
                    self._text_to_speech.submit(text=self._tts_content)
                    self._tts_content = ""
