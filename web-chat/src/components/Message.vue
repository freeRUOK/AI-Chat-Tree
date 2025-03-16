<script setup>
// filename: Message.vue
// Author: FreeRUOK <2651688427@qq.com>
// Date: 2025-03
// Description: AI-Chat-Tree的web前端
// 展示一条完整用户消息或AI模型的消息

import { ref, onMounted, watch } from "vue";
import ClipboardJS from "clipboard";
import Message from "../models/message.js";
import { useMessageBus } from "../event-bus.js";
import Uploader from "./Uploader.vue";
const { showMessage } = useMessageBus();
const props = defineProps({ message: Message, file: [File, null] });
const messageRef = ref(null);

// 给拷贝按钮添加拷贝文本到系统剪贴板的函数
const initClipboard = () => {
  new ClipboardJS(".copy-code, .copy-all", {
    text: function (trigger) {
      let block;
      if (trigger.classList.contains("copy-code")) {
        block = trigger.nextElementSibling;
      } else if (trigger.classList.contains("copy-all")) {
        block = trigger.previousElementSibling;
      }
      showMessage("成功拷贝 ");
      return block?.textContent ?? "empty";
    },
  });
};
// 监听内容变化
// 给所有class: copy-all或copy-code按钮添加拷贝功能
watch(
  () => props.message?.body,
  () => {
    initClipboard();
  },
);

watch(
  () => props.message?.isDone,
  (isDone) => {
    if (isDone) {
      messageRef.value?.focus();
    }
  },
);

onMounted(initClipboard);
</script>
<template>
  <h2 aria-live="off">{{ message.title }}</h2>
  <div ref="messageRef" tabindex="0" class="message">
    <div v-html="message.body"></div>
    <button v-show="message.body !== ''" class="copy-all">Copy All</button>
  </div>
  <div v-if="message.body == ''">正在生成内容……</div>
</template>
