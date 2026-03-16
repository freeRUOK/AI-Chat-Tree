# --*-- Encoding: UTF-8 --*--
#! filename: model_loader.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2026-03
# * description: 一个简单的AI LLM聊天程序
# 用于模型加载， 模型的发现； 加载； 缓存和查询创建等
from threading import Lock
from datetime import timedelta
from copy import deepcopy
from diskcache import Cache  # type: ignore
import ollama
from config import Config
from model import Model
from error_handling import emit_error


class _ModelManager:
    def __init__(self, config: Config):
        self._config = config
        self._cache = Cache("./tmp/cache")
        self._models: list[dict] = self.load_all_models()
        self._lock = Lock()

    def find_model_group_index(self, name: str | None = None) -> int:
        """
        根据子模型查询模型组的索引
        """
        if not name:
            return -1

        for index, model in enumerate(self._models):
            for sub_model in model["sub_models"]:
                if name == sub_model:
                    return index

        return -1

    def copy_models(self) -> list:
        return deepcopy(self._models)

    def create_or_switch(
        self, model_name: str | None, model: Model | None = None
    ) -> Model | None:
        """
        根据条件切换或者创建模型
        如果新的子模型在当前模型组之内则简单切换
        如果子模型不在当前模型组则重新创建模型组
        """
        index = self.find_model_group_index(model_name)

        if index == -1:
            return None

        if model and model_name in model.sub_models:
            model.current_model = model_name
            return model
        else:
            self._models[index].update({"current_model": model_name})
            new_model = Model.from_dict(self._models[index])
            return new_model

    def _load_ollama_models(self, is_online: bool) -> dict:
        """
        获取ollama提供的所有可用的模型
        如果 is_online == True 则尝试获取ollama云端模型
        """
        if is_online:
            ollama_host = "https://ollama.com"
        elif host := self._config.get("usage.ollama_host"):
            ollama_host = host
        else:
            ollama_host = "http://127.0.0.1:11434"
        ollama_models = {
            "group_name": "ollama_local" if is_online else "ollama_cloud",
            "show_reasoning": True,
            "is_online": is_online,
            "base_url": ollama_host,
            "api_key": self._config.get("usage.ollama_api_key"),
        }
        try:
            # ollama没有运行或者没有安装， 所以这里需要提醒用户
            ollama_sub_models = [
                f"{item.model}{'-cloud' if is_online else ''}"
                for item in ollama.Client(host=ollama_host).list().models
                if item.model and "cloud" not in item.model
            ]
        except ollama.ResponseError as e:
            ollama_sub_models = []
            emit_error(
                msg="加载ollama模型失败， 请检查ollama服务是否正在运行或者建议安装配置ollama服务。。",
                exception=e,
            )

        if ollama_sub_models:
            ollama_models["sub_models"] = ollama_sub_models
        else:
            ollama_models = {}

        return ollama_models

    def load_all_models(self, skip_cache: bool = False) -> list:
        """
        获取配置文件里的和本地ollama的模型元数据
        :param :skip_cache 是否跳过缓存
        :return: 返回所有的ollama模型
        :rtype: list
        """
        cache_key = "model_list"
        if not skip_cache:
            if cache_models := self._cache.get(cache_key):
                return cache_models

        models = []
        if result := self._config.get("models"):
            models = result

        models.append(self._load_ollama_models(is_online=True))
        models.append(self._load_ollama_models(is_online=False))
        self._cache.set(cache_key, models, expire=timedelta(days=2).total_seconds())

        return models

    def has_models(self) -> bool:
        """
        :return: 是否有可用的模型
        :rtype: bool
        """
        return len(self._models) > 0

    def build_model(
        self, first_model_name: str, second_model_name: str | None
    ) -> tuple[Model, Model | None]:
        """
        通过sub_model_name查询创建主要模型和备用模型
        # 真正加载模型， 必须有一个主要模型， 备用模型可选
        # 如果主要模型出现问题就切换到备用模型
        """
        if not self.has_models():
            raise ValueError("没有可用的模型, 请安装ollama或者添加在线模型。")

        first_model = self.create_or_switch(first_model_name)
        second_model = self.create_or_switch(second_model_name)
        if first_model is None:
            raise ValueError(f"没有找到子模型： {first_model_name}")

        return (
            first_model,
            second_model,
        )


_mm_lock = Lock()
_mm_instance: _ModelManager | None = None


def get_model_manager(config: Config | None = None) -> _ModelManager:
    global _mm_instance
    if _mm_instance is None:
        with _mm_lock:
            if _mm_instance is None:
                if config is None:
                    raise ValueError(
                        "首次获取Model_manager Instance需要Config配置参数。"
                    )

                _mm_instance = _ModelManager(config)

    return _mm_instance
