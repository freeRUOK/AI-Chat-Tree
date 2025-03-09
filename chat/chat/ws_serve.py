# --*-- Coding: UTF-8 --*--
#! filename: wx_serve_sync.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2025-03
# * description: 一个简单的AI LLM聊天程序
# web后端
# 和web前端协同工作

from io import BytesIO
from contextlib import ExitStack
import os
from datetime import datetime
from flask import Flask, send_from_directory
from flask_socketio import SocketIO
from data_status import DataStatus as ServeStatus
from config import Config
from consts import ContentTag
from application import Application
from model import ModelResult
from util import debug_logger


class WSServe:
    """
    socket io 服务（同步版本），处理socketio事件和Flask路由
    """

    def __init__(self):
        self.serve_status = ServeStatus()
        self.application: Application | None = None
        self.app = Flask(__name__)
        self.app.config["SECRET_KEY"] = "secret!"
        self.sio = SocketIO(self.app, cors_allowed_origins="*")
        self.setup_routes()
        self.setup_socketio_events()

    def __enter__(self):
        """
        上下文自动管理
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_bt):
        """
        上下文自动管理
        """
        self.serve_status.message_queue.put(None)

    def setup_routes(self):
        """
        设置http路由，便于处理静态文件和首页重定向
        """
        static_folder_path = os.path.abspath(os.path.join(os.getcwd(), "static"))

        @self.app.route("/<path:filename>")
        def static_files(filename):
            return send_from_directory(static_folder_path, filename)

        @self.app.route("/")
        def index():
            return send_from_directory(static_folder_path, "index.html")

    def setup_socketio_events(self):
        """
        注册socketio的事件
        """

        @self.sio.on("connect")
        def handle_connect():
            """
            socketio的connect事件
            """
            debug_logger.info("Client connected")

        @self.sio.on("chat")
        def handle_chat(message):
            """
            处理socketio的chat自定义事件
            """
            debug_logger.info(f"Received message: {message}")
            msg = message["text"].strip()
            if msg:
                self.serve_status.message_queue.put(msg)
            else:
                self.sio.emit("chat", {"text": "Empty Input Message."})

        @self.sio.on("disconnect")
        def handle_disconnect():
            """
            socketio disconnect事件
            """
            debug_logger.info("Client disconnected")

    def output_chunk(self, model_result: ModelResult):
        """
        每次模型输出消息块的时候调用
        """
        self.serve_status.line += model_result.content
        if self.serve_status.line[-1:] == "\n" or model_result.tag == ContentTag.end:
            self.sio.emit("chat", {"text": self.serve_status.line})
            self.serve_status.line = ""

    def output_audio(self, audio_buffer: BytesIO):
        """
        每次一段TTS音频生成的时候调用
        """
        self.sio.emit("audio", {"audio/mpeg3": audio_buffer.read()})

    def output_finish(self, messages: list | None = None):
        """
        模型输出完成之后调用，清空缓冲区
        """
        self.output_chunk(model_result=ModelResult("", tag=ContentTag.end))

    def run(self, port=8001):
        """
        启动服务
        """
        with ExitStack() as stack:
            config = stack.enter_context(Config())
            application = stack.enter_context(
                Application(
                    config=config,
                    model_name="deepseek-reasoner",
                    second_model_name="qwq",
                    is_speak=False,
                    input_callback=self.serve_status.message_queue.get,
                    chunk_callback=self.output_chunk,
                    audio_callback=self.output_audio,
                    finish_callback=self.output_finish,
                )
            )
            application.start()

            self.sio.run(self.app, host="0.0.0.0", port=port)
