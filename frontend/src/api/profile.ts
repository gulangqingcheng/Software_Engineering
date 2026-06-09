import request from './request'
import type {
  APIResponse,
  UserProfile,
  UserInfo,
  ProfileUpdateParams,
  PasswordChangeParams,
  UsernameChangeParams,
  AiToggleParams,
} from '@/types'

/**
 * 获取当前用户完整信息（含个人资料）
 */
export function getProfileApi(): Promise<APIResponse<UserInfo>> {
  return request.get('/v1/profile/me')
}

/**
 * 更新个人资料
 */
export function updateProfileApi(
  data: ProfileUpdateParams
): Promise<APIResponse<UserProfile>> {
  return request.put('/v1/profile/me', data)
}

/**
 * 修改密码
 */
export function changePasswordApi(
  data: PasswordChangeParams
): Promise<APIResponse<null>> {
  return request.put('/v1/profile/password', data)
}

/**
 * 修改用户名
 */
export function changeUsernameApi(
  data: UsernameChangeParams
): Promise<APIResponse<UserInfo>> {
  return request.put('/v1/profile/username', data)
}

/**
 * 上传头像
 */
export function uploadAvatarApi(
  file: File
): Promise<APIResponse<{ avatar_url: string }>> {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/v1/profile/avatar', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
}

/**
 * 切换 AI 使用个人信息开关
 */
export function toggleAiUseApi(
  data: AiToggleParams
): Promise<APIResponse<UserProfile>> {
  return request.put('/v1/profile/ai-toggle', data)
}
