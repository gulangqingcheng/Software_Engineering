import request from './request'
import type {
  Conversation,
  Message,
  ChatMessage,
  ChatArtifact,
  APIResponse,
} from '@/types'

/**
 * 获取对话列表
 */
export function getConversationsApi(): Promise<APIResponse<Conversation[]>> {
  return request.get('/v1/chat/conversations')
}

/**
 * 创建新对话
 */
export function createConversationApi(data: {
  title: string
  agent_type: string
}): Promise<APIResponse<Conversation>> {
  return request.post('/v1/chat/conversations', data)
}

/**
 * 获取对话消息
 */
export function getMessagesApi(
  conversationId: number | string
): Promise<APIResponse<ChatMessage[]>> {
  return request.get(`/v1/chat/conversations/${conversationId}/messages`)
}

/**
 * 发送消息（非流式）
 */
export function sendMessageApi(
  conversationId: number | string,
  data: {
    content: string
    file_url?: string
  }
): Promise<APIResponse<{ user_message: Message; assistant_message: Message }>> {
  return request.post(`/v1/chat/conversations/${conversationId}/messages`, data)
}

/**
 * 流式对话（SSE）
 * 注意：此方法返回 EventSource，由调用方自行管理
 */
export function streamChatApi(conversationId: number | string, content: string): EventSource {
  const token = localStorage.getItem('access_token')
  const url = `/api/v1/chat/conversations/${conversationId}/stream?content=${encodeURIComponent(content)}&token=${encodeURIComponent(token || '')}`

  // SSE 需要手动处理 EventSource，这里的 baseURL 问题：
  // 直接构造完整 URL 绕过 Axios
  const eventSource = new EventSource(url)

  return eventSource
}

/**
 * 删除对话
 */
export function deleteConversationApi(
  conversationId: number | string
): Promise<APIResponse<null>> {
  return request.delete(`/v1/chat/conversations/${conversationId}`)
}

/**
 * 获取会话产物列表
 */
export function getArtifactsApi(
  conversationId: number | string
): Promise<APIResponse<ChatArtifact[]>> {
  return request.get(`/v1/chat/conversations/${conversationId}/artifacts`)
}

/**
 * 预览会话产物
 */
export function previewArtifactApi(
  conversationId: number | string,
  filename: string
): Promise<string> {
  return request.get(`/v1/chat/conversations/${conversationId}/artifacts/${encodeURIComponent(filename)}/preview`)
}
