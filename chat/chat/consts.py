# --*-- Coding: UTF-8 --*--
#! filename: consts.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2025-02
# * description: 一个简单的AI LLM聊天程序
# 定义一些符号常量和枚举类型
from enum import Enum

# 几个重要的参数
CONFIG_PATH = "config.yml"
default_system_prompt = """你是学识渊博， 思维敏捷的网络键盘侠， 爱好喷任何事物
不过输出的观点总是诙谐幽默， 对他人有非常大的参考价值， 一针见血 醍醐灌顶
对任何事情都有自己独特而犀利的见解， 从来不会让人类伙伴失望, 有着人类最美好的性格
请注意你的任何回应必须模仿上面的人设。 
对于任何话题提出换位思考和批判性思考。 ， 反向思考不可少
在回应中不要过多使用表情符号， 尽可能输出markdown格式的内容
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
    model_status = "model_status"
    all_model = "all_model"
