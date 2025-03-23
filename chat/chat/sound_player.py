# --*-- Coding: UTF-8 --*--
#! filename: sound_player.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2025-03
# * description: 一个简单的AI LLM聊天程序
# 音效播放器
from pathlib import Path
from enum import Enum
from queue import Queue
import threading
import simpleaudio as sa  # type: ignore
from util import clear_queue, debug_log


class PlayMode(str, Enum):
    """
    播放模式
    """

    loop = "loop"
    ones_async = "ones_async"
    ones_sync = "ones_sync"


class SoundPlayer(threading.Thread):
    """
    在独立线程实现一个简单音效播放器
    """

    def __init__(self):
        super().__init__()
        self._lock = threading.Lock()
        self.queue: Queue = Queue()
        self._back_play_mode = PlayMode.ones_async
        self.play_object: sa.PlayObject | None = None
        self.is_loop = False
        self._sounds: dict[str, sa.WaveObject] = {}
        try:
            self._sounds = {
                path.stem.lower(): sa.WaveObject.from_wave_file(str(path))
                for path in Path("./sounds").glob("*.wav")
                if path.is_file()
            }
        except Exception as e:
            debug_log(e)

    def play(self, name: str, play_mode: PlayMode):
        """
        播放指定的音效
        """
        if name in self._sounds:
            self.queue.put(
                (
                    name,
                    play_mode,
                )
            )

    def stop(self):
        """
        停止播放器
        """
        with self._lock:
            try:
                self.queue.put(None)
                self.join()
                if self.play_object:
                    self.play_object.stop()
            except Exception as e:
                debug_log(e)

    def stop_play(self):
        """
        停止当前播放的音效
        """
        with self._lock:
            self.is_loop = False
            if self.play_object:
                self.play_object.stop()

    def run(self):
        """
        播放器核心逻辑
        """
        while res := self.queue.get():
            name, play_mode = res
            wave_object = self._sounds.get(name)
            if wave_object is None:
                continue

            if play_mode == PlayMode.loop:
                self.is_loop = True

            self._back_play_mode = play_mode
            try:
                while self.is_loop:
                    self.play_object = wave_object.play()
                    self.play_object.wait_done()
                else:
                    self.play_object = wave_object.play()

                if play_mode == PlayMode.ones_sync:
                    self.play_object.wait_done()

            except Exception as e:
                debug_log(e)
                continue

        clear_queue(self.queue)
