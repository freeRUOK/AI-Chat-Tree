# --*-- Coding: UTF-8 --*--
#! filename: gui.py
# * Author： 2651688427@qq.com <FreeRUOK>
# * date： 2025-02
# * description: 一个简单的AI LLM聊天程序
# 主要实现了wxpython的GUI界面
# 消息列表使用树状图来呈现
# 这样可以在内容之间快速跳转
from contextlib import ExitStack
import threading
import wx  # type: ignore
import pyperclip  # type: ignore
import pygetwindow as gw  # type: ignore
from model import ModelResult
from config import Config
from application import Application
from consts import ContentTag
from sound_player import PlayMode, get_sound_player
from util import clear_queue, ImageHandler
from gui_consts import MENU_ITEM_SET_FIRST_MODEL, MENU_ITEM_SET_SECOND_MODEL
from data_status import DataStatus as FrameStatus
from text_to_speech import TextToSpeechOption


class MainFrame(wx.Frame):
    """
    主窗口类
    """

    def __init__(self):
        super().__init__(parent=None, title="AI Chat Tree", size=(1200, 900))

        self.status = FrameStatus()
        self.application: Application | None = None
        self._image_handler = ImageHandler()

        self.panel = wx.Panel(self)

        self.system_prompt_label = wx.StaticText(
            self.panel,
            label="系统提示词（AI遵循的最高指令，可以按照自己的喜好随意修改）：",
        )
        self.system_prompt_ctrl = wx.TextCtrl(
            self.panel, style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER
        )
        self.system_prompt_ctrl.SetMinSize((700, 100))  # 保持最小尺寸
        self.system_prompt_ctrl.Bind(wx.EVT_KILL_FOCUS, self.on_system_prompt_change)

        self.system_prompt_ctrl.SetValue(self.status.system_prompt)

        self.model_label = wx.StaticText(self.panel, label="可用模型：")
        self.model_list_box = wx.ListBox(self.panel)
        self.model_list_box.Bind(wx.EVT_KEY_DOWN, self.on_model_list_box_keydown)

        self.tts_checkbox = wx.CheckBox(self.panel, label="自动大声朗读(\t&U)")
        self.tts_checkbox.Bind(wx.EVT_CHECKBOX, self.on_tts_switch_check)

        self.input_label = wx.StaticText(self.panel, label="消息：")
        self.input_ctrl = wx.TextCtrl(
            self.panel, style=wx.TE_MULTILINE | wx.TE_PROCESS_ENTER
        )
        self.input_ctrl.SetMinSize((700, 100))  # 保持最小尺寸

        self.send_button = wx.Button(self.panel, label="发送(\t&S)")
        self.send_button.Bind(wx.EVT_BUTTON, self.on_send)

        self.tree_label = wx.StaticText(self.panel, label="AI会话：")
        self.tree = wx.TreeCtrl(
            self.panel, style=wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT
        )
        self.root = self.tree.AddRoot("AI Chat")
        self.tree.SetItemText(self.root, "消息列表：")
        self.tree.ExpandAll()
        self.tree.Bind(wx.EVT_KEY_UP, self.on_message_tree_key_up)
        self.current_message_node = None
        self.current_reasoning_node = None

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
        sizer.Add(self.tree, 2, wx.EXPAND | wx.ALL, 5)

        self.panel.SetSizer(sizer)
        self.input_ctrl.SetFocus()

        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.capture_hot_key_id = wx.NewIdRef()
        if not self.register_hot_key():
            wx.MessageBox(
                "请检查 ctrl+shift+f1 到 ctrl+shift+f4 是否被占用。",
                "注册截屏热键热键失败",
                wx.ICON_ERROR,
            )
        self.sound_player = get_sound_player()
        self.new_menu_bar()
        self.record_hotkey = wx.NewIdRef()
        if self.RegisterHotKey(
            self.record_hotkey, wx.MOD_ALT | wx.MOD_SHIFT, wx.WXK_F5
        ):
            self.Bind(wx.EVT_HOTKEY, self.on_record, id=self.record_hotkey)

    def register_hot_key(self) -> bool:
        """
        注册截屏热键
        Alt+shift+f1全屏截图
        alt+shift+f2前台窗口截图
        alt+shift+f3 调用设备镜头拍照
        alt+shift+f4 选择一个图片文件
        """
        for key_code in [wx.WXK_F1, wx.WXK_F2, wx.WXK_F3, wx.WXK_F4]:
            if not self.RegisterHotKey(
                self.capture_hot_key_id, wx.MOD_ALT | wx.MOD_SHIFT, key_code
            ):
                return False

        self.Bind(wx.EVT_HOTKEY, self.on_capture_hot_key, id=self.capture_hot_key_id)
        return True

    def on_capture_hot_key(self, event):
        """
        处理截屏热键事件
        """
        if not self.send_button.IsEnabled():
            return

        key_code = event.GetKeyCode()
        if key_code in [wx.WXK_F1, wx.WXK_F2]:
            self._image_handler.capture_screen(is_full_screen=key_code == wx.WXK_F1)

        elif key_code == wx.WXK_F3:
            self._image_handler.capture()
        elif key_code == wx.WXK_F4:
            self.open_image_file()
        else:
            return

        self.send_image()

    def open_image_file(self):
        """
        从文件管理器里打开一个图片文件并转换到Image.Image对象
        """
        file_dialog = wx.FileDialog(
            self,
            "请选择一个图片文件",
            "",
            "",
            "所有文件 (*.*)|*.*",
            wx.FD_FILE_MUST_EXIST | wx.FD_OPEN,
        )
        if file_dialog.ShowModal() == wx.ID_OK:
            image_path = file_dialog.GetPath()
            self._image_handler.read_image_file(image_path)

        file_dialog.Destroy()

    def send_image(self):
        """
        添加base64编码的图片并发送
        """
        if base64_image := self._image_handler.to_base64():
            self.set_global_focus_()
            self.sound_player.play("capture", PlayMode.ones_sync)
            self.send_message(
                self.input_ctrl.GetValue().strip() or "图片里是什么？",
                base64_image,
            )

        else:
            wx.MessageBox("获取图片失败")

        self._image_handler.close_current_image()

    def on_record(self, event):
        """
        录音事件处理函数
        """
        if self.application.voice_input_manager._speech_to_text.is_recording():
            self.application.voice_input_manager.end_voice_input()
            self.create_message_tree_element("语音输入的内容： ")
        else:
            self.application.voice_input_manager.begin_voice_input()

    def new_menu_bar(self):
        """
        创建alt菜单
        """
        menu_bar = wx.MenuBar()
        file_menu = wx.Menu()
        file_menu.Append(wx.ID_OPEN, "打开\tCtrl+O", "打开图片文件")

        help_menu = wx.Menu()
        help_menu.Append(wx.ID_ABOUT, "关于\tCtrl+A", "关于本程序")

        menu_bar.Append(file_menu, "文件(&F)")
        menu_bar.Append(help_menu, "帮助(&H)")
        self.SetMenuBar(menu_bar)
        self.Bind(wx.EVT_MENU, self.on_menu_bar, id=wx.ID_OPEN)
        self.Bind(wx.EVT_MENU, self.on_menu_bar, id=wx.ID_ABOUT)

    def on_menu_bar(self, event):
        """
        处理alt菜单的事件
        """
        menu_id = event.GetId()
        if menu_id == wx.ID_OPEN:
            self.open_image_file()
        elif menu_id == wx.ID_ABOUT:
            wx.MessageBox("版权所有 2025 FreeRUOK")

    def on_error(self, exc: Exception, is_fail: bool):
        wx.MessageBox(str(exc), "出错了", wx.ICON_ERROR)
        if is_fail:
            wx.CallAfter(self.Close)

    def set_window_title(
        self, first_title: str | None, last_title: str = "AI Chat Tree"
    ):
        """
        修改窗口标题
        """
        if first_title is None:
            first_title = ""

        if first_title := first_title.strip():
            first_title = f"{first_title} - "
        else:
            first_title = ""

        self.SetTitle(f"{first_title}{last_title}")

    def set_global_focus_(self):
        """
        在全局范围内让当前窗口聚焦系统焦点
        """

        if not self.IsActive():
            if result_window := gw.getWindowsWithTitle(self.Title):
                result_window[0].activate()

    def on_system_prompt_change(self, event):
        """
        同步前台系统提示词到最新状态
        """
        value = self.system_prompt_ctrl.GetValue().strip()
        if self.status.system_prompt != value:
            self.status.is_change = True
            self.status.system_prompt = value

    def on_tts_switch_check(self, event):
        """
        语音朗读开关变化
        """
        self.status.text_to_speech_option = (
            TextToSpeechOption.play
            if self.tts_checkbox.IsChecked()
            else TextToSpeechOption.off
        )
        self.status.is_change = True

    def on_close(self, event):
        """
        处理窗口关闭事件
        """
        self.status.message_queue.put(None)
        self.UnregisterHotKey(self.capture_hot_key_id)
        self.Destroy()
        self.sound_player.stop()

    def load_models_status(self, application: Application):
        """
        获取后端模型， 包括所有可用的模型和当前模型和备用模型
        """
        self.status.load_models_status(application=application)
        self.tts_checkbox.SetValue(
            self.status.text_to_speech_option != TextToSpeechOption.off
        )
        self.set_model_list_box()

    def set_model_list_box(self, selection: int = 0):
        """
        填充模型列表
        """
        if self.status.models:
            self.model_list_box.Clear()
            self.model_list_box.Set(
                [self.fmt_model(model) for model in self.status.models]
            )

            self.model_list_box.SetSelection(selection)

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
        target_index = self.model_list_box.GetSelection()
        is_change = self.status.set_current_model(
            target_index, is_first_model=menu_label == MENU_ITEM_SET_FIRST_MODEL
        )
        if is_change:
            self.set_model_list_box(selection=target_index)

    def on_send(self, event):
        """
        处理发送消息事件
        """
        user_input = self.input_ctrl.GetValue().strip()
        if user_input:
            self.send_message(user_input)
            self.input_ctrl.Clear()
        else:
            wx.MessageBox("输入有效的文本内容！", "无效或者空的输入：", wx.ICON_WARNING)

    def send_message(self, message: str, base64_image: str | None = None):
        """
        更新UI发送消息
        """
        self.status.current_user_input = message
        self.status.message_queue.put((message, base64_image))
        self.change_Enable(False)
        self.create_message_tree_element(message)
        self.sound_player.play("send-message", PlayMode.ones_sync)
        self.sound_player.play("wait", PlayMode.loop)

    def create_message_tree_element(self, user_input: str):
        """
        添加用户消息， AI推理和AI回应节点
        """
        self.current_message_node = self.tree.AppendItem(
            self.root, f"{user_input.splitlines()[0]} ....."
        )

        self.tree.SetFocus()
        self.tree.SelectItem(self.current_message_node)

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
        if self.status.current_content_tag != model_result.tag:
            self.status.current_content_tag = model_result.tag
            model_result.content = f"\n{model_result.content}"

        self.status.line += model_result.content
        if self.status.current_model_name != model_result.model_name:
            self.status.current_model_name = model_result.model_name
            wx.CallAfter(self.set_window_title, model_result.model_name)

        if self.status.line[-1:] == "\n" or model_result.tag == ContentTag.end:
            content = self.status.line.strip()
            if content:
                wx.CallAfter(self.add_message_to_tree, content)

            self.status.line = ""

    def on_finish(self, messages: list):
        """
        三大接口之一， 这里没有用到messages参数
        """
        self.change_Enable(True)
        if not messages:
            return

        # 更新最后残留的内容
        self.on_chunk(
            ModelResult("", ContentTag.end, model_name=self.status.current_model_name)
        )
        self.current_reasoning_node = None
        self.sound_player.stop_play()

    def add_message_to_tree(self, line: str):
        """
        最后在这个方法里更新UI内容
        """

        if self.status.current_content_tag == ContentTag.reasoning_content:
            if self.current_reasoning_node is None:
                self.current_reasoning_node = self.tree.AppendItem(
                    self.current_message_node,
                    "思考内容：",
                )

            self.tree.AppendItem(self.current_reasoning_node, line)

        else:
            self.tree.AppendItem(self.current_message_node, line)

        self.tree.Expand(self.current_message_node)
        self.sound_player.stop_play()
        self.sound_player.play("display-message", PlayMode.ones_async)

    def get_tree_all_text(self, begin_node):
        """
        生成器函数， 获取self.tree的某个节点及其子孙节点的文本内容
        """
        child, cookie = self.tree.GetFirstChild(begin_node)
        while child.IsOk():
            yield self.tree.GetItemText(child)
            yield from self.get_tree_all_text(child)
            child, cookie = self.tree.GetNextChild(begin_node, cookie)

    def on_message_tree_key_up(self, event):
        """
        消息树状图键盘按键被按下
        """
        if event.GetKeyCode() == ord("C") and event.ControlDown():
            selection = self.tree.GetSelection()
            text = self.tree.GetItemText(selection)
            if event.ShiftDown():
                lines = "\n".join(self.get_tree_all_text(selection))
                text = f"{text}\n{lines}"

            pyperclip.copy(text=text)

        event.Skip()


if __name__ == "__main__":
    app = wx.App()
    with ExitStack() as stack:
        config = stack.enter_context(Config())
        frame = MainFrame()

        # 启动 AI 聊天线程
        application = stack.enter_context(
            Application(
                config=config,
                model_name="gemma3:27b",
                second_model_name="deepseek-chat",
                text_to_speech_option=TextToSpeechOption.play,
                error_callback=frame.on_error,
                begin_callback=frame.status.on_begin,
                input_callback=frame.status.message_queue.get,
                chunk_callback=frame.on_chunk,
                finish_callback=frame.on_finish,
                voice_input_callback=frame.status.on_speech_result,
            )
        )

        frame.load_models_status(application=application)
        application.start()
        frame.application = application

        frame.Show()
        app.MainLoop()
        if threading.active_count() > 1:
            clear_queue(frame.status.message_queue)
            application.join()
