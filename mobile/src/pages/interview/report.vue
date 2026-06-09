<template>
  <view class="report-container">
    <view class="navbar">
      <view class="back-btn" @click="goBack">
        <text>←</text>
      </view>
      <text class="title">面试报告</text>
      <view class="placeholder"></view>
    </view>

    <view v-if="loading" class="loading">
      <text class="loading-icon">🔄</text>
      <text class="loading-text">加载中...</text>
    </view>

    <scroll-view v-else scroll-y class="content">
      <view class="score-section">
        <view class="score-circle">
          <text class="score-num">{{ report?.total_score || 0 }}</text>
          <text class="score-label">总分</text>
        </view>
        <view class="score-level" :class="scoreLevel">
          <text>{{ scoreLevelText }}</text>
        </view>
      </view>

      <view class="section-card">
        <view class="section-title">
          <text class="icon">📊</text>
          <text class="text">维度得分</text>
        </view>
        <view class="dimension-list">
          <view v-for="(score, key) in report?.dimension_scores" :key="key" class="dimension-item">
            <text class="dimension-name">{{ getDimensionName(key as string) }}</text>
            <view class="dimension-bar">
              <view class="bar-fill" :style="{ width: score + '%' }"></view>
            </view>
            <text class="dimension-score">{{ score }}</text>
          </view>
        </view>
      </view>

      <view class="section-card">
        <view class="section-title">
          <text class="icon">📝</text>
          <text class="text">总体评价</text>
        </view>
        <view class="summary-content">
          <text>{{ report?.summary || '暂无评价' }}</text>
        </view>
      </view>

      <view class="section-card">
        <view class="section-title">
          <text class="icon">✨</text>
          <text class="text">优势</text>
        </view>
        <view class="list-content">
          <view v-for="(item, index) in report?.strengths" :key="index" class="list-item">
            <text class="list-icon">✓</text>
            <text class="list-text">{{ item }}</text>
          </view>
          <view v-if="!report?.strengths?.length" class="empty-list">
            <text>暂无优势评价</text>
          </view>
        </view>
      </view>

      <view class="section-card">
        <view class="section-title">
          <text class="icon">💪</text>
          <text class="text">待改进</text>
        </view>
        <view class="list-content">
          <view v-for="(item, index) in report?.weaknesses" :key="index" class="list-item">
            <text class="list-icon">✗</text>
            <text class="list-text">{{ item }}</text>
          </view>
          <view v-if="!report?.weaknesses?.length" class="empty-list">
            <text>暂无待改进项</text>
          </view>
        </view>
      </view>

      <view class="section-card">
        <view class="section-title">
          <text class="icon">💡</text>
          <text class="text">改进建议</text>
        </view>
        <view class="list-content">
          <view v-for="(item, index) in report?.suggestions" :key="index" class="list-item">
            <text class="list-icon">{{ index + 1 }}</text>
            <text class="list-text">{{ item }}</text>
          </view>
          <view v-if="!report?.suggestions?.length" class="empty-list">
            <text>暂无改进建议</text>
          </view>
        </view>
      </view>

      <view v-if="report?.turn_details?.length" class="section-card">
        <view class="section-title">
          <text class="icon">📋</text>
          <text class="text">答题详情</text>
        </view>
        <view class="turn-list">
          <view v-for="(turn, index) in report.turn_details" :key="index" class="turn-item">
            <view class="turn-header">
              <text class="turn-num">第 {{ index + 1 }} 题</text>
              <view class="turn-score">
                <text>{{ turn.score }}分</text>
              </view>
            </view>
            <view class="turn-content">
              <view class="turn-question">
                <text class="label">问题</text>
                <text class="value">{{ turn.question }}</text>
              </view>
              <view class="turn-answer">
                <text class="label">你的回答</text>
                <text class="value">{{ turn.answer }}</text>
              </view>
              <view class="turn-feedback">
                <text class="label">评价</text>
                <text class="value">{{ turn.feedback }}</text>
              </view>
              <view class="turn-suggestion">
                <text class="label">建议</text>
                <text class="value">{{ turn.suggestion }}</text>
              </view>
            </view>
          </view>
        </view>
      </view>

      <view class="bottom-space"></view>
    </scroll-view>

    <view class="bottom-bar safe-area-bottom">
      <button class="btn btn-primary" @click="shareReport">
        <text>分享报告</text>
      </button>
      <button class="btn btn-outline" @click="startNewInterview">
        <text>再次面试</text>
      </button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { getInterviewReport, type InterviewReport } from '@/api/interview'

const sessionId = ref<number | null>(null)
const loading = ref(true)
const report = ref<InterviewReport | null>(null)

onLoad((options: any) => {
  if (options?.id) {
    sessionId.value = parseInt(options.id)
  }
})

onMounted(() => {
  if (sessionId.value) {
    loadReport()
  }
})

async function loadReport() {
  if (!sessionId.value) return
  
  loading.value = true
  
  try {
    report.value = await getInterviewReport(sessionId.value)
  } catch (error) {
    uni.showToast({
      title: '加载报告失败',
      icon: 'none'
    })
  } finally {
    loading.value = false
  }
}

const scoreLevel = computed(() => {
  const score = report.value?.total_score || 0
  if (score >= 90) return 'level-excellent'
  if (score >= 80) return 'level-good'
  if (score >= 60) return 'level-pass'
  return 'level-fail'
})

const scoreLevelText = computed(() => {
  const score = report.value?.total_score || 0
  if (score >= 90) return '优秀'
  if (score >= 80) return '良好'
  if (score >= 60) return '及格'
  return '需努力'
})

