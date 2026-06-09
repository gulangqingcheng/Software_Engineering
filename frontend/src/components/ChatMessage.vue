<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, Loading, CopyDocument, Check } from '@element-plus/icons-vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import type { ChatMessage } from '@/types'
import ReportCard from './ReportCard.vue'

const props = defineProps<{
  message: ChatMessage
}>()

marked.setOptions({
  breaks: true,
  gfm: true,
})

function renderMarkdown(text: string): string {
  const processed = convertJsonToMarkdown(text)
  const raw = marked.parse(processed) as string
  return DOMPurify.sanitize(raw)
}

function formatQuestionItem(item: any, index: number) {
  const question = item.question || item.title || `题目 ${index + 1}`
  const answer = formatAnswer(item.answer || item.reference_answer || item.referenceAnswer || '未填写')
  const category = item.category ? `类别：${item.category}` : ''
  const difficulty = item.difficulty ? `难度：${item.difficulty}` : ''
  const tags = Array.isArray(item.tags) && item.tags.length ? `标签：${item.tags.join('、')}` : ''
  const keyPoints = Array.isArray(item.key_points || item.reference_points)
    ? (item.key_points || item.reference_points).map((point: string) => `- ${point}`).join('\n')
    : ''

  let md = `### ${index + 1}. ${question}\n\n`
  const meta = [category, difficulty, tags].filter(Boolean).join('  ')
  if (meta) md += `${meta}\n\n`
  if (keyPoints) md += `**考察要点：**\n${keyPoints}\n\n`
  md += `**参考答案：**\n${answer}\n\n`
  return md
}

function formatAnswer(answer: any): string {
  if (answer === null || answer === undefined || answer === '') return '未填写'
  if (typeof answer === 'string') return answer
  if (Array.isArray(answer)) {
    const scalarItems = answer.filter((item) => typeof item !== 'object' || item === null)
    if (scalarItems.length === answer.length) {
      return scalarItems.map((item) => `- ${String(item)}`).join('\n')
    }
  }
  if (typeof answer === 'object') {
    const direct = answer.reference_answer || answer.referenceAnswer || answer.answer || answer.content || answer.text
    if (direct) return formatAnswer(direct)
  }
  return `\`\`\`json\n${JSON.stringify(answer, null, 2)}\n\`\`\``
}

function isQuestionItem(item: any): boolean {
  return Boolean(
    item &&
    typeof item === 'object' &&
    !Array.isArray(item) &&
    (item.question || item.title || item.reference_answer || item.referenceAnswer || item.answer)
  )
}

function getQuestionItems(data: any): any[] | null {
  if (Array.isArray(data) && data.some(isQuestionItem)) {
    return data.filter(isQuestionItem)
  }
  if (data && typeof data === 'object') {
    const wrapped = data.questions || data.items || data.data || data.result
    if (Array.isArray(wrapped) && wrapped.some(isQuestionItem)) {
      return wrapped.filter(isQuestionItem)
    }
    if (isQuestionItem(data)) {
      return [data]
    }
  }
  return null
}

function questionsToMarkdown(items: any[]): string {
  return `## 个性化面试练习题\n\n${items.map(formatQuestionItem).join('\n')}`
}

function parseJsonCandidate(candidate: string): any | null {
  try {
    return JSON.parse(candidate)
  } catch {
    try {
      return JSON.parse(candidate.replace(/,\s*([}\]])/g, '$1'))
    } catch {
      return null
    }
  }
}

function findBalancedJsonCandidates(text: string): string[] {
  const candidates: string[] = []
  for (let start = 0; start < text.length; start += 1) {
    const first = text[start]
    if (first !== '[' && first !== '{') continue

    const stack: string[] = []
    let inString = false
    let escaped = false
    for (let index = start; index < text.length; index += 1) {
      const current = text[index]
      if (inString) {
        if (escaped) escaped = false
        else if (current === '\\') escaped = true
        else if (current === '"') inString = false
        continue
      }

      if (current === '"') inString = true
      else if (current === '[' || current === '{') stack.push(current)
      else if (current === ']' || current === '}') {
        const opener = stack[stack.length - 1]
        if (!opener) break
        if ((opener === '[' && current !== ']') || (opener === '{' && current !== '}')) break
        stack.pop()
        if (stack.length === 0) {
          candidates.push(text.slice(start, index + 1))
          break
        }
      }
    }
  }
  return candidates
}

function extractEmbeddedQuestionMarkdown(text: string): string | null {
  const candidates = findBalancedJsonCandidates(text)
  for (const candidate of candidates) {
    const data = parseJsonCandidate(candidate)
    const items = getQuestionItems(data)
    if (items && items.length > 0) {
      return questionsToMarkdown(items)
    }
  }
  return null
}

