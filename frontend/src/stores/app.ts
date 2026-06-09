import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'

type ThemeType = 'light' | 'dark'

function getInitialTheme(): ThemeType {
  localStorage.setItem('app-theme', 'light')
  return 'light'
}

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  const theme = ref<ThemeType>(getInitialTheme())
  const globalLoading = ref(false)
  const loadingText = ref('加载中...')

  const isDark = computed(() => theme.value === 'dark')

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function setSidebarCollapsed(collapsed: boolean) {
    sidebarCollapsed.value = collapsed
  }

  function toggleTheme() {
    theme.value = 'light'
  }

  function setTheme(_t: ThemeType) {
    theme.value = 'light'
  }

  function showLoading(text?: string) {
    globalLoading.value = true
    if (text) loadingText.value = text
  }

  function hideLoading() {
    globalLoading.value = false
    loadingText.value = '加载中...'
  }

  watch(theme, () => {
    const nextTheme = 'light'
    const isDarkTheme = false

    document.documentElement.setAttribute('data-theme', nextTheme)
    document.documentElement.classList.toggle('theme-dark', isDarkTheme)
    document.documentElement.classList.toggle('theme-light', !isDarkTheme)
    document.documentElement.classList.toggle('dark', isDarkTheme)
    document.body.classList.toggle('theme-dark', isDarkTheme)
    document.body.classList.toggle('theme-light', !isDarkTheme)
    document.body.classList.toggle('dark', isDarkTheme)
    localStorage.setItem('app-theme', nextTheme)
    setTimeout(() => {
      ;(window as any).__APP_DEBUG_CHECK__?.(`theme-store:${nextTheme}`)
    }, 120)
  }, { immediate: true })

  return {
    sidebarCollapsed,
    theme,
    globalLoading,
    loadingText,
    isDark,
    toggleSidebar,
    setSidebarCollapsed,
    toggleTheme,
    setTheme,
    showLoading,
    hideLoading,
  }
})
