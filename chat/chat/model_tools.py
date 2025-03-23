# --*-- Coding: UTF-8 --*--
#! filename: model_tools.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2025-03
# * description: 一个简单的AI LLM聊天程序
# 定义操作Model对象的快捷函数
from model import Model


def find_model_group_index(model_list: list, name: str | None = None) -> int:
    """
    根据子模型查询模型组的索引
    """
    if name is None:
        return -1

    for index, model in enumerate(model_list):
        for sub_model in model["sub_models"]:
            if name in sub_model:
                return index

    return -1


def create_or_switch_model(
    model_list: list, model_name: str | None, model: Model | None = None
) -> Model | None:
    """
    根据条件切换或者创建模型
    如果新的子模型在当前模型组之内则简单切换
    如果子模型不在当前模型组则重新创建模型组
    """
    index = find_model_group_index(model_list, model_name)

    if index == -1:
        return None

    if model and model_name in model.sub_models:
        model.current_model = model_name
        return model
    else:
        model_list[index].update({"current_model": model_name})
        new_model = Model.from_dict(model_list[index])
        return new_model
