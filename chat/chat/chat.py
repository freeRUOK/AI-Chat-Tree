# --*-- Coding: UTF-8 --*--
#! filename: chat.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2025-02
# * description: 一个简单的AI LLM聊天程序
# Chat类是核心， 给模型发送用户的消息， 从模型接受消息
# 机器和人通过这个类相互交流
import threading
from copy import deepcopy
from typing import Callable
from datetime import datetime, timedelta
import ollama
from openai import APIStatusError, RateLimitError, APIConnectionError
from httpx import ReadTimeout as OpenAIReadTimeout
from model_tools import create_or_switch_model
from util import debug_log

from model import Model, ModelResult, ModelOutput
from consts import ContentTag, _format, _has_image, _is_request


class Chat:
    """
    定义一个聊天机器人
    """

    def __init__(
        self,
        first_model: Model,
        model_output: ModelOutput,
        models: list,
        second_model: Model | None = None,
        system_prompt: str = "你是一个乐于助人的AI助手， 性格和网络喷子差不多， 批评用户毫无手软， 不过说出的话总是让人发人深省",
        begin_callback: Callable[[], dict | None] | None = None,
    ):
        """
        初始化Chat， 作为中间人准备好模型的所有方面
        """
        self._first_model = first_model
        self._second_model = second_model
        self._models = models
        self._model = self._first_model
        self._begin_callback = begin_callback
        self._lock = threading.Lock()

        self._model_output = model_output

        self._content = ""
        self._reasoning_content = ""
        self._model_result_tag = ContentTag.chunk

        self._start_time: datetime

        self._messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
        ]

    def _append_message(
        self, user_message: str, base64_image: str | None = None
    ) -> bool:
        """
        在会话队列当中插入新的用户消息
        :param user_message: 用户发送给LLM的文本消息
        :type user_message: str
        :param base64_image: base64编码后的图片
        :type base64_image: str | None
        成功添加消息返回True， 否则返回False
        """
        new_message = {}
        if self._model.is_online:
            content = [{"type": "text", "text": user_message}]
            if base64_image:
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_image}"},
                    }
                )
            new_message = {"role": "user", "content": content}
        else:
            msg = {"role": "user", "content": user_message}
            if base64_image:
                msg["images"] = [
                    base64_image,
                ]
            new_message = msg

        if new_message:
            new_message[_format] = "openai" if self._model.is_online else "ollama"
            new_message[_has_image] = base64_image is not None
            new_message[_is_request] = True
            self._messages.append(new_message)
            return True

        return False

    def send_message(self, user_message: str, base64_image: str | None = None):
        """
        发送聊天消息， 处理AI的回复消息
        """
        self._model = self._first_model
        self._model_result_tag = ContentTag.chunk
        self._append_message(user_message=user_message, base64_image=base64_image)
        # 如果错误可以恢复的话最多3次重试
        for i in range(3):
            try:
                response = self._model.chat(messages=self._messages)

                self._start_time = datetime.now()
                # 处理流逝返回的消息块
                for chunk in response:
                    self._chunk_handler(chunk=chunk)

                break
            except (
                APIStatusError,
                RateLimitError,
                APIConnectionError,
                OpenAIReadTimeout,
                ollama.ResponseError,
            ) as e:
                debug_log(e)
                if not self._error_handler(e, call_count=i):
                    print("建议查看网络状态或查看配置是否异常。")
                    self._model = self._first_model
                    break

            print(f"第{i + 1}次重试。")
            if self._second_model is not None:
                self._model = self._second_model

    def _error_handler(self, err: Exception, call_count: int) -> bool:
        """
        处理发送聊天信息期间的错误
        返回True暂时故障，
        返回False不可恢复错误， 可能是程序bug或者配置错误
        """

        err_code = -1
        if isinstance(err, APIStatusError):
            print(f"错误： {err.message}")
            err_code = err.status_code
        elif isinstance(err, OpenAIReadTimeout):
            err_code = 600
            print("读取超时")
        elif isinstance(err, ollama.ResponseError):
            print(f"错误： Error Code {err.status_code} {err}")
            err_code = err.status_code
        else:
            print(f"错误： {err}")

        if err_code >= 500 and call_count < 3:
            return True

        self._messages.pop(-1)
        self._model_output.output_done([])

        return False

    def _chunk_handler(self, chunk):
        """
        处理每个流逝返回的消息块
        """
        if self._model.is_online:
            delta = chunk.choices[0].delta
            finish_reason = chunk.choices[0].finish_reason
        else:
            delta = chunk.message
            finish_reason = chunk.done_reason

        model_result = self._delta_handler(delta=delta)
        model_result.model_name = chunk.model

        self._model_output.output_chunk(
            model_result=deepcopy(
                model_result
            ),  #  防止在其他地方意外修改， 这里直接拷贝， 在这里我实际吃过亏
            show_reasoning=self._model.show_reasoning,
            finish_reason=finish_reason,
        )

        if model_result.tag == ContentTag.reasoning_content:
            self._reasoning_content += model_result.content
        else:
            self._content += model_result.content

        if finish_reason == "stop":
            self._chunk_completing_handler(last_chunk=chunk)

    def _delta_handler(self, delta) -> ModelResult:
        """
        返回消息块， 并且标记这个消息块是否为reasoning content
        """
        # 有些LLM后端单独提供了reasoning_content属性， 有的在content开头使用<think> </think>包裹
        # 这里分别处理两种情况
        if hasattr(delta, "reasoning_content"):
            if delta.content is not None:
                return ModelResult(delta.content, ContentTag.chunk)
            else:
                return ModelResult(
                    delta.reasoning_content, ContentTag.reasoning_content
                )
        elif delta.content in ["<think>", "</think>"]:
            self._model_result_tag = (
                ContentTag.reasoning_content
                if delta.content == "<think>"
                else ContentTag.chunk
            )
            delta.content = "\n"

        return ModelResult(delta.content, self._model_result_tag)

    def _clear_message(self):
        """
        调用结束之后清理额外的数据， 统一格式
        """
        index = -1
        target = self._messages[index]
        while _is_request not in target and index >= 0:
            target = self._messages[index]
            index -= 1

        if _is_request not in target:
            return

        if target[_format] == "openai":
            target["content"] = target["content"][0]["text"]

        if target[_has_image] and "images" in target:
            target.pop("images")

    def _chunk_completing_handler(self, last_chunk):
        """
        处理最后一个消息块
        在OpenAI 流逝消息块的最后保存了本次API调用的统计信息
        在本地ollama后端里没有返回这些统计信息
        """
        self._show_running_info(last_chunk, datetime.now() - self._start_time)
        self._clear_message()
        self._messages.append({"role": "assistant", "content": self._content})
        self._model_output.output_done(messages=self._messages)
        self._reasoning_content = ""
        self._content = ""
        self._tts_content = ""

    def _show_running_info(self, chunk, running_td: timedelta):
        """
        显示最后一次聊天的统计信息
        """
        if not hasattr(chunk, "usage"):
            completion_tokens = chunk.eval_count
            token_speed = completion_tokens / running_td.total_seconds()
            print(f"Token Speed: {token_speed}, completion token: {completion_tokens}")
        elif chunk.usage is not None:
            usage = chunk.usage
            token_speed = usage.completion_tokens / running_td.total_seconds()
            prompt_tokens = usage.prompt_tokens
            completion_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens
            print(
                f"Token speed: {token_speed}, promptTokens: {prompt_tokens}, Completion Tokens: {completion_tokens}, totalTokens: {total_tokens}"
            )
        else:
            print(" Token statistics are currently unavailable.")

    def run(self, input_callback: Callable[[], tuple[str, str | None]] | None = None):
        """
        运行聊天机器人
        默认情况下从命令行获取用户的输入
        如果想要从其他来源输入内容的话需要传递有效的input_callback函数
        input_callback应当返回一个Tuple[str, str | None]类型
        如果需要输入图片的话第二个元素传入base64编码的图片
        """
        if input_callback:
            while user_message := input_callback():
                self.set_status()
                self.send_message(
                    user_message=user_message[0], base64_image=user_message[1]
                )

        else:
            raise RuntimeError("InputCallback Callback Is None.")

    def set_status(self):
        """
        使用前端客户端的最新状态更新模型状态
        初始化阶段客户端需要传递begin_callback函数
        """
        if self._begin_callback is None:
            return

        with self._lock:
            client_status = self._begin_callback()
            if client_status is None:
                return

            self._model_output.set_text_to_text_option(
                client_status["text_to_speech_option"]
            )

            new_system_prompt = client_status["system_prompt"]
            if self._messages[0]["content"] != new_system_prompt:
                self._messages[0]["content"] = new_system_prompt

            self.switch_model(
                first_model=client_status["first_model_name"],
                second_model=client_status["second_model_name"],
            )

    def switch_model(self, first_model: str, second_model: str | None = None):
        """
        切换模型
        """
        if self._first_model.current_model != first_model:
            if new_model := create_or_switch_model(
                model_list=self._models, model_name=first_model, model=self._first_model
            ):
                self._first_model = new_model

        if self._second_model and self._second_model.current_model != second_model:
            self._second_model = create_or_switch_model(
                model_list=self._models,
                model_name=second_model,
                model=self._second_model,
            )
