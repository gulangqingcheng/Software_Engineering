import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { LoginParams, RegisterParams, User } from '@/types'
import { getUserInfoApi, loginApi, registerApi } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string>(localStorage.getItem('access_token') || '')

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const currentUser = computed(() => user.value)

  async function login(params: LoginParams) {
    const res = await loginApi(params)
    token.value = res.data.access_token
    user.value = res.data.user
    localStorage.setItem('access_token', res.data.access_token)
    localStorage.setItem('user', JSON.stringify(res.data.user))
    return res
  }

  async function register(params: RegisterParams) {
    return registerApi(params)
  }

  async function fetchUserInfo() {
    const res = await getUserInfoApi()
    user.value = res.data
    localStorage.setItem('user', JSON.stringify(res.data))
    return res
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('user')

    const params = new URLSearchParams(window.location.search)
    const keepDebugPanel = params.get('debug-panel') === '1' || sessionStorage.getItem('app-debug-panel') === '1'
    if (keepDebugPanel) {
      const debugTheme = params.get('debug-theme') || localStorage.getItem('app-theme') || 'light'
      window.location.href = `/login?debug-panel=1&debug-theme=${encodeURIComponent(debugTheme)}`
      return
    }

    window.location.href = '/login'
  }

  function initAuth() {
    const savedToken = localStorage.getItem('access_token')
    const savedUser = localStorage.getItem('user')

    if (savedToken) {
      token.value = savedToken
    }

    if (savedUser) {
      try {
        user.value = JSON.parse(savedUser)
      } catch {
        localStorage.removeItem('user')
      }
    }
  }

  return {
    user,
    token,
    isLoggedIn,
    isAdmin,
    currentUser,
    login,
    register,
    fetchUserInfo,
    logout,
    initAuth,
  }
})
