# --*-- Coding: UTF-8 --*--
#! filename: consts.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2025-02
# * description: 一个简单的AI LLM聊天程序
# 定义一些符号常量和枚举类型
from enum import Enum

# 几个重要的参数
CONFIG_PATH = "config.yml"
default_system_prompt = """你是一个聪明伶俐， 可爱温柔， 古灵精怪 善解人意的女孩
对任何事情都有自己独特而犀利的见解， 从来不会让人类伙伴失望
请注意你的任何回应必须模仿上面的人设。 
对于任何话题提出换位思考和批判性思考。 
在回应中不要过多使用表情符号
当然介绍一些难以理解的概念的时候总是说人话， 竭尽所能通俗化解释任何事物。
"""


class ContentTag(str, Enum):
    """
    文本内容的来源的标记
    """

    help = "help"
    file = "file"
    multi_line = "multi_line"
    chunk = "chunk"
    clipboard = "clipboard"
    empty = "empty"
    end = "end"
    error = "error"
    reasoning_content = "reasoning_content"
