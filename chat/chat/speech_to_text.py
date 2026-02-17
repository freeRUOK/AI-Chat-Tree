# --*-- Coding: UTF-8 --*--
#! filename: speech_to_text.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2026-02
# * description: 一个简单的AI LLM聊天程序
# 实践了语音到文本的转换
import wave
import os
import threading
import json
import numpy as np
import vosk  # type: ignore
import sounddevice as sd  # type: ignore
from util import debug_log


class SpeechToText(threading.Thread):
    """
    Docstring for SpeechToText
    实现了录音和语音转换到文本的功能
    sounddevice录音； vosk语音识别
    """

    def __init__(
        self,
        model_path: str | None = None,
        samplerate: int = 16000,
        callback=None,
    ):
        """
        :param model_path: Description vosk语音识别模型的路径
        :type model_path: str
        :param samplerate: Description 采样率
        :type samplerate: int
        :param callback: Description 语音识别成功之后的回调函数, 接受识别之后的文本
        """
        super().__init__(daemon=True)
        if model_path is None or not os.path.exists(model_path):
            raise FileNotFoundError(f"vosk Model File: {model_path} Not Found.")

        self.model = vosk.Model(model_path)
        self.samplerate = samplerate
        self.callback = callback
        self._stop_flag = threading.Event()
        self._record_trigger = threading.Event()
        self._record_stop = threading.Event()
        self._result_ready = threading.Event()
        self._last_result = ""

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
        停止SpeechToText组件， 整个组件全部停运
        """
        self._stop_flag.set()
        self._record_stop.set()
        self.join(timeout=3)

    def begin(self) -> bool:
        """
        发送语音转换文本信号, 立即返回
        返回值： 是否成功发送
        注意该方法和end方法只是发送信号， 实际状态通过其他方式获取
        """
        if self._record_trigger.is_set():
            return False

        self._record_stop.clear()
        self._result_ready.clear()
        self._record_trigger.set()
        return True

    def end(self) -> bool:
        """
        发送结束语音到文本任务的信号
        """
        if not self._record_trigger.is_set():
            return False

        self._record_stop.set()
        return True

    def get_result(self, timeout: float | None = None) -> str:
        """
        获取识别后的文本内容
        :param timeout: 等待时间
        :type timeout: float | None
        :return: 本次识别的结果
        :rtype: str
        """
        if self._result_ready.wait(timeout=timeout):
            return self._last_result

        return ""

    def is_recording(self) -> bool:
        """
        是否在录音
        :rtype: bool
        """
        return self._record_trigger.is_set() and not self._result_ready.is_set()

    def _record_audio(self):
        """
        录音
        """
        audio_buffer = []

        def callback(indata, frames, time, status):
            if not self._record_stop.is_set():
                audio_buffer.append(indata.copy())

        try:
            with sd.InputStream(
                samplerate=self.samplerate,
                channels=1,
                dtype="float32",
                callback=callback,
                blocksize=1024,
            ):
                while not self._record_stop.is_set():
                    sd.sleep(100)

            self._last_result = self._recognize(audio_buffer=audio_buffer)
        except Exception as e:
            debug_log(e)

        if self.callback:
            self.callback(self._last_result)
        else:
            print(f"Result: {self._last_result}")

        self._result_ready.set()
        self._record_trigger.clear()

    def save_wave_file(self, filename, audio_buffer: list) -> bool:
        """
        保存录音文件
        :param filename: Description
        :return: 文件是否保存成功
        """
        if not audio_buffer:
            return False

        audio = np.concatenate(audio_buffer, axis=0)
        audio_int16 = (audio * 32767).astype(np.int16)
        with wave.open(filename, "wb") as wav_stream:
            wav_stream.setnchannels(1)
            wav_stream.setsampwidth(2)
            wav_stream.setframerate(self.samplerate)
            wav_stream.writeframes(audio_int16.tobytes())

        return True

    def _recognize(self, audio_buffer: list) -> str:
        """
        从音频流当中识别文本内容
        :return: Description 返回识别的文本
        :rtype: str
        """
        if not audio_buffer:
            return ""

        recognizer = vosk.KaldiRecognizer(self.model, self.samplerate)
        audio = np.concatenate(audio_buffer, axis=0)
        audio_int16 = (audio * 32767).astype(np.int16)
        chunk_size = 4000
        total_samples = len(audio_int16)

        for start in range(0, total_samples, chunk_size):
            end = min(start + chunk_size, total_samples)
            chunk = audio_int16[start:end].tobytes()
            recognizer.AcceptWaveform(chunk)

        result = json.loads(recognizer.FinalResult())
        return result.get("text", "").strip()

    def run(self):
        """
        开启子Thread处理录音和文本识别任务
        """

        while not self._stop_flag.is_set():
            if not self._record_trigger.wait(timeout=0.1):
                continue

            worker = threading.Thread(target=self._record_audio, daemon=True)
            worker.start()
            worker.join()
