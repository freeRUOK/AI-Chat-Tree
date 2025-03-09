# --*-- Coding: UTF-8 --*--
#! filename: data_status.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2025-02
# * description: 一个简单的AI LLM聊天程序
# 单独分离UI相关的一些数据
from queue import Queue
from consts import default_system_prompt


class DataStatus:
    """
    单独管理和UI相关联的一些状态数据
    """

    def __init__(self):
        self.models: list | None = None
        self.first_model = ""
        self.second_model = ""
        self.is_speak = True
        self.message_queue: Queue = Queue()
        self.line = ""
        self.system_prompt = default_system_prompt
