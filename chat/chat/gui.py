# --*-- Coding: UTF-8 --*--
#! filename: gui.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2025-02
# * description: 一个简单的AI LLM聊天程序
# 主要实现了wxpython的GUI界面
# 消息列表使用树状图来呈现
# 这样可以在内容之间快速跳转
import wx  # type: ignore
import threading
from queue import Queue
from model import ModelResult
from run import run
from consts import ContentTag
from util import clear_queue


# 主窗口类
class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title="AI Chat Tree", size=(800, 600))
        self.panel = wx.Panel(self)

        self.input_ctrl = wx.TextCtrl(
            self.panel, style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER
        )
        self.input_ctrl.SetMinSize((700, 100))

        self.send_button = wx.Button(self.panel, label="Send")
        self.send_button.Bind(wx.EVT_BUTTON, self.on_send)

        self.model_combo = wx.ComboBox(
            self.panel, choices=["Model 1", "Model 2"], style=wx.CB_READONLY
        )
        self.model_combo.SetSelection(0)

        self.tts_checkbox = wx.CheckBox(self.panel, label="TTS")

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
        sizer.Add(self.input_ctrl, 0, wx.EXPAND | wx.ALL, 5)
        sizer.Add(self.send_button, 0, wx.ALL | wx.CENTER, 5)
        sizer.Add(self.model_combo, 0, wx.ALL | wx.CENTER, 5)
        sizer.Add(self.tts_checkbox, 0, wx.ALL | wx.CENTER, 5)
        sizer.Add(self.tree, 1, wx.EXPAND)
        self.panel.SetSizer(sizer)

        self.messageQueue = Queue()
        self.line = ""
        self.Bind(wx.EVT_CLOSE, self.on_close)

    def on_close(self, event):
        """
        处理窗口关闭事件
        """
        self.messageQueue.put(None)
        self.Destroy()

    def on_send(self, event):
        """
        处理发送消息事件
        """
        user_input = self.input_ctrl.GetValue()
        if user_input:
            self.messageQueue.put(user_input)
            self.input_ctrl.Clear()
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

    def OnChunk(self, model_result: ModelResult):
        """
        从后台线程获取消息块
         这是给chat.Chat提供的三个接口之一
         run函数传递到最后的chat.Chat类
         另外两个接口也一样
        """
        if model_result.content in ["<think>", "</think>"]:
            model_result.content = "\n"

        self.line += model_result.content
        if len(model_result.content) > 0 and model_result.content[-1] == "\n":
            self.line = self.line.strip()
            if self.line:
                model_result.content = self.line
                self.line = ""
                # 线程安全的方式把后台数据更新到前台UI
                wx.CallAfter(self.add_message_to_tree, model_result)

    def OnFinish(self, messages: list):
        """
        三大接口之一， 这里没有用到messages参数
        """
        # 创建新的消息节点， 在每个消息节点包含了 用户消息 AI推理和AI回应三个节点的内容
        self.current_message_node = self.tree.AppendItem(self.root, "Message:")
        self.tree.Expand(self.current_content_node)
        self.tree.SelectItem(self.current_content_node)
        # 发送完成信号
        self.OnChunk(ModelResult("\n", ContentTag.chunk))

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
    frame = MainFrame()

    # 启动 AI 聊天线程
    ai_chat_thread = threading.Thread(
        target=run,
        kwargs={
            "input_callback": frame.messageQueue.get,
            "chunk_callback": frame.OnChunk,
            "finish_callback": frame.OnFinish,
        },
    )
    ai_chat_thread.setDaemon(True)
    ai_chat_thread.start()

    frame.Show()
    app.MainLoop()
    clear_queue(frame.messageQueue)
    ai_chat_thread.join()
