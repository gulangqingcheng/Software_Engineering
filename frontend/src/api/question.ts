import request from './request'
import type {
  Question,
  DuplicateQuestionGroup,
  QuestionGenerateParams,
  APIResponse,
  PaginatedResponse,
  PaginationParams,
} from '@/types'

/**
 * AI 生成面试题
 */
export function generateQuestionsApi(
  params: QuestionGenerateParams
): Promise<APIResponse<Question[]>> {
  return request.post('/v1/question/generate', params)
}

/**
 * 获取题库列表（分页）
 */
export function getQuestionBankApi(
  params: PaginationParams & {
    category?: string
    difficulty?: string
    keyword?: string
    mine?: boolean
  }
): Promise<APIResponse<PaginatedResponse<Question>>> {
  return request.get('/v1/question/library', { params })
}

/**
 * 获取单个面试题详情
 */
export function getQuestionDetailApi(questionId: number): Promise<APIResponse<Question>> {
  return request.get(`/v1/question/library/${questionId}`)
}

/**
 * 创建面试题
 */
export function createQuestionApi(
  data: Omit<Question, 'id' | 'created_at' | 'updated_at'>
): Promise<APIResponse<Question>> {
  return request.post('/v1/question/create', data)
}

/**
 * 更新面试题
 */
export function updateQuestionApi(
  questionId: number,
  data: Partial<Question>
): Promise<APIResponse<Question>> {
  return request.put(`/v1/question/library/${questionId}`, data)
}

/**
 * 删除面试题
 */
export function deleteQuestionApi(questionId: number): Promise<APIResponse<null>> {
  return request.delete(`/v1/question/library/${questionId}`)
}

/**
 * 获取个人题库中题目相同但答案不同的重复项
 */
export function getDuplicateQuestionsApi(): Promise<APIResponse<DuplicateQuestionGroup[]>> {
  return request.get('/v1/question/duplicates')
}

/**
 * 保留一条重复题目记录，删除同题目的其他记录
 */
export function resolveDuplicateQuestionApi(data: {
  keep_id: number
  remove_ids?: number[]
}): Promise<APIResponse<null>> {
  return request.post('/v1/question/duplicates/resolve', data)
}
