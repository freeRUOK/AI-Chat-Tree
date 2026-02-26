# --*-- Encoding: UTF-8 --*--
#! filename: tools/shell_tool.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2026-02
# * description: 一个简单的AI LLM聊天程序
# 简单实现了一个简单执行shell命令的工具
import subprocess
import time
import platform
from pathlib import Path
from pydantic import BaseModel, Field
from tools.result import Result
from tools import get_tool_registry

SHELL_BOX_DIR = "shell_box"
_registry = get_tool_registry()


class ShellInputModel(BaseModel):
    """
    shell命令执行工具的输入参数
    """

    timeout: float = Field(
        description="shell命令执行的超时时间（秒）",
        default=120.0,
    )
    command: str = Field(
        description=f"要执行的{platform.system()} shell命令，格外注意平台差异，路径和可用的命令都需要额外留意",
    )
    shell_work_directory: str = Field(
        description="单独工作文件夹，鼓励使用有意义的名称，鼓励同一组任务在相同文件夹下运行",
        default=f"code-{int(time.time() % 100000)}",
    )


@_registry.register
def execute_shell(shell_input_model: ShellInputModel) -> Result:
    """
    执行给定的shell命令
    严禁调用删除文件； 修改系统配置等危险命令，除非有正当理由
    :param shell_input_model: 所需的参数
    :type shell_input_model: ShellInputModel
    :return: 执行结果
    :rtype: Result
    """
    cwd = Path(SHELL_BOX_DIR).joinpath(shell_input_model.shell_work_directory)
    cwd.mkdir(parents=True, exist_ok=True)

    process = None
    result = Result(result={})

    try:
        process = subprocess.run(
            shell_input_model.command,
            cwd=cwd,
            capture_output=True,
            text=True,
            shell=True,
            timeout=shell_input_model.timeout,
        )
    except subprocess.TimeoutExpired:
        result.error = TimeoutError(
            f"Shell Command Execute Timeout: {shell_input_model.timeout}S."
        )
    except Exception as e:
        result.error = e
    finally:
        if process is not None:
            result.result = {
                "command": shell_input_model.command,
                "sdtout": process.stdout,
                "stderr": process.stderr,
                "exit_code": process.returncode,
            }

        return result