function convertJsonToMarkdown(text: string): string {
  const trimmed = text.trim()
  if (!trimmed) return text

  try {
    if (trimmed.startsWith('[') && trimmed.endsWith(']')) {
      const data = JSON.parse(trimmed)
      const items = getQuestionItems(data)
      if (items) {
        return questionsToMarkdown(items)
      }
    }

    if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
      const data = JSON.parse(trimmed)
      if (typeof data !== 'object' || data === null) return text

      const items = getQuestionItems(data)
      if (items) {
        return questionsToMarkdown(items)
      }

      let md = ''
      if (data.overall_score !== undefined) {
        md += `## 综合评分\n\n**总分：${data.overall_score}/100**\n\n`
      }
      if (data.scores && typeof data.scores === 'object') {
        md += '| 评估维度 | 得分 |\n| --- | --- |\n'
        const nameMap: Record<string, string> = {
          completeness: '内容完整度',
          format: '排版规范',
          highlights: '亮点突出度',
          job_match: '岗位匹配度',
          language: '语言表达',
          clarity: '清晰度',
          skills_match: '技能匹配度',
          experience_quality: '经历质量',
        }
        for (const [key, val] of Object.entries(data.scores)) {
          md += `| ${nameMap[key] || key} | ${val} |\n`
        }
        md += '\n'
      }
      if (Array.isArray(data.strengths) && data.strengths.length > 0) {
        md += '## 主要亮点\n\n'
        data.strengths.forEach((s: string) => { md += `- ${s}\n` })
        md += '\n'
      }
      if (Array.isArray(data.weaknesses) && data.weaknesses.length > 0) {
        md += '## 不足之处\n\n'
        data.weaknesses.forEach((w: string) => { md += `- ${w}\n` })
        md += '\n'
      }
      if (Array.isArray(data.suggestions) && data.suggestions.length > 0) {
        md += '## 改进建议\n\n'
        data.suggestions.forEach((s: string, i: number) => { md += `${i + 1}. ${s}\n` })
        md += '\n'
      }
      if (data.detailed_analysis) {
        md += `## 综合分析\n\n${data.detailed_analysis}\n`
      }
      return md || text
    }
  } catch {
    const embeddedMarkdown = extractEmbeddedQuestionMarkdown(trimmed)
    return embeddedMarkdown || text
  }

  const embeddedMarkdown = extractEmbeddedQuestionMarkdown(trimmed)
  return embeddedMarkdown || text
}

const copied = ref(false)

async function copyContent() {
  try {
    await navigator.clipboard.writeText(props.message.content)
    copied.value = true
    ElMessage.success('已复制到剪贴板')
    setTimeout(() => { copied.value = false }, 2000)
  } catch {
    const textarea = document.createElement('textarea')
    textarea.value = props.message.content
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    copied.value = true
    ElMessage.success('已复制到剪贴板')
    setTimeout(() => { copied.value = false }, 2000)
  }
}

const isUser = computed(() => props.message.role === 'user')
const isSystem = computed(() => props.message.role === 'system')
const aiAvatarUrl = '/ai-avatar.png'
const roleLabel = computed(() => {
  if (isUser.value) return '你'
  if (isSystem.value) return '系统'
  return props.message.agent_name || 'AI 助手'
})

const timeStr = computed(() => {
  const date = new Date(props.message.created_at)
  if (isNaN(date.getTime())) return ''
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  })
})

const hasThinking = computed(() => !!props.message.thinking)

const fileIcon = computed(() => {
  const name = props.message.file_name || ''
  const ext = name.split('.').pop()?.toLowerCase() || ''
  const audioExts = ['mp3', 'wav', 'm4a', 'aac', 'ogg', 'flac']
  const videoExts = ['mp4', 'avi', 'mov', 'mkv', 'webm', 'wmv']
  if (audioExts.includes(ext)) return 'Microphone'
  if (videoExts.includes(ext)) return 'Film'
  return 'Document'
})

const renderedContent = computed(() => renderMarkdown(props.message.content || ''))
</script>

