<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { formatFileSize, getFileIcon } from '@/utils'

/**
 * 文件拖拽上传组件
 * 支持拖拽和点击上传，显示文件类型图标和上传进度
 */

const props = withDefaults(
  defineProps<{
    /** 接受的文件类型（MIME） */
    accept?: string
    /** 最大文件大小（字节） */
    maxSize?: number
    /** 上传中提示文字 */
    uploading?: boolean
    /** 上传进度（0-100） */
    progress?: number
    /** 已选文件名 */
    fileName?: string
  }>(),
  {
    accept: '',
    maxSize: 10 * 1024 * 1024, // 10MB
    uploading: false,
    progress: 0,
    fileName: '',
  }
)

const emit = defineEmits<{
  (e: 'upload', file: File): void
  (e: 'remove'): void
}>()

/** 文件输入框引用 */
const fileInputRef = ref<HTMLInputElement | null>(null)

/** 是否正在拖拽 */
const isDragOver = ref(false)

/** 文件图标名称 */
const fileIcon = computed(() => {
  if (!props.fileName) return 'Upload'
  return getFileIcon(props.fileName)
})

/**
 * 触发文件选择
 */
function triggerFileInput() {
  fileInputRef.value?.click()
}

/**
 * 处理文件选择
 */
function handleFileSelect(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) {
    validateAndUpload(file)
  }
  // 重置 input，允许重复选择同一文件
  input.value = ''
}

/**
 * 拖拽进入
 */
function handleDragEnter(e: DragEvent) {
  e.preventDefault()
  isDragOver.value = true
}

/**
 * 拖拽离开
 */
function handleDragLeave(e: DragEvent) {
  e.preventDefault()
  isDragOver.value = false
}

/**
 * 拖拽悬停
 */
function handleDragOver(e: DragEvent) {
  e.preventDefault()
}

/**
 * 文件放下
 */
function handleDrop(e: DragEvent) {
  e.preventDefault()
  isDragOver.value = false

  const file = e.dataTransfer?.files?.[0]
  if (file) {
    validateAndUpload(file)
  }
}

/**
 * 校验并上传文件
 */
function validateAndUpload(file: File) {
  // 校验文件类型
  if (props.accept) {
    const acceptTypes = props.accept.split(',').map((t) => t.trim())
    const fileExt = '.' + file.name.split('.').pop()?.toLowerCase()
    const isAccepted = acceptTypes.some(
      (type) =>
        type === file.type ||
        type === fileExt ||
        (type.endsWith('/*') && file.type.startsWith(type.replace('/*', '/')))
    )
    if (!isAccepted) {
      ElMessage.warning(`不支持的文件类型，请上传 ${props.accept} 格式的文件`)
      return
    }
  }

  // 校验文件大小
  if (file.size > props.maxSize) {
    ElMessage.warning(
      `文件大小不能超过 ${formatFileSize(props.maxSize)}，当前文件大小 ${formatFileSize(file.size)}`
    )
    return
  }

  emit('upload', file)
}

/**
 * 移除文件
 */
function handleRemove() {
  emit('remove')
}
</script>

<template>
  <div class="file-upload">
    <!-- 未上传：显示上传区域 -->
    <div v-if="!fileName && !uploading" class="upload-area-wrapper">
      <div
        class="upload-area"
        :class="{ 'drag-over': isDragOver }"
        @click="triggerFileInput"
        @dragenter="handleDragEnter"
        @dragleave="handleDragLeave"
        @dragover="handleDragOver"
        @drop="handleDrop"
      >
        <el-icon class="upload-icon" :size="32">
          <component :is="fileIcon" />
        </el-icon>
        <div class="upload-text">
          <span class="upload-link">点击上传</span>
          <span> 或拖拽文件到此处</span>
        </div>
        <div class="upload-hint" v-if="accept">
          支持 {{ accept }} 格式
        </div>
      </div>
      <input
        ref="fileInputRef"
        type="file"
        :accept="accept"
        class="file-input-hidden"
        @change="handleFileSelect"
      />
    </div>

    <!-- 上传中：显示进度 -->
    <div v-else-if="uploading" class="upload-progress">
      <div class="progress-header">
        <el-icon :size="20"><Loading class="is-loading" /></el-icon>
        <span class="progress-name">{{ fileName }}</span>
      </div>
      <el-progress
        :percentage="progress"
        :stroke-width="6"
        :show-text="true"
        class="progress-bar"
      />
      <span class="progress-status">上传中...</span>
    </div>

    <!-- 已上传：显示文件信息 -->
    <div v-else class="upload-result">
      <div class="result-info">
        <el-icon :size="24">
          <component :is="fileIcon" />
        </el-icon>
        <span class="result-name text-ellipsis">{{ fileName }}</span>
        <el-button
          type="danger"
          :icon="'Close'"
          circle
          size="small"
          @click.stop="handleRemove"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.file-upload {
  width: 100%;
}

/* ========== 上传区域 ========== */
.upload-area-wrapper {
  position: relative;
}

.upload-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-lg);
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-card);
  cursor: pointer;
  transition: all 0.3s ease;
}

.upload-area:hover,
.upload-area.drag-over {
  border-color: var(--color-primary);
  background: var(--color-primary-lighter);
}

.upload-icon {
  color: var(--color-text-placeholder);
  margin-bottom: var(--spacing-sm);
}

.drag-over .upload-icon {
  color: var(--color-primary);
}

.upload-text {
  font-size: var(--font-md);
  color: var(--color-text-secondary);
}

.upload-link {
  color: var(--color-primary);
  cursor: pointer;
}

.upload-link:hover {
  text-decoration: underline;
}

.upload-hint {
  font-size: var(--font-xs);
  color: var(--color-text-placeholder);
  margin-top: var(--spacing-xs);
}

.file-input-hidden {
  display: none;
}

/* ========== 上传进度 ========== */
.upload-progress {
  padding: var(--spacing-md);
  background: var(--color-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.progress-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
  color: var(--color-primary);
}

.progress-name {
  font-size: var(--font-sm);
  color: var(--color-text);
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.progress-bar {
  margin-bottom: var(--spacing-xs);
}

.progress-status {
  font-size: var(--font-xs);
  color: var(--color-text-placeholder);
}

/* ========== 上传结果 ========== */
.upload-result {
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.result-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  color: var(--color-success);
}

.result-name {
  flex: 1;
  font-size: var(--font-sm);
  color: var(--color-text);
  max-width: 200px;
}
</style>
