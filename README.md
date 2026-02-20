# AI-Chat-Tree

多端 AI 聊天程序，支持在线 OpenAI 和本地 Ollama 调用，支持 CLI、GUI 和 Web 界面，支持工具调用和全链路语音控制。

## 介绍

一个 LLM 聊天助手，支持 CLI、GUI 和 Web 三种界面形式，正在逐步实现 Agent 能力。

GUI 部分使用树状图展示聊天列表，从而在各个聊天会话之间灵活跳转。

Web 前端使用 Vue + Socket.IO 实现，目前功能尚不完善。

配置功能暂未提供图形化界面和命令行接口，请手动编辑配置文件，注意不能违反 YAML 格式文件的语法。

支持全链路语音操作（语音唤醒、语音输入和语音朗读），需要安装 ffmpeg 工具。

## 构建和运行

项目使用 Poetry 作为依赖管理工具，在 Windows Python 3.11.0 环境下开发。

由于大量使用 Windows 特定库，目前只能在 Windows 平台上运行，后续可能扩展到其他平台。

如遇到问题可以编辑 pyproject.toml 文件调整依赖关系。

使用如下命令构建并运行：

```bash
git clone https://github.com/FreeRUOK/AI-Chat-Tree.git
cd AI-Chat-Tree\chat
poetry install
poetry shell
set DEBUG_MODE=1 # 启用调试模式
python chat chat # CLI 模式
python chat/gui.py # GUI 模式
pythonw chat/gui.py # 无控制台窗口
python chat serve # 启动 Web 服务，默认在 8001 端口运行
```

## 构建 Web 前端

进入项目根目录的 web-chat 文件夹：

```bash
npm install
npm start # 调试预览
npm run all # 打包前端页面
```

成功打包之后，将 `web-chat/dist` 文件夹移动到项目根目录之下的 `chat/` 文件夹，并重命名为 `static`，这样就可以使用 Python Flask 静态文件服务了。

## 关于配置 API-KEY

替换或拷贝 `chat\config.yml` 文件，配置文件不要包含注释等其他内容：

```yml
usage:
  ollama_host: http://127.0.0.1:11434 # 本地 Ollama 接口，如果修改了端口需要在这里修改
  ollama_api_key: my-key # 如果需要使用 Ollama 云端模型的话需要获取
  chat_collection_dir: chat_collections # 聊天文件的保存文件夹
models: # 这里列举不同配置的在线模型，Ollama 模型自动获取
- group_name: deepseek # 模型组，共享同一套配置的若干模型
  is_online: true # 是否网络模型
  show_reasoning: true # 是否输出推理思维链
  base_url: https://api.deepseek.com # 模型提供的调用地址
  api_key: my-api-key # API 密钥
  sub_models:
  - deepseek-reasoner # 相同配置的若干模型
  - deepseek-chat
  # 假设模型组
- group_name: my-model
  is_online: true
  show_reasoning: true
  base_url: http://my-server.com/v1
  api_key: my-api-key # API 密钥
  sub_models:
  - deepseek-r1
  - llama3.2
text_to_speech: # 具体可用的语音参数参考 edge_tts
  voice: Microsoft Server Speech Text to Speech Voice (zh-CN, XiaoxiaoNeural)
  rate: +100%
  volume: +20%
voice_input: # 语音唤醒和语音输入方面
  porcupine_access_key: my-key # 支持中文唤醒短语，首次可能需要特殊网络条件
  porcupine_model_path: C:\Users\free\.models\porcupine\porcupine_params_zh.pv # 特定语言模型
  porcupine_wake_zh_model_path: C:\Users\free\.models\porcupine\黑鹰_zh_windows_v4_0_0\黑鹰_zh_windows_v4_0_0.ppn # 可以在控制台生成自定义短语，这里是黑鹰
  vosk_model_path: C:\Users\free\.models\vosk\vosk-model-small-cn-0.22 # 这是小的语音识别模型，效果不理想，建议使用标准中文模型
```

## 关于项目架构

项目使用多线程架构，主要防止 UI 的冻结。

在底层 LLM 模型和顶层 UI 之间引入 Application 抽象层，统一管理多种类型的顶层 UI 和底层的 LLM。

用户的输入和模型的输出使用回调函数来降低耦合度，提升单独扩展性和整体的稳定性。

### 主要源文件的用途

- `cli.py` `gui.py` `ws_serve.py`：分别是 CLI、GUI 和 Web 界面，定义了用户消息的输入和模型输出的展示，三个 UI 使用 `data_status.py` 管理 UI 状态。
- `application.py`：模型和 UI 之间的抽象层，此外管理全链路语音服务，承上启下是最好的概括。
- `chat.py` `model.py` `model_tools.py`：主要是 LLM 模型的管理和辅助功能。
- `voice_input_manager.py` `speech_to_text.py` `wake_word_detector.py`：语音唤醒和语音输入的实现，`voice_input_manager.py` 协调整个语音唤醒和语音输入流程。

## 后续开发路线

正在实现工具调用能力，并且做到让其他人方便地添加新工具的能力。

后续添加 Web 端的全链路语音能力。

