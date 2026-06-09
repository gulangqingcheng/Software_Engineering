import request from './request'
import type { Resume, ResumeResult, ResumeEvaluation, APIResponse } from '@/types'

/**
 * 上传简历文件
 */
export function uploadResumeApi(file: File): Promise<APIResponse<Resume>> {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/v1/resume/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/**
 * 获取简历解析结果
 */
export function getResumeResultApi(resumeId: number): Promise<APIResponse<ResumeResult>> {
  return request.get(`/v1/resume/${resumeId}/result`)
}

/**
 * 获取简历评估结果
 */
export function getResumeEvaluationApi(resumeId: number): Promise<APIResponse<ResumeEvaluation>> {
  return request.get(`/v1/resume/${resumeId}/evaluation`)
}

/**
 * 获取简历列表
 */
export function getResumesApi(): Promise<APIResponse<Resume[]>> {
  return request.get('/v1/resume/list')
}

/**
 * 删除简历
 */
export function deleteResumeApi(resumeId: number): Promise<APIResponse<null>> {
  return request.delete(`/v1/resume/${resumeId}`)
}
