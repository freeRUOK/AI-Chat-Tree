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
import OptionBar from "./components/OptionBar.vue";
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

const marked = new MarkdownParser();
const audioPlayer = new AudioPlayer();
const currentMessage = ref(null);
const { showMessage } = useMessageBus();
const messages = ref(new MessageCollection());
messages.value.all();

socket.on("chat", (newMessage) => {
  if (newMessage) {
    const html_doc = marked.parseLine(newMessage.text);
    if (html_doc) {
      currentMessage.value?.appendBody(html_doc, newMessage[["tag"]] === "end");
    }
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

const systemPrompt = ref("默认提示");
const modelList = ref([
  { value: "m1", label: "1" },
  { value: "m2", label: "2" },
  { value: "m3", label: "3" },
  { value: "m4", label: "4" },
  { value: "m5", label: "5" },
  { value: "m6", label: "6" },
]);
const firstModel = ref("null");
const secondModel = ref("null");
const textToSpeechSwitch = ref(false);
</script>
<template>
  <OptionBar
    :systemPrompt="systemPrompt"
    :modelList="modelList"
    :textToSpeechSwitch="textToSpeechSwitch"
    @update:systemPrompt="systemPrompt = $event"
    @update:firstModel="firstModel = $event"
    @update:secondModel="secondModel = $event"
    @update:textToSpeechSwitch="textToSpeechSwitch = $event"
  />
  <div>
    <p>{{ systemPrompt }}</p>
    <p>{{ firstModel }}</p>
    <p>{{ secondModel }}</p>
    <p>{{ textToSpeechSwitch }}</p>
  </div>

  <MessageListComponent :message-collection="messages" />
  <SendMessageComponent @new-message="send" />
  <StatusBar ref="statusBarRef" />
</template>
