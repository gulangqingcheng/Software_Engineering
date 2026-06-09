<script setup lang="ts">
import { computed } from 'vue'

/**
 * Agent 执行进度组件
 * 显示当前执行的 Agent 名称、进度条动画、状态文字
 */

const props = withDefaults(
  defineProps<{
    /** Agent 状态 */
    status: 'processing' | 'completed' | 'failed'
    /** 进度（0-100） */
    progress: number
    /** Agent 名称 */
    agentName: string
    /** 提示消息 */
    message?: string
  }>(),
  {
    message: '',
  }
)

/** 状态文字 */
const statusText = computed(() => {
  switch (props.status) {
    case 'processing':
      return '处理中...'
    case 'completed':
      return '已完成'
    case 'failed':
      return '失败'
    default:
      return ''
  }
})

/** 状态图标 */
const statusIcon = computed(() => {
  switch (props.status) {
    case 'processing':
      return 'Loading'
    case 'completed':
      return 'CircleCheck'
    case 'failed':
      return 'CircleClose'
    default:
      return ''
  }
})

/** 进度条颜色 */
const progressColor = computed(() => {
  switch (props.status) {
    case 'completed':
      return '#0F6E56'
    case 'failed':
      return '#A32D2D'
    default:
      return '#534AB7'
  }
})
</script>

<template>
  <div class="progress-status" :class="`status-${status}`">
    <div class="progress-header flex-between">
      <div class="flex gap-sm">
        <el-icon :size="16" :class="{ 'is-loading': status === 'processing' }">
          <component :is="statusIcon" />
        </el-icon>
        <span class="agent-name">{{ agentName }}</span>
      </div>
      <span class="status-text" :class="`text-${status}`">{{ statusText }}</span>
    </div>

    <!-- 进度条 -->
    <el-progress
      :percentage="Math.min(progress, 100)"
      :color="progressColor"
      :stroke-width="6"
      :indeterminate="status === 'processing' && progress <= 0"
      :duration="2"
    />

    <!-- 消息提示 -->
    <div v-if="message" class="status-message">{{ message }}</div>
  </div>
</template>

<style scoped>
.progress-status {
  padding: 10px 16px;
  background: var(--color-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  margin-bottom: var(--spacing-sm);
  transition: all 0.3s ease;
}

.progress-status.status-completed {
  border-color: #0F6E56;
  background: #f6fdf9;
}

.progress-status.status-failed {
  border-color: #A32D2D;
  background: #fef6f6;
}

.progress-header {
  margin-bottom: 8px;
}

.agent-name {
  font-size: var(--font-sm);
  font-weight: 500;
  color: var(--color-text);
}

.status-text {
  font-size: var(--font-xs);
  font-weight: 500;
}

.status-text.text-processing {
  color: var(--color-primary);
}

.status-text.text-completed {
  color: #0F6E56;
}

.status-text.text-failed {
  color: #A32D2D;
}

.status-message {
  font-size: var(--font-xs);
  color: var(--color-text-secondary);
  margin-top: 6px;
  padding-left: 24px;
}
</style>
