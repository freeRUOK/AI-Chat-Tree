# --*-- Encoding: UTF-8 --*--
#! filename: tools/result.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2026-02
# * description: 一个简单的AI LLM聊天程序
# 定义工具调用执行结果
import json
from typing_extensions import Any


class Result:
    """
    表示工具调用的结果
    如果LLM不更新todos这里返回系统提示
    """

    def __init__(
        self, result: dict, error: Exception | None = None, reminder: str | None = None
    ):
        """
        工具应当返回这个类型
            :param result: 执行结果， 应当使用可读性高的格式返回
            :type result: dict
            :param error: 工具执行错误
            :type error: Exception | None
            :param reminder: 系统提醒消息， 比如通过这个字段来提醒LLM该更新todos了
            :type reminder: str | None
        """
        self.result = result
        self.error = error
        self.reminder = reminder

    def to_json(self) -> dict[str, Any]:
        """
        转换到json object， 方便发送给LLM
        :return: 返回原始python Object类型
        :rtype: dict[str, dict]
        """
        data = {"error": str(self.error), "result": self.result}
        if self.reminder:
            data["system_reminder"] = self.reminder

        return data

    def __repr__(self) -> str:
        """
        返回json格式的字符串
        """
        return json.dumps(self.to_json(), ensure_ascii=False)
