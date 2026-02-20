# --*-- Coding: UTF-8 --*--
#! filename: util.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2025-02
# * description: 一个简单的AI LLM聊天程序
# 一些随时都可能使用到的工具函数
# 这里提供了日志文件的配置， 也许该分离日志和错误处理部分
from queue import Queue
from io import BytesIO
import base64
from pathlib import Path
import re
import socket
import os
from PIL import Image
import cv2
import pyautogui
import pygetwindow as gw  # type: ignore
from loguru import logger
import prompt_toolkit
import pyperclip  # type: ignore
import chardet
from consts import ContentTag

# 配置日志记录
logger.remove()
logger.add(
    "logs/debug.log",
    format="{line} | {message} | {time:YYYY-MM-DD HH:mm:ss}",
    rotation="1 MB",
    compression="zip",
    backtrace=True,
    diagnose=True,
    enqueue=True,
)
debug_logger = logger
DEBUG_MODE = os.getenv("DEBUG_MODE", None)


def debug_log(err: Exception):
    """
    记录错误和调用堆栈
    """
    if DEBUG_MODE:
        logger.exception(f"Error: {err}")


def clear_queue(queue: Queue):
    """
    清空队列
    """
    while not queue.empty():
        queue.get()


def validate_values(
    values: list,
    default_reges_pattern: str = r"^\S{3,}$",
) -> list:
    """
    简单验证是否为符合条件的字符串， 可以自定义验证正则表达式
     默认验证正则表达式条件长度大于或者等于3且非空白字符
     可以输入list类型的一系列str，
    如果自定义正则表达式可以输入有两个元素的tuple
    第一个元素需要验证的str值， 第二个元素相对应的正则表达式值
    """
    for value in values:
        if isinstance(value, tuple):
            if len(value) != 2:
                raise ValueError(f"值： {value} 必须提供合适的验证表达式。")

            result = re.fullmatch(value[1], value[0])
        else:
            result = re.fullmatch(default_reges_pattern, value)

        if not result:
            raise ValueError(f"无效的值: {value}.")

    return values


def read_file_text(filename: str, require: bool = False) -> str | None:
    """
    读取一个文本文件所有内容
    不限制文件后缀名， 只要是有效的文本编码即可读取内容
    """
    try:
        buf = Path(filename).read_bytes()
        if encoding := chardet.detect(buf)["encoding"]:
            return buf.decode(encoding=encoding)
        else:
            raise ValueError(f"文件: {filename} 不是纯文本文件。")

    except (FileNotFoundError, PermissionError, ValueError) as e:
        if require:
            raise e

        debug_log(e)

        return None


def multi_line_input(prompt=">>> ") -> str | None:
    """
    接受用户的多行内容
    就像文本编辑器上工作一样
    完成后先按下ESC退出编辑模式， 按下enter提交内容
    """
    try:
        session: prompt_toolkit.PromptSession = prompt_toolkit.PromptSession()
        return session.prompt(
            message=prompt,
            vi_mode=True,
            multiline=True,
        )
    except KeyboardInterrupt:
        print("取消本次输入， 如果想要提交输入按下esc后在按下Enter。")
    return None


def input_handler(user_message: str) -> tuple[ContentTag, str | None]:
    """
    在控制台上和用户交互
    /开头的属于特殊指令
    """
    if len(user_message) < 2:
        return (ContentTag.error, None)

    match user_message[:2]:
        case "/m" | "/M":
            return (
                ContentTag.multi_line,
                multi_line_input(
                    prompt="多行输入可用回车换行， 完成后按下ESC在按下回车提交内容\n"
                ),
            )

        case "/q" | "/Q":
            return (ContentTag.end, None)
        case "/f" | "/F":
            filename = user_message[2:].strip()
            return (
                ContentTag.file,
                read_file_text(filename=filename),
            )

        case "/t" | "/T":
            return (
                ContentTag.clipboard,
                pyperclip.paste(),
            )
        case "/h" | "/H" | "/?":
            return (
                ContentTag.help,
                read_file_text(filename="readMe.md"),
            )
        case "/v" | "/V":
            return (ContentTag.speech, None)

    return (ContentTag.empty, None)


def first_online_host(addresss: tuple[str, int], timeout: float = 0.3) -> str | None:
    """
    返回第一个可用的主机名和端口， 把优先使用的主机名放到靠前的位置， 备用主机名放到靠后的位置
    :param addresss: 主机名和端口列表
    :type addresss: tuple[str, int]
    :param timeout: 超时（秒）
    :type timeout: float
    :return: 返回第一个能够成功连接的主机名和端口
    :rtype: str | None
    """
    for address in addresss:
        try:
            with socket.create_connection(address=address, timeout=timeout):
                return address
        except (ConnectionRefusedError, OSError, socket.timeout):
            continue

    return None


class ImageHandler:
    """
    简单处理图片
    """

    def __init__(self):
        """
        初始化
        """
        self._image: Image.Image | None = None

    def close_current_image(self):
        """
        关闭当前Image.Image对象
        """
        if self._image is not None:
            self._image.close()
            self._image = None

    def to_base64(self) -> str | None:
        """
        把图片转换到base64字符串
        """
        if self._image is None:
            return None

        try:
            buffer = BytesIO()
            self._image.save(buffer, format="JPEG")
            img_bytes = buffer.getvalue()
            base64_str = base64.b64encode(img_bytes).decode(encoding="UTF-8")
            return base64_str
        except Exception as e:
            debug_log(e)

        return None

    def read_image_file(self, image_data: str | bytes):
        """
        打开图片文件
        """
        try:
            if isinstance(image_data, bytes):
                self._image = Image.open(BytesIO(image_data))
            else:
                self._image = Image.open(image_data)

        except Exception as e:
            debug_log(e)

    def capture_screen(self, is_full_screen: bool = False):
        """
        对当前活动的窗口截屏
        is_full_screen: bool, 是否全屏截图默认活动窗口
        """
        try:
            region = None
            if not is_full_screen:
                if window := gw.getActiveWindow():
                    region = (window.left, window.top, window.width, window.height)

            self._image = pyautogui.screenshot(region=region)
        except Exception as e:
            debug_log(e)

    def capture(self):
        """
        调用设备的默认镜头拍照
        调用该函数注意隐私安全
        """
        try:
            capture = cv2.VideoCapture(0)
            if not capture.isOpened():
                raise ValueError("Open Capture Fail")
            ret, frame = capture.read()
            if ret is None:
                raise ValueError("Read Image Frame Fail.")
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self._image = Image.fromarray(frame_rgb)
            capture.release()

        except ValueError as e:
            debug_log(e)
