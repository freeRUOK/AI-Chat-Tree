# --*-- Coding: UTF-8 --*--
#! filename: cli.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2025-02
# * description: 一个简单的AI LLM聊天程序
# 主要实现了cli接口
import os
import msvcrt
from contextlib import ExitStack
from typing_extensions import Annotated
import typer
import yaml
from config import Config
from consts import CONFIG_PATH, default_system_prompt, ContentTag
from application import Application
from ws_serve import WSServe
from util import input_handler, clear_queue
from util import DEBUG_MODE, debug_log
from text_to_speech import TextToSpeechOption
from data_status import DataStatus as CLIStatus


def cli_input(application: Application, status: CLIStatus):
    """
    默认从命令行获取用户的输入
    """
    print("欢迎使用AI Chat， 键入文字开始聊天， 键入 /h 获取更多帮助。")
    while True:
        user_message = input("Enter Text >> ").strip()

        if user_message[0] == "/":
            result = input_handler(user_message)
            match result[0]:
                case ContentTag.speech:
                    application.voice_input_manager.begin_voice_input()
                    msvcrt.getch()
                    application.voice_input_manager.end_voice_input()
                    continue

                case ContentTag.end:
                    break
                case ContentTag.empty | ContentTag.error:
                    print("错误输入或空输入， 再试一次")
                    continue
                case (
                    ContentTag.file
                    | ContentTag.clipboard
                    | ContentTag.multi_line
                    | ContentTag.help
                ):
                    if result[1] is not None:
                        print(
                            f"{result[0].value}\n<{'-' * 40}>\n{result[1]}\n<{'-' * 40}>"
                        )
                        if result[0] != ContentTag.help:
                            user_message = result[1]
                        else:
                            continue

                    else:
                        print("没有获取有效内容。")
                        continue

        status.message_queue.put(
            (
                user_message,
                None,
            )
        )


# 创建typer app， 并且在创建config_app， 最后把config_app作为app的子命令
app = typer.Typer()
config_app = typer.Typer()
app.add_typer(config_app, name="config")


@app.command()
def chat(
    model_name: Annotated[str, typer.Argument()] = "qwq",
    second_model_name: Annotated[str, typer.Argument()] = "deepseek-r1:14b",
    system_prompt: Annotated[
        str, typer.Option("--system-prompt", "-sp")
    ] = default_system_prompt,
):
    status = CLIStatus()
    # 按照chat的默认方式运行
    application: Application | None = None
    try:
        with ExitStack() as stack:
            config = stack.enter_context(Config())
            application = stack.enter_context(
                Application(
                    config=config,
                    model_name=model_name,
                    second_model_name=second_model_name,
                    system_prompt=system_prompt,
                    text_to_speech_option=TextToSpeechOption.play,
                    input_callback=status.message_queue.get,
                    voice_input_callback=status.on_speech_result,
                    enable_tools=True,
                )
            )
            application.start()
            cli_input(application=application, status=status)
    except Exception as e:
        raise e
    finally:
        clear_queue(status.message_queue)
        print("下次再见！")


@config_app.command("tts")
def config_tts():
    print("config TTS")


@config_app.command("add_model")
def add_config_model(
    name: Annotated[str, typer.Option("--group-name", "-g")],
    is_online: Annotated[bool, typer.Option("--is-online", "-io")],
    show_reasoning: Annotated[bool, typer.Option("--show-reasoning", "-sr")],
    base_url: Annotated[str, typer.Option("--url", "-u")],
    api_key: Annotated[str, typer.Option("--api-key", "-k")],
    sub_models: list[str],
):
    pass


@config_app.command("init")
def config_init(
    ollama_port: Annotated[int, typer.Option("--ollama-port", "-op")] = 11434,
    chat_collection_dir: Annotated[
        str, typer.Option("chat-collection-dir", "-co")
    ] = "chat-collections",
    force_override: Annotated[bool, typer.Option("--yes")] = False,
):
    """
    初始化配置文件
    原来的配置文件被覆盖， 做好备份
    """
    usage = {
        "ollama_host": f"http://127.0.0.1:{ollama_port}",
        "chat_collection_dir": chat_collection_dir,
    }
    text_to_speech = {
        "voice": "Microsoft Server Speech Text to Speech Voice (zh-CN, XiaoxiaoNeural)",
        "rate": "+100%",
        "volume": "+20%",
    }
    config = {
        "usage": usage,
        "text_to_speech": text_to_speech,
    }
    if force_override and os.path.exists(CONFIG_PATH):
        if not input("你确实要强制覆盖现有的配置文件么？").lower().strip() == "yes":
            print("配置文件未初始化， 命令已取消")
            typer.Exit()

    with open(CONFIG_PATH, "w", encoding="UTF-8") as fp:
        yaml.dump(
            config, fp, allow_unicode=True, default_flow_style=False, sort_keys=False
        )


@app.command()
def serve(port: Annotated[int, typer.Argument()] = 8001):
    try:
        with WSServe() as ws_serve:
            ws_serve.run(port=port)
    except Exception as e:
        debug_log(e)
        if DEBUG_MODE:
            raise e
        else:
            print(f"错误： {e}")
