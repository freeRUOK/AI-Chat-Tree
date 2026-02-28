# --*-- Encoding: UTF-8 --*--
#! filename: tools/shell_tool.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2026-02
# * description: 一个简单的AI LLM聊天程序
# 简单实现了一个简单执行shell命令的工具
from typing import Literal, Union, Optional
import subprocess
import time
import re
import platform
from pathlib import Path
from pydantic import BaseModel, Field, model_validator
from tools.result import Result
from tools import get_tool_registry
from util import read_file_text

SHELL_BOX_DIR = "shell_box"
DANGEROUS_PATTERNS = [
    "rm -rf /",
    "rm -rf /*",
    "rd /s /q \\",
    "del /f /s /q c:\\",
    "mkfs.",
    "dd if=",
    "format ",
    "diskpart",
    " /boot",
    " /etc",
    " /sys",
    " /proc",
    ":\\windows\\system32",
    " /system",
    " /bin/sh ",
    "nc -l",
    "ncat -l",
    "nc -e",
    "bash -i",
    "sh -i",
    "python -c 'import socket'",
    "python3 -c 'import socket'",
    "sudo",
    "su -",
    "chmod 777 /",
    "chown root",
    "tar cf - / | nc",
    "cat /etc/passwd",
    "type %SystemRoot%\\system32\\config\\sam",
]
_registry = get_tool_registry()


class ShellInputModel(BaseModel):
    """
    shell命令执行工具的输入参数
    """

    inner_fun_name: Literal[
        "command",  # 执行shell命令
        "read",  # 读文件
        "write",  # 写文件
        "list",  # 列举文件
        "edit",  # 编辑文件（搜索替换）
        "grep",  # 文件内搜索
        "state",  # 文件基本信息
    ] = Field(description="所有可用功能")

    # === command 专用参数 ===
    timeout: float = Field(
        description="command专用，shell命令执行的超时时间（秒）",
        default=120.0,
        ge=0.1,
        le=3600.0,
    )
    command: str | None = Field(
        default=None,
        description=f"command专用，要执行的{platform.system()} shell命令，格外注意平台差异",
        examples=["ls -la", "dir /B", "gcc hello.c -o hello.out", "node main.js"],
    )
    # === 除了command之外所有功能专用参数 ===
    file_path: str | None = Field(
        default=None,
        description="非command专用参数文件路劲，必须是shell_work_directory目录的子路径，否则阻断",
        examples=["./hello.c", "D:\\src\\util.js"],
    )
    # === write 专用参数 ===
    content: str | None = Field(default=None, description="write专用，要写入的文本")
    append: bool = Field(default=False, description="write专用，True追加；False覆盖")
    # === read 专用参数 ===
    limit: int | None = Field(
        default=None, description="read专用，None读入全部，否则截断行数", ge=1
    )
    tail: bool = Field(
        default=False,
        description="是否从文件尾部读取",
    )
    # === list专用参数 ===
    show_hidden: bool = Field(
        default=False,
        description="list专用，是否显是隐藏文件",
    )

    # === edit专用参数
    old_string: str | None = Field(
        default=None, description="edit专用，要被替换的字符串，必须唯一"
    )
    new_string: str | None = Field(
        default=None, description="edit专用，用于替换的新字符串"
    )
    replace_all: bool = Field(default=True, description="是否全部替换")
    # === grep专用参数 ===
    pattern: str | None = Field(
        default=None, description="grep专用，搜索模式字符串或正则表达式"
    )
    context_lines: int = Field(
        default=2, gt=0, le=20, description="grep专用，匹配行前行后显是的行数"
    )

    # === 通用参数 ===
    shell_work_directory: str = Field(
        description="单独工作文件夹，鼓励使用有意义的名称，鼓励同一组任务在相同文件夹下运行",
        default=f"code-{int(time.time() % 100000)}",
    )

    @model_validator(mode="after")
    def check_required_params(self) -> "ShellInputModel":
        """
        动态验证输入参数
        :return: 验证后的参数
        :rtype: ShellInputModel
        """
        fun = self.inner_fun_name
        required_map: dict[str, list[str]] = {
            "command": ["command"],
            "read": ["file_path"],
            "write": ["file_path", "content"],
            "list": [],
            "edit": ["old_string", "new_string"],
            "grep": ["file_path", "pattern"],
            "state": ["file_path"],
        }
        required = required_map.get(fun, [])
        missing = []
        for r in required:
            val = getattr(self, r)
            if val is None or (isinstance(val, str) and not val.strip()):
                missing.append(r)

        if missing:
            raise ValueError(f"内部工具： {fun} 缺少必填参数 {' '.join(missing)}")

        return self


