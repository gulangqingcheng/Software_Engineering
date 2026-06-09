<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'

const authStore = useAuthStore()
const appStore = useAppStore()
const authReady = ref(true)

onMounted(async () => {
  authStore.initAuth()
  if (authStore.isLoggedIn) {
    authStore.fetchUserInfo().catch(() => {
      authStore.logout()
    })
  }
})
</script>

<template>
  <div class="app-container" :class="appStore.isDark ? 'theme-dark' : 'theme-light'">
    <div v-if="!authReady" class="app-loading">
      <img src="/logo.png" alt="智能面试助手" />
      <span>正在加载...</span>
    </div>
    <router-view v-else />
  </div>
</template>

<style scoped>
.app-container {
  width: 100vw;
  height: 100vh;
  min-width: 100vw;
  min-height: 100vh;
  overflow: hidden;
  background: var(--color-bg);
}

.app-loading {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--color-text-secondary);
}

.app-loading img {
  width: 56px;
  height: 56px;
  border-radius: 12px;
}
</style>
