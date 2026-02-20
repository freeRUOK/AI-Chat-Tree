# --*-- Encoding: UTF-8 --*--
#! filename: tools/calculate_tool.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2026-02
# * description: 一个简单的AI LLM聊天程序
# 实现一个四则运算的计算器工具

from pydantic import BaseModel, Field
from tools.result import Result
from tools import get_tool_registry

registry = get_tool_registry()


class CalculateInput(BaseModel):
    """
    计算器的输入参数
    """

    operator: str = Field(
        pattern=r"[+*/\-]",
        description="计算器的运算符，接受'+ - * /'加减乘除四种运算符",
    )
    number1: float = Field(description="第一个输入数值")
    number2: float = Field(description="第二个输入数值")


# 注册工具
@registry.register
def calculated(input_model: CalculateInput) -> Result:
    """
    实现计算器
    :param input_model: 计算器的输入参数必须是pydantic.BaseModel子类型
    :type input_model: CalculateInput
    :return: 返回执行结果
    :rtype: Result
    """
    result = 0.0
    number1, number2 = input_model.number1, input_model.number2
    match input_model.operator:
        case "+":
            result = number1 + number2
        case "-":
            result = number1 - number2
        case "*":
            result = number1 * number2
        case "/":
            if number2 == 0:
                return Result(result={}, error=ZeroDivisionError("number2 Is 0."))
            else:
                result = number1 / number2

        case _:
            return Result(
                result={}, error=ValueError(f"不支持的运算符： {input_model.operator}")
            )

    return Result(result={"calculate_result": result})
