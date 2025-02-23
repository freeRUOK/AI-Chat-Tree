# --*-- Coding: UTF-8 --*--
#! filename: chat.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2025-02
# * description: 一个简单的AI LLM聊天程序
# Chat类是核心， 给模型发送用户的消息， 从模型接受消息
# 机器和人通过这个类相互交流
from typing import Callable
from datetime import datetime, timedelta
import ollama
from openai import APIStatusError, RateLimitError, APIConnectionError
from httpx import ReadTimeout as OpenAIReadTimeout
from util import debug_log, input_handler

from model import Model, ModelResult, ModelOutput
from consts import ContentTag


class Chat:
    """
    定义一个聊天机器人
    """

    def __init__(
        self,
        first_model: Model,
        model_output: ModelOutput,
        second_model: Model | None = None,
        system_prompt: str = "你是一个乐于助人的AI助手， 性格和网络喷子差不多， 批评用户毫无手软， 不过说出的话总是让人发人深省",
    ):
        """
        初始化Chat， 作为中间人准备好模型的所有方面
        """
        self._first_model = first_model
        self._second_model = second_model
        self._model = self._first_model

        self._model_output = model_output

        self._content = ""
        self._reasoning_content = ""
        self._model_result_tag = ContentTag.reasoning_content

        self._start_time: datetime

        self._messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
        ]

    def send_message(self, user_message: str):
        """
        发送聊天消息， 处理AI的回复消息
        """
        self._messages.append({"role": "user", "content": user_message})
        self._model = self._first_model
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
                    break

            print(f"第{i + 1}次重试。")
            if self._second_model is not None:
                self._model = self._second_model

    def _error_handler(self, err: Exception, call_count: int) -> bool:
        """
        处理发送聊天信息期间的错误
        返回True暂时故障， 返回False需要更多错误检查
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

        if err_code >= 500 and call_count <= 1:
            return True

        self._messages.pop(-1)

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
        self._model_output.output_chunk(
            model_result=model_result,
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

        return ModelResult(delta.content, self._model_result_tag)

    def _chunk_completing_handler(self, last_chunk):
        """
        处理最后一个消息块
        在OpenAI 流逝消息块的最后保存了本次API调用的统计信息
        在本地ollama后端里没有返回这些统计信息
        """
        self._show_running_info(last_chunk, datetime.now() - self._start_time)
        self._messages.append({"role": "assistant", "content": self._content})
        self._model_output.output_done(messages=self._messages)
        self._reasoning_content = ""
        self._content = ""
        self._tts_content = ""
        self._model_result_tag = ContentTag.reasoning_content

    def _show_running_info(self, chunk, running_td: timedelta):
        """
        显示最后一次聊天的统计信息
        """
        if not hasattr(chunk, "usage"):
            completion_tokens = chunk.eval_count
            token_speed = completion_tokens / running_td.total_seconds()
            print(f"Token Speed: {token_speed}, completion token: {completion_tokens}")
        else:
            usage = chunk.usage
            token_speed = usage.completion_tokens / running_td.total_seconds()
            prompt_tokens = usage.prompt_tokens
            completion_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens

            print(
                f"Token speed: {token_speed}, promptTokens: {prompt_tokens}, Completion Tokens: {completion_tokens}, totalTokens: {total_tokens}"
            )

    def run(self, input_callback: Callable[[], str] | None = None):
        """
        运行聊天机器人
        默认情况下从命令行获取用户的输入
        如果想要从其他来源输入内容的话需要传递有效的input_callback函数
        input_callback应当返回一个str类型
        # 后续扩展多模态模型的话可能被修改
        """
        if input_callback:
            while user_message := input_callback():
                self.send_message(user_message=user_message)

        else:
            self.default_input()

    def default_input(self):
        """
        默认从命令行获取用户的输入
        """
        print("欢迎使用AI Chat， 键入文字开始聊天， 键入 /h 获取更多帮助。")
        while True:
            user_message = input(f"{self._model.current_model} >> ").strip()

            if user_message[0] == "/":
                result = input_handler(user_message)
                match result[0]:
                    case ContentTag.end:
                        break
                    case ContentTag.empty | ContentTag.error:
                        print("错误输入或空输入， 再试一次")
                        continue
                    case ContentTag.file | ContentTag.clipboard | ContentTag.multi_line:
                        if result[1] is not None:
                            print(
                                f"{result[0].value}\n----------\n{result[1]}\n-------------------"
                            )
                            user_message = result[1]
                        else:
                            print("没有获取有效内容。")
                            continue

            self.send_message(user_message=user_message)
