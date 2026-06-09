<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const formRef = ref<FormInstance>()
const loading = ref(false)
const errorMsg = ref('')

const formData = reactive({ username: '', password: '' })

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 30, message: '用户名长度为 3-30 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 50, message: '密码长度至少 6 个字符', trigger: 'blur' },
  ],
}

async function handleLogin() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  loading.value = true
  errorMsg.value = ''
  try {
    await authStore.login({ username: formData.username, password: formData.password })
    router.push((route.query.redirect as string) || '/')
  } catch (err: any) {
    errorMsg.value = err?.response?.data?.message || err?.response?.data?.detail || '登录失败，请重试'
  } finally {
    loading.value = false
  }
}

function goToRegister() {
  router.push('/register')
}
</script>

<template>
  <div class="login-page">
    <div class="login-card card">
      <div class="login-header">
        <img class="logo" src="/logo.png" alt="智能面试助手" />
        <h1 class="title">智能面试助手</h1>
        <p class="subtitle">AI 驱动的智能面试平台</p>
      </div>

      <el-form ref="formRef" :model="formData" :rules="rules" class="login-form" @submit.prevent="handleLogin">
        <el-form-item prop="username">
          <el-input v-model="formData.username" input-id="login-username" name="username" autocomplete="username" placeholder="请输入用户名" :prefix-icon="'User'" size="large" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="formData.password" type="password" input-id="login-password" name="password" autocomplete="current-password" placeholder="请输入密码" :prefix-icon="'Lock'" size="large" show-password @keyup.enter="handleLogin" />
        </el-form-item>
        <el-alert v-if="errorMsg" :title="errorMsg" type="error" show-icon :closable="false" class="login-error" />
        <el-form-item>
          <el-button type="primary" size="large" class="w-full auth-primary-btn" :loading="loading" @click="handleLogin">登录</el-button>
        </el-form-item>
      </el-form>

      <div class="login-footer">
        <span class="text-secondary">还没有账号？</span>
        <el-button link type="primary" @click="goToRegister">立即注册</el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle at 50% 0, rgba(79, 70, 229, 0.08), transparent 32%), var(--color-bg);
}

.login-card {
  width: 420px;
  padding: var(--spacing-xl);
  border: 1px solid var(--color-subtle-line);
  background: var(--color-card);
  box-shadow: var(--shadow-lg);
}

.login-header { text-align: center; margin-bottom: var(--spacing-xl); }
.logo { width: 56px; height: 56px; margin: 0 auto var(--spacing-md); object-fit: cover; border-radius: var(--radius-lg); }
.title { font-size: var(--font-title); font-weight: 700; color: var(--color-text); margin-bottom: var(--spacing-xs); }
.subtitle { font-size: var(--font-sm); color: var(--color-text-secondary); }
.login-form { margin-top: var(--spacing-lg); }
.login-error { margin-bottom: var(--spacing-md); }
.auth-primary-btn { height: 44px; border: none; border-radius: 12px; background: var(--theme-gradient); box-shadow: 0 12px 24px rgba(83, 74, 183, 0.22); }
.auth-primary-btn:hover, .auth-primary-btn:focus { background: var(--theme-gradient-hover); border: none; }
.login-footer { text-align: center; font-size: var(--font-sm); }
</style>
