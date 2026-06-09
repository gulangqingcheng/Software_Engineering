<script setup lang="ts">
import { ref, onMounted, nextTick, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useChatStore } from '@/stores/chat'
import Sidebar from '@/components/Sidebar.vue'
import AppHeader from '@/components/AppHeader.vue'
import ChatMessage from '@/components/ChatMessage.vue'
import { getArtifactsApi, previewArtifactApi } from '@/api/chat'
import type { ChatArtifact } from '@/types'

interface FeatureTag {
  key: string
  label: string
  icon: string
  accept: string
}

const chatStore = useChatStore()
const messageListRef = ref<HTMLElement | null>(null)
const inputText = ref('')
const resumeInputRef = ref<HTMLInputElement | null>(null)
const recordingInputRef = ref<HTMLInputElement | null>(null)
const questionResumeInputRef = ref<HTMLInputElement | null>(null)
const isDragOver = ref(false)
const dragCounter = ref(0)
const artifacts = ref<ChatArtifact[]>([])
const artifactsLoading = ref(false)
const selectedArtifact = ref<ChatArtifact | null>(null)
const artifactPreview = ref('')
const previewLoading = ref(false)
const artifactsCollapsed = ref(false)

const featureTags: FeatureTag[] = [
  { key: 'resume', label: '简历评估', icon: 'Document', accept: '.pdf,.doc,.docx,.jpg,.jpeg,.png' },
  { key: 'recording', label: '录音分析', icon: 'Microphone', accept: '.mp3,.wav,.m4a,.aac,.ogg,.flac,.mp4,.avi,.mov' },
  { key: 'question', label: '面试题生成', icon: 'EditPen', accept: '.pdf,.doc,.docx,.jpg,.jpeg,.png' },
]

const activeTag = computed(() => chatStore.activeAgentType)

function scrollToBottom() {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight
    }
  })
}

function handleTagClick(tag: FeatureTag) {
  if (activeTag.value === tag.key) {
    chatStore.activeAgentType = 'general'
    return
  }

  chatStore.activeAgentType = tag.key
  if (tag.key === 'resume') {
    resumeInputRef.value?.click()
  } else if (tag.key === 'recording') {
    recordingInputRef.value?.click()
  } else if (tag.key === 'question') {
    questionResumeInputRef.value?.click()
  }
}

async function handleResumeSelect(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files?.length) {
    await handleFilesSelected(Array.from(input.files), 'resume')
  }
  input.value = ''
}

async function handleRecordingSelect(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files?.length) {
    await handleFilesSelected(Array.from(input.files), 'recording')
  }
  input.value = ''
}

async function handleQuestionResumeSelect(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files?.length) {
    await handleFilesSelected(Array.from(input.files), 'question')
  }
  input.value = ''
}

async function handleFilesSelected(files: File[], agentType: string) {
  try {
    chatStore.activeAgentType = agentType
    for (const file of files) {
      await chatStore.addPendingFile(file)
    }
    const message = files.length === 1
      ? `${files[0].name} 上传成功，可输入补充文字后点击发送`
      : `${files.length} 个文件上传成功，可输入补充文字后点击发送`
    ElMessage.success(message)
  } catch {
    ElMessage.error('文件上传失败，请重试')
  }
}

function pendingFileIcon(fileName: string) {
  const ext = fileName.split('.').pop()?.toLowerCase() || ''
  if (['mp3', 'wav', 'm4a', 'aac', 'ogg', 'flac', 'mp4', 'avi', 'mov', 'mkv', 'webm'].includes(ext)) {
    return 'Headset'
  }
  return 'Document'
}

async function fetchArtifacts() {
  if (!chatStore.currentConversationId) {
    artifacts.value = []
    selectedArtifact.value = null
    artifactPreview.value = ''
    return
  }
  artifactsLoading.value = true
  try {
    const res = await getArtifactsApi(chatStore.currentConversationId)
    artifacts.value = res.data || []
  } finally {
    artifactsLoading.value = false
  }
}

async function previewArtifact(artifact: ChatArtifact) {
  if (!chatStore.currentConversationId) return
  selectedArtifact.value = artifact
  previewLoading.value = true
  try {
    artifactPreview.value = await previewArtifactApi(chatStore.currentConversationId, artifact.name)
  } finally {
    previewLoading.value = false
  }
}

