<template>
  <view class="room-container">
    <view class="navbar">
      <view class="back-btn" @click="handleExit">
        <text>←</text>
      </view>
      <view class="nav-center">
        <text class="title">AI面试</text>
        <text class="progress">{{ currentIndex }}/{{ totalCount }}</text>
      </view>
      <view class="timer">
        <text class="timer-icon">⏱️</text>
        <text class="timer-text">{{ formatTime(timer) }}</text>
      </view>
    </view>

    <scroll-view 
      scroll-y 
      class="chat-container"
      :scroll-into-view="scrollToId"
      scroll-with-animation
    >
      <view 
        v-for="(msg, index) in messages" 
        :key="index"
        :id="'msg-' + index"
        class="message-item"
        :class="{ 'is-ai': msg.type === 'ai', 'is-user': msg.type === 'user', 'is-feedback': msg.type === 'feedback' }"
      >
        <view v-if="msg.type === 'ai'" class="ai-message">
          <view class="avatar">🤖</view>
          <view class="bubble">
            <text class="content">{{ msg.content }}</text>
          </view>
        </view>

        <view v-else-if="msg.type === 'user'" class="user-message">
          <view class="bubble">
            <text class="content">{{ msg.content }}</text>
            <text class="duration">{{ msg.duration }}</text>
          </view>
          <view class="avatar">👤</view>
        </view>

        <view v-else-if="msg.type === 'feedback'" class="feedback-message">
          <view class="feedback-card">
            <view class="score-row">
              <text class="score-label">本轮得分</text>
              <view class="score-value">
                <text class="num">{{ msg.score }}</text>
                <text class="unit">分</text>
              </view>
            </view>
            <view class="feedback-content">
              <view class="feedback-item">
                <text class="feedback-title">💬 评价</text>
                <text class="feedback-text">{{ msg.feedback }}</text>
              </view>
              <view class="feedback-item">
                <text class="feedback-title">💡 建议</text>
                <text class="feedback-text">{{ msg.suggestion }}</text>
              </view>
            </view>
          </view>
        </view>
      </view>
    </scroll-view>

    <view class="input-area safe-area-bottom">
      <view class="input-wrapper">
        <textarea
          class="input-textarea"
          v-model="answerText"
          placeholder="请输入你的回答..."
          placeholder-class="placeholder"
          :maxlength="2000"
          auto-height
          :adjust-position="true"
        />
        <view class="input-actions">
          <view class="char-count">
            <text>{{ answerText.length }}/2000</text>
          </view>
          <button 
            class="submit-btn" 
            :disabled="!answerText.trim()"
            @click="submitAnswer"
          >
            <text>{{ currentIndex >= totalCount ? '结束面试' : '提交' }}</text>
          </button>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { submitAnswer, finishInterview } from '@/api/interview'

interface Message {
  type: 'ai' | 'user' | 'feedback'
  content: string
  score?: number
  feedback?: string
  suggestion?: string
  duration?: string
}

const sessionId = ref<number>(0)
const currentIndex = ref(1)
const totalCount = ref(5)
const timer = ref(0)
const answerText = ref('')
const messages = ref<Message[]>([])
const scrollToId = ref('')

let timerInterval: number | null = null

onLoad((options: any) => {
  if (options?.id) {
    sessionId.value = parseInt(options.id)
  }
  if (options?.question) {
    const question = decodeURIComponent(options.question)
    messages.value.push({ type: 'ai', content: question })
  }
  if (options?.count) {
    totalCount.value = parseInt(options.count)
  }
})

onMounted(() => {
  startTimer()
  scrollToBottom()
})

onUnmounted(() => {
  stopTimer()
})

function startTimer() {
  timerInterval = setInterval(() => {
    timer.value++
  }, 1000) as unknown as number
}

function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval)
    timerInterval = null
  }
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

function scrollToBottom() {
  setTimeout(() => {
    scrollToId.value = 'msg-' + (messages.value.length - 1)
  }, 100)
}

watch(messages, () => {
  scrollToBottom()
})

async function submitAnswer() {
  if (!answerText.value.trim()) return
  
  const answerDuration = timer.value
  messages.value.push({
    type: 'user',
    content: answerText.value,
    duration: `用时 ${formatTime(answerDuration)}`
  })
  
  answerText.value = ''
  stopTimer()
  
  uni.showLoading({
    title: 'AI评分中...'
  })
  
  try {
    if (currentIndex.value >= totalCount.value) {
      const report = await finishInterview(sessionId.value)
      
      messages.value.push({
        type: 'feedback',
        content: '',
        score: report.total_score,
        feedback: report.summary,
        suggestion: report.suggestions.join('\n')
      })
      
      uni.hideLoading()
      
      setTimeout(() => {
        uni.showModal({
          title: '面试结束',
          content: `您的总得分为 ${report.total_score} 分，是否查看详细报告？`,
          success: (res) => {
            if (res.confirm) {
              uni.redirectTo({
                url: `/pages/interview/report?id=${sessionId.value}`
              })
            } else {
              uni.switchTab({
                url: '/pages/home/home'
              })
            }
          }
        })
      }, 500)
    } else {
      const result = await submitAnswer(sessionId.value, {
        answer_text: messages.value[messages.value.length - 1].content,
        answer_duration_seconds: answerDuration
      })
      
      messages.value.push({
        type: 'feedback',
        content: '',
        score: result.score,
        feedback: result.feedback,
        suggestion: result.suggestion
      })
      
      currentIndex.value++
      timer.value = 0
      startTimer()
      
      if (result.next_question) {
        messages.value.push({
          type: 'ai',
          content: result.next_question
        })
      }
      
      uni.hideLoading()
    }
  } catch (error) {
    uni.hideLoading()
    uni.showToast({
      title: '提交失败，请重试',
      icon: 'none'
    })
    timer.value = answerDuration
    startTimer()
  }
}

