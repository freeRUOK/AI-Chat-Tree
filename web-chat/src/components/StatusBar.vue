<script setup>
// filename: StatusBar.vue
// Author: FreeRUOK <2651688427@qq.com>
// Date: 2025-03
// Description: AI-Chat-Tree的web前端
// 定义一个状态栏， 实时显示App状态
import { useMessageBus } from "../event-bus";
const { message } = useMessageBus();
</script>

<template>
  <div role="status" aria-live="polite" aria-atomic="true">
    <b v-if="message">{{ message }}</b>
  </div>
</template>