async function downloadArtifact(artifact: ChatArtifact) {
  const token = localStorage.getItem('access_token')
  const response = await fetch(encodeURI(artifact.download_url), {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  })
  if (!response.ok) {
    ElMessage.error('下载失败，请重试')
    return
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = artifact.name
  link.click()
  URL.revokeObjectURL(url)
}

function artifactIcon(type: string) {
  if (type === 'txt') return 'Document'
  if (type === 'docx') return 'Tickets'
  if (type === 'md') return 'Memo'
  return 'Document'
}

function toggleArtifactsPanel() {
  artifactsCollapsed.value = !artifactsCollapsed.value
  if (artifactsCollapsed.value) {
    selectedArtifact.value = null
    artifactPreview.value = ''
  }
}

async function handleSend() {
  const content = inputText.value.trim()
  if ((!content && chatStore.pendingFiles.length === 0) || chatStore.isSending) return

  const agentType = chatStore.activeAgentType || 'general'
  const fileUrls = chatStore.pendingFiles.map((file) => file.fileUrl)
  inputText.value = ''

  try {
    if (!chatStore.currentConversationId) {
      const title = agentType === 'resume' ? '简历评估'
        : agentType === 'recording' ? '录音分析'
          : agentType === 'question' ? '面试题生成'
            : '新对话'
      await chatStore.createConversation(title, agentType)
    }

    await chatStore.streamChat(content || '分析上传的文件', agentType, fileUrls)
    await fetchArtifacts()
    scrollToBottom()
  } catch {
    ElMessage.error('发送失败，请重试')
  }
}

function handleKeyDown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

function autoResizeTextarea(e: Event) {
  const target = e.target as HTMLTextAreaElement
  target.style.height = 'auto'
  target.style.height = `${Math.min(target.scrollHeight, 120)}px`
}

function handleDragEnter(e: DragEvent) {
  e.preventDefault()
  dragCounter.value++
  if (dragCounter.value === 1) isDragOver.value = true
}

function handleDragLeave(e: DragEvent) {
  e.preventDefault()
  dragCounter.value--
  if (dragCounter.value <= 0) {
    dragCounter.value = 0
    isDragOver.value = false
  }
}

function handleDragOver(e: DragEvent) {
  e.preventDefault()
}

async function handleDrop(e: DragEvent) {
  e.preventDefault()
  dragCounter.value = 0
  isDragOver.value = false
  const files = e.dataTransfer?.files
  if (!files || files.length === 0) return
  chatStore.activeAgentType = 'general'
  await handleFilesSelected(Array.from(files), 'general')
}

watch(() => chatStore.messages.length, scrollToBottom)
watch(() => chatStore.agentStatus, scrollToBottom)
watch(() => chatStore.currentConversationId, fetchArtifacts)

onMounted(() => {
  chatStore.fetchConversations()
  fetchArtifacts()
})
</script>

<template>
  <div class="chat-layout" @dragenter="handleDragEnter" @dragleave="handleDragLeave" @dragover="handleDragOver" @drop="handleDrop">
    <AppHeader />

    <div class="chat-body">
      <Sidebar />

      <div class="chat-main">
        <div class="chat-content">
          <div v-if="!chatStore.currentConversationId" class="empty-state">
            <div class="empty-icon">
              <el-icon :size="64" color="#9E9D9A"><ChatDotRound /></el-icon>
            </div>
            <h2 class="empty-title">智能面试助手</h2>
            <p class="empty-desc">选择功能标签或发送消息开始对话</p>
            <div class="feature-tags-inline">
              <div
                v-for="tag in featureTags"
                :key="tag.key"
                class="feature-tag-card"
                @click="handleTagClick(tag)"
              >
                <el-icon :size="28" color="#534AB7"><component :is="tag.icon" /></el-icon>
                <span class="tag-label">{{ tag.label }}</span>
              </div>
            </div>
          </div>

          <div v-else ref="messageListRef" class="message-list">
            <div v-if="chatStore.messages.length === 0 && !chatStore.isSending" class="empty-conversation">
              <p>发送消息开始对话，或使用下方功能标签</p>
            </div>

            <template v-for="msg in chatStore.sortedMessages" :key="msg.id">
              <ChatMessage :message="msg" />
            </template>

            <div v-if="chatStore.agentStatus" class="agent-status-area">
              <div class="agent-status-card">
                <el-icon :size="16" class="is-loading" color="#534AB7"><Loading /></el-icon>
                <span class="agent-status-text">{{ chatStore.agentStatus.agent_name }} - {{ chatStore.agentStatus.message || '处理中...' }}</span>
                <el-progress
                  v-if="chatStore.agentStatus.progress"
                  :percentage="chatStore.agentStatus.progress"
                  :stroke-width="4"
                  :show-text="false"
                  style="width: 80px"
                />
              </div>
            </div>
          </div>
        </div>

        <div class="chat-input-area">
          <div v-if="isDragOver" class="drag-overlay">
            <el-icon :size="48" color="#534AB7"><Upload /></el-icon>
            <span>释放文件上传</span>
          </div>

          <div v-if="chatStore.pendingFiles.length > 0" class="pending-files">
            <div
              v-for="(pf, index) in chatStore.pendingFiles"
              :key="index"
              class="pending-file-item"
            >
              <el-icon :size="18" color="#534AB7">
                <component :is="pendingFileIcon(pf.fileName)" />
              </el-icon>
              <span class="pending-file-name text-ellipsis">{{ pf.fileName }}</span>
              <el-icon
                :size="16"
                class="pending-file-remove"
                @click="chatStore.removePendingFile(index)"
              ><Close /></el-icon>
            </div>
          </div>

          <div class="feature-tags">
            <div
              v-for="tag in featureTags"
              :key="tag.key"
              class="feature-tag"
              :class="{ active: activeTag === tag.key }"
              @click="handleTagClick(tag)"
            >
              <el-icon :size="14"><component :is="tag.icon" /></el-icon>
              <span>{{ tag.label }}</span>
            </div>
          </div>

          <div class="input-row">
            <textarea
              v-model="inputText"
              id="chat-input"
              name="chat-input"
              class="chat-textarea"
              :placeholder="activeTag === 'question' ? '输入岗位方向，生成面试题...' : '输入您的问题，按 Enter 发送，Shift+Enter 换行...'"
              rows="1"
              :disabled="chatStore.isSending"
              @keydown="handleKeyDown"
              @input="autoResizeTextarea"
            ></textarea>
            <div class="control-row">
              <div class="input-tools">
                <el-tooltip content="上传简历（PDF/Word/图片）" placement="top">
                  <el-button
                    :icon="'Document'"
                    circle
                    :type="activeTag === 'resume' ? 'primary' : 'default'"
                    @click="resumeInputRef?.click()"
                  />
                </el-tooltip>
                <el-tooltip content="上传录音（音频/视频）" placement="top">
                  <el-button
                    :icon="'Microphone'"
                    circle
                    :type="activeTag === 'recording' ? 'primary' : 'default'"
                    @click="recordingInputRef?.click()"
                  />
                </el-tooltip>
              </div>
              <el-button
                type="primary"
                :icon="'Promotion'"
                :disabled="(!inputText.trim() && chatStore.pendingFiles.length === 0) || chatStore.isSending"
                :loading="chatStore.isSending"
                @click="handleSend"
              >
                发送
              </el-button>
            </div>
          </div>

          <input
            ref="resumeInputRef"
            type="file"
            accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
            multiple
            style="display: none"
            @change="handleResumeSelect"
          />
          <input
            ref="recordingInputRef"
            type="file"
            accept=".mp3,.wav,.m4a,.aac,.ogg,.flac,.mp4,.avi,.mov"
            multiple
            style="display: none"
            @change="handleRecordingSelect"
          />
          <input
            ref="questionResumeInputRef"
            type="file"
            accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
            multiple
            style="display: none"
            @change="handleQuestionResumeSelect"
          />
        </div>
      </div>

      <aside class="artifacts-panel" :class="{ collapsed: artifactsCollapsed }">
        <div class="artifacts-header">
          <el-icon v-if="artifactsCollapsed" :size="18"><Folder /></el-icon>
          <span>产物</span>
          <el-button
            v-if="!artifactsCollapsed"
            :icon="'Refresh'"
            text
            circle
            :loading="artifactsLoading"
            @click="fetchArtifacts"
          />
        </div>
        <div v-if="!artifactsCollapsed && artifacts.length === 0" class="artifacts-empty">
          暂无产物
        </div>
        <div v-else-if="!artifactsCollapsed" class="artifacts-list">
          <div
            v-for="artifact in artifacts"
            :key="artifact.name"
            class="artifact-row"
            :class="{ active: selectedArtifact?.name === artifact.name }"
            @click="previewArtifact(artifact)"
          >
            <el-icon :size="15"><component :is="artifactIcon(artifact.type)" /></el-icon>
            <span class="artifact-name text-ellipsis">{{ artifact.name }}</span>
            <el-button
              :icon="'Download'"
              text
              circle
              size="small"
              @click.stop="downloadArtifact(artifact)"
            />
          </div>
        </div>
        <div class="artifacts-footer">
          <div class="artifacts-footer-item" @click="toggleArtifactsPanel">
            <el-icon :size="18">
              <Fold v-if="!artifactsCollapsed" />
              <Expand v-else />
            </el-icon>
            <span v-if="!artifactsCollapsed">收起</span>
          </div>
        </div>
      </aside>

      <aside v-if="selectedArtifact && !artifactsCollapsed" class="artifact-preview-panel">
        <div class="preview-header">
          <span class="text-ellipsis">{{ selectedArtifact.name }}</span>
          <el-button :icon="'Close'" text circle @click="selectedArtifact = null; artifactPreview = ''" />
        </div>
        <div v-loading="previewLoading" class="preview-content">
          <pre>{{ artifactPreview }}</pre>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.chat-layout {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background:
    linear-gradient(135deg, var(--color-tech-glow-primary), var(--color-tech-glow-accent) 42%, transparent 72%),
    var(--color-bg);
}

.chat-body {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  background:
    linear-gradient(var(--color-tech-grid-primary) 1px, transparent 1px),
    linear-gradient(90deg, var(--color-tech-grid-accent) 1px, transparent 1px);
  background-size: 28px 28px;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
  background:
    radial-gradient(circle at 50% 0, var(--color-tech-glow-primary), transparent 36%),
    var(--color-bg);
}

.artifacts-panel {
  width: 260px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--color-surface-glass);
  border-left: 1px solid var(--color-subtle-line);
  box-shadow: -12px 0 28px rgba(9, 9, 11, 0.025);
  backdrop-filter: blur(14px);
  transition: width 0.3s ease;
  overflow: hidden;
}