class ShellToolDispatcher:
    """
    shell工具的内部分发器
    """

    def __init__(self, base_dir: str = SHELL_BOX_DIR):
        """
        初始化分发器
        :param base_dir: 工具执行的文件夹
        :type base_dir: str
        """
        self.base_path = Path(base_dir)
        self._handlers = {
            "command": self._handler_command,
            "read": self._handler_read,
            "write": self._handler_write,
            "list": self._handler_list,
            "edit": self._handler_edit,
            "grep": self._handler_grep,
            "state": self._handler_state,
        }

    def _safe_path(self, parent: Path, sub: str, auto_mkdir: bool = False) -> Path:
        """
        解析并创建安全路径
        :param parent: 安全的父路径
        :type parent: Path
        :param sub: 子路径
        :type sub: str
        :param auto_mkdir: 是否自动创建目录
        :type auto_mkdir: bool
        :return: 验证而且创建后的路径
        :rtype: Path
        """
        full_path = parent.joinpath(sub)
        if not full_path.resolve().is_relative_to(parent.resolve()):
            raise ValueError(
                f"路径： {full_path} 不是 路径： {parent} 的子路径， 有路径逃逸的风险。任务被阻断"
            )

        if auto_mkdir:
            full_path.mkdir(parents=True, exist_ok=True)

        return full_path

    def dispatch(self, paramms: ShellInputModel) -> Result:
        handler = self._handlers.get(paramms.inner_fun_name)
        if not handler:
            return Result(
                error=ValueError(f"内部功能： {paramms.inner_fun_name} 不存在"),
                result={},
            )

        try:
            cwd = self._safe_path(
                self.base_path, paramms.shell_work_directory, auto_mkdir=True
            )
            return handler(paramms, cwd)
        except Exception as e:
            return Result(error=e, result={})

    def _handler_command(self, p: ShellInputModel, cwd: Path) -> Result:
        """
        执行shell命令
        如下_handler开头的方法全部都是某种内部功能的实现
        输入参数和返回值全部相同， 输入参数定义参考： ShellToolInputModel类
        返回值参考./tools/result.py
        :param p: 工具的输入参数
        :type p: ShellInputModel
        :param cwd: 工具执行的工作目录
        :type cwd: Path
        :return: 执行结果
        :rtype: Result
        """
        lower_command = p.command.lower()
        if any(pattern in lower_command for pattern in DANGEROUS_PATTERNS):
            raise PermissionError("非法命令被阻断")

        process = None
        result = Result(result={})

        try:
            process = subprocess.run(
                p.command,
                cwd=cwd,
                capture_output=True,
                text=True,
                shell=True,
                timeout=p.timeout,
            )
        except subprocess.TimeoutExpired:
            result.error = TimeoutError(f"Shell Command Execute Timeout: {p.timeout}S.")
        except Exception as e:
            result.error = e
        finally:
            if process is not None:
                result.result = {
                    "command": p.command,
                    "stdout": process.stdout,
                    "stderr": process.stderr,
                    "exit_code": process.returncode,
                }

            return result

    def _handler_read(self, p: ShellInputModel, cwd: Path) -> Result:
        """
        读取一个文本文件
        """
        try:
            file_path = self._safe_path(cwd, p.file_path)
            content = read_file_text(str(file_path), require=True)
            if p.limit or p.tail:
                lines = content.splitlines()
                if p.tail:
                    selected = lines[-p.limit :] if p.limit else lines
                else:
                    selected = lines[: p.limit] if p.limit else lines
                content = "\n".join(selected)

            return Result(result={"path": str(file_path), "file_content": content})
        except Exception as e:
            return Result(error=e, result={})

    def _handler_write(self, p: ShellInputModel, cwd: Path) -> Result:
        """
        写入一个文本文件
        """
        try:
            if p.content is None:
                raise ValueError("Write 没有提供写入内容")

            file_path = self._safe_path(cwd, p.file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            mod = "a" if p.append else "w"
            with file_path.open(mode=mod, encoding="UTF-8") as f:
                f.write(p.content)

            return Result(
                result={
                    "status": "ok",
                    "path": str(file_path),
                    "encoding": "UTF-8",
                    "mode": "append" if p.append else "overwrite",
                    "size": file_path.stat().st_size,
                }
            )

        except Exception as e:
            return Result(error=e, result={})

    def _handler_list(self, p: ShellInputModel, cwd: Path) -> Result:
        """
        列举目录和文件
        """
        try:
            target = p.file_path or "."
            file_path = self._safe_path(cwd, target)
            items = []
            for item in file_path.iterdir():
                if not p.show_hidden and item.name.startswith("."):
                    continue
                stat = item.stat()
                items.append(
                    {
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "size": item.st_size if item.is_file() else None,
                        "modified": stat.st_mtime,
                    }
                )
            return Result(
                result={
                    "path": str(file_path),
                    "items": items,
                    "total": len(items),
                }
            )
        except Exception as e:
            return Result(error=e, result={})

    def _handler_edit(self, p: ShellInputModel, cwd: Path) -> Result:
        """
        编辑文件（查找和替换
        """
        try:
            if not p.old_string:
                raise ValueError("old_string不能为空")

            file_path = self._safe_path(cwd, p.file_path)
            content = read_file_text(str(file_path), require=True)
            old_count = content.count(p.old_string)
            replace_count = old_count if p.replace_all else (1 if old_count > 0 else 0)
            new_content = content.replace(
                p.old_string, p.new_string, -1 if p.replace_all else 1
            )

            if new_content != content:
                with file_path.open("w", encoding="UTF-8") as f:
                    f.write(new_content)

            return Result(
                result={
                    "path": str(file_path),
                    "replace_all": p.replace_all,
                    "replace_count": replace_count,
                }
            )
        except Exception as e:
            return Result(error=e, result={})

    def _handler_grep(self, p: ShellInputModel, cwd: Path) -> Result:
        """
        在文件内搜索
        """
        try:
            file_path = self._safe_path(cwd, p.file_path)
            content = read_file_text(str(file_path), require=True)
            lines = content.splitlines()
            pattern = re.compile(p.pattern, re.IGNORECASE)
            matches = []
            for i, line in enumerate(lines, 1):
                if pattern.search(line):
                    start = max(0, i - p.context_lines - 1)
                    end = min(len(lines), i + p.context_lines)
                    matches.append(
                        {
                            "line_number": i,
                            "content": line,
                            "context": {
                                "start_line": start + 1,
                                "lines": lines[start:end],
                            },
                        }
                    )

            return Result(
                result={
                    "file_path": str(file_path),
                    "pattern": p.pattern,
                    "total_matches": len(matches),
                    "matches": matches,
                }
            )
        except Exception as e:
            return Result(error=e, result={})

    def _handler_state(self, p: ShellInputModel, cwd: Path) -> Result:
        """
        获取目录或文件的属性
        """
        try:
            file_path = self._safe_path(cwd, p.file_path)
            stat = file_path.stat()
            result = {
                "path": str(file_path),
                "type": "directory" if file_path.is_dir() else "file",
                "size_bytes": stat.st_size,
                "modified_time": stat.st_mtime,
                "created_time": stat.st_ctime,
                "permissions": oct(stat.st_mode)[-3:],
            }
            if file_path.is_dir():
                result["children_count"] = len(list(file_path.iterdir()))

            return Result(result=result)
        except Exception as e:
            return Result(error=e, result={})


_dispatcher = ShellToolDispatcher()


@_registry.register
def execute_shell(shell_inputModel: ShellInputModel) -> Result:
    """
    shell工具的统一入口：
    根据ShellInputModel.inner_fun_name自动分发给内部处理子工具
    command; 执行shell命令
    read; 读取文本文件
    write; 写入文本文件
    list 列举路径
    edit; 编辑文件（查找替换）
    grep; 文件内部搜索
    state; 查看目录文件的属性
    安全限制
    所有的工作在ShellInputModel.shell_work_directory目录内； 禁止访问上级目录或目录逃逸
    :param shell_inputModel: 包含inner_fun_name和所需参数
    :type shell_inputModel: ShellInputModel
    :return: 工具执行结果
    :rtype: Result
    """
    global _dispatcher
    return _dispatcher.dispatch(shell_inputModel)
