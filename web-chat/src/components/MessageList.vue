<script setup>
// filename: MessageList.vue
// Author: FreeRUOK <2651688427@qq.com>
// Date: 2025-03
// Description: AI-Chat-Tree的web前端
// 消息列表的vue组件

import Message from "./Message.vue";
import MessageCollection from "../models/message-collection";
defineProps({ messageCollection: MessageCollection });
</script>

<template>
  <h1>message list</h1>
  <ul>
    <li>
      <Message v-for="item in messageCollection.messages" :message="item" />
    </li>
  </ul>
</template>
