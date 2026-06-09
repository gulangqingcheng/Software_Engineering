export const storage = {
  set(key: string, value: any): void {
    try {
      const data = typeof value === 'string' ? value : JSON.stringify(value)
      uni.setStorageSync(key, data)
    } catch (error) {
      console.error('Storage set error:', error)
    }
  },

  get(key: string): any {
    try {
      const data = uni.getStorageSync(key)
      if (typeof data === 'string') {
        try {
          return JSON.parse(data)
        } catch {
          return data
        }
      }
      return data
    } catch (error) {
      console.error('Storage get error:', error)
      return null
    }
  },

  remove(key: string): void {
    try {
      uni.removeStorageSync(key)
    } catch (error) {
      console.error('Storage remove error:', error)
    }
  },

  clear(): void {
    try {
      uni.clearStorageSync()
    } catch (error) {
      console.error('Storage clear error:', error)
    }
  }
}

export const TOKEN_KEY = 'access_token'
export const USER_KEY = 'user'

export function getToken(): string | null {
  return storage.get(TOKEN_KEY)
}

export function setToken(token: string): void {
  storage.set(TOKEN_KEY, token)
}

export function removeToken(): void {
  storage.remove(TOKEN_KEY)
}

export function getUser(): any {
  return storage.get(USER_KEY)
}

export function setUser(user: any): void {
  storage.set(USER_KEY, user)
}

export function removeUser(): void {
  storage.remove(USER_KEY)
}

export function isLoggedIn(): boolean {
  return !!getToken()
}
