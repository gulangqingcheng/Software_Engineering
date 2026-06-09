<template>
  <view class="custom-tabbar safe-area-bottom">
    <view 
      v-for="item in tabs" 
      :key="item.path"
      class="tab-item"
      :class="{ active: currentPath === item.path }"
      @click="switchTab(item.path)"
    >
      <view class="tab-icon">{{ item.icon }}</view>
      <text class="tab-text">{{ item.text }}</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const tabs = [
  { path: '/pages/home/home', text: '首页', icon: '🏠' },
  { path: '/pages/interview/setup', text: '面试', icon: '🎯' },
  { path: '/pages/profile/profile', text: '我的', icon: '👤' }
]

const currentPath = ref('/pages/home/home')

function updateCurrentPath() {
  const pages = getCurrentPages()
  if (pages.length > 0) {
    const page = pages[pages.length - 1]
    currentPath.value = '/' + page.route
  }
}

function switchTab(path: string) {
  if (currentPath.value === path) return
  uni.switchTab({ url: path })
}

onMounted(() => {
  updateCurrentPath()
})
</script>

<style lang="scss" scoped>
.custom-tabbar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 100rpx;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-around;
  box-shadow: 0 -4rpx 16rpx rgba(0, 0, 0, 0.06);
  z-index: 999;
}

.tab-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  height: 100%;
  transition: all 0.3s ease;
  
  .tab-icon {
    font-size: 40rpx;
    margin-bottom: 8rpx;
  }
  
  .tab-text {
    font-size: 22rpx;
    color: #9ca3af;
  }
  
  &.active {
    .tab-icon {
      transform: scale(1.1);
    }
    
    .tab-text {
      color: #6366f1;
      font-weight: 500;
    }
  }
}

.safe-area-bottom {
  padding-bottom: env(safe-area-inset-bottom);
  height: calc(100rpx + env(safe-area-inset-bottom));
}
</style>
