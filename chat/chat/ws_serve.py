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
from flask import Flask, send_from_directory
from flask_socketio import SocketIO
from data_status import DataStatus as ServeStatus
from config import Config
from consts import ContentTag
from application import Application
from model import ModelResult
from util import debug_logger, ImageHandler
from text_to_speech import TextToSpeechOption


class WSServe:
    """
    socket io 服务（同步版本），处理socketio事件和Flask路由
    """

    def __init__(self):
        self.serve_status = ServeStatus()
        self._image_handler = ImageHandler()
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

    def load_models_status(self):
        """
        获取后端模型， 包括所有可用的模型和当前模型和备用模型
        """
        if self.application:
            self.serve_status.load_models_status(application=self.application)
            status = {
                "system_prompt": self.serve_status.system_prompt,
                "models": self.serve_status.models,
                "first_model": self.serve_status.first_model,
                "second_model": self.serve_status.second_model,
                "text_to_speech_option": not self.serve_status.text_to_speech_option
                == TextToSpeechOption.off,
            }
            self.sio.emit("model_status", status)

    def setup_socketio_events(self):
        """
        注册socketio的事件
        """

        @self.sio.on("connect")
        def handle_connect():
            """
            socketio的connect事件
            """
            self.load_models_status()
            debug_logger.info("Client connected")

        @self.sio.on("chat")
        def handle_chat(message):
            """
            处理socketio的chat自定义事件
            """
            debug_logger.info(f"Received message: {message}")
            msg = message.get("text", "简明扼要的描述一下这个图片")
            image_buf = message.get("image")
            if image_buf:
                self._image_handler.read_image_file(image_buf)

            if msg:
                self.serve_status.message_queue.put(
                    (
                        msg.strip() or "这个图片里是什么？",
                        self._image_handler.to_base64(),
                    )
                )
                self._image_handler.close_current_image()
            else:
                self.sio.emit("chat", {"text": "Empty Input Message."})

        @self.sio.on("update_status")
        def handle_update_status(new_status):
            """
            处理socketio的update_status自定义事件
            """
            if new_status is None:
                return

            self.serve_status.is_change = True
            self.serve_status.system_prompt = new_status["system_prompt"]
            self.serve_status.first_model = new_status["first_model"]
            self.serve_status.second_model = new_status["second_model"]
            self.serve_status.text_to_speech_option = (
                TextToSpeechOption.byte_io
                if new_status["text_to_speech_option"]
                else TextToSpeechOption.off
            )
            debug_logger.info(f"Received New Status: {new_status}")

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
        if self.serve_status.current_content_tag != model_result.tag:
            self.serve_status.current_content_tag = model_result.tag
            model_result.content = f"\n{model_result.content}"

        self.serve_status.line += model_result.content
        self.serve_status.current_model_name = model_result.model_name
        if self.serve_status.line[-1:] == "\n" or model_result.tag == ContentTag.end:
            self.sio.emit(
                "chat",
                ModelResult(
                    self.serve_status.line,
                    self.serve_status.current_content_tag,
                    self.serve_status.current_model_name,
                ).to_dict(),
            )
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
        self.output_chunk(
            model_result=ModelResult(
                "", tag=ContentTag.end, model_name=self.serve_status.current_model_name
            )
        )

    def run(self, port=8001):
        """
        启动服务
        """
        with ExitStack() as stack:
            config = stack.enter_context(Config())
            self.application = stack.enter_context(
                Application(
                    config=config,
                    model_name="qwq:latest",
                    second_model_name="deepseek-r1:8b",
                    text_to_speech_option=TextToSpeechOption.byte_io,
                    begin_callback=self.serve_status.on_begin,
                    input_callback=self.serve_status.message_queue.get,
                    chunk_callback=self.output_chunk,
                    audio_callback=self.output_audio,
                    finish_callback=self.output_finish,
                )
            )
            if self.application:
                self.application.start()

            self.sio.run(self.app, host="0.0.0.0", port=port)
