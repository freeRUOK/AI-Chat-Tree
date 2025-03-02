# --*-- Coding: UTF-8 --*--
#! filename: cli.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2025-02
# * description: 一个简单的AI LLM聊天程序
# 主要实现了cli接口
import os
from contextlib import ExitStack
from typing_extensions import Annotated
import typer
import yaml
from config import Config
from consts import CONFIG_PATH, default_system_prompt
from application import Application

# 创建typer app， 并且在创建config_app， 最后把config_app作为app的子命令
app = typer.Typer()
config_app = typer.Typer()
app.add_typer(config_app, name="config")


@app.command()
def chat(
    model_name: Annotated[str, typer.Argument()] = "deepseek-reasoner",
    second_model_name: Annotated[str, typer.Argument()] = "deepseek-r1:14b",
    system_prompt: Annotated[
        str, typer.Option("--system-prompt", "-sp")
    ] = default_system_prompt,
):
    # 按照chat的默认方式运行
    with ExitStack() as stack:
        config = stack.enter_context(Config())
        application = stack.enter_context(
            Application(
                config=config,
                model_name=model_name,
                second_model_name=second_model_name,
                system_prompt=system_prompt,
            )
        )
        application.run()


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
