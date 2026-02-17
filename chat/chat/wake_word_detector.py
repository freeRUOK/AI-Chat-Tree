# --*-- Coding: UTF-8 --*--
#! filename: wake_word_detector.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2026-02
# * description: 一个简单的AI LLM聊天程序
# 实现了语音唤醒， 使用porcupine的服务
from typing import Callable
import threading
import numpy as np
import pvporcupine  # type: ignore
import sounddevice as sd  # type: ignore


class WakeWordDetector(threading.Thread):
    """
    Docstring for WakeWordDetector
    持续监听系统麦克风检测唤醒词
    检测到唤醒词之后在单独线程调用回调函数
    """

    def __init__(
        self,
        access_key: str | None = None,
        keywords: list | None = None,
        keyword_paths: list | None = None,
        model_path: str | None = None,
        on_wake: Callable[[], None] | None = None,
    ):
        """
        初始化语音唤醒组件， 注意keyword_paths 或 keywords参数二选一传递， 不可同时传递
        :param access_key: 参考： https://console.picovoice.ai/
        :type access_key: str | None
        :param keywords: 唤醒短语， 参考同上
        :type keywords: list | None
        :param keyword_paths: 唤醒短语模型路径， 若传递了该参数无需传入keywords参数， 在这里生成唤醒短语： https://console.picovoice.ai/
        :type keyword_paths: list | None
        :param model_path: 特定语言的模型路径， 默认英语， 如果是中文短语的话需要传递中文模型的路径
        :type model_path: str | None
        :param on_wake: 成功唤醒之后运行的回调函数（异步执行）
        :type on_wake: Callable[[], None] | None
        """
        super().__init__(daemon=True)
        if not access_key:
            raise ValueError("Not Found PORCUPINE_ACCESS_KEY.")

        self._porcupine = pvporcupine.create(
            access_key=access_key,
            keywords=keywords,
            keyword_paths=keyword_paths,
            model_path=model_path,
        )
        self._on_wake = on_wake
        self._stop_flag = threading.Event()

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

    def stop(self):
        """
        停止组件的运行
        """
        self._stop_flag.set()
        self.join()

    def run(self):
        """
        检测唤醒的后台线程， 这里持续录音
        持续分析从系统麦克风获取的音频数据
        如果成功检测到唤醒短语之后调用回调函数
        所有的音频数据仅用于检测唤醒短语， 检测完毕之后丢弃
        """

        def audio_callback(indata, frames, time, status):
            if self._stop_flag.is_set():
                return

            pcm = (np.frombuffer(indata, dtype="float32") * 32767).astype(np.int16)
            if self._porcupine.process(pcm=pcm) >= 0:
                if self._on_wake:
                    threading.Thread(target=self._on_wake, daemon=True).start()

        with sd.RawInputStream(
            samplerate=self._porcupine.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=self._porcupine.frame_length,
            callback=audio_callback,
        ):
            self._stop_flag.wait()
