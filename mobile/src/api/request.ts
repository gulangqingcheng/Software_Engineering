import { storage } from '@/utils/storage'

const baseUrl = process.env.NODE_ENV === 'development' ? 'http://localhost:8000' : ''

export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

export async function request<T = any>(
  url: string,
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' = 'GET',
  data?: Record<string, any>,
  headers?: Record<string, string>
): Promise<ApiResponse<T>> {
  const token = storage.get('access_token')
  
  const defaultHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {})
  }

  try {
    const response = await uni.request({
      url: `${baseUrl}${url}`,
      method,
      data,
      header: { ...defaultHeaders, ...headers },
      timeout: 30000
    })

    if (response.statusCode === 401) {
      storage.remove('access_token')
      storage.remove('user')
      uni.navigateTo({ url: '/pages/login/login' })
      throw new Error('登录已过期，请重新登录')
    }

    if (response.statusCode >= 400) {
      throw new Error(response.data?.message || '请求失败')
    }

    return response.data as ApiResponse<T>
  } catch (error: any) {
    uni.showToast({
      title: error.message || '网络请求失败',
      icon: 'none'
    })
    throw error
  }
}

export function get<T = any>(url: string, params?: Record<string, any>): Promise<ApiResponse<T>> {
  const query = params ? `?${new URLSearchParams(params).toString()}` : ''
  return request<T>(`${url}${query}`, 'GET')
}

export function post<T = any>(url: string, data?: Record<string, any>): Promise<ApiResponse<T>> {
  return request<T>(url, 'POST', data)
}

export function put<T = any>(url: string, data?: Record<string, any>): Promise<ApiResponse<T>> {
  return request<T>(url, 'PUT', data)
}

export function del<T = any>(url: string): Promise<ApiResponse<T>> {
  return request<T>(url, 'DELETE')
}