<template>
  <div v-if="isSystem" class="message-system">
    <span class="system-text">{{ message.content }}</span>
  </div>

  <div v-else-if="isUser" class="message-wrapper message-right">
    <div class="message-body">
      <div class="message-meta">
        <span class="message-time">{{ timeStr }}</span>
      </div>
      <div class="message-bubble message-bubble-user">
        <template v-if="message.message_type === 'file' && message.file_name">
          <div class="user-file-attachment">
            <el-icon :size="20"><component :is="fileIcon" /></el-icon>
            <span class="user-file-name">{{ message.file_name }}</span>
          </div>
          <div v-if="message.content" class="user-file-text">{{ message.content }}</div>
        </template>
        <template v-else>
          <div class="bubble-text">{{ message.content }}</div>
        </template>
      </div>
      <div v-if="message.status === 'sending'" class="message-status">
        <el-icon class="is-loading"><Loading /></el-icon>
      </div>
      <div v-else-if="message.status === 'error'" class="message-status message-error">
        发送失败
      </div>
    </div>
  </div>

  <div v-else class="message-wrapper message-left">
    <div class="message-avatar">
      <el-avatar :size="36" :src="aiAvatarUrl" class="ai-avatar" />
    </div>
    <div class="message-body">
      <div class="message-meta">
        <span class="message-role">{{ roleLabel }}</span>
        <span class="message-time">{{ timeStr }}</span>
      </div>

      <div v-if="hasThinking" class="thinking-section">
        <div class="thinking-header">
          <span class="thinking-dot"></span>
          <span class="thinking-label">{{ message.isThinking ? '正在思考中...' : '思考过程' }}</span>
        </div>
        <div class="thinking-content">{{ message.thinking }}</div>
      </div>

      <div class="message-bubble message-bubble-ai">
        <template v-if="message.streaming">
          <div class="bubble-text markdown-body" v-html="renderedContent"></div>
          <span v-if="message.isThinking" class="thinking-indicator">
            <span class="thinking-dot"></span>正在思考
          </span>
          <span v-else class="typing-cursor">|</span>
        </template>
        <template v-else-if="message.message_type === 'text'">
          <div class="bubble-text markdown-body" v-html="renderedContent"></div>
        </template>
        <template v-else-if="message.message_type === 'report' && message.report_data">
          <ReportCard
            :report="message.report_data"
            :title="message.report_data?.title || '分析报告'"
          />
        </template>
        <template v-else-if="message.message_type === 'file'">
          <div class="bubble-file">
            <el-icon><Document /></el-icon>
            <a v-if="message.file_url" :href="message.file_url" target="_blank">
              {{ message.file_name || '下载文件' }}
            </a>
            <span v-else>{{ message.file_name || '文件' }}</span>
          </div>
        </template>
        <template v-else>
          <div class="bubble-text">{{ message.content }}</div>
        </template>
      </div>

      <div v-if="message.content && !message.streaming" class="message-actions">
        <button class="copy-btn" :class="{ copied }" @click="copyContent" title="复制内容">
          <el-icon :size="14">
            <Check v-if="copied" />
            <CopyDocument v-else />
          </el-icon>
          <span>{{ copied ? '已复制' : '复制' }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.message-system {
  display: flex;
  justify-content: center;
  padding: var(--spacing-sm) 0;
}

.system-text {
  font-size: var(--font-xs);
  color: var(--color-text-placeholder);
  background: var(--color-bg-dark);
  padding: 4px 12px;
  border-radius: var(--radius-sm);
}

.message-wrapper {
  display: flex;
  margin-bottom: var(--spacing-md);
  padding: 0 var(--spacing-md);
}

.message-left {
  justify-content: flex-start;
}

.message-right {
  justify-content: flex-end;
}

.message-avatar {
  flex-shrink: 0;
  margin-right: var(--spacing-sm);
  margin-top: 4px;
}

.ai-avatar {
  padding: 0;
  background: transparent !important;
  border: 1px solid rgba(79, 70, 229, 0.45);
  box-shadow: 0 10px 24px rgba(83, 74, 183, 0.16);
}

.ai-avatar :deep(img) {
  object-fit: contain;
  background: transparent !important;
}

.message-body {
  max-width: 75%;
  display: flex;
  flex-direction: column;
}

.message-right .message-body {
  align-items: flex-end;
}

.message-meta {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: 4px;
  padding: 0 4px;
}

.message-role {
  font-size: var(--font-xs);
  font-weight: 500;
  color: var(--color-text-secondary);
}

.message-time {
  font-size: 11px;
  color: var(--color-text-placeholder);
}

.thinking-section {
  margin-bottom: 8px;
  padding: 8px 12px;
  background: var(--color-primary-lighter);
  border: 1px solid rgba(79, 70, 229, 0.14);
  border-radius: 8px;
  max-width: 600px;
}

.thinking-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.thinking-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-primary);
  animation: pulse 1.5s ease-in-out infinite;
}