.artifacts-panel.collapsed {
  width: 64px;
}

.artifacts-header,
.preview-header {
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 14px;
  border-bottom: 1px solid var(--color-subtle-line);
  font-size: var(--font-md);
  font-weight: 600;
  color: var(--color-text);
  background: var(--color-surface-input);
}

.artifacts-panel.collapsed .artifacts-header {
  justify-content: center;
  padding: 0;
}

.artifacts-panel.collapsed .artifacts-header span {
  display: none;
}

.artifacts-empty {
  padding: var(--spacing-lg);
  color: var(--color-text-placeholder);
  font-size: var(--font-sm);
  text-align: center;
}

.artifacts-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.artifact-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  padding: 7px 9px;
  border: 1px solid transparent;
  border-radius: 10px;
  cursor: pointer;
  color: var(--color-text-secondary);
  transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease;
}

.artifact-row:hover,
.artifact-row.active {
  background: rgba(83, 74, 183, 0.08);
  border-color: rgba(83, 74, 183, 0.14);
  color: var(--color-primary);
  transform: translateX(-2px);
}

.artifact-name {
  flex: 1;
  font-size: var(--font-sm);
}

.artifacts-footer {
  padding: var(--spacing-sm) 0;
  border-top: 1px solid var(--color-border-light);
  margin-top: auto;
}