function handleExit() {
  uni.showModal({
    title: '确认退出',
    content: '退出后面试进度将不会保存，确定要退出吗？',
    success: (res) => {
      if (res.confirm) {
        stopTimer()
        uni.navigateBack()
      }
    }
  })
}
</script>

<style lang="scss" scoped>
.room-container {
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
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.06);
  
  .back-btn {
    width: 64rpx;
    height: 64rpx;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 40rpx;
    color: #333;
  }
  
  .nav-center {
    text-align: center;
    
    .title {
      display: block;
      font-size: 32rpx;
      font-weight: 600;
      color: #1f2937;
    }
    
    .progress {
      font-size: 22rpx;
      color: #6b7280;
    }
  }
  
  .timer {
    display: flex;
    align-items: center;
    gap: 8rpx;
    padding: 12rpx 20rpx;
    background: rgba(99, 102, 241, 0.1);
    border-radius: 20rpx;
    
    .timer-icon {
      font-size: 28rpx;
    }
    
    .timer-text {
      font-size: 26rpx;
      font-weight: 600;
      color: #6366f1;
      font-family: monospace;
    }
  }
}

.chat-container {
  flex: 1;
  padding: 24rpx;
}

.message-item {
  margin-bottom: 32rpx;
  
  &.is-ai {
    .ai-message {
      display: flex;
      gap: 16rpx;
      
      .avatar {
        width: 72rpx;
        height: 72rpx;
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 32rpx;
        flex-shrink: 0;
      }
      
      .bubble {
        max-width: 80%;
        padding: 24rpx;
        background: #fff;
        border-radius: 24rpx;
        border-bottom-left-radius: 8rpx;
        box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.06);
        
        .content {
          font-size: 28rpx;
          color: #1f2937;
          line-height: 1.6;
        }
      }
    }
  }
  
  &.is-user {
    display: flex;
    justify-content: flex-end;
    
    .user-message {
      display: flex;
      gap: 16rpx;
      flex-direction: row-reverse;
      
      .avatar {
        width: 72rpx;
        height: 72rpx;
        background: #e5e7eb;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 32rpx;
        flex-shrink: 0;
      }
      
      .bubble {
        max-width: 80%;
        padding: 24rpx;
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
        border-radius: 24rpx;
        border-bottom-right-radius: 8rpx;
        
        .content {
          font-size: 28rpx;
          color: #fff;
          line-height: 1.6;
          display: block;
          margin-bottom: 8rpx;
        }
        
        .duration {
          font-size: 22rpx;
          color: rgba(255, 255, 255, 0.7);
        }
      }
    }
  }
  
  &.is-feedback {
    .feedback-card {
      background: #fff;
      border-radius: 20rpx;
      padding: 28rpx;
      box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.06);
      
      .score-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 24rpx;
        padding-bottom: 24rpx;
        border-bottom: 1rpx solid #f3f4f6;
        
        .score-label {
          font-size: 28rpx;
          color: #6b7280;
        }
        
        .score-value {
          display: flex;
          align-items: baseline;
          
          .num {
            font-size: 56rpx;
            font-weight: 700;
            color: #6366f1;
          }
          
          .unit {
            font-size: 28rpx;
            color: #6b7280;
            margin-left: 4rpx;
          }
        }
      }
      
      .feedback-content {
        .feedback-item {
          margin-bottom: 20rpx;
          
          &:last-child {
            margin-bottom: 0;
          }
          
          .feedback-title {
            display: block;
            font-size: 26rpx;
            color: #1f2937;
            font-weight: 500;
            margin-bottom: 12rpx;
          }
          
          .feedback-text {
            font-size: 26rpx;
            color: #4b5563;
            line-height: 1.6;
          }
        }
      }
    }
  }
}

.input-area {
  padding: 20rpx 32rpx;
  background: #fff;
  box-shadow: 0 -4rpx 16rpx rgba(0, 0, 0, 0.06);
}

.input-wrapper {
  .input-textarea {
    width: 100%;
    min-height: 120rpx;
    padding: 24rpx;
    background: #f9fafb;
    border: 2rpx solid #e5e7eb;
    border-radius: 16rpx;
    font-size: 28rpx;
    line-height: 1.6;
    
    &:focus {
      border-color: #6366f1;
      background: #fff;
    }
  }
  
  .placeholder {
    color: #d1d5db;
  }
  
  .input-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 16rpx;
    
    .char-count {
      font-size: 24rpx;
      color: #9ca3af;
    }
    
    .submit-btn {
      padding: 20rpx 48rpx;
      background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
      border-radius: 40rpx;
      border: none;
      font-size: 28rpx;
      color: #fff;
      font-weight: 500;
      
      &[disabled] {
        opacity: 0.5;
      }
    }
  }
}

.safe-area-bottom {
  padding-bottom: calc(20rpx + env(safe-area-inset-bottom));
}
</style>
