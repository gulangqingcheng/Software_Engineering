import request from './request'
import type { Recording, RecordingResult, APIResponse } from '@/types'

/**
 * 上传录音文件
 */
export function uploadRecordingApi(file: File): Promise<APIResponse<Recording>> {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/v1/recording/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/**
 * 获取录音处理状态
 */
export function getRecordingStatusApi(recordingId: number): Promise<APIResponse<Recording>> {
  return request.get(`/v1/recording/${recordingId}/status`)
}

/**
 * 获取录音分析结果
 */
export function getRecordingResultApi(recordingId: number): Promise<APIResponse<RecordingResult>> {
  return request.get(`/v1/recording/${recordingId}/result`)
}

/**
 * 获取录音列表
 */
export function getRecordingsApi(): Promise<APIResponse<Recording[]>> {
  return request.get('/v1/recording/list')
}

/**
 * 删除录音
 */
export function deleteRecordingApi(recordingId: number): Promise<APIResponse<null>> {
  return request.delete(`/v1/recording/${recordingId}`)
}