.artifacts-footer-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 8px var(--spacing-md);
  cursor: pointer;
  transition: all 0.2s;
  color: var(--color-text-secondary);
  font-size: var(--font-sm);
}

.artifacts-panel.collapsed .artifacts-footer-item {
  justify-content: center;
  padding: 8px 0;
}

.artifacts-footer-item:hover {
  background: var(--color-bg);
  color: var(--color-primary);
}

.artifact-preview-panel {
  width: 360px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--color-surface-glass-strong);
  border-left: 1px solid var(--color-subtle-line);
  backdrop-filter: blur(14px);
}

.preview-content {
  flex: 1;
  overflow: auto;
  padding: 16px;
  background:
    linear-gradient(var(--color-tech-grid-primary) 1px, transparent 1px),
    var(--color-card);
  background-size: 24px 24px;
}

.preview-content pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: var(--font-sm);
  line-height: 1.7;
  color: var(--color-text);
}

.chat-content {
  flex: 1;
  overflow: hidden;
  background: transparent;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: var(--spacing-md);
}

.empty-icon {
  opacity: 0.4;
}

.empty-title {
  font-size: var(--font-title);
  font-weight: 700;
  color: var(--color-text);
}

.empty-desc {
  font-size: var(--font-md);
  color: var(--color-text-secondary);
}

