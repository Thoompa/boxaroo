<script setup lang="ts">
import AppHeader from '@/components/AppHeader.vue'
</script>

<template>
  <AppHeader />
  <div class="content">
    <VBtn onclick="console.log('hi')">Run</VBtn>
  </div>
</template>

<style scoped>
.content {
  justify-content: center;
  display: flex;
  margin-top: 100px;
}
</style>
