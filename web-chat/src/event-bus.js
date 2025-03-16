// filename: eventBus.js
// Author: FreeRUOK <2651688427@qq.com>
// Date: 2025-03
// Description: AI-Chat-Tree的web前端
// 定义一个全局通讯BUS
import { ref } from "vue";

const message = ref("");
const duration = ref(3000);

export const useMessageBus = () => {
  return {
    message,
    duration,
    clearMessage() {
      message.value = "";
    },
    showMessage(msg, customDuration = 3000) {
      message.value = msg;
      duration.value = customDuration;
      setTimeout(() => {
        message.value = "";
      }, duration.value);
    },
  };
};
