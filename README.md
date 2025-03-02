# AI-Chat-Tree
简单AI聊天程序， 支持在线OpenAI和本地ollama调用， 聊天内容在Tree Ctrl上展示

## 介绍
目前支持命令行和gui（不完善不稳定）模式运行， 接下来打算添加web前端和服务端， 从而实现非本机远程调用的目的。  
gui部分使用树状图展示聊天列表， 从而在各个部分之间灵活跳转。
配置功能不完善， 请手动编辑， 注意不能违反yml格式文件的语法。 
支持语音朗读功能， 需要ffmpeg工具。

## 构建和运行

项目使用poetry作为管理工具， 在Windowspython 3.11.0环境下开发。  
如遇到问题可以编辑pyProject.toml文件调整依赖关系。  

使用如下命令构建并运行
```bash
git clone https://github.com/FreeRUOK/AI-Chat-Tree.git
cd AI-Chat-Tree\chat
protry install
poetry shell
set DEBUG_MODE=1 # 启用调试模式
python chat chat # cli
python chat\gui.py # gui
pythonw chat\gui.py # 无控制台
```

## 关于配置API-KEY

替换或拷贝chat\config.yml文件， 配置文件不要包含注释等其他内容
```yml
usage:
  ollama_host: http://127.0.0.1:11434 # 本地ollama接口， 如果修改了端口需要这里修改
  chat_collection_dir: chat_collections # 聊天文件的保存文件夹
models: # 这里列举不同配置的在线模型， ollama模型自动获取
- group_name: deepseek # 模型组， 共享同一套配置的若干模型
  is_online: true # 是否网络模型
  show_reasoning: true # 是否输出推理思维练
  base_url: https://api.deepseek.com # 模型提供的调用地址
  api_key: my-api-key # api密钥
  sub_models:
  - deepseek-reasoner # 相同配置的若干模型
  - deepseek-chat
  # 假设模型组
- group_name: my-model
  is_online: true
  show_reasoning: true
  base_url: http://my-server.com/v1
  api_key: my-api-key # api密钥
  sub_models:
  - deepseek-r1
  - llama3.2
text_to_speech: # 具体可以用的语音参数参考edge_tts
  voice: Microsoft Server Speech Text to Speech Voice (zh-CN, XiaoxiaoNeural)
  rate: +100%
  volume: +20%
```
