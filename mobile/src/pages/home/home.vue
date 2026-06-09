<template>
  <view class="home-container">
    <view class="header">
      <view class="user-info">
        <view class="avatar">
          <text>👤</text>
        </view>
        <view class="welcome">
          <text class="greeting">你好，{{ user?.username || '用户' }}</text>
          <text class="subtitle">准备好开始今天的面试了吗？</text>
        </view>
      </view>
      <view class="header-actions">
        <view class="action-btn" @click="goToSettings">
          <text>⚙️</text>
        </view>
      </view>
    </view>

    <view class="quick-start">
      <view class="start-card" @click="startQuickInterview">
        <view class="card-content">
          <view class="icon-wrapper">
            <text class="start-icon">🚀</text>
          </view>
          <view class="card-text">
            <text class="card-title">快速开始面试</text>
            <text class="card-desc">一键进入面试，体验AI面试官</text>
          </view>
        </view>
        <view class="arrow">
          <text>→</text>
        </view>
      </view>
    </view>

    <view class="section">
      <view class="section-header">
        <text class="section-title">面试类型</text>
      </view>
      <view class="type-grid">
        <view 
          class="type-card" 
          v-for="type in interviewTypes" 
          :key="type.key"
          @click="selectType(type)"
        >
          <view class="type-icon">{{ type.icon }}</view>
          <text class="type-name">{{ type.name }}</text>
          <text class="type-desc">{{ type.desc }}</text>
        </view>
      </view>
    </view>

    <view class="section">
      <view class="section-header">
        <text class="section-title">最近面试</text>
        <text class="view-all" @click="viewAllHistory">查看全部 →</text>
      </view>
      <view v-if="historyList.length > 0" class="history-list">
        <view 
          class="history-item" 
          v-for="item in historyList" 
          :key="item.id"
          @click="viewReport(item.id)"
        >
          <view class="history-info">
            <text class="history-position">{{ item.target_position }}</text>
            <text class="history-time">{{ formatTime(item.created_at) }}</text>
          </view>
          <view class="history-score" v-if="item.total_score">
            <text class="score-num">{{ item.total_score }}</text>
            <text class="score-label">分</text>
          </view>
          <view class="history-status" v-else>
            <text>{{ item.status === 'in_progress' ? '进行中' : '已结束' }}</text>
          </view>
        </view>
      </view>
      <view v-else class="empty-history">
        <text class="empty-icon">📋</text>
        <text class="empty-text">暂无面试记录</text>
        <text class="empty-hint">开始你的第一次AI面试吧！</text>
      </view>
    </view>

    <view class="section">
      <view class="section-header">
        <text class="section-title">面试技巧</text>
      </view>
      <view class="tips-card">
        <view class="tip-item">
          <text class="tip-num">1</text>
          <text class="tip-text">提前了解目标岗位的技术要求</text>
        </view>
        <view class="tip-item">
          <text class="tip-num">2</text>
          <text class="tip-text">准备常见问题的结构化回答</text>
        </view>
        <view class="tip-item">
          <text class="tip-num">3</text>
          <text class="tip-text">保持回答简洁，突出重点</text>
        </view>
        <view class="tip-item">
          <text class="tip-num">4</text>
          <text class="tip-text">注意时间管理，合理分配答题时间</text>
        </view>
      </view>
    </view>
    
    <CustomTabBar />
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { storage } from '@/utils/storage'
import { listInterviewSessions, type InterviewSession } from '@/api/interview'
import CustomTabBar from '@/components/TabBar/CustomTabBar.vue'

const user = ref<any>(null)
const historyList = ref<InterviewSession[]>([])

const interviewTypes = [
  { key: 'technical', name: '技术面试', desc: '深入技术能力考察', icon: '💻' },
  { key: 'behavioral', name: '行为面试', desc: '考察软技能和经验', icon: '🧠' },
  { key: 'comprehensive', name: '综合面试', desc: '全面能力评估', icon: '🎯' }
]

onMounted(() => {
  user.value = storage.get('user')
  loadHistory()
})

async function loadHistory() {
  try {
    historyList.value = await listInterviewSessions()
  } catch (error) {
    console.error('加载面试历史失败:', error)
  }
}

function selectType(type: any) {
  uni.navigateTo({
    url: `/pages/interview/setup?type=${type.key}`
  })
}

function startQuickInterview() {
  uni.navigateTo({
    url: '/pages/interview/setup'
  })
}

function viewReport(sessionId: number) {
  uni.navigateTo({
    url: `/pages/interview/report?id=${sessionId}`
  })
}

function viewAllHistory() {
  uni.navigateTo({
    url: '/pages/interview/report'
  })
}

function goToSettings() {
  uni.navigateTo({
    url: '/pages/profile/profile'
  })
}

