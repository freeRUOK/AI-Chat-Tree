# --*-- Coding: UTF-8 --*--
#! filename:
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2026-02
# * description: 一个简单的AI LLM聊天程序
# 整合语音唤醒和语音识别
# 在一个协调器里统一调度
from typing import Callable
import threading

from wake_word_detector import WakeWordDetector
from speech_to_text import SpeechToText
from config import Config
from sound_player import get_sound_player, PlayMode


class VoiceInputManager:
    """
    Docstring for VoiceInputManager
    统一管理和调度语音输入
    包括语音唤醒和语音识别
    """

    def __init__(
        self,
        record_timeout: float = 10,
        config: Config | None = None,
        stt_callback: Callable[[str], None] | None = None,
    ):
        """
        初始化， 必须通过Config传递 初始化WakeWordDetector和SpeechToText所需的参数
        :param record_timeout: 语音唤醒之后语音识别的固定时间， 后续通过人生检测动态调整此参数
        :type record_timeout: float
        :param config: 应用程序全局配置项， 组件自动获取相关参数初始化WakeWordDetector & SpeechToText
        :type config: Config | None
        :param stt_callback: 识别到文本之后调用这个函数， 应用程序的其他层可以进一步处理文本， 如发送到LLM
        :type stt_callback: callable[[str], None] | None
        """
        if config is None:
            raise RuntimeError("Config Is None.")

        self._record_timeout = record_timeout
        self._auto_stop_timer: threading.Timer | None = None
        voice_input = config.get("voice_input")

        self._speech_to_text = SpeechToText(
            model_path=voice_input["vosk_model_path"], callback=stt_callback
        )
        self._wake_word_detector = WakeWordDetector(
            access_key=voice_input["porcupine_access_key"],
            model_path=voice_input["porcupine_model_path"],
            keyword_paths=[
                voice_input["porcupine_wake_zh_model_path"],
            ],
            on_wake=self.on_wake,
        )

        self._lock = threading.Lock()
        self._sound_player = get_sound_player()

    def __enter__(self):
        """
        自动管理上下文， 启动组件
        """
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        自动上下文管理， 停止组件
        """
        self.stop()
        return False

    def start(self):
        """
        启动语音唤醒和语音识别
        """
        self._speech_to_text.start()
        self._wake_word_detector.start()

    def stop(self):
        """
        停止双语音组件
        """
        self._cancel_timer()
        self._wake_word_detector.stop()
        self._speech_to_text.stop()

    def _cancel_timer(self):
        """
        取消定时
        """
        if self._auto_stop_timer:
            self._auto_stop_timer.cancel()
            self._auto_stop_timer = None

    def _start_timer(self):
        """
        启动定时定时结束之后自动调用auto_end方法， 结束录音
        """
        self._cancel_timer()
        self._auto_stop_timer = threading.Timer(self._record_timeout, self._auto_end)
        self._auto_stop_timer.start()

    def _auto_end(self):
        """
        结束录音， 该函数是定时结束后自动调用的
        """
        with self._lock:
            if not self._speech_to_text.is_recording():
                return

            self._speech_to_text.end()
            self._auto_stop_timer = None

    def begin_voice_input(self) -> bool:
        """
        外部手动发送语音识别开始信号
        :return: 发送成功与否
        :rtype: bool
        """
        with self._lock:
            if self._speech_to_text.is_recording():
                return False
            self._sound_player.play(name="wake", play_mode=PlayMode.ones_async)
        return self._speech_to_text.begin()

    def end_voice_input(self) -> bool:
        """
        手动发送语音识别结束信号
        :return: 成功与否
        :rtype: bool
        """
        self._sound_player.play(name="voice-done", play_mode=PlayMode.ones_async)
        return self._speech_to_text.end()

    def on_wake(self):
        """
        唤醒成功后调用， 发送语音识别信号成功之后开始定时， 定时结束之后自动结束语音识别
        """
        if self._speech_to_text.begin():
            self._start_timer()
