# --*-- Coding: UTF-8 --*--
#! filename: config.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2025-02
# * description: 一个简单的AI LLM聊天程序
# 集中管理所有配置项目
from typing import Any
import yaml
from consts import CONFIG_PATH
from util import read_file_text, debug_log, validate_values


class Config:
    """
    集中管理程序的配置项目
    """

    def __init__(self, config_path: str = CONFIG_PATH, build_empty: bool = False):
        self._config_path = config_path
        self._build_empty = build_empty
        self._config: dict = {}
        self._is_change = False

    def load(self):
        """
        加载配置.yml文件
        """
        try:
            if yml_data := read_file_text(filename=self._config_path, require=True):
                self._config = yaml.safe_load(yml_data)
        except (yaml.error.YAMLError, FileNotFoundError, PermissionError) as e:
            debug_log(e)
            if not self._build_empty:
                print(f"致命错误： {e}\n详细信息参考启用调试模式之后输出的日志文件。")
                exit(-1)

    def __enter__(self):
        """
        with语句上下文自动管理
        """
        self.load()
        return self

    def save(self) -> bool:
        """
        保存配置文件
        """
        if not self._is_change:
            return True
        try:
            with open(self._config_path, "w", encoding="UTF-8") as fp:
                yaml.dump(
                    self._config,
                    fp,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False,
                )
                self._is_change = False
                return True
        except PermissionError as e:
            debug_log(e)
        return False

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save()

    def _path(self, path: str, auto_update: bool = False) -> tuple[dict, str]:
        """
        定位配置项目的路径， 父项目和子项目使用点号分割
        配置项目的名称只能小写字母开头， 可以尾随小写字母数字下划线和短斜杠
        """

        paths = validate_values([it for it in path.split(".")])

        tar_item = self._config

        for key in paths[:-1]:
            if key not in tar_item:
                if not auto_update:
                    raise ValueError(f"Path: {path} Not Exist.")

                tar_item.update({key: {}})

            tar_item = tar_item[key]

        return (
            tar_item,
            paths[-1],
        )

    def add(self, path: str, obj: Any):
        """
        添加配置项目
        """
        if (not isinstance(obj, dict)) and (not hasattr(obj, "to_dict")):
            raise TypeError("Config Object Not Has Method to_dict")

        tar_item, name = self._path(path=path)
        tar_item.update({name: obj.to_dict() if not isinstance(obj, dict) else obj})
        self._is_change = True

    def get(self, path: str) -> Any:
        """
        获取配置项目
        """
        try:
            item, name = self._path(path=path)
            return item[name]
        except (TypeError, ValueError) as e:
            debug_log(e)
            if isinstance(e, TypeError):
                print(f"yml配置文件可能有语法错误\n请检查{path}字段")

        return None
