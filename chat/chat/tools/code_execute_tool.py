# --*-- Encoding: UTF-8 --*--
#! filename: tools/code_execute_tool.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2026-02
# * description: 一个简单的AI LLM聊天程序
# 简单实现了一个代码执行工具
import subprocess
import time
from pathlib import Path
import os
from pydantic import BaseModel, Field
from tools.result import Result
from tools import get_tool_registry

EXECUTE_ROOT_DIR = "code-execute"
_registry = get_tool_registry()


class CodeExecuteInputModel(BaseModel):
    """
    代码执行工具的输入参数
    """

    code: str = Field(description="需要执行的代码内容字符串")
    timeout: float = Field(
        description="每一条命令执行的超时时间（秒）",
        default=30.0,
    )
    input_filename: str = Field(
        description="源文件名称，工具首先把代码写入到这个文件之后在实际运行编译器或解释器"
    )
    output_filename: str = Field(description="目标文件名，如果需要", default=None)
    commands: list[list[str]] = Field(
        description="命令列表，$OUTPUT_FILENAME 和 $INPUT_FILENAME实际被上面的output_filename 和 input_filename两个参数替代",
        examples="如： output_filename='main.exe', input_filename='hello.c', commands=['gcc', '$INPUT_FILENAME', '-o', '$OUTPUT_FILENAME'], ['$OUTPUT_FILENAME']], 最后的两个命令如下 gcc hello.c -o main.exe; main.exe",
    )
    execute_directory: str = Field(
        description="相关生成文件存放的文件夹，相关工具命令也在此文件夹之下运行，鼓励设置一个有意义的名称",
        default=f"code-{int(time.time() % 100000)}",
    )


def _replace_placeholders(
    args: list[str], input_filename: str, output_filename: str
) -> list[str]:
    """
    把占位符替换为真实路径
    :param args: 需要处理的指令序列
    :type args: list[str]
    :param input_filename: 输入文件的真实路径
    :type input_filename: str
    :param output_filename: 输出文件的真实路径
    :type output_filename: str
    :return: 替换为真实路径的命令序列
    :rtype: list[str]
    """
    result = []
    for arg in args:
        arg = arg.replace("$INPUT_FILENAME", input_filename)
        arg = arg.replace("$OUTPUT_FILENAME", output_filename)
        result.append(arg)

    return result


@_registry.register
def code_execute(code_execute_input_model: CodeExecuteInputModel) -> Result:
    """
    执行给定的代码
    将code写入到input_filename里， 可能的目标文件输出到output_filename文件里
    顺序执行commands里的命令列表
    给该工具传递代码之前必须认真检查。
    严禁调用删除文件； 修改系统配置等危险操作
    :param code_execute_input_model: 所需的参数
    :type code_execute_input_model: CodeExecuteInputModel
    :return: 执行结果
    :rtype: Result
    """
    tmp_dir = Path(EXECUTE_ROOT_DIR).joinpath(
        code_execute_input_model.execute_directory
    )
    tmp_dir.mkdir(parents=True, exist_ok=True)

    input_filename = tmp_dir.joinpath(Path(code_execute_input_model.input_filename))
    with input_filename.open("w", encoding="UTF-8") as fp:
        fp.write(code_execute_input_model.code)

    output_filename = tmp_dir.joinpath(
        Path(
            code_execute_input_model.output_filename
            if code_execute_input_model.output_filename is not None
            else Path("")
        )
    )

    results = []
    for cmd in code_execute_input_model.commands:
        command = _replace_placeholders(
            cmd,
            input_filename=str(input_filename),
            output_filename=str(output_filename),
        )

        process = None

        try:
            process = subprocess.run(
                command,
                cwd=tmp_dir,
                capture_output=True,
                text=True,
                shell=True,
                timeout=code_execute_input_model.timeout,
            )

            results.append(
                {
                    "command": " ".join(command),
                    "stdout": process.stdout,
                    "stderr": process.stderr,
                    "exit_code": process.returncode,
                }
            )

        except Exception as e:
            if process:
                results.append(
                    {
                        "args": " ".join(command),
                        "stdout": process.stdout,
                        "stderr": process.stderr,
                        "error": str(e),
                        "exit_code": process.returncode,
                    }
                )
            else:
                return Result(error=e, result=[])

    return Result(result=results, error=None)
