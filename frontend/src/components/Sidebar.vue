<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import { useChatStore } from '@/stores/chat'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { formatRelativeTime } from '@/utils'

const router = useRouter()
const route = useRoute()
const chatStore = useChatStore()
const authStore = useAuthStore()
const appStore = useAppStore()

const sidebarWidth = computed(() =>
  appStore.sidebarCollapsed ? '64px' : 'var(--sidebar-width)'
)

async function handleNewChat() {
  try {
    await chatStore.createConversation('新对话', 'general')
  } catch {
    // Keep the UI quiet; API errors are surfaced elsewhere.
  }
}

function handleSelectConversation(conversationId: number | string) {
  chatStore.switchConversation(conversationId)
}

function goToAdmin() {
  router.push('/admin')
}

function goToInterview() {
  router.push('/interview')
}

const isInAdmin = computed(() => route.path.startsWith('/admin'))
const isInInterview = computed(() => route.path.startsWith('/interview'))

async function handleDeleteConversation(e: Event, conversationId: number | string) {
  e.stopPropagation()
  try {
    await ElMessageBox.confirm('确定要删除这条对话记录吗？删除后不可恢复。', '删除对话', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await chatStore.deleteConversation(conversationId)
    ElMessage.success('对话已删除')
  } catch {
    // User canceled or deletion failed.
  }
}

function plainPreview(text?: string | null) {
  if (!text) return '暂无消息'
  return text
    .replace(/```[\s\S]*?```/g, '代码片段')
    .replace(/[#>*_`~\[\]()+|!-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim() || '暂无消息'
}
</script>

<template>
  <aside class="sidebar" :style="{ width: sidebarWidth }">
    <div v-if="!appStore.sidebarCollapsed" class="sidebar-header">
      <el-button
        type="primary"
        :icon="'Plus'"
        class="new-chat-btn"
        @click="handleNewChat()"
      >
        新建对话
      </el-button>
    </div>

    <div v-if="!appStore.sidebarCollapsed" class="conversations-section">
      <div class="section-title">对话历史</div>

      <div class="conversations-list">
        <div v-if="chatStore.conversations.length === 0" class="empty-state">
          <el-icon :size="24" color="#9E9D9A"><ChatLineRound /></el-icon>
          <span>暂无对话记录</span>
        </div>

        <div
          v-for="conv in chatStore.conversations"
          :key="conv.id"
          class="conversation-item"
          :class="{ active: conv.id === chatStore.currentConversationId }"
          @click="handleSelectConversation(conv.id)"
        >
          <div class="conv-header flex-between">
            <span class="conv-title text-ellipsis">{{ conv.title }}</span>
            <div class="conv-header-actions">
              <span class="conv-time">{{ formatRelativeTime(conv.updated_at) }}</span>
              <el-icon
                class="conv-delete-btn"
                :size="14"
                @click="handleDeleteConversation($event, conv.id)"
              ><Delete /></el-icon>
            </div>
          </div>
          <div class="conv-preview text-ellipsis">
            {{ plainPreview(conv.last_message) }}
          </div>
          <div class="conv-meta">
            <span class="conv-count">共 {{ conv.message_count }} 条</span>
          </div>
        </div>
      </div>
    </div>

    <div class="sidebar-footer">
      <div
        v-if="!appStore.sidebarCollapsed"
        class="footer-item"
        :class="{ active: isInInterview }"
        @click="goToInterview"
      >
        <el-icon :size="18"><UserFilled /></el-icon>
        <span>AI面试</span>
      </div>

      <div
        v-if="authStore.isAdmin && !appStore.sidebarCollapsed"
        class="footer-item"
        :class="{ active: isInAdmin }"
        @click="goToAdmin"
      >
        <el-icon :size="18"><Setting /></el-icon>
        <span>后台管理</span>
      </div>

      <div class="footer-item" @click="appStore.toggleSidebar()">
        <el-icon :size="18">
          <Fold v-if="!appStore.sidebarCollapsed" />
          <Expand v-else />
        </el-icon>
        <span v-if="!appStore.sidebarCollapsed">收起</span>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  height: 100%;
  min-height: 0;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--color-card);
  border-right: 1px solid var(--color-border-light);
  transition: width 0.3s ease;
  overflow: hidden;
}

.sidebar-header {
  padding: var(--spacing-md);
  border-bottom: 1px solid var(--color-border-light);
}

.new-chat-btn {
  width: 100%;
  height: 44px;
  border: none;
  border-radius: 12px;
  background: var(--theme-gradient);
  box-shadow: 0 12px 24px rgba(83, 74, 183, 0.18);
}

.conversations-section {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.section-title {
  font-size: var(--font-xs);
  font-weight: 600;
  color: var(--color-text-placeholder);
  padding: var(--spacing-sm) var(--spacing-md);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.conversations-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 var(--spacing-sm);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-xl);
  color: var(--color-text-placeholder);
  font-size: var(--font-sm);
}

.conversation-item {
  padding: 9px 11px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
  margin-bottom: 2px;
  border: 1px solid transparent;
}

.conversation-item:hover {
  background: var(--color-bg);
}

.conversation-item.active {
  background: var(--color-primary-lighter);
}

:global(.theme-dark) .conversation-item:hover {
  background: rgba(255, 255, 255, 0.035);
}

:global(.theme-dark) .conversation-item.active {
  background: rgba(79, 70, 229, 0.16);
  border-color: rgba(99, 102, 241, 0.22);
}

:global(.theme-dark) .conversation-item.active .conv-title {
  color: #F3F4F6;
}

:global(.theme-dark) .conversation-item.active .conv-preview,
:global(.theme-dark) .conversation-item.active .conv-count,
:global(.theme-dark) .conversation-item.active .conv-time {
  color: #A7AFBE;
}

.conv-header {
  margin-bottom: 4px;
}

.conv-title {
  font-size: var(--font-sm);
  font-weight: 500;
  color: var(--color-text);
  max-width: 70%;
}

.conv-time {
  font-size: 11px;
  color: var(--color-text-placeholder);
  flex-shrink: 0;
}

.conv-header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.conv-delete-btn {
  opacity: 0;
  cursor: pointer;
  color: var(--color-text-placeholder);
  transition: all 0.2s;
  padding: 2px;
  border-radius: 4px;
}

.conv-delete-btn:hover {
  color: var(--color-danger);
  background: rgba(245, 108, 108, 0.1);
}

.conversation-item:hover .conv-delete-btn {
  opacity: 1;
}

.conv-preview {
  font-size: var(--font-xs);
  color: var(--color-text-secondary);
  margin-bottom: 4px;
}

.conv-meta {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.conv-count {
  font-size: 11px;
  color: var(--color-text-placeholder);
}

.sidebar-footer {
  padding: var(--spacing-sm) 0;
  border-top: 1px solid var(--color-border-light);
  margin-top: auto;
}

.footer-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 8px var(--spacing-md);
  cursor: pointer;
  transition: all 0.2s;
  color: var(--color-text-secondary);
  font-size: var(--font-sm);
}

.footer-item:hover,
.footer-item.active {
  background: var(--color-bg);
  color: var(--color-primary);
}
</style>