function getDimensionName(key: string): string {
  const names: Record<string, string> = {
    'relevance': '岗位相关性',
    'technical_depth': '技术深度',
    'logic': '逻辑结构',
    'cases': '案例与结果',
    'communication': '表达沟通',
    'time_control': '时间控制'
  }
  return names[key] || key
}

function goBack() {
  uni.navigateBack()
}

function shareReport() {
  uni.showToast({
    title: '分享功能开发中',
    icon: 'none'
  })
}

function startNewInterview() {
  uni.navigateTo({
    url: '/pages/interview/setup'
  })
}
</script>

<style lang="scss" scoped>
.report-container {
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

.loading {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  
  .loading-icon {
    font-size: 64rpx;
    animation: spin 1s linear infinite;
    margin-bottom: 20rpx;
  }
  
  .loading-text {
    font-size: 28rpx;
    color: #6b7280;
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.content {
  flex: 1;
  padding: 24rpx;
}

.score-section {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  border-radius: 24rpx;
  padding: 48rpx;
  text-align: center;
  margin-bottom: 24rpx;
  
  .score-circle {
    margin-bottom: 24rpx;
    
    .score-num {
      display: block;
      font-size: 120rpx;
      font-weight: 700;
      color: #fff;
      line-height: 1;
    }
    
    .score-label {
      font-size: 28rpx;
      color: rgba(255, 255, 255, 0.8);
    }
  }
  
  .score-level {
    display: inline-block;
    padding: 12rpx 32rpx;
    border-radius: 40rpx;
    font-size: 28rpx;
    font-weight: 600;
    
    &.level-excellent {
      background: rgba(34, 197, 94, 0.3);
      color: #22c55e;
    }
    
    &.level-good {
      background: rgba(59, 130, 246, 0.3);
      color: #3b82f6;
    }
    
    &.level-pass {
      background: rgba(245, 158, 11, 0.3);
      color: #f59e0b;
    }
    
    &.level-fail {
      background: rgba(239, 68, 68, 0.3);
      color: #ef4444;
    }
  }
}

.section-card {
  background: #fff;
  border-radius: 20rpx;
  padding: 28rpx;
  margin-bottom: 24rpx;
  
  .section-title {
    display: flex;
    align-items: center;
    gap: 12rpx;
    margin-bottom: 24rpx;
    
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

.dimension-list {
  .dimension-item {
    display: flex;
    align-items: center;
    gap: 16rpx;
    margin-bottom: 20rpx;
    
    &:last-child {
      margin-bottom: 0;
    }
    
    .dimension-name {
      width: 140rpx;
      font-size: 26rpx;
      color: #4b5563;
    }
    
    .dimension-bar {
      flex: 1;
      height: 16rpx;
      background: #f3f4f6;
      border-radius: 8rpx;
      overflow: hidden;
      
      .bar-fill {
        height: 100%;
        background: linear-gradient(90deg, #6366f1 0%, #8b5cf6 100%);
        border-radius: 8rpx;
        transition: width 0.5s ease;
      }
    }
    
    .dimension-score {
      width: 60rpx;
      font-size: 26rpx;
      font-weight: 600;
      color: #6366f1;
      text-align: right;
    }
  }
}

.summary-content {
  text {
    font-size: 28rpx;
    color: #4b5563;
    line-height: 1.8;
  }
}

.list-content {
  .list-item {
    display: flex;
    align-items: flex-start;
    gap: 12rpx;
    padding: 16rpx 0;
    border-bottom: 1rpx solid #f3f4f6;
    
    &:last-child {
      border-bottom: none;
    }
    
    .list-icon {
      width: 36rpx;
      height: 36rpx;
      background: rgba(99, 102, 241, 0.1);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 22rpx;
      color: #6366f1;
      flex-shrink: 0;
    }
    
    .list-text {
      font-size: 26rpx;
      color: #4b5563;
      line-height: 1.6;
    }
  }
  
  .empty-list {
    text-align: center;
    padding: 24rpx;
    color: #9ca3af;
    font-size: 26rpx;
  }
}

.turn-list {
  .turn-item {
    margin-bottom: 28rpx;
    padding-bottom: 28rpx;
    border-bottom: 1rpx solid #f3f4f6;
    
    &:last-child {
      margin-bottom: 0;
      padding-bottom: 0;
      border-bottom: none;
    }
    
    .turn-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20rpx;
      
      .turn-num {
        font-size: 28rpx;
        font-weight: 600;
        color: #1f2937;
      }
      
      .turn-score {
        padding: 8rpx 20rpx;
        background: rgba(99, 102, 241, 0.1);
        border-radius: 20rpx;
        font-size: 26rpx;
        font-weight: 600;
        color: #6366f1;
      }
    }
    
    .turn-content {
      .turn-question, .turn-answer, .turn-feedback, .turn-suggestion {
        margin-bottom: 16rpx;
        
        .label {
          display: block;
          font-size: 24rpx;
          color: #6b7280;
          margin-bottom: 8rpx;
        }
        
        .value {
          font-size: 26rpx;
          color: #4b5563;
          line-height: 1.6;
        }
      }
    }
  }
}

.bottom-space {
  height: 160rpx;
}

.bottom-bar {
  display: flex;
  gap: 20rpx;
  padding: 20rpx 32rpx;
  background: #fff;
  box-shadow: 0 -4rpx 16rpx rgba(0, 0, 0, 0.06);
}

.btn {
  flex: 1;
  height: 88rpx;
  border-radius: 16rpx;
  font-size: 28rpx;
  font-weight: 600;
  border: none;
  
  &-primary {
    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
    color: #fff;
  }
  
  &-outline {
    background: #fff;
    border: 2rpx solid #6366f1;
    color: #6366f1;
  }
}

.safe-area-bottom {
  padding-bottom: calc(20rpx + env(safe-area-inset-bottom));
}
</style>