function formatTime(timeStr: string): string {
  const date = new Date(timeStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  
  if (diff < 60000) {
    return '刚刚'
  } else if (diff < 3600000) {
    return `${Math.floor(diff / 60000)}分钟前`
  } else if (diff < 86400000) {
    return `${Math.floor(diff / 3600000)}小时前`
  } else {
    return `${date.getMonth() + 1}/${date.getDate()}`
  }
}
</script>

<style lang="scss" scoped>
.home-container {
  min-height: 100vh;
  background: #f5f7fa;
  padding-bottom: calc(env(safe-area-inset-bottom) + 120rpx);
}

.header {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  padding: 60rpx 32rpx 48rpx;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 20rpx;
  
  .avatar {
    width: 96rpx;
    height: 96rpx;
    background: rgba(255, 255, 255, 0.2);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 40rpx;
  }
  
  .welcome {
    .greeting {
      display: block;
      font-size: 34rpx;
      font-weight: 600;
      color: #fff;
      margin-bottom: 8rpx;
    }
    
    .subtitle {
      font-size: 26rpx;
      color: rgba(255, 255, 255, 0.8);
    }
  }
}

.header-actions {
  .action-btn {
    width: 72rpx;
    height: 72rpx;
    background: rgba(255, 255, 255, 0.2);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 32rpx;
  }
}

.quick-start {
  padding: 0 32rpx;
  margin-top: -32rpx;
  
  .start-card {
    background: #fff;
    border-radius: 24rpx;
    padding: 32rpx;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 8rpx 32rpx rgba(99, 102, 241, 0.15);
    
    .card-content {
      display: flex;
      align-items: center;
      gap: 24rpx;
      
      .icon-wrapper {
        width: 88rpx;
        height: 88rpx;
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        border-radius: 20rpx;
        display: flex;
        align-items: center;
        justify-content: center;
        
        .start-icon {
          font-size: 44rpx;
        }
      }
      
      .card-text {
        .card-title {
          display: block;
          font-size: 32rpx;
          font-weight: 600;
          color: #1f2937;
          margin-bottom: 8rpx;
        }
        
        .card-desc {
          font-size: 26rpx;
          color: #6b7280;
        }
      }
    }
    
    .arrow {
      font-size: 40rpx;
      color: #6366f1;
    }
  }
}

.section {
  padding: 32rpx;
  
  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24rpx;
    
    .section-title {
      font-size: 32rpx;
      font-weight: 600;
      color: #1f2937;
    }
    
    .view-all {
      font-size: 26rpx;
      color: #6366f1;
    }
  }
}

.type-grid {
  display: flex;
  gap: 20rpx;
}

.type-card {
  flex: 1;
  background: #fff;
  border-radius: 20rpx;
  padding: 28rpx 20rpx;
  text-align: center;
  box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.06);
  
  .type-icon {
    font-size: 48rpx;
    margin-bottom: 16rpx;
  }
  
  .type-name {
    display: block;
    font-size: 28rpx;
    font-weight: 600;
    color: #1f2937;
    margin-bottom: 8rpx;
  }
  
  .type-desc {
    font-size: 22rpx;
    color: #6b7280;
  }
}

.history-list {
  .history-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 28rpx;
    background: #fff;
    border-radius: 16rpx;
    margin-bottom: 16rpx;
    
    .history-info {
      .history-position {
        display: block;
        font-size: 30rpx;
        font-weight: 500;
        color: #1f2937;
        margin-bottom: 8rpx;
      }
      
      .history-time {
        font-size: 24rpx;
        color: #9ca3af;
      }
    }
    
    .history-score {
      display: flex;
      align-items: baseline;
      
      .score-num {
        font-size: 40rpx;
        font-weight: 700;
        color: #6366f1;
      }
      
      .score-label {
        font-size: 24rpx;
        color: #6b7280;
        margin-left: 4rpx;
      }
    }
    
    .history-status {
      font-size: 24rpx;
      color: #f59e0b;
      padding: 8rpx 16rpx;
      background: rgba(245, 158, 11, 0.1);
      border-radius: 20rpx;
    }
  }
}

.empty-history {
  background: #fff;
  border-radius: 16rpx;
  padding: 48rpx;
  text-align: center;
  
  .empty-icon {
    font-size: 64rpx;
    margin-bottom: 16rpx;
  }
  
  .empty-text {
    display: block;
    font-size: 28rpx;
    color: #6b7280;
    margin-bottom: 8rpx;
  }
  
  .empty-hint {
    font-size: 24rpx;
    color: #9ca3af;
  }
}

.tips-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  
  .tip-item {
    display: flex;
    align-items: center;
    gap: 16rpx;
    padding: 16rpx 0;
    border-bottom: 1rpx solid #f3f4f6;
    
    &:last-child {
      border-bottom: none;
    }
    
    .tip-num {
      width: 40rpx;
      height: 40rpx;
      background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 24rpx;
      font-weight: 600;
      color: #fff;
    }
    
    .tip-text {
      font-size: 26rpx;
      color: #4b5563;
    }
  }
}
</style>
