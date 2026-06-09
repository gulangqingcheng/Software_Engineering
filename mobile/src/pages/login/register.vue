<template>
  <view class="register-container">
    <view class="navbar">
      <view class="back-btn" @click="goBack">
        <text>←</text>
      </view>
      <text class="title">注册账号</text>
      <view class="placeholder"></view>
    </view>

    <view class="form-container">
      <view class="input-group">
        <text class="label">用户名</text>
        <input
          class="input"
          type="text"
          v-model="form.username"
          placeholder="请输入用户名"
          placeholder-class="placeholder"
        />
      </view>

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

      <view class="input-group">
        <text class="label">确认密码</text>
        <input
          class="input"
          type="password"
          v-model="form.confirm_password"
          placeholder="请再次输入密码"
          placeholder-class="placeholder"
          :password="!showConfirmPassword"
        />
        <view class="password-toggle" @click="showConfirmPassword = !showConfirmPassword">
          <text>{{ showConfirmPassword ? '👁️' : '🙈' }}</text>
        </view>
      </view>

      <button class="btn btn-primary" :disabled="!canSubmit" @click="handleRegister">
        <text>注 册</text>
      </button>

      <view class="login-link">
        <text>已有账号？</text>
        <text class="link" @click="goToLogin">立即登录</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { register } from '@/api/interview'

const form = ref({
  username: '',
  email: '',
  password: '',
  confirm_password: ''
})

const showPassword = ref(false)
const showConfirmPassword = ref(false)
const loading = ref(false)

const canSubmit = computed(() => {
  return form.value.username && 
         form.value.email && 
         form.value.password && 
         form.value.confirm_password &&
         form.value.password === form.value.confirm_password &&
         !loading.value
})

async function handleRegister() {
  if (!canSubmit.value) return
  
  if (form.value.password !== form.value.confirm_password) {
    uni.showToast({
      title: '两次密码输入不一致',
      icon: 'none'
    })
    return
  }
  
  loading.value = true
  
  try {
    await register(form.value)
    
    uni.showToast({
      title: '注册成功',
      icon: 'success'
    })
    
    setTimeout(() => {
      uni.navigateBack()
    }, 1500)
  } catch (error) {
    uni.showToast({
      title: '注册失败，请重试',
      icon: 'none'
    })
  } finally {
    loading.value = false
  }
}

function goBack() {
  uni.navigateBack()
}

function goToLogin() {
  uni.navigateBack()
}
</script>

<style lang="scss" scoped>
.register-container {
  min-height: 100vh;
  background: #f5f7fa;
}

.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 88rpx;
  padding: 0 32rpx;
  background: #fff;
  position: sticky;
  top: 0;
  z-index: 100;
  
  .back-btn {
    width: 64rpx;
    height: 64rpx;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 40rpx;
    color: #333;
  }
  
  .title {
    font-size: 34rpx;
    font-weight: 600;
    color: #1f2937;
  }
  
  .placeholder {
    width: 64rpx;
  }
}

.form-container {
  padding: 40rpx 32rpx;
}

.input-group {
  position: relative;
  margin-bottom: 28rpx;
  
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
    background: #fff;
    
    &:focus {
      border-color: #6366f1;
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

.btn {
  width: 100%;
  height: 96rpx;
  border-radius: 16rpx;
  font-size: 32rpx;
  font-weight: 600;
  border: none;
  margin-top: 16rpx;
  
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

.login-link {
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
</style>
