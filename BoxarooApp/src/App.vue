<script setup lang="ts">
import AppHeader from '@/components/AppHeader.vue'
</script>

<template>
  <AppHeader />
  <div class="content">
    <button onclick="console.log('hi')">Run</button>
  </div>
</template>

<style scoped>
.content {
  justify-content: center;
  display: flex;
  margin-top: 100px;
}
</style>
