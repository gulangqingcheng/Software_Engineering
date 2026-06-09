import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Conversation, ChatMessage, AgentStatusEvent } from '@/types'
import {
  getConversationsApi,
  getMessagesApi,
  sendMessageApi,
  createConversationApi,
} from '@/api/chat'
import request from '@/api/request'

function deriveTitle(content: string) {
  const cleaned = (content || '文件分析')
    .replace(/[#>*_`~\[\]（）(){}|!-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
  return cleaned.length > 24 ? `${cleaned.slice(0, 24)}...` : cleaned || '文件分析'
}

function agentDisplayName(agentType: string) {
  if (agentType === 'resume') return '简历评估'
  if (agentType === 'recording') return '录音分析'
  if (agentType === 'question') return '题目生成'
  if (agentType === 'multi') return 'multi'
  return 'general'
}

function defaultTitle(agentType: string) {
  if (agentType === 'resume') return '简历评估'
  if (agentType === 'recording') return '录音分析'
  if (agentType === 'question') return '面试题生成'
  return '新对话'
}

export const useChatStore = defineStore('chat', () => {
  const conversations = ref<Conversation[]>([])
  const currentConversationId = ref<number | string | null>(null)
  const messages = ref<ChatMessage[]>([])
  const agentStatus = ref<AgentStatusEvent | null>(null)
  const isSending = ref(false)
  const pendingFiles = ref<{ file: File; fileUrl: string; fileName: string }[]>([])
  const activeAgentType = ref<string>('general')

  let eventSource: EventSource | null = null

  const currentConversation = computed(() =>
    conversations.value.find((c) => c.id === currentConversationId.value)
  )

  const sortedMessages = computed(() =>
    [...messages.value].sort(
      (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
    )
  )

  async function fetchConversations() {
    try {
      const res = await getConversationsApi()
      const data = res.data as any
      if (data && Array.isArray(data.conversations)) {
        conversations.value = data.conversations
      } else if (Array.isArray(data)) {
        conversations.value = data
      }
    } catch (error) {
      console.error('获取对话列表失败:', error)
    }
  }

  async function fetchMessages(conversationId: number | string) {
    try {
      const res = await getMessagesApi(conversationId)
      messages.value = res.data
    } catch (error) {
      console.error('获取消息失败:', error)
    }
  }

  async function createConversation(title: string, agentType: string = 'general') {
    try {
      const res = await createConversationApi({ title, agent_type: agentType })
      conversations.value.unshift(res.data)
      currentConversationId.value = res.data.id
      messages.value = []
      agentStatus.value = null
      activeAgentType.value = agentType
    } catch (error) {
      console.error('创建对话失败:', error)
      throw error
    }
  }

  async function uploadFile(file: File): Promise<{ fileUrl: string; fileName: string }> {
    const formData = new FormData()
    formData.append('file', file)
    const res: any = await request.post('/v1/chat/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    const data = res.data || res
    return {
      fileUrl: data.file_url,
      fileName: data.file_name || file.name,
    }
  }

  async function addPendingFile(file: File) {
    try {
      const { fileUrl, fileName } = await uploadFile(file)
      pendingFiles.value.push({ file, fileUrl, fileName })
    } catch (error) {
      console.error('文件上传失败:', error)
      throw error
    }
  }

  function removePendingFile(index: number) {
    pendingFiles.value.splice(index, 1)
  }

  function clearPendingFiles() {
    pendingFiles.value = []
  }

  async function sendMessage(content: string, fileUrl?: string) {
    if (!currentConversationId.value) return

    isSending.value = true
    try {
      const userMsg: ChatMessage = {
        id: Date.now().toString(),
        conversation_id: currentConversationId.value,
        role: 'user',
        content,
        message_type: 'text',
        status: 'sending',
        created_at: new Date().toISOString(),
      }
      messages.value.push(userMsg)

      const current = conversations.value.find((c) => c.id === currentConversationId.value)
      if (current && (!current.title || current.title === '新对话')) {
        current.title = deriveTitle(content)
      }

      const res = await sendMessageApi(currentConversationId.value, { content, file_url: fileUrl })
      userMsg.status = 'sent'
      userMsg.id = res.data.user_message?.id || userMsg.id

      if (res.data.assistant_message) {
        messages.value.push({ ...res.data.assistant_message, status: 'sent' })
      }
    } catch (error) {
      console.error('发送消息失败:', error)
      const lastUserMsg = [...messages.value].reverse().find((m) => m.role === 'user')
      if (lastUserMsg) lastUserMsg.status = 'error'
    } finally {
      isSending.value = false
    }
  }

  function streamChat(
    content: string,
    agentType: string = 'general',
    fileUrls: string[] = [],
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!currentConversationId.value) {
        reject(new Error('没有活跃对话'))
        return
      }

      isSending.value = true
      const fileNames = pendingFiles.value.map((f) => f.fileName)
      const firstFileUrl = fileUrls[0]

      const userMsg: ChatMessage = {
        id: Date.now().toString(),
        conversation_id: currentConversationId.value,
        role: 'user',
        content,
        message_type: fileUrls.length > 0 ? 'file' : 'text',
        file_name: fileNames.length > 0 ? fileNames.join('、') : undefined,
        file_url: firstFileUrl || undefined,
        status: 'sending',
        created_at: new Date().toISOString(),
      }
      messages.value.push(userMsg)

      const current = conversations.value.find((c) => c.id === currentConversationId.value)
      if (current && (!current.title || current.title === '新对话')) {
        current.title = deriveTitle(content || fileNames.join(' '))
      }

      const aiMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        conversation_id: currentConversationId.value,
        role: 'assistant',
        content: '',
        message_type: 'text',
        streaming: true,
        status: 'sent',
        agent_name: agentDisplayName(agentType),
        thinking: '',
        isThinking: agentType === 'general' || agentType === 'multi',
        created_at: new Date().toISOString(),
      }
      messages.value.push(aiMsg)
      const reactiveMsg = messages.value[messages.value.length - 1]

      const token = localStorage.getItem('access_token')
      const conversationId = currentConversationId.value
      let url = `/api/v1/chat/conversations/${conversationId}/stream?content=${encodeURIComponent(content || '分析上传的文件')}&token=${encodeURIComponent(token || '')}&agent_type=${encodeURIComponent(agentType)}`
      if (firstFileUrl) {
        url += `&file_url=${encodeURIComponent(firstFileUrl)}`
      }
      if (fileUrls.length > 0) {
        url += `&file_urls=${encodeURIComponent(fileUrls.join(','))}`
        url += `&file_names=${encodeURIComponent(fileNames.join(','))}`
      }

      eventSource = new EventSource(url)
      clearPendingFiles()

      eventSource.addEventListener('message', (event) => {
        try {
          const data = JSON.parse(event.data)
          const chunkType = data.type

          if (chunkType === 'thinking') {
            reactiveMsg.thinking = (reactiveMsg.thinking || '') + (data.content || '')
            reactiveMsg.isThinking = true
          } else if (chunkType === 'content') {
            if (data.content) reactiveMsg.content += data.content
            if (reactiveMsg.isThinking) reactiveMsg.isThinking = false
          } else if (chunkType === 'status') {
            agentStatus.value = {
              agent_name: data.agent_name || '处理中',
              status: 'processing',
              progress: data.progress || 0,
              message: data.message || '处理中...',
            }
          } else if (data.content) {
            reactiveMsg.content += data.content
          }

          if (data.agent_name) reactiveMsg.agent_name = data.agent_name
          if (data.message_type) reactiveMsg.message_type = data.message_type
        } catch {
          reactiveMsg.content += event.data
        }
      })

      eventSource.addEventListener('agent_status', (event) => {
        try {
          const data: AgentStatusEvent = JSON.parse(event.data)
          agentStatus.value = data
          if (data.status === 'completed') {
            reactiveMsg.content += `\n\n--- ${data.agent_name} 阶段完成 ---\n\n`
          } else if (data.status === 'failed') {
            reactiveMsg.content += `\n\n--- ${data.agent_name} 阶段失败: ${data.message || ''} ---\n\n`
          }
        } catch {
          // ignore parse error
        }
      })

      eventSource.addEventListener('done', () => {
        reactiveMsg.streaming = false
        reactiveMsg.isThinking = false
        isSending.value = false
        agentStatus.value = null
        closeSSE()
        resolve()
      })

      eventSource.addEventListener('error', (event) => {
        console.error('SSE 连接错误:', event)
        reactiveMsg.streaming = false
        if (!reactiveMsg.content) {
          reactiveMsg.content += '\n\n[连接中断，请检查网络或刷新页面重试]'
        }
        isSending.value = false
        closeSSE()
        reject(new Error('SSE 连接错误'))
      })

      userMsg.status = 'sent'
    })
  }

  async function useFeatureTag(agentType: string, prompt?: string) {
    activeAgentType.value = agentType
    if (!currentConversationId.value) {
      await createConversation(defaultTitle(agentType), agentType)
    }
    return { agentType, prompt }
  }

  async function deleteConversation(conversationId: number | string) {
    try {
      await request.delete(`/v1/chat/conversations/${conversationId}`)
      const idx = conversations.value.findIndex((c) => c.id === conversationId)
      if (idx !== -1) conversations.value.splice(idx, 1)
      if (currentConversationId.value === conversationId) {
        currentConversationId.value = null
        messages.value = []
        agentStatus.value = null
        activeAgentType.value = 'general'
        closeSSE()
      }
    } catch (error) {
      console.error('删除对话失败:', error)
      throw error
    }
  }

  function closeSSE() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
  }

  function switchConversation(conversationId: number | string) {
    const conv = conversations.value.find((c) => c.id === conversationId)
    currentConversationId.value = conversationId
    messages.value = []
    agentStatus.value = null
    activeAgentType.value = (conv?.agent_type as string) || 'general'
    closeSSE()
    fetchMessages(conversationId)
  }

  function reset() {
    conversations.value = []
    currentConversationId.value = null
    messages.value = []
    agentStatus.value = null
    isSending.value = false
    activeAgentType.value = 'general'
    pendingFiles.value = []
    closeSSE()
  }

  return {
    conversations,
    currentConversationId,
    messages,
    agentStatus,
    isSending,
    pendingFiles,
    activeAgentType,
    currentConversation,
    sortedMessages,
    fetchConversations,
    fetchMessages,
    createConversation,
    sendMessage,
    streamChat,
    uploadFile,
    addPendingFile,
    removePendingFile,
    clearPendingFiles,
    useFeatureTag,
    closeSSE,
    deleteConversation,
    switchConversation,
    reset,
  }
})
