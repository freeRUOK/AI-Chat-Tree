// eventBus.js
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
