import axios from 'axios'
import type { AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'

/**
 * 创建 Axios 实例
 */
const request: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

/**
 * 请求拦截器
 */
request.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 自动添加 Authorization header
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

/**
 * 响应拦截器
 */
request.interceptors.response.use(
  (response: AxiosResponse) => {
    return response.data
  },
  (error) => {
    if (error.response) {
      const { status, data } = error.response

      switch (status) {
        case 401:
          // 未授权，清除登录信息并跳转登录页
          localStorage.removeItem('access_token')
          localStorage.removeItem('user')
          ElMessage.error('登录已过期，请重新登录')
          window.location.href = '/login'
          break
        case 403:
          ElMessage.error(data?.message || '没有访问权限')
          break
        case 404:
          ElMessage.error(data?.message || '请求的资源不存在')
          break
        case 422:
          // 请求参数校验失败
          const detail = data?.detail
          if (Array.isArray(detail)) {
            const msg = detail.map((e: any) => e.msg).join('；')
            ElMessage.error(msg || '请求参数有误')
          } else {
            ElMessage.error(data?.message || '请求参数有误')
          }
          break
        case 500:
          ElMessage.error('服务器内部错误，请稍后重试')
          break
        default:
          ElMessage.error(data?.message || `请求失败 (${status})`)
          break
      }
    } else if (error.code === 'ECONNABORTED') {
      ElMessage.error('请求超时，请检查网络连接')
    } else {
      ElMessage.error('网络连接失败，请检查网络')
    }

    return Promise.reject(error)
  }
)

export default request
