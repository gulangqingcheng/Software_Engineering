import { post, get, del } from './request'

export interface UserLoginRequest {
  email: string
  password: string
}

export interface UserRegisterRequest {
  username: string
  email: string
  password: string
  confirm_password: string
}

export interface UserResponse {
  id: number
  username: string
  email: string
  avatar: string | null
  role: string
  created_at: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: UserResponse
}

export interface InterviewSession {
  id: number
  target_position: string
  interview_type: string
  difficulty: string
  question_count: number
  answer_mode: string
  status: string
  total_score: number | null
  created_at: string
  updated_at: string
}

export interface InterviewTurn {
  id: number
  session_id: number
  question_index: number
  question: string
  question_type: string
  answer_text: string | null
  score: number | null
  feedback: string | null
  suggestion: string | null
  answer_duration_seconds: number | null
  created_at: string
  answered_at: string | null
}

export interface InterviewReport {
  total_score: number
  dimension_scores: Record<string, number>
  summary: string
  strengths: string[]
  weaknesses: string[]
  suggestions: string[]
  turn_details: Array<{
    question: string
    answer: string
    score: number
    feedback: string
    suggestion: string
  }>
  generated_at: string
}

export async function login(data: UserLoginRequest): Promise<LoginResponse> {
  const response = await post<LoginResponse>('/api/v1/auth/login', data)
  return response.data
}

export async function register(data: UserRegisterRequest): Promise<UserResponse> {
  const response = await post<UserResponse>('/api/v1/auth/register', data)
  return response.data
}

export async function getCurrentUser(): Promise<UserResponse> {
  const response = await get<UserResponse>('/api/v1/auth/me')
  return response.data
}

export async function createInterviewSession(data: {
  target_position: string
  interview_type: string
  difficulty: string
  question_count: number
  answer_mode: string
  use_profile?: boolean
}): Promise<InterviewSession> {
  const response = await post<InterviewSession>('/api/v1/interview/sessions', data)
  return response.data
}

export async function getInterviewSession(sessionId: number): Promise<InterviewSession> {
  const response = await get<InterviewSession>(`/api/v1/interview/sessions/${sessionId}`)
  return response.data
}

export async function listInterviewSessions(): Promise<InterviewSession[]> {
  const response = await get<InterviewSession[]>('/api/v1/interview/sessions')
  return response.data
}

export async function startInterview(sessionId: number): Promise<{ session: InterviewSession; question: string }> {
  const response = await post<{ session: InterviewSession; question: string }>(`/api/v1/interview/sessions/${sessionId}/start`)
  return response.data
}

export async function submitAnswer(sessionId: number, data: {
  answer_text: string
  answer_duration_seconds: number
}): Promise<{ next_question: string | null; score: number; feedback: string; suggestion: string }> {
  const response = await post<{ next_question: string | null; score: number; feedback: string; suggestion: string }>(
    `/api/v1/interview/sessions/${sessionId}/answer`,
    data
  )
  return response.data
}

export async function finishInterview(sessionId: number): Promise<InterviewReport> {
  const response = await post<InterviewReport>(`/api/v1/interview/sessions/${sessionId}/finish`)
  return response.data
}

export async function deleteInterviewSession(sessionId: number): Promise<void> {
  await del(`/api/v1/interview/sessions/${sessionId}`)
}

export async function getInterviewReport(sessionId: number): Promise<InterviewReport> {
  const response = await get<InterviewReport>(`/api/v1/interview/sessions/${sessionId}/report`)
  return response.data
}
