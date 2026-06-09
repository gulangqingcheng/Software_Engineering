<template>
  <view class="login-container">
    <view class="header">
      <view class="logo">
        <view class="logo-icon">🎯</view>
        <text class="logo-title">AI面试助手</text>
        <text class="logo-subtitle">智能面试，助力求职</text>
      </view>
    </view>

    <view class="form-container">
      <view class="input-group">
        <text class="label">邮箱</text>
        <input
          class="input"
          type="text"
          v-model="form.email"
          placeholder="请输入邮箱"
          placeholder-class="placeholder"
        />
      </view>

      <view class="input-group">
        <text class="label">密码</text>
        <input
          class="input"
          type="password"
          v-model="form.password"
          placeholder="请输入密码"
          placeholder-class="placeholder"
          :password="!showPassword"
        />
        <view class="password-toggle" @click="showPassword = !showPassword">
          <text>{{ showPassword ? '👁️' : '🙈' }}</text>
        </view>
      </view>

      <view class="forgot-password" @click="goToForgot">
        <text>忘记密码？</text>
      </view>

      <button class="btn btn-primary" :disabled="!canSubmit" @click="handleLogin">
        <text>登 录</text>
      </button>

      <view class="register-link">
        <text>还没有账号？</text>
        <text class="link" @click="goToRegister">立即注册</text>
      </view>
    </view>

    <view class="footer">
      <text>© 2024 AI面试助手</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { login } from '@/api/interview'
import { storage } from '@/utils/storage'

const form = ref({
  email: '',
  password: ''
})

const showPassword = ref(false)
const loading = ref(false)

const canSubmit = computed(() => {
  return form.value.email && form.value.password && !loading.value
})

async function handleLogin() {
  if (!canSubmit.value) return
  
  loading.value = true
  
  try {
    const result = await login(form.value)
    storage.set('access_token', result.access_token)
    storage.set('user', result.user)
    
    uni.showToast({
      title: '登录成功',
      icon: 'success'
    })
    
    setTimeout(() => {
      uni.switchTab({
        url: '/pages/home/home'
      })
    }, 1500)
  } catch (error) {
    uni.showToast({
      title: '登录失败，请检查邮箱和密码',
      icon: 'none'
    })
  } finally {
    loading.value = false
  }
}

function goToRegister() {
  uni.navigateTo({
    url: '/pages/login/register'
  })
}

function goToForgot() {
  uni.showToast({
    title: '功能开发中',
    icon: 'none'
  })
}
</script>

<style lang="scss" scoped>
.login-container {
  min-height: 100vh;
  background: linear-gradient(180deg, #6366f1 0%, #8b5cf6 50%, #a78bfa 100%);
  padding: 40rpx;
  display: flex;
  flex-direction: column;
}

.header {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo {
  text-align: center;
  
  .logo-icon {
    font-size: 120rpx;
    margin-bottom: 24rpx;
  }
  
  .logo-title {
    display: block;
    font-size: 48rpx;
    font-weight: 700;
    color: #fff;
    margin-bottom: 12rpx;
  }
  
  .logo-subtitle {
    display: block;
    font-size: 28rpx;
    color: rgba(255, 255, 255, 0.8);
  }
}

.form-container {
  background: #fff;
  border-radius: 32rpx;
  padding: 48rpx 40rpx;
  box-shadow: 0 20rpx 60rpx rgba(0, 0, 0, 0.15);
}

.input-group {
  position: relative;
  margin-bottom: 32rpx;
  
  .label {
    display: block;
    font-size: 26rpx;
    color: #6b7280;
    margin-bottom: 12rpx;
  }
  
  .input {
    width: 100%;
    height: 88rpx;
    padding: 0 32rpx;
    border: 2rpx solid #e5e7eb;
    border-radius: 16rpx;
    font-size: 30rpx;
    background: #f9fafb;
    
    &:focus {
      border-color: #6366f1;
      background: #fff;
    }
  }
  
  .placeholder {
    color: #d1d5db;
  }
  
  .password-toggle {
    position: absolute;
    right: 24rpx;
    top: 50%;
    transform: translateY(-50%);
    font-size: 32rpx;
    padding: 8rpx;
  }
}

.forgot-password {
  text-align: right;
  margin-bottom: 32rpx;
  
  text {
    font-size: 26rpx;
    color: #6366f1;
  }
}

.btn {
  width: 100%;
  height: 96rpx;
  border-radius: 16rpx;
  font-size: 32rpx;
  font-weight: 600;
  border: none;
  
  &-primary {
    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
    color: #fff;
    box-shadow: 0 8rpx 24rpx rgba(99, 102, 241, 0.3);
    
    &:active {
      opacity: 0.9;
    }
    
    &[disabled] {
      opacity: 0.5;
    }
  }
}

.register-link {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 32rpx;
  gap: 8rpx;
  
  text {
    font-size: 26rpx;
    color: #6b7280;
  }
  
  .link {
    color: #6366f1;
  }
}

.footer {
  text-align: center;
  padding: 40rpx 0;
  
  text {
    font-size: 24rpx;
    color: rgba(255, 255, 255, 0.7);
  }
}
</style>
