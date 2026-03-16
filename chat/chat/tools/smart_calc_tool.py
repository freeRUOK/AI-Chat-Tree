# --*-- Encoding: UTF-8 --*--
#! filename: /tools/smart_calc_tool.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2026-03
# * description: 一个简单的AI LLM聊天程序
"""
SmartCalc - 智能计算工具
数学计算 + 单位换算 + 历法查询
"""

from typing import Literal
from datetime import datetime
from pydantic import BaseModel, Field
from simpleeval import simple_eval  # type: ignore
from lunar_python import Lunar, Solar  # type: ignore
import chinese_calendar as calendar  # type: ignore
from pint import UnitRegistry
from tools import get_tool_registry
from tools.result import Result

registry = get_tool_registry()
ureg: UnitRegistry = UnitRegistry()


class SmartInput(BaseModel):
    func: Literal["calc", "convert", "time"]
    expr: str = Field(default="", description="表达式或换算")
    year: int = Field(default=2026)
    month: int = Field(default=1, ge=1, le=12)
    day: int = Field(default=1, ge=1, le=31)


def _now() -> dict:
    """
    当前时间信息
    """
    dt = datetime.now()
    lunar = Lunar.fromDate(dt)
    is_hol, name = calendar.get_holiday_detail(dt.date())

    return {
        "datetime": dt.isoformat(),
        "date": dt.strftime("%Y-%m-%d"),
        "weekday": dt.strftime("%A"),
        "lunar": lunar.toString(),
        "shengxiao": lunar.getYearShengXiao(),
        "jieqi": lunar.getJieQi(),
        "holiday": name or "无",
    }


@registry.register
def smart_calc(p: SmartInput) -> Result:
    """
    smart_calc - 计算/换算/时间查询

    calc:   数学计算  {"func": "calc", "expr": "2 + 3 * 4"}
    convert:单位换算  {"func": "convert", "expr": "10 m to km"}
    time:   时间查询  {"func": "time", "expr": "now"} 或 {"func": "time", "year": 2024, "month": 8, "day": 23}
    """
    try:
        match p.func:
            case "calc":
                return Result(result={"result": simple_eval(p.expr)})
            case "convert":
                # 解析 "10 m to km"
                a, b, c = p.expr.replace(" to ", " ").split()
                r = (float(a) * ureg(b)).to(c)
                return Result(
                    result={"result": float(r.magnitude), "unit": str(r.units)}
                )
            case "time":
                # expr="now" 或指定日期转换
                if p.expr == "now" or not any([p.year, p.month, p.day]):
                    return Result(result=_now())

                # 公历转农历
                solar = Solar.fromYmd(p.year, p.month, p.day)
                lunar = solar.getLunar()
                return Result(
                    result={
                        "solar": f"{p.year}-{p.month:02d}-{p.day:02d}",
                        "lunar": lunar.toString(),
                        "shengxiao": lunar.getYearShengXiao(),
                    }
                )

            case _:
                return Result(error=ValueError(f"未知: {p.func}"), result={})

    except Exception as e:
        return Result(error=e, result={})
