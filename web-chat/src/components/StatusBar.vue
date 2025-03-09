<script setup>
import { useMessageBus } from "../event-bus";
const { message } = useMessageBus();
</script>

<template>
  <div role="status" aria-live="polite" aria-atomic="true">
    <b v-if="message">{{ message }}</b>
  </div>
</template>
