<template>
  <view class="profile-container">
    <view class="header-bg"></view>
    
    <view class="profile-header">
      <view class="avatar-wrapper">
        <view class="avatar">
          <text>👤</text>
        </view>
        <view class="edit-avatar">
          <text>📷</text>
        </view>
      </view>
      <text class="username">{{ user?.username || '用户' }}</text>
      <text class="email">{{ user?.email || '' }}</text>
    </view>

    <view class="stats-card">
      <view class="stat-item">
        <text class="stat-num">{{ stats.interviewCount }}</text>
        <text class="stat-label">面试次数</text>
      </view>
      <view class="stat-divider"></view>
      <view class="stat-item">
        <text class="stat-num">{{ stats.avgScore }}</text>
        <text class="stat-label">平均分</text>
      </view>
      <view class="stat-divider"></view>
      <view class="stat-item">
        <text class="stat-num">{{ stats.bestScore }}</text>
        <text class="stat-label">最高分</text>
      </view>
    </view>

    <view class="menu-list">
      <view class="menu-item" @click="goToHistory">
        <view class="menu-icon">📋</view>
        <text class="menu-text">面试历史</text>
        <text class="menu-arrow">→</text>
      </view>
      <view class="menu-item" @click="goToSettings">
        <view class="menu-icon">⚙️</view>
        <text class="menu-text">设置</text>
        <text class="menu-arrow">→</text>
      </view>
      <view class="menu-item" @click="goToHelp">
        <view class="menu-icon">❓</view>
        <text class="menu-text">帮助与反馈</text>
        <text class="menu-arrow">→</text>
      </view>
      <view class="menu-item" @click="goToAbout">
        <view class="menu-icon">ℹ️</view>
        <text class="menu-text">关于我们</text>
        <text class="menu-arrow">→</text>
      </view>
    </view>

    <view class="logout-section">
      <button class="logout-btn" @click="handleLogout">
        <text>退出登录</text>
      </button>
    </view>
    
    <CustomTabBar />
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { storage } from '@/utils/storage'
import { listInterviewSessions } from '@/api/interview'
import CustomTabBar from '@/components/TabBar/CustomTabBar.vue'

const user = ref<any>(null)
const stats = ref({
  interviewCount: 0,
  avgScore: 0,
  bestScore: 0
})

onMounted(() => {
  user.value = storage.get('user')
  loadStats()
})

async function loadStats() {
  try {
    const sessions = await listInterviewSessions()
    const completedSessions = sessions.filter(s => s.total_score !== null)
    
    stats.value.interviewCount = sessions.length
    
    if (completedSessions.length > 0) {
      const scores = completedSessions.map(s => s.total_score as number)
      stats.value.avgScore = Math.round(scores.reduce((a, b) => a + b, 0) / scores.length)
      stats.value.bestScore = Math.max(...scores)
    }
  } catch (error) {
    console.error('加载统计数据失败:', error)
  }
}

function goToHistory() {
  uni.navigateTo({
    url: '/pages/interview/report'
  })
}

function goToSettings() {
  uni.showToast({
    title: '设置功能开发中',
    icon: 'none'
  })
}

function goToHelp() {
  uni.showToast({
    title: '帮助功能开发中',
    icon: 'none'
  })
}

function goToAbout() {
  uni.showModal({
    title: '关于AI面试助手',
    content: '版本：1.0.0\n\nAI面试助手是一款基于大语言模型的智能面试辅助工具，帮助求职者提升面试技巧，获得更好的职业发展机会。',
    showCancel: false
  })
}

function handleLogout() {
  uni.showModal({
    title: '确认退出',
    content: '确定要退出登录吗？',
    success: (res) => {
      if (res.confirm) {
        storage.remove('access_token')
        storage.remove('user')
        uni.redirectTo({
          url: '/pages/login/login'
        })
      }
    }
  })
}
</script>

<style lang="scss" scoped>
.profile-container {
  min-height: 100vh;
  background: #f5f7fa;
  padding-bottom: calc(env(safe-area-inset-bottom) + 120rpx);
}

.header-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 360rpx;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
}

.profile-header {
  position: relative;
  padding: 80rpx 32rpx 40rpx;
  text-align: center;
  
  .avatar-wrapper {
    position: relative;
    width: 160rpx;
    height: 160rpx;
    margin: 0 auto 24rpx;
    
    .avatar {
      width: 100%;
      height: 100%;
      background: #fff;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 64rpx;
      box-shadow: 0 8rpx 32rpx rgba(0, 0, 0, 0.15);
    }
    
    .edit-avatar {
      position: absolute;
      bottom: 0;
      right: 0;
      width: 48rpx;
      height: 48rpx;
      background: #6366f1;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 24rpx;
      border: 4rpx solid #fff;
    }
  }
  
  .username {
    display: block;
    font-size: 36rpx;
    font-weight: 600;
    color: #fff;
    margin-bottom: 8rpx;
  }
  
  .email {
    font-size: 26rpx;
    color: rgba(255, 255, 255, 0.8);
  }
}

.stats-card {
  display: flex;
  align-items: center;
  justify-content: space-around;
  background: #fff;
  border-radius: 20rpx;
  padding: 32rpx;
  margin: 0 32rpx -40rpx;
  position: relative;
  box-shadow: 0 8rpx 32rpx rgba(0, 0, 0, 0.08);
  
  .stat-item {
    text-align: center;
    
    .stat-num {
      display: block;
      font-size: 44rpx;
      font-weight: 700;
      color: #6366f1;
      margin-bottom: 8rpx;
    }
    
    .stat-label {
      font-size: 24rpx;
      color: #6b7280;
    }
  }
  
  .stat-divider {
    width: 1rpx;
    height: 60rpx;
    background: #e5e7eb;
  }
}

.menu-list {
  margin: 60rpx 32rpx;
  
  .menu-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 28rpx 32rpx;
    background: #fff;
    border-radius: 16rpx;
    margin-bottom: 16rpx;
    box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);
    
    .menu-icon {
      font-size: 36rpx;
      margin-right: 20rpx;
    }
    
    .menu-text {
      flex: 1;
      font-size: 30rpx;
      color: #1f2937;
    }
    
    .menu-arrow {
      font-size: 32rpx;
      color: #9ca3af;
    }
  }
}

.logout-section {
  padding: 0 32rpx;
  
  .logout-btn {
    width: 100%;
    height: 88rpx;
    background: #fff;
    border: 2rpx solid #ef4444;
    border-radius: 16rpx;
    font-size: 30rpx;
    color: #ef4444;
    font-weight: 500;
  }
}
</style>
