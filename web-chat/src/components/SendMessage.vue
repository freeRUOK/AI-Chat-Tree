<script setup>
// filename: SendMessage.vue
// Author: FreeRUOK <2651688427@qq.com>
// Date:2025-03
// Description: AI-Chat-Tree的web前端
// 发送消息的vue组件

import { ref } from "vue";
const message = ref("");
const fileData = ref(null);
const inputFileRef = ref(null);
const emits = defineEmits({ newMessage: null });
/** 上传文件的时候被调用
 */
function onFileDataChange(event) {
  const files = event?.target?.files;
  fileData.value = files[0] ?? null;
}
/**
 * 把组件内的消息往外发送， 这样其他组件可以获取消息进一步处理了
 比如 发送到后端服务器， 展示到消息列表等等
 */
function emitNewMessage() {
  const eventBody = { isEmpty: true };
  const userMessage = message.value.trim();
  if (userMessage !== "") {
    eventBody.isEmpty = false;
    eventBody.message = userMessage;
    message.value = "";
  }
  if (fileData.value !== null) {
    eventBody.isEmpty = false;
    eventBody.fileData = fileData.value;
    fileData.value = null;
  }
  // 真正从内部发送消息
  if (!eventBody.isEmpty) {
    emits("newMessage", {
      text: eventBody?.message,
      image: eventBody?.fileData,
    });
  }
}
/**
 * 处理组件内部的键盘事件
 * 比如alt+s发送消息， alt+o上传文件
 * 注意这里仅仅是把组件内部的消息发送到外部， 无法控制外部如何处理
 * @param e
 */
function onKeydown(e) {
  const keyCode = e.key.toLowerCase();
  if (e.altKey && ["s", "o"].includes(keyCode)) {
    e.preventDefault();
    switch (keyCode) {
      case "s":
        emitNewMessage();
        break;
      case "o":
        inputFileRef.value.click();
        break;
      default:
        break;
    }
  }
}
</script>

<template>
  <div
    role="toolbar"
    aria-label="Alt+S发送消息， Alt+O上传文件"
    @keydown="onKeydown"
  >
    <textarea v-model="message" placeholder="消息："></textarea>

    <button @click="emitNewMessage">发送</button>
    <input
      ref="inputFileRef"
      @change="onFileDataChange"
      type="file"
      aria-label="选择文件发送： "
    />
    <div v-if="fileData">
      可以附加到文本消息， 也可以单独发送<br />文件名： {{ fileData.name
      }}<br />文件大小： {{ fileData.size }} 字节
    </div>
  </div>
</template>
