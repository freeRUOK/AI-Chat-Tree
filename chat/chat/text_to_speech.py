# --*-- Coding: UTF-8 --*--
#! filename: text_to_speech.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2025-02
# * description: 一个简单的AI LLM聊天程序
# 实现了TTS功能， 首先通过edge_tts生成音频随后排队播放
from typing import Callable
from enum import Enum
from io import BytesIO
import asyncio
import re
import threading
from queue import Queue
import edge_tts
import simpleaudio as sa  # type: ignore
from pydub import AudioSegment  # type: ignore
from aiohttp.client_exceptions import WSServerHandshakeError as EdgeTTSServerError
from util import clear_queue, debug_log


class TextToSpeechOption(str, Enum):
    """
    标记如何处理生成的音频流
    """

    off = "off"  # 完全关闭， 客户端不应该创建TextToSpeech实例
    play = "play"  # 自动播放
    byte_io = "byte_io"  # 作为ByteIO数据流让audio_callback处理
    all = "all"  # 自动播放和后续处理


class TextToSpeech(threading.Thread):
    """
    使用edge-tts实现一个TTS功能
    """

    def __init__(
        self,
        option: TextToSpeechOption = TextToSpeechOption.play,
        voice: str = "Microsoft Server Speech Text to Speech Voice (zh-CN, YunjianNeural)",
        rate: str = "+100%",
        volume: str = "+0%",
        process_callback: Callable[[BytesIO], None] | None = None,
    ):
        super().__init__()
        self.daemon = True
        self.option = option
        self._voice = voice
        self._rate = rate
        self._volume = volume
        self._process_callback = process_callback
        self._textQueue: Queue = Queue()
        self._reg_replace = re.compile(r"[#*|]")

    def submit(self, text: str):
        """
        外部线程提交需要合成的文本内容
        """
        text = self._reg_replace.sub(",", text.strip())
        if text:
            self._textQueue.put(text)

    def stop(self):
        """
        停止运行
        """
        if self.is_alive():
            self._textQueue.put(None)
            self.join()

        print("Text To Thread Stop.")

    def playAudioSegment(self, audio_segment: AudioSegment):
        """
        播放音频
        """
        rawData = audio_segment.raw_data
        numChannels = audio_segment.channels
        sampleRate = audio_segment.frame_rate
        bytesPerSample = audio_segment.sample_width

        try:
            waveObj = sa.WaveObject(rawData, numChannels, bytesPerSample, sampleRate)
            playObj = waveObj.play()
            playObj.wait_done()
        except Exception as e:
            debug_log(e)
        finally:
            playObj.stop()

    def process(self, audioQueue: Queue):
        """
        处理音频， 自动播放或者让process_callback处理
        """
        while audio_buffer := audioQueue.get():
            if self.option == TextToSpeechOption.off:
                continue

            if self.option != TextToSpeechOption.byte_io:
                audio_segment = AudioSegment.from_mp3(audio_buffer)
                self.playAudioSegment(audio_segment=audio_segment)
            if self._process_callback and self.option != TextToSpeechOption.play:
                audio_buffer.seek(0)
                self._process_callback(audio_buffer)

        clear_queue(audioQueue)

    async def _convert_async(self, text: str) -> BytesIO | None:
        """
        把文本内容转换到mp3AudioSegment
        """
        try:
            communicate = edge_tts.Communicate(
                text=text, voice=self._voice, rate=self._rate, volume=self._volume
            )

            buffer = BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    buffer.write(chunk["data"])

            buffer.seek(0)
            return buffer
        except Exception as e:
            raise e

            return None

    def convert(self, text: str) -> BytesIO | None:
        """
        对文本到语音函数的包装
        """
        try:
            return asyncio.run(self._convert_async(text=text))
        except (edge_tts.exceptions.EdgeTTSException, EdgeTTSServerError) as e:
            debug_log(e)
            debug_log(ValueError(f"Error Text: {text}"))
        return None

    def run(self):
        """
        run函数， 启动播放任务， 监听文本内容提交
        """
        audioQueue: Queue = Queue()
        threading.Thread(
            target=self.process,
            args=[
                audioQueue,
            ],
        ).start()
        try:
            while text := self._textQueue.get():
                if audio_buffer := self.convert(text):
                    audioQueue.put(audio_buffer)

        except Exception as e:
            print(f"tts Thread出现错误： {e}")
            debug_log(e)
        finally:
            clear_queue(self._textQueue)
            audioQueue.put(None)
