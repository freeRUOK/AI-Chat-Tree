# --*-- Coding: UTF-8 --*--
#! filename: cli.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2025-02
# * description: 一个简单的AI LLM聊天程序
# 懒人必备
# 这样一搞牺牲掉了很大的灵活性
from typing import Callable
from contextlib import ExitStack
from config import Config
from application import Application
from consts import default_system_prompt
from model import ModelOutput, ModelResult
from util import debug_log, DEBUG_MODE


def run(
    model_name: str = "deepseek-reasoner",
    second_model_name: str = "deepseek-r1:14b",
    system_prompt: str = default_system_prompt,
    is_speak: bool = True,
    input_callback: Callable[[], str] | None = None,
    chunk_callback: Callable[[ModelResult], None] | None = None,
    finish_callback: Callable[[list], None] | None = None,
):
    """
    如果对细节不感兴趣直接调用这个函数
    只不过需要检查配置文件和ollama可用的模型， 只要这些没问题可以在cli调用
    如果需要在web或gui上使用的话需要实现线程安全的三大接口
    """
    try:
        # 串联支持with语句的对象
        with ExitStack() as context_stack:
            config = context_stack.enter_context(Config())
            model_output = context_stack.enter_context(
                ModelOutput(
                    config=config,
                    is_speak=is_speak,
                    chunk_callback=chunk_callback,
                    finish_callback=finish_callback,
                )
            )

            application = context_stack.enter_context(Application(config=config))

            application._begin(
                model_output=model_output,
                first_model_name=model_name,
                second_model_name=second_model_name,
                system_prompt=system_prompt,
            )
            application.run(input_callback=input_callback)
    except Exception as e:
        if DEBUG_MODE:
            raise e
        else:
            print(
                f"错误： {e}\n可以设置环境变量debug_mode启用调试模式之后查看日志文件和调用堆栈。"
            )

        debug_log(e)
