<template>
  <view class="setup-container">
    <view class="navbar">
      <view class="back-btn" @click="goBack">
        <text>←</text>
      </view>
      <text class="title">面试配置</text>
      <view class="placeholder"></view>
    </view>

    <scroll-view scroll-y class="form-scroll">
      <view class="form-section">
        <view class="section-title">
          <text class="icon">🎯</text>
          <text class="text">面试信息</text>
        </view>

        <view class="form-item">
          <text class="label">目标岗位</text>
          <input
            class="input"
            type="text"
            v-model="form.target_position"
            placeholder="请输入目标岗位"
            placeholder-class="placeholder"
          />
        </view>

        <view class="form-item">
          <text class="label">面试类型</text>
          <view class="options">
            <view 
              class="option" 
              :class="{ active: form.interview_type === 'technical' }"
              @click="form.interview_type = 'technical'"
            >
              <text>💻 技术面试</text>
            </view>
            <view 
              class="option" 
              :class="{ active: form.interview_type === 'behavioral' }"
              @click="form.interview_type = 'behavioral'"
            >
              <text>🧠 行为面试</text>
            </view>
            <view 
              class="option" 
              :class="{ active: form.interview_type === 'comprehensive' }"
              @click="form.interview_type = 'comprehensive'"
            >
              <text>🎯 综合面试</text>
            </view>
          </view>
        </view>

        <view class="form-item">
          <text class="label">难度</text>
          <view class="options">
            <view 
              class="option" 
              :class="{ active: form.difficulty === 'easy' }"
              @click="form.difficulty = 'easy'"
            >
              <text>🌱 简单</text>
            </view>
            <view 
              class="option" 
              :class="{ active: form.difficulty === 'medium' }"
              @click="form.difficulty = 'medium'"
            >
              <text>🌿 进阶</text>
            </view>
            <view 
              class="option" 
              :class="{ active: form.difficulty === 'hard' }"
              @click="form.difficulty = 'hard'"
            >
              <text>🌳 困难</text>
            </view>
          </view>
        </view>

        <view class="form-item">
          <text class="label">题目数量</text>
          <view class="options">
            <view 
              class="option" 
              :class="{ active: form.question_count === 3 }"
              @click="form.question_count = 3"
            >
              <text>3 题</text>
            </view>
            <view 
              class="option" 
              :class="{ active: form.question_count === 5 }"
              @click="form.question_count = 5"
            >
              <text>5 题</text>
            </view>
            <view 
              class="option" 
              :class="{ active: form.question_count === 8 }"
              @click="form.question_count = 8"
            >
              <text>8 题</text>
            </view>
            <view 
              class="option" 
              :class="{ active: form.question_count === 10 }"
              @click="form.question_count = 10"
            >
              <text>10 题</text>
            </view>
          </view>
        </view>

        <view class="form-item">
          <text class="label">回答方式</text>
          <view class="options">
            <view 
              class="option" 
              :class="{ active: form.answer_mode === 'text' }"
              @click="form.answer_mode = 'text'"
            >
              <text>✍️ 文字</text>
            </view>
            <view 
              class="option" 
              :class="{ active: form.answer_mode === 'voice' }"
              @click="form.answer_mode = 'voice'"
            >
              <text>🎤 语音</text>
            </view>
          </view>
        </view>

        <view class="form-item">
          <view class="checkbox-row">
            <view 
              class="checkbox" 
              :class="{ checked: form.use_profile }"
              @click="form.use_profile = !form.use_profile"
            >
              <text v-if="form.use_profile">✓</text>
            </view>
            <text class="checkbox-label">结合个人资料提问</text>
          </view>
        </view>
      </view>

      <view class="form-section">
        <view class="section-title">
          <text class="icon">💡</text>
          <text class="text">面试说明</text>
        </view>
        <view class="tips">
          <view class="tip">
            <text class="tip-icon">1️⃣</text>
            <text class="tip-text">请确保网络畅通，面试过程中需要联网</text>
          </view>
          <view class="tip">
            <text class="tip-icon">2️⃣</text>
            <text class="tip-text">每题建议回答时间：1-3分钟</text>
          </view>
          <view class="tip">
            <text class="tip-icon">3️⃣</text>
            <text class="tip-text">面试结束后将生成详细报告</text>
          </view>
        </view>
      </view>
    </scroll-view>

    <view class="bottom-bar">
      <button class="btn btn-primary" :disabled="!canSubmit" @click="startInterview">
        <text>开始面试</text>
      </button>
    </view>
    
    <CustomTabBar />
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onLoad } from '@dcloudio/uni-app'
import { createInterviewSession, startInterview } from '@/api/interview'
import CustomTabBar from '@/components/TabBar/CustomTabBar.vue'

