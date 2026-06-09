<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const formRef = ref<FormInstance>()
const loading = ref(false)
const errorMsg = ref('')

const formData = reactive({ username: '', email: '', password: '', confirmPassword: '' })

const validatePassword = (_rule: any, value: string, callback: (error?: Error) => void) => {
  if (!value) callback(new Error('请输入密码'))
  else if (value.length < 6) callback(new Error('密码长度至少 6 个字符'))
  else callback()
}

const validateConfirmPassword = (_rule: any, value: string, callback: (error?: Error) => void) => {
  if (!value) callback(new Error('请再次输入密码'))
  else if (value !== formData.password) callback(new Error('两次输入的密码不一致'))
  else callback()
}

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 30, message: '用户名长度为 3-30 个字符', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' },
  ],
  password: [{ required: true, validator: validatePassword, trigger: 'blur' }],
  confirmPassword: [{ required: true, validator: validateConfirmPassword, trigger: 'blur' }],
}

async function handleRegister() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  loading.value = true
  errorMsg.value = ''
  try {
    await authStore.register({
      username: formData.username,
      email: formData.email,
      password: formData.password,
      confirm_password: formData.confirmPassword,
    })
    await authStore.login({ username: formData.username, password: formData.password })
    router.push('/')
  } catch (err: any) {
    errorMsg.value = err?.response?.data?.detail || err?.response?.data?.message || '注册失败，请重试'
  } finally {
    loading.value = false
  }
}

function goToLogin() {
  router.push('/login')
}
</script>

<template>
  <div class="register-page">
    <div class="register-card card">
      <div class="register-header">
        <img class="logo" src="/logo.png" alt="智能面试助手" />
        <h1 class="title">创建账号</h1>
        <p class="subtitle">开启您的智能面试之旅</p>
      </div>

      <el-form ref="formRef" :model="formData" :rules="rules" class="register-form" @submit.prevent="handleRegister">
        <el-form-item prop="username"><el-input v-model="formData.username" input-id="register-username" name="username" autocomplete="username" placeholder="请输入用户名" :prefix-icon="'User'" size="large" /></el-form-item>
        <el-form-item prop="email"><el-input v-model="formData.email" input-id="register-email" name="email" autocomplete="email" placeholder="请输入邮箱" :prefix-icon="'Message'" size="large" /></el-form-item>
        <el-form-item prop="password"><el-input v-model="formData.password" type="password" input-id="register-password" name="password" autocomplete="new-password" placeholder="请输入密码（至少6位）" :prefix-icon="'Lock'" size="large" show-password /></el-form-item>
        <el-form-item prop="confirmPassword"><el-input v-model="formData.confirmPassword" type="password" input-id="register-confirm-password" name="confirmPassword" autocomplete="new-password" placeholder="请再次输入密码" :prefix-icon="'Lock'" size="large" show-password @keyup.enter="handleRegister" /></el-form-item>
        <el-alert v-if="errorMsg" :title="errorMsg" type="error" show-icon :closable="false" class="register-error" />
        <el-form-item><el-button type="primary" size="large" class="w-full auth-primary-btn" :loading="loading" @click="handleRegister">注册</el-button></el-form-item>
      </el-form>

      <div class="register-footer">
        <span class="text-secondary">已有账号？</span>
        <el-button link type="primary" @click="goToLogin">立即登录</el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.register-page { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: radial-gradient(circle at 50% 0, rgba(79, 70, 229, 0.08), transparent 32%), var(--color-bg); }
.register-card { width: 420px; padding: var(--spacing-xl); border: 1px solid var(--color-subtle-line); background: var(--color-card); box-shadow: var(--shadow-lg); }
.register-header { text-align: center; margin-bottom: var(--spacing-xl); }
.logo { width: 56px; height: 56px; margin: 0 auto var(--spacing-md); object-fit: cover; border-radius: var(--radius-lg); }
.title { font-size: var(--font-title); font-weight: 700; color: var(--color-text); margin-bottom: var(--spacing-xs); }
.subtitle { font-size: var(--font-sm); color: var(--color-text-secondary); }
.register-form { margin-top: var(--spacing-lg); }
.register-error { margin-bottom: var(--spacing-md); }
.auth-primary-btn { height: 44px; border: none; border-radius: 12px; background: var(--theme-gradient); box-shadow: 0 12px 24px rgba(83, 74, 183, 0.22); }
.auth-primary-btn:hover, .auth-primary-btn:focus { background: var(--theme-gradient-hover); border: none; }
.register-footer { text-align: center; font-size: var(--font-sm); }
</style>
