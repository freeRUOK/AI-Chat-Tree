<script setup>
defineProps({ file: File });
</script>
<template>
  <h1>{{ file.name }}</h1>
</template>
