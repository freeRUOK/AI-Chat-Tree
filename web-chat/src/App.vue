<script setup>
// filename: App.vue
// Author: FreeRUOK <2651688427@qq.com>
// Date: 2025-03
//Description: AI-Chat-Tree的web前端
// vue应用的主要组件， 需要挂在到html文档

import { ref } from "vue";
import io from "socket.io-client";
import MarkdownParser from "./markdown-parser.js";
import AudioPlayer from "./audio-player.js";
import StatusBar from "./components/StatusBar.vue";
import { useMessageBus } from "./event-bus.js";
import MessageListComponent from "./components/MessageList.vue";
import SendMessageComponent from "./components/SendMessage.vue";
import Message from "./models/message.js";
import MessageCollection from "./models/message-collection.js";

const socket = io({ query: { userName: "ou2024" } });
socket.on("connect", () => {});
socket.on("error", (e) => {
  throw e;
});

const marked = MarkdownParser();
const audioPlayer = new AudioPlayer();
const currentMessage = ref(null);
const { showMessage } = useMessageBus();
const messages = ref(new MessageCollection());
messages.value.all();

socket.on("chat", (newMessage) => {
  if (newMessage) {
    const html_doc = marked(newMessage.text);
    currentMessage.value?.appendBody(html_doc);
  }
});

socket.on("audio", (newAudio) => {
  if (newAudio) {
    audioPlayer.play(newAudio["audio/mpeg3"]);
  }
});

function send(messageBody) {
  messages.value.put(new Message("Self:", messageBody.text, "user-message"));
  currentMessage.value = new Message("Assistant:", "", "llm-message");
  messages.value.put(currentMessage.value);
  socket.emit("chat", messageBody);
  showMessage("发送成功");
}
</script>
<template>
  <MessageListComponent :message-collection="messages" />
  <SendMessageComponent @new-message="send" />
  <StatusBar ref="statusBarRef" />
</template>
