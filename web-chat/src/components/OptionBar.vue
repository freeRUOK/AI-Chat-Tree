<script setup>
// filename: OptionBar.vue
// Author: FreeRUOK <2651688427@qq.com>
// Date: 2025-03
// Description: AI-Chat-Tree的web前端
// 定义web前端的选项， 如 系统提示词 模型 语音朗读开关
import { ref, watch } from "vue";

const props = defineProps({
  systemPrompt: [String, null],
  firstModel: [String, null],
  secondModel: [String, null],
  modelList: {
    type: Array,
    default: () => [],
  },
  textToSpeechSwitch: Boolean,
  isChange: Boolean,
});

const emit = defineEmits([
  "update:systemPrompt",
  "update:firstModel",
  "update:secondModel",
  "update:textToSpeechSwitch",
  "update:isChange",
]);

// 响应式变量
const systemPromptRef = ref(props.systemPrompt);
const firstModelRef = ref(props.firstModel?.value || "");
const secondModelRef = ref(props.secondModel?.value || "");
const textToSpeechSwitchRef = ref(props.textToSpeechSwitch);
const isChangeRef = ref(props.isChange);

// 监听 props 的变化并同步到响应式变量
watch(
  () => props.systemPrompt,
  (newValue) => {
    systemPromptRef.value = newValue;
    isChangeRef.value = true;
  },
);

watch(
  () => props.firstModel,
  (newValue) => {
    firstModelRef.value = newValue;
    isChangeRef.value = true;
  },
);

watch(
  () => props.secondModel,
  (newValue) => {
    secondModelRef.value = newValue;
    isChangeRef.value = true;
  },
);
watch(
  () => props.textToSpeechSwitch,
  (newValue) => {
    textToSpeechSwitchRef.value = newValue;
    isChangeRef.value = true;
  },
);

// 监听响应式变量的变化并触发事件
watch(systemPromptRef, (newValue) => {
  emit("update:systemPrompt", newValue);
});

watch(firstModelRef, (newValue) => {
  emit("update:firstModel", newValue);
});

watch(secondModelRef, (newValue) => {
  emit("update:secondModel", newValue);
});

watch(textToSpeechSwitchRef, (newValue) => {
  emit("update:textToSpeechSwitch", newValue);
});

watch(isChangeRef, (newValue) => {
  emit("update:isChange", newValue);
});
</script>

<template>
  <div role="menubar" aria-label="选项">
    <h1>选项栏</h1>
    <textarea v-model="systemPromptRef" placeholder="System Prompt:"></textarea>

    <select v-model="firstModelRef" aria-label="First Model:">
      <option
        v-for="option in props.modelList"
        :key="option.value"
        :value="option.value"
      >
        {{ option.label }}
      </option>
    </select>

    <select v-model="secondModelRef" aria-label="Second Model:">
      <option
        v-for="option in props.modelList"
        :key="option.value"
        :value="option.value"
      >
        {{ option.label }}
      </option>
    </select>

    <label>
      <input type="checkbox" v-model="textToSpeechSwitchRef" />
      语音朗读
    </label>
  </div>
</template>
