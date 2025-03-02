# --*-- Coding: UTF-8 --*--
#! filename: text_to_speech.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2025-02
# * description: 一个简单的AI LLM聊天程序
# 实现了TTS功能， 首先通过edge_tts生成音频随后排队播放
from typing import Callable
from io import BytesIO
import asyncio
import threading
from queue import Queue
import edge_tts
import simpleaudio as sa  # type: ignore
from pydub import AudioSegment  # type: ignore
from aiohttp.client_exceptions import WSServerHandshakeError as EdgeTTSServerError
from util import clear_queue, debug_log


class TextToSpeech(threading.Thread):
    """
    使用edge-tts实现一个TTS功能
    """

    def __init__(
        self,
        auto_play: bool,
        voice: str = "Microsoft Server Speech Text to Speech Voice (zh-CN, YunjianNeural)",
        rate: str = "+100%",
        volume: str = "+0%",
        process_callback: Callable[[AudioSegment], None] | None = None,
    ):
        super().__init__()
        self.daemon = True
        self.auto_play = auto_play
        self._voice = voice
        self._rate = rate
        self._volume = volume
        self._process_callback = process_callback
        self._textQueue: Queue = Queue()

    def submit(self, text: str):
        """
        外部线程提交需要合成的文本内容
        """
        text = text.strip()
        if text:
            self._textQueue.put(text)

    def stop(self):
        """
        停止运行
        """
        self._textQueue.put(None)
        self.join()
        print("所有线程都正确结束。")

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
        while audio_segment := audioQueue.get():
            if self.auto_play:
                self.playAudioSegment(audio_segment=audio_segment)
            elif self._process_callback:
                self._process_callback(audio_segment)
            else:
                raise RuntimeWarning(
                    "TTS转换后的结果没有处理, 应当设置auto_play=True或者传递process_callback函数"
                )

        clear_queue(audioQueue)

    async def _convert_async(self, text: str) -> AudioSegment | None:
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

            audio = AudioSegment.from_mp3(buffer)

            return audio
        except Exception as e:
            raise e

            return None

    def convert(self, text: str) -> AudioSegment | None:
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
        audioQueue = Queue()
        threading.Thread(
            target=self.process,
            args=[
                audioQueue,
            ],
        ).start()
        try:
            while text := self._textQueue.get():
                if audio_segment := self.convert(text):
                    audioQueue.put(audio_segment)

        except Exception as e:
            print(f"tts Thread出现错误： {e}")
            debug_log(e)
        finally:
            clear_queue(self._textQueue)
            audioQueue.put(None)
