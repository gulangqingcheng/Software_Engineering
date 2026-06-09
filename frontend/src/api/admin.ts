import request from './request'
import type { APIResponse } from '@/types'

export interface AdminDashboardStats {
  total_users: number
  total_conversations: number
  total_resumes: number
  total_recordings: number
  total_questions: number
  active_users_today: number
  total_agent_calls: number
  avg_latency_ms?: number | null
}

export interface AdminUserItem {
  id: number
  username: string
  email?: string
  role: string
  created_at: string
  updated_at?: string | null
}

export interface AdminAgentLog {
  id: number
  conversation_id: number
  agent_name: string
  input_tokens?: number | null
  output_tokens?: number | null
  latency_ms?: number | null
  status: string
  error_msg?: string | null
  created_at: string
}

export interface AdminAgentStat {
  agent_name: string
  calls: number
  success_rate: number
  avg_latency_ms: number
}

export function getAdminDashboardApi(): Promise<APIResponse<AdminDashboardStats>> {
  return request.get('/v1/admin/dashboard')
}

export function getAdminUsersApi(params: {
  page: number
  page_size: number
  keyword?: string
  role?: string
}): Promise<APIResponse<{ items: AdminUserItem[]; total: number; page: number; page_size: number }>> {
  return request.get('/v1/admin/users', { params })
}

export function updateAdminUserRoleApi(userId: number, role: string): Promise<APIResponse<{ id: number; role: string }>> {
  return request.put(`/v1/admin/users/${userId}/role`, null, { params: { role } })
}

export function getAgentLogsApi(params: {
  page?: number
  page_size?: number
  agent_name?: string
  status_filter?: string
}): Promise<APIResponse<AdminAgentLog[]>> {
  return request.get('/v1/admin/agent-logs', { params })
}

export function getAgentStatsApi(): Promise<APIResponse<AdminAgentStat[]>> {
  return request.get('/v1/admin/agent-stats')
}

export function getKnowledgeStatsApi(): Promise<APIResponse<{ file_count: number; vector_count: number; kb_dir: string }>> {
  return request.get('/v1/admin/knowledge/stats')
}