.thinking-label {
  font-size: 12px;
  color: var(--color-primary);
  font-weight: 500;
}

.thinking-content {
  font-size: 12px;
  color: var(--color-text-secondary);
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 120px;
  overflow-y: auto;
}

.message-bubble {
  padding: 10px 16px;
  border-radius: var(--radius-md);
  line-height: 1.6;
  word-break: break-word;
}

.message-bubble-user {
  background: var(--theme-gradient);
  color: var(--color-text-inverse);
  border-bottom-right-radius: 4px;
  box-shadow: 0 12px 28px rgba(83, 74, 183, 0.2);
}

.message-bubble-ai {
  background: var(--color-surface-glass-strong);
  border: 1px solid var(--color-subtle-line);
  border-bottom-left-radius: 4px;
  box-shadow: 0 10px 30px rgba(9, 9, 11, 0.035);
  backdrop-filter: blur(12px);
}

.markdown-body {
  font-size: var(--font-md);
  line-height: 1.7;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  margin: 12px 0 8px;
  font-weight: 600;
  line-height: 1.4;
}

.markdown-body :deep(h1) { font-size: 1.3em; }
.markdown-body :deep(h2) { font-size: 1.15em; }
.markdown-body :deep(h3) { font-size: 1.05em; }
.markdown-body :deep(p) { margin: 6px 0; }

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 6px 0;
  padding-left: 20px;
}

.markdown-body :deep(li) { margin: 3px 0; }
.markdown-body :deep(strong) { font-weight: 600; }

.markdown-body :deep(code) {
  background: var(--color-bg-dark);
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 0.9em;
  font-family: Menlo, Monaco, 'Courier New', monospace;
}

.markdown-body :deep(pre) {
  background: var(--color-bg-dark);
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
}

.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
  font-size: 0.88em;
  line-height: 1.5;
}

.markdown-body :deep(blockquote) {
  border-left: 3px solid var(--color-primary);
  padding-left: 12px;
  margin: 8px 0;
  color: var(--color-text-secondary);
}

.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid var(--color-border);
  margin: 12px 0;
}

.markdown-body :deep(table) {
  border-collapse: collapse;
  margin: 8px 0;
  width: 100%;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid var(--color-border);
  padding: 6px 10px;
  text-align: left;
}

.markdown-body :deep(th) {
  background: var(--color-bg-dark);
  font-weight: 600;
}

.bubble-text {
  font-size: var(--font-md);
  line-height: 1.7;
}

.bubble-file {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: var(--font-sm);
}

.bubble-file a {
  color: var(--color-primary);
  text-decoration: underline;
}

.user-file-attachment {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 999px;
  margin-bottom: 6px;
  font-size: var(--font-sm);
  max-width: 100%;
  border: 1px solid rgba(255, 255, 255, 0.18);
}

.user-file-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 240px;
}

.user-file-text {
  font-size: var(--font-sm);
  opacity: 0.9;
  word-break: break-word;
  white-space: pre-wrap;
}

.typing-cursor {
  display: inline-block;
  animation: blink 1s step-end infinite;
  color: var(--color-primary);
  font-weight: bold;
}

.thinking-indicator {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #8b7fc7;
  animation: fadeInOut 1.5s ease-in-out infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.8); }
}

@keyframes fadeInOut {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.message-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 4px;
  padding-right: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.message-body:hover .message-actions {
  opacity: 1;
}

.copy-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--color-text-placeholder);
  font-size: 12px;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
}

.copy-btn:hover {
  background: var(--color-primary-lighter);
  border-color: rgba(83, 74, 183, 0.14);
  color: var(--color-primary);
}

.copy-btn.copied {
  color: var(--color-accent);
}

.message-status {
  font-size: var(--font-xs);
  color: var(--color-text-placeholder);
  padding: 2px 4px;
  margin-top: 2px;
}

.message-error {
  color: var(--color-danger);
}

:global(.theme-dark) .message-bubble-ai {
  background: rgba(22, 24, 34, 0.86);
  border-color: rgba(255, 255, 255, 0.08);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.36);
}

:global(.theme-dark) .thinking-section {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 255, 255, 0.08);
}

:global(.theme-dark) .markdown-body :deep(code),
:global(.theme-dark) .markdown-body :deep(pre),
:global(.theme-dark) .markdown-body :deep(th) {
  background: rgba(255, 255, 255, 0.04);
}

:global(.theme-dark) .copy-btn:hover {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 255, 255, 0.08);
}

:global(.theme-dark) .ai-avatar {
  background: transparent !important;
  border-color: rgba(99, 102, 241, 0.55);
}
</style>
