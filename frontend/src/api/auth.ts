import request from './request'
import type { LoginParams, LoginResponse, RegisterParams, User, APIResponse } from '@/types'

/**
 * 用户登录
 */
export function loginApi(data: LoginParams): Promise<APIResponse<LoginResponse>> {
  return request.post('/v1/auth/login', data)
}

/**
 * 用户注册
 */
export function registerApi(data: RegisterParams): Promise<APIResponse<LoginResponse>> {
  return request.post('/v1/auth/register', data)
}

/**
 * 刷新 Token
 */
export function refreshTokenApi(): Promise<APIResponse<{ access_token: string }>> {
  return request.post('/v1/auth/refresh')
}

/**
 * 获取当前用户信息
 */
export function getUserInfoApi(): Promise<APIResponse<User>> {
  return request.get('/v1/auth/me')
}
