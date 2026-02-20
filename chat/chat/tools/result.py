# --*-- Encoding: UTF-8 --*--
#! filename: tools/result.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2026-02
# * description: 一个简单的AI LLM聊天程序
# 定义工具调用执行结果


class Result:
    """
    表示工具调用的结果
    """

    def __init__(self, result: dict, error: Exception | None = None):
        """
        工具应当返回这个类型
            :param result: 执行结果， 应当使用可读性高的格式返回
            :type result: dict
            :param error: 工具执行错误
            :type error: Exception | None
        """
        self.result = result
        self.error = error

    def to_json(self) -> dict[str, dict]:
        """
        转换到json object， 方便发送给LLM
        :return: 返回原始python Object类型
        :rtype: dict[str, dict]
        """
        return {"error": str(self.error), "result": self.result}
