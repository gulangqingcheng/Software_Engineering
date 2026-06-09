<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

defineProps<{
  title: string
  showProfileEntry?: boolean
  showQuestionsEntry?: boolean
}>()

const router = useRouter()
const authStore = useAuthStore()
const avatarTimestamp = ref(Date.now())
const userMenuVisible = ref(false)

watch(
  () => authStore.user?.avatar_url,
  () => {
    avatarTimestamp.value = Date.now()
  }
)

function avatarUrl() {
  const url = authStore.currentUser?.avatar_url
  if (!url) return ''
  return url.includes('?') ? `${url}&t=${avatarTimestamp.value}` : `${url}?t=${avatarTimestamp.value}`
}

function goBack() {
  router.push('/')
}

function goToProfile() {
  userMenuVisible.value = false
  router.push('/profile')
}

function goToMyQuestions() {
  userMenuVisible.value = false
  router.push('/my-questions')
}

function toggleUserMenu() {
  userMenuVisible.value = !userMenuVisible.value
}

function closeUserMenu() {
  userMenuVisible.value = false
}

function handleLogout() {
  userMenuVisible.value = false
  ElMessageBox.confirm('确定要退出登录吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(() => authStore.logout())
    .catch(() => {})
}

onMounted(() => {
  document.addEventListener('click', closeUserMenu)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', closeUserMenu)
})
</script>

<template>
  <header class="page-top-header">
    <div class="header-left">
      <el-button text @click="goBack">
        <el-icon><ArrowLeft /></el-icon>
        <span>返回对话</span>
      </el-button>
      <span class="header-divider">|</span>
      <span class="header-title">{{ title }}</span>
    </div>

    <div class="header-right">
      <div class="user-menu-wrap" @click.stop>
        <div class="user-info" @click="toggleUserMenu">
          <el-avatar :size="32" :src="avatarUrl()" :style="{ backgroundColor: '#534AB7' }">
            {{ authStore.currentUser?.username?.charAt(0)?.toUpperCase() || 'U' }}
          </el-avatar>
          <span class="user-name">{{ authStore.currentUser?.username || '用户' }}</span>
          <el-icon :size="12"><ArrowDown /></el-icon>
        </div>
        <div v-if="userMenuVisible" class="user-menu">
          <button v-if="showProfileEntry" class="user-menu-item" @click="goToProfile">
            <el-icon><User /></el-icon>
            <span>个人中心</span>
          </button>
          <button v-if="showQuestionsEntry" class="user-menu-item" @click="goToMyQuestions">
            <el-icon><Collection /></el-icon>
            <span>我的题库</span>
          </button>
          <button class="user-menu-item danger" @click="handleLogout">
            <el-icon><SwitchButton /></el-icon>
            <span>退出登录</span>
          </button>
        </div>
      </div>
    </div>
  </header>
</template>

<style scoped>
.page-top-header {
  height: var(--header-height);
  padding: 0 var(--spacing-lg);
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--color-subtle-line);
  background: var(--color-surface-input);
  box-shadow: 0 10px 30px rgba(9, 9, 11, 0.025);
  backdrop-filter: blur(16px);
  flex-shrink: 0;
  position: sticky;
  top: 0;
  z-index: 20;
}

.header-left,
.header-right,
.user-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.user-menu-wrap {
  position: relative;
}

.theme-toggle-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.theme-toggle-wrap::after {
  content: attr(data-tooltip);
  position: absolute;
  top: calc(100% + 8px);
  left: 50%;
  z-index: 120;
  min-width: 64px;
  padding: 5px 8px;
  border-radius: 7px;
  background: var(--color-text);
  color: var(--color-text-inverse);
  font-size: 12px;
  line-height: 1.2;
  text-align: center;
  white-space: nowrap;
  box-shadow: 0 10px 24px rgba(9, 9, 11, 0.14);
  opacity: 0;
  pointer-events: none;
  transform: translate(-50%, -2px);
  transition: opacity 0.16s ease, transform 0.16s ease;
}

.theme-toggle-wrap::before {
  content: "";
  position: absolute;
  top: calc(100% + 3px);
  left: 50%;
  z-index: 121;
  width: 8px;
  height: 8px;
  background: var(--color-text);
  opacity: 0;
  pointer-events: none;
  transform: translate(-50%, -2px) rotate(45deg);
  transition: opacity 0.16s ease, transform 0.16s ease;
}

.theme-toggle-wrap:hover::after {
  opacity: 1;
  transform: translate(-50%, 0);
}

.theme-toggle-wrap:hover::before {
  opacity: 1;
  transform: translate(-50%, 0) rotate(45deg);
}

.user-menu {
  position: absolute;
  top: calc(100% + 10px);
  right: 0;
  width: 148px;
  padding: 6px;
  background: var(--color-card);
  border: 1px solid var(--color-subtle-line);
  border-radius: 10px;
  box-shadow: 0 16px 38px rgba(9, 9, 11, 0.12);
  z-index: 100;
}

.user-menu::before {
  content: "";
  position: absolute;
  top: -6px;
  right: 22px;
  width: 10px;
  height: 10px;
  background: var(--color-card);
  border-left: 1px solid var(--color-subtle-line);
  border-top: 1px solid var(--color-subtle-line);
  transform: rotate(45deg);
}

.user-menu-item {
  position: relative;
  z-index: 1;
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 10px;
  border-radius: 8px;
  color: var(--color-text-secondary);
  font-size: var(--font-sm);
  text-align: left;
  background: transparent;
}

.user-menu-item:hover {
  color: var(--color-primary);
  background: var(--color-primary-lighter);
}

.user-menu-item.danger {
  border-top: 1px solid var(--color-border-light);
  margin-top: 4px;
  border-radius: 0 0 8px 8px;
}

.header-divider {
  color: var(--color-border);
}

.header-title {
  font-size: var(--font-lg);
  font-weight: 700;
  color: var(--color-text);
}

.user-info {
  padding: 5px 10px 5px 6px;
  border: 1px solid var(--color-subtle-line);
  border-radius: 999px;
  cursor: pointer;
  transition: background 0.2s, box-shadow 0.2s, transform 0.2s;
  background: var(--color-surface-glass-soft);
}

.user-info:hover {
  background: var(--color-surface-glass-strong);
  box-shadow: 0 10px 24px rgba(36, 38, 66, 0.08);
  transform: translateY(-1px);
}

.user-name {
  font-size: var(--font-sm);
  color: var(--color-text);
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

:global(.theme-dark) .page-top-header {
  background: linear-gradient(180deg, rgba(17, 19, 26, 0.92), rgba(9, 10, 15, 0.86));
  border-bottom-color: rgba(255, 255, 255, 0.08);
}

:global(.theme-dark) .user-info {
  background: rgba(22, 24, 34, 0.72);
  border-color: rgba(255, 255, 255, 0.08);
}

:global(.theme-dark) .user-menu {
  background: #161822;
  border-color: rgba(255, 255, 255, 0.08);
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.42);
}

:global(.theme-dark) .user-menu::before {
  background: #161822;
  border-color: rgba(255, 255, 255, 0.08);
}

@media (max-width: 768px) {
  .header-title,
  .user-name {
    display: none;
  }
}
</style>
