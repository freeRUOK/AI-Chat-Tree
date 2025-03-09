# --*-- Coding: UTF-8 --*--
#! filename: gui.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2025-02
# * description: 一个简单的AI LLM聊天程序
# 主要实现了wxpython的GUI界面
# 消息列表使用树状图来呈现
# 这样可以在内容之间快速跳转
from contextlib import ExitStack
from typing import Any
import wx  # type: ignore
from model import ModelResult
from config import Config
from application import Application
from consts import ContentTag
from util import clear_queue
from gui_consts import MENU_ITEM_SET_FIRST_MODEL, MENU_ITEM_SET_SECOND_MODEL
from data_status import DataStatus as FrameStatus


class MainFrame(wx.Frame):
    """
    主窗口类
    """

    def __init__(self):
        super().__init__(parent=None, title="AI Chat Tree", size=(800, 600))

        self.status = FrameStatus()
        self.panel = wx.Panel(self)

        self.system_prompt_label = wx.StaticText(
            self.panel,
            label="系统提示词（AI遵循的最高指令， 可以按照自己的喜好随意修改）：",
        )
        self.system_prompt_ctrl = wx.TextCtrl(
            self.panel, style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER
        )
        self.system_prompt_ctrl.SetMinSize((700, 100))
        self.system_prompt_ctrl.Bind(wx.EVT_KILL_FOCUS, self.on_system_prompt_change)

        self.system_prompt_ctrl.SetValue(self.status.system_prompt)

        self.model_label = wx.StaticText(self.panel, label="可用模型：")
        self.model_list_box = wx.ListBox(self.panel)
        self.model_list_box.Bind(wx.EVT_KEY_DOWN, self.on_model_list_box_keydown)

        self.tts_checkbox = wx.CheckBox(self.panel, label="自动大声朗读(\t&U)")

        self.input_label = wx.StaticText(self.panel, label="消息：")
        self.input_ctrl = wx.TextCtrl(
            self.panel, style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER
        )
        self.input_ctrl.SetMinSize((700, 100))

        self.send_button = wx.Button(self.panel, label="发送(\t&S)")
        self.send_button.Bind(wx.EVT_BUTTON, self.on_send)

        self.tree_label = wx.StaticText(self.panel, label="AI会话：")
        self.tree = wx.TreeCtrl(
            self.panel, style=wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT
        )
        self.root = self.tree.AddRoot("AI Chat")
        self.tree.SetItemText(self.root, "Message List:")
        self.current_message_node = self.tree.AppendItem(self.root, "Message:")
        self.tree.ExpandAll()
        self.current_reasoning_node = None
        self.current_content_node = None

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.system_prompt_label, 0, wx.ALL | wx.CENTER, 5)
        sizer.Add(self.system_prompt_ctrl, 0, wx.EXPAND | wx.ALL, 5)

        sizer.Add(self.model_label, 0, wx.ALL | wx.CENTER, 5)
        sizer.Add(self.model_list_box, 0, wx.ALL | wx.CENTER, 5)
        sizer.Add(self.tts_checkbox, 0, wx.ALL | wx.CENTER, 5)
        sizer.Add(self.input_label, 0, wx.ALL | wx.CENTER, 5)
        sizer.Add(self.input_ctrl, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(self.send_button, 0, wx.ALL | wx.CENTER, 5)
        sizer.Add(self.tree_label, 0, wx.ALL | wx.CENTER, 5)
        sizer.Add(self.tree, 1, wx.EXPAND)
        self.panel.SetSizer(sizer)
        self.input_ctrl.SetFocus()

        self.Bind(wx.EVT_CLOSE, self.on_close)

    def on_system_prompt_change(self, event):
        """
        同步前台系统提示词到最新状态
        """
        value = self.system_prompt_ctrl.GetValue().strip()
        if self.status.system_prompt != value:
            self.status.system_prompt = value

    def on_close(self, event):
        """
        处理窗口关闭事件
        """
        self.status.message_queue.put(None)
        self.Destroy()

    def on_begin(self) -> dict[str, Any]:
        """
        每次调用模型之前获取前端设定状态
        线程不安全， 后端调用的时候需要枷锁
        """
        return {
            "first_model_name": self.status.first_model,
            "second_model_name": self.status.second_model,
            "auto_tts": self.status.is_speak,
            "system_prompt": self.status.system_prompt,
        }

    def load_models_status(self, application: Application):
        """
        获取后端模型， 包括所有可用的模型和当前模型和备用模型
        """
        model_info = application.get_model_info(ContentTag.all_model)
        if model_info.content_tag != ContentTag.all_model:
            return

        self.status.models = model_info.metadata["models"]
        self.status.first_model = model_info.metadata["first_model"]
        self.status.second_model = model_info.metadata["second_model"]
        self.status.is_speak = model_info.metadata["is_speak"]
        self.tts_checkbox.SetValue(self.status.is_speak)

        self.set_model_list_box()

    def set_model_list_box(self):
        """
        填充模型列表
        """
        if self.status.models:
            self.model_list_box.Clear()
            self.model_list_box.Set(
                [self.fmt_model(model) for model in self.status.models]
            )

            self.model_list_box.SetSelection(0)

    def fmt_model(self, model: tuple, auto_label: bool = True) -> str:
        """
        格式化和标记模型
        """
        label = ""
        if auto_label and model[0] in [
            self.status.first_model,
            self.status.second_model,
        ]:
            label = "优先 " if model[0] == self.status.first_model else "备用 "

        return f"{label} {model[0]}, {'在线' if model[1] else '本地'}"

    def on_model_list_box_keydown(self, event):
        """
        让用户选择标记某个模型， 优先或者备用
        选择某个模型之后需要按下空格键 弹出菜单标记
        """
        if (
            self.model_list_box.GetSelection() >= 0
            and event.GetKeyCode() == wx.WXK_SPACE
        ):
            self.show_context_menu(self.model_list_box)

        event.Skip()

    def show_context_menu(self, obj):
        """
        设置上下文菜单并且弹出让用户标记模型
        """
        menu = wx.Menu()
        menu.Append(wx.ID_ANY, MENU_ITEM_SET_FIRST_MODEL)
        menu.Append(wx.ID_ANY, MENU_ITEM_SET_SECOND_MODEL)
        menu.Bind(wx.EVT_MENU, self.on_model_context_menu)

        self.PopupMenu(menu, obj.GetPosition())

    def on_model_context_menu(self, event):
        """
        真正标记模型， 需要取消上一个模型的标记
        """
        menu_item = event.GetEventObject()
        menu_label = menu_item.GetLabel(event.GetId())
        if menu_label == MENU_ITEM_SET_FIRST_MODEL:
            wx.MessageBox("设定主要模型")
        elif menu_label == MENU_ITEM_SET_SECOND_MODEL:
            wx.MessageBox("设定备用模型")

    def on_send(self, event):
        """
        处理发送消息事件
        """
        user_input = self.input_ctrl.GetValue()
        if user_input:
            self.status.message_queue.put(user_input)
            self.input_ctrl.Clear()
            self.change_Enable(False)
            # 添加用户消息， AI推理和AI回应节点
            user_node = self.tree.AppendItem(
                self.current_message_node, f"User: {user_input}"
            )
            self.current_reasoning_node = self.tree.AppendItem(
                self.current_message_node, "Reasoning:"
            )
            self.current_content_node = self.tree.AppendItem(
                self.current_message_node, "assistant:"
            )
            self.tree.SetFocus()
            self.tree.Expand(self.current_message_node)
            self.tree.SelectItem(user_node)

    def change_Enable(self, enable: bool):
        """
        模型输出阶段禁用某些控件， 输出完成后在启用
        """
        self.send_button.Enable(enable)
        self.model_list_box.Enable(enable)
        self.tts_checkbox.Enable(enable)

    def on_chunk(self, model_result: ModelResult):
        """
        从后台线程获取消息块
         这是给chat.Chat提供的三个接口之一
         run函数传递到最后的chat.Chat类
         另外两个接口也一样
        """
        if model_result.content in ["<think>", "</think>"]:
            model_result.content = "\n"

        self.status.line += model_result.content
        if len(model_result.content) > 0 and model_result.content[-1] == "\n":
            self.status.line = self.status.line.strip()
            if self.status.line:
                model_result.content = self.status.line
                self.status.line = ""
                # 线程安全的方式把后台数据更新到前台UI
                wx.CallAfter(self.add_message_to_tree, model_result)

    def on_finish(self, messages: list):
        """
        三大接口之一， 这里没有用到messages参数
        """
        self.change_Enable(True)
        if not messages:
            return

        # 创建新的消息节点， 在每个消息节点包含了 用户消息 AI推理和AI回应三个节点的内容
        self.current_message_node = self.tree.AppendItem(self.root, "Message:")
        self.tree.Expand(self.current_content_node)
        self.tree.SelectItem(self.current_content_node)
        # 发送完成信号
        self.on_chunk(ModelResult("\n", ContentTag.chunk))

    def add_message_to_tree(self, model_result: ModelResult):
        """
        最后在这个方法里更新UI内容
        """
        if model_result.tag == ContentTag.reasoning_content:
            child_node = self.tree.AppendItem(self.current_reasoning_node, "reasoning:")

        else:
            child_node = self.tree.AppendItem(self.current_content_node, "AI助手：")

        self.tree.SetItemText(child_node, f"{model_result.content}")


if __name__ == "__main__":
    app = wx.App()
    with ExitStack() as stack:
        config = stack.enter_context(Config())
        frame = MainFrame()

        # 启动 AI 聊天线程
        application = stack.enter_context(
            Application(
                config=config,
                model_name="deepseek-r1:14b",
                second_model_name="deepseek-chat",
                begin_callback=frame.on_begin,
                input_callback=frame.status.message_queue.get,
                chunk_callback=frame.on_chunk,
                finish_callback=frame.on_finish,
            )
        )

        application.daemon = True
        frame.load_models_status(application=application)
        application.start()

        frame.Show()
        app.MainLoop()
        clear_queue(frame.status.message_queue)
        application.join()
