// ==================== 通用类型 ====================

/** 通用 API 响应 */
export interface APIResponse<T = any> {
  code: number
  message: string
  data: T
}

/** 分页参数 */
export interface PaginationParams {
  page: number
  page_size: number
}

/** 分页响应 */
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

// ==================== 用户相关 ====================

/** 用户信息 */
export interface User {
  id: number
  username: string
  email: string
  avatar_url?: string
  role: 'user' | 'admin'
  created_at: string
  updated_at: string
}

/** 登录参数 */
export interface LoginParams {
  username: string
  password: string
}

/** 注册参数 */
export interface RegisterParams {
  username: string
  email: string
  password: string
  confirm_password: string
}

/** 登录响应 */
export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: User
}

// ==================== 对话相关 ====================

/** 对话 */
export interface Conversation {
  id: number | string
  title: string
  agent_type: string
  last_message?: string
  last_message_time?: string
  message_count: number
  created_at: string
  updated_at: string
}

/** 消息类型 */
export type MessageType = 'text' | 'file' | 'report' | 'system' | 'agent_status'

/** 消息角色 */
export type MessageRole = 'user' | 'assistant' | 'system'

/** 对话消息 */
export interface Message {
  id: number | string
  conversation_id: number | string
  role: MessageRole
  content: string
  message_type: MessageType
  file_url?: string
  file_name?: string
  report_data?: any
  agent_name?: string
  created_at: string
}

/** 聊天消息（前端显示用，扩展 Message） */
export interface ChatMessage extends Message {
  /** 是否正在流式接收 */
  streaming?: boolean
  /** 消息状态 */
  status?: 'sending' | 'sent' | 'error'
  /** AI 思考过程（DeepSeek 思考模式） */
  thinking?: string
  /** 是否正在思考中 */
  isThinking?: boolean
}

/** SSE Agent 状态事件 */
export interface AgentStatusEvent {
  agent_name: string
  status: 'processing' | 'completed' | 'failed'
  progress: number
  message?: string
}

// ==================== 简历相关 ====================

/** 简历 */
export interface Resume {
  id: number
  user_id: number
  file_name: string
  file_url: string
  file_type: string
  file_size: number
  status: 'pending' | 'processing' | 'completed' | 'failed'
  created_at: string
}

/** 简历解析结果 */
export interface ResumeResult {
  id: number
  resume_id: number
  name: string
  email: string
  phone: string
  skills: string[]
  education: Education[]
  experience: WorkExperience[]
  projects: Project[]
  summary: string
}

/** 简历评估结果 */
export interface ResumeEvaluation {
  overall_score: number
  scores: {
    completeness: number
    clarity: number
    skills_match: number
    experience_quality: number
  }
  strengths: string[]
  weaknesses: string[]
  suggestions: string[]
  optimized_resume?: string
}

/** 教育经历 */
export interface Education {
  school: string
  degree: string
  major: string
  start_date: string
  end_date: string
}

/** 工作经历 */
export interface WorkExperience {
  company: string
  position: string
  start_date: string
  end_date: string
  description: string
}

/** 项目经历 */
export interface Project {
  name: string
  description: string
  role: string
  technologies: string[]
  start_date?: string
  end_date?: string
}

// ==================== 录音相关 ====================

/** 录音 */
export interface Recording {
  id: number
  user_id: number
  file_name: string
  file_url: string
  duration: number
  file_size: number
  status: 'pending' | 'processing' | 'completed' | 'failed'
  created_at: string
}

/** 录音分析结果 */
export interface RecordingResult {
  id: number
  recording_id: number
  transcription: string
  analysis: {
    fluency: number
    clarity: number
    logic: number
    emotion: string
    keywords: string[]
  }
  suggestions: string[]
  summary: string
}

// ==================== 面试题相关 ====================

/** 面试题 */
export interface Question {
  id: number
  user_id?: number
  question: string
  answer?: string
  reference_answer?: string
  category: string
  difficulty: 'easy' | 'medium' | 'hard'
  tags: string[]
  reference_points?: string[]
  source?: string
  created_at: string
  updated_at?: string
}

/** 重复题目组 */
export interface DuplicateQuestionGroup {
  question: string
  items: Question[]
}

/** 出题参数 */
export interface QuestionGenerateParams {
  role: string
  category?: string
  difficulty?: 'easy' | 'medium' | 'hard'
  count: number
  style?: 'technical' | 'behavioral' | 'mixed'
}

// ==================== Agent 相关 ====================

/** Agent 执行日志 */
export interface AgentLog {
  id: number
  conversation_id: number
  agent_name: string
  status: 'success' | 'failed'
  input: string
  output: string
  duration: number
  error?: string
  created_at: string
}

/** 仪表盘统计数据 */
export interface DashboardStats {
  total_users: number
  active_users_today: number
  total_conversations: number
  total_messages: number
  agent_calls: number
  avg_satisfaction: number
  conversations_today: number
  messages_today: number
  daily_stats: {
    date: string
    conversations: number
    messages: number
    agent_calls: number
  }[]
}

// ==================== 文件上传相关 ====================

/** 文件上传响应 */
export interface FileUploadResponse {
  file_url: string
  file_name: string
  file_size: number
}

/** 会话产物 */
export interface ChatArtifact {
  name: string
  size: number
  type: string
  created_at: number
  preview_url: string
  download_url: string
}

/** 上传进度 */
export interface UploadProgress {
  loaded: number
  total: number
  percentage: number
}

// ==================== 个人中心相关 ====================

/** 用户个人资料 */
export interface UserProfile {
  id: number
  user_id: number
  age?: number
  gender?: 'male' | 'female' | 'other'
  major?: string
  grade?: string
  university?: string
  education_level?: string
  degree?: string
  graduation_year?: string
  target_position?: string
  target_city?: string
  skills?: string
  certificates?: string
  internship_experience?: string
  allow_ai_use: boolean
  created_at: string
  updated_at: string
}

/** 完整用户信息（含个人资料） */
export interface UserInfo {
  id: number
  username: string
  email?: string
  avatar_url?: string
  role: string
  created_at: string
  profile?: UserProfile
}

/** 更新个人资料参数 */
export interface ProfileUpdateParams {
  age?: number
  gender?: string
  major?: string
  grade?: string
  university?: string
  education_level?: string
  degree?: string
  graduation_year?: string
  target_position?: string
  target_city?: string
  skills?: string
  certificates?: string
  internship_experience?: string
}

/** 修改密码参数 */
export interface PasswordChangeParams {
  old_password: string
  new_password: string
}

/** 修改用户名参数 */
export interface UsernameChangeParams {
  new_username: string
}

/** AI 使用开关 */
export interface AiToggleParams {
  allow_ai_use: boolean
}
