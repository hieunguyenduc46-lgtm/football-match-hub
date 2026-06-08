<script setup>
import TheHeader from './components/TheHeader.vue'
</script>

<template>
  <TheHeader />
  <main class="container">
    <router-view v-slot="{ Component }">
      <keep-alive>
        <component :is="Component" />
      </keep-alive>
    </router-view>
  </main>
</template>