.feature-tags-inline {
  display: flex;
  gap: var(--spacing-lg);
  margin-top: var(--spacing-md);
}

.feature-tag-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-lg) var(--spacing-xl);
  border: 1px solid var(--color-subtle-line);
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
  background: var(--color-surface-input);
  box-shadow: 0 10px 30px rgba(9, 9, 11, 0.04);
  min-width: 120px;
}

.feature-tag-card:hover {
  border-color: var(--color-primary);
  background: var(--color-primary-lighter);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.tag-label {
  font-size: var(--font-sm);
  font-weight: 500;
  color: var(--color-text);
}

.empty-conversation {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-text-placeholder);
  font-size: var(--font-md);
}

.message-list {
  height: 100%;
  overflow-y: auto;
  padding: 22px 0 18px;
}

.agent-status-area {
  padding: 0 var(--spacing-md) var(--spacing-sm);
}

.agent-status-card {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 10px 16px;
  background: var(--color-surface-input);
  border: 1px solid var(--color-subtle-line);
  border-radius: 999px;
  box-shadow: 0 10px 24px rgba(83, 74, 183, 0.08);
  font-size: var(--font-sm);
  color: var(--color-primary);
}

.agent-status-text {
  flex: 1;
}

.chat-input-area {
  position: relative;
  margin: 0 28px 20px;
  padding: 10px 14px 12px;
  background: var(--color-surface-input);
  border: 1px solid var(--color-subtle-line);
  border-radius: 26px;
  box-shadow:
    0 10px 30px rgba(9, 9, 11, 0.04),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(18px);
}

.chat-input-area::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  border-radius: inherit;
  background: linear-gradient(90deg, rgba(79, 70, 229, 0.14), rgba(6, 182, 212, 0.12), rgba(79, 70, 229, 0.08));
  opacity: 0.2;
  mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  padding: 1px;
  -webkit-mask-composite: xor;
  mask-composite: exclude;
}

.drag-overlay {
  position: absolute;
  inset: 0;
  background: rgba(83, 74, 183, 0.08);
  border: 2px dashed var(--color-primary);
  border-radius: 26px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  z-index: 10;
  color: var(--color-primary);
  font-size: var(--font-md);
  font-weight: 500;
}

.pending-files {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  margin-bottom: 10px;
}

.pending-file-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  min-height: 30px;
  background: var(--color-primary-lighter);
  border: 1px solid rgba(79, 70, 229, 0.16);
  border-radius: 999px;
  font-size: var(--font-sm);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.75);
}

.pending-file-name {
  max-width: 160px;
  color: var(--color-text);
}

.pending-file-remove {
  cursor: pointer;
  color: var(--color-text-placeholder);
  transition: color 0.2s;
}

.pending-file-remove:hover {
  color: var(--color-danger);
}

.feature-tags {
  display: flex;
  gap: 10px;
  margin-bottom: 8px;
  overflow-x: auto;
  padding-bottom: 2px;
}

.feature-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  cursor: pointer;
  font-size: var(--font-sm);
  color: var(--color-text-secondary);
  transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
  background: var(--color-bg-dark);
  user-select: none;
  box-shadow: none;
  white-space: nowrap;
}

.feature-tag:hover {
  border-color: rgba(79, 70, 229, 0.3);
  color: var(--color-primary);
  background: var(--color-primary-lighter);
  transform: translateY(-1px);
}

.feature-tag.active {
  border-color: rgba(79, 70, 229, 0.3);
  color: #fff;
  background: var(--theme-gradient);
  box-shadow: 0 10px 22px rgba(83, 74, 183, 0.2);
}