const form = ref({
  target_position: '',
  interview_type: 'technical',
  difficulty: 'medium',
  question_count: 5,
  answer_mode: 'text',
  use_profile: false
})

onLoad((options: any) => {
  if (options?.type) {
    form.value.interview_type = options.type
  }
})

const canSubmit = computed(() => {
  return form.value.target_position.trim() !== ''
})

async function startInterview() {
  if (!canSubmit.value) {
    uni.showToast({
      title: '请填写目标岗位',
      icon: 'none'
    })
    return
  }
  
  uni.showLoading({
    title: '创建面试中...'
  })
  
  try {
    const session = await createInterviewSession({
      target_position: form.value.target_position,
      interview_type: form.value.interview_type,
      difficulty: form.value.difficulty,
      question_count: form.value.question_count,
      answer_mode: form.value.answer_mode,
      use_profile: form.value.use_profile
    })
    
    const result = await startInterview(session.id)
    
    uni.hideLoading()
    
    uni.navigateTo({
      url: `/pages/interview/room?id=${session.id}&question=${encodeURIComponent(result.question)}`
    })
  } catch (error) {
    uni.hideLoading()
    uni.showToast({
      title: '创建面试失败',
      icon: 'none'
    })
  }
}

function goBack() {
  uni.navigateBack()
}
</script>

<style lang="scss" scoped>
.setup-container {
  min-height: 100vh;
  background: #f5f7fa;
  display: flex;
  flex-direction: column;
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

.form-scroll {
  flex: 1;
  padding: 24rpx;
}

.form-section {
  background: #fff;
  border-radius: 20rpx;
  padding: 28rpx;
  margin-bottom: 24rpx;
  
  .section-title {
    display: flex;
    align-items: center;
    gap: 12rpx;
    margin-bottom: 28rpx;
    
    .icon {
      font-size: 32rpx;
    }
    
    .text {
      font-size: 30rpx;
      font-weight: 600;
      color: #1f2937;
    }
  }
}

.form-item {
  margin-bottom: 28rpx;
  
  &:last-child {
    margin-bottom: 0;
  }
  
  .label {
    display: block;
    font-size: 26rpx;
    color: #6b7280;
    margin-bottom: 16rpx;
  }
  
  .input {
    width: 100%;
    height: 88rpx;
    padding: 0 28rpx;
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
}

.options {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
  
  .option {
    padding: 20rpx 28rpx;
    border-radius: 16rpx;
    border: 2rpx solid #e5e7eb;
    font-size: 26rpx;
    color: #6b7280;
    background: #fff;
    transition: all 0.3s ease;
    
    &.active {
      border-color: #6366f1;
      background: rgba(99, 102, 241, 0.1);
      color: #6366f1;
    }
  }
}

.checkbox-row {
  display: flex;
  align-items: center;
  gap: 16rpx;
  
  .checkbox {
    width: 44rpx;
    height: 44rpx;
    border: 2rpx solid #e5e7eb;
    border-radius: 8rpx;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 28rpx;
    color: #fff;
    background: #fff;
    
    &.checked {
      background: #6366f1;
      border-color: #6366f1;
    }
  }
  
  .checkbox-label {
    font-size: 28rpx;
    color: #4b5563;
  }
}

.tips {
  .tip {
    display: flex;
    align-items: flex-start;
    gap: 12rpx;
    padding: 16rpx 0;
    
    .tip-icon {
      font-size: 28rpx;
    }
    
    .tip-text {
      font-size: 26rpx;
      color: #6b7280;
      line-height: 1.6;
    }
  }
}

.bottom-bar {
  padding: 24rpx 32rpx;
  background: #fff;
  box-shadow: 0 -4rpx 16rpx rgba(0, 0, 0, 0.06);
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

.safe-area-bottom {
  padding-bottom: calc(24rpx + env(safe-area-inset-bottom));
}
</style>
