import request from './request'
import type { APIResponse, PaginatedResponse } from '@/types'

export interface InterviewSessionCreateParams {
  title?: string
  target_position: string
  interview_type: 'technical' | 'behavioral' | 'comprehensive'
  difficulty: 'easy' | 'medium' | 'hard'
  question_count: number
  answer_mode: 'text' | 'audio'
}

export interface InterviewAnswerParams {
  answer_text: string
  answer_duration_seconds?: number
  answer_audio_url?: string
}

export interface InterviewTurn {
  id: number
  question_index: number
  question: string
  answer_text?: string | null
  answer_duration_seconds?: number | null
  score?: number | null
  feedback?: string | null
  suggestion?: string | null
  answered_at?: string | null
}

export interface InterviewSession {
  id: number
  title: string
  target_position: string
  interview_type: string
  difficulty: string
  question_count: number
  answer_mode: string
  status: 'pending' | 'in_progress' | 'finished'
  total_score?: number | null
  report?: InterviewReport | null
  turns?: InterviewTurn[]
  created_at: string
}

export interface InterviewReport {
  session_id: number
  total_score: number
  status: string
  summary: string
  score_basis?: string
  dimension_scores?: Record<string, number>
  turn_performance: Array<{
    question_index: number
    question: string
    answer?: string
    answer_duration_seconds?: number | null
    score: number
    dimensions?: Record<string, number>
    evidence?: string[]
    missing_points?: string[]
    feedback: string
    suggestion: string
  }>
  strengths?: string[]
  weaknesses?: string[]
  suggestions: string[]
  action_plan?: string[]
  generated_at: string
}

export function createInterviewSessionApi(data: InterviewSessionCreateParams): Promise<APIResponse<InterviewSession>> {
  return request.post('/v1/interview/sessions', data)
}

export function getInterviewSessionsApi(params = { page: 1, page_size: 20 }): Promise<APIResponse<PaginatedResponse<InterviewSession>>> {
  return request.get('/v1/interview/sessions', { params })
}

export function startInterviewSessionApi(sessionId: number): Promise<APIResponse<InterviewSession>> {
  return request.post(`/v1/interview/sessions/${sessionId}/start`)
}

export function answerInterviewSessionApi(sessionId: number, data: InterviewAnswerParams): Promise<APIResponse<InterviewSession>> {
  return request.post(`/v1/interview/sessions/${sessionId}/answer`, data)
}

export function finishInterviewSessionApi(sessionId: number): Promise<APIResponse<InterviewReport>> {
  return request.post(`/v1/interview/sessions/${sessionId}/finish`)
}

export function getInterviewReportApi(sessionId: number): Promise<APIResponse<InterviewReport>> {
  return request.get(`/v1/interview/sessions/${sessionId}/report`)
}

export function getInterviewReportDownloadUrl(sessionId: number): string {
  return `/api/v1/interview/sessions/${sessionId}/report.docx`
}
