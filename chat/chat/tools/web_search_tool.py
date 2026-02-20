# --*-- Encoding: UTF-8 --*--
#!filename: tools/web_search_tool.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2026-02
# * description: 一个简单的AI LLM聊天程序
# 实现了一个Web搜索工具， 优先使用duckduckgo， 备用百度
import requests
from ddgs import DDGS
from baidusearch.baidusearch import search as bds
from pydantic import BaseModel, Field
from tools.result import Result
from tools import get_tool_registry
from util import first_online_host

_registry = get_tool_registry()
_web_search_address: tuple | None = first_online_host(
    addresss=[("duckduckgo.com", 443), ("baidu.com", 443)]
)


class _WebSearchInput(BaseModel):
    """
    WebSearch工具的输入参数
    """

    query: str = Field(description="搜索关键词")

    max_results: int = Field(default=8, description="返回结果数量，默认 8", ge=1, le=25)


def _get_real_url(baidu_link: str) -> str:
    """
    获取百度搜索结果的真是URL
    :param baidu_link: 被百度加密的跳转URL
    :type baidu_link: str
    :return: 如果能查到真是URL则返回， 否则加密URL原样返回
    :rtype: str
    """
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0"
    }
    try:
        response = requests.get(baidu_link, headers=headers, allow_redirects=False)
        if response.status_code == 302:
            return response.headers.get("Location", baidu_link)

    except Exception:
        pass

    return baidu_link


# 自动注册工具
@_registry.register
def web_search(input_model: _WebSearchInput) -> Result:
    """
    工具的实现
    :param input_model: 工具的参数统一接受 pydantic.BaseModel 的子类型
    :type input_model: _WebSearchInput
    :return: 返回工具执行结果， , 执行结果统一使用Result类型
    :rtype: Result
    """
    global _web_search_address
    search_results = []
    url_name, body_name = "href", "body"
    # 开始搜索
    try:
        if (
            _web_search_address is not None
            and _web_search_address[0] == "duckduckgo.com"
        ):
            with DDGS() as ddgs:
                search_results = list(
                    ddgs.text(input_model.query, max_results=input_model.max_results)
                )
        else:
            search_results = bds(input_model.query, num_results=input_model.max_results)
            url_name = "url"
            body_name = "abstract"
        # 统一搜索结果
        search_data = [
            {
                "title": result.get("title", ""),
                "url": result.get(url_name, "")
                if _web_search_address[0] != "baidu.com"
                else _get_real_url(result.get("url")),
                "snippet": result.get(body_name, ""),
            }
            for result in search_results
        ]

        return Result(result=search_data)
    except Exception as e:
        return Result(result={}, error=e)
