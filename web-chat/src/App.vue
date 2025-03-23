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
    const html_doc = marked.parseLine(newMessage.content);
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

const systemPrompt = ref("");
const modelList = ref([]);
const firstModel = ref("null");
const secondModel = ref("null");
const textToSpeechSwitch = ref(false);
const isChange = ref(false);

socket.on("model_status", (modelStatus) => {
  if (modelStatus) {
    systemPrompt.value = modelStatus.system_prompt;
    modelList.value.slice(0, modelList.value.length);
    modelStatus.models.forEach((item) => {
      modelList.value.push({
        value: item[0],
        label: `${item[0]}, ${item[1] ? "在线" : "本地"}`,
      });
    });

    firstModel.value = modelStatus.first_model;
    secondModel.value = modelStatus.second_model;
    textToSpeechSwitch.value = modelStatus.text_to_speech_option;
  }
});

function sendNewStatus() {
  if (!isChange.value) {
    return;
  }
  isChange.value = false;
  const updateStatus = {
    system_prompt: systemPrompt.value,
    first_model: firstModel.value,
    second_model: secondModel.value,
    text_to_speech_option: textToSpeechSwitch.value,
  };
  socket.emit("update_status", updateStatus);
}

function send(messageBody) {
  messages.value.put(new Message("Self:", messageBody.text, "user-message"));
  currentMessage.value = new Message("Assistant:", "", "llm-message");
  messages.value.put(currentMessage.value);
  sendNewStatus();
  socket.emit("chat", messageBody);
  showMessage("发送成功");
}
</script>
<template>
  <OptionBar
    :systemPrompt="systemPrompt"
    :modelList="modelList"
    :firstModel="firstModel"
    :secondModel="secondModel"
    :textToSpeechSwitch="textToSpeechSwitch"
    @update:systemPrompt="systemPrompt = $event"
    @update:firstModel="firstModel = $event"
    @update:secondModel="secondModel = $event"
    @update:textToSpeechSwitch="textToSpeechSwitch = $event"
    @update:isChange="isChange = $event"
  />

  <MessageListComponent :message-collection="messages" />
  <SendMessageComponent @new-message="send" />
  <StatusBar ref="statusBarRef" />
</template>