.input-row {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 5px;
  padding: 8px;
  background: var(--color-surface-glass-soft);
  border: 1px solid var(--color-subtle-line);
  border-radius: 20px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.85);
}

.input-tools {
  display: flex;
  gap: 6px;
  align-items: center;
}

.input-tools :deep(.el-button) {
  width: 30px;
  height: 30px;
  border-color: var(--color-border);
  background: var(--color-surface-glass-strong);
  box-shadow: 0 3px 9px rgba(9, 9, 11, 0.03);
  font-size: 12px;
}

.input-tools :deep(.el-button .el-icon) {
  font-size: 14px;
}

.control-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.chat-textarea {
  flex: 1;
  resize: none;
  border: none;
  border-radius: 16px;
  padding: 8px 12px;
  font-size: var(--font-md);
  line-height: 1.5;
  color: var(--color-text);
  background: transparent;
  outline: none;
  max-height: 120px;
  min-height: 38px;
  font-family: inherit;
  transition: background 0.2s;
}

.chat-textarea:focus {
  background: var(--color-surface-glass-soft);
}

.chat-textarea:disabled {
  background: var(--color-bg-dark);
  cursor: not-allowed;
}

.chat-textarea::placeholder {
  color: var(--color-text-placeholder);
}

.input-row :deep(.el-button--primary) {
  min-width: 62px;
  height: 30px;
  border-radius: 11px;
  background: var(--theme-gradient);
  border: none;
  box-shadow: 0 8px 16px rgba(83, 74, 183, 0.2);
  font-size: 12px;
}

.input-row :deep(.el-button--primary .el-icon) {
  font-size: 13px;
}

.input-tools :deep(.el-button.is-circle) {
  width: 30px;
  min-width: 30px;
  height: 30px;
  padding: 0;
  border-radius: 50%;
}

@media (max-width: 960px) {
  .chat-input-area {
    margin: 0 14px 14px;
  }

  .artifacts-panel {
    width: 220px;
  }

  .artifact-preview-panel {
    width: 300px;
  }
}

:global(.theme-dark) .chat-layout {
  background:
    linear-gradient(135deg, rgba(79, 70, 229, 0.12), rgba(6, 182, 212, 0.08) 42%, transparent 72%),
    var(--color-bg);
}

:global(.theme-dark) .chat-body {
  background:
    linear-gradient(rgba(99, 102, 241, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(6, 182, 212, 0.03) 1px, transparent 1px);
  background-size: 28px 28px;
}

:global(.theme-dark) .chat-main {
  background:
    radial-gradient(circle at 50% 0, rgba(79, 70, 229, 0.16), transparent 36%),
    linear-gradient(180deg, rgba(9, 10, 15, 0.84), rgba(9, 10, 15, 0.94));
}

:global(.theme-dark) .chat-input-area,
:global(.theme-dark) .artifacts-panel,
:global(.theme-dark) .artifact-preview-panel {
  background: rgba(22, 24, 34, 0.75);
  border-color: rgba(148, 163, 184, 0.12);
  box-shadow: 0 -8px 28px rgba(0, 0, 0, 0.38);
  backdrop-filter: blur(14px);
}

:global(.theme-dark) .chat-input-area::before {
  display: none;
}

:global(.theme-dark) .artifacts-header,
:global(.theme-dark) .preview-header,
:global(.theme-dark) .preview-content {
  background: rgba(17, 19, 26, 0.82);
  border-color: rgba(255, 255, 255, 0.08);
}

:global(.theme-dark) .feature-tag-card,
:global(.theme-dark) .agent-status-card {
  background: rgba(22, 24, 34, 0.72);
  border-color: rgba(255, 255, 255, 0.08);
  box-shadow: var(--shadow-md);
}

:global(.theme-dark) .input-row,
:global(.theme-dark) .feature-tag,
:global(.theme-dark) .pending-file-item {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(148, 163, 184, 0.12);
  color: var(--color-text-secondary);
  box-shadow: none;
}

:global(.theme-dark) .input-tools :deep(.el-button) {
  background: rgba(22, 24, 34, 0.84);
  border-color: rgba(255, 255, 255, 0.08);
}

:global(.theme-dark) .chat-textarea:focus {
  background: rgba(255, 255, 255, 0.04);
}

:global(.theme-dark) .chat-textarea:disabled {
  background: rgba(17, 19, 26, 0.84);
}
</style>
