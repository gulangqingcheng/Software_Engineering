<script setup lang="ts">
import { ref } from 'vue'

/**
 * 结构化报告卡片组件
 * 递归渲染 JSON 结构化报告，支持评分进度条、问题列表、建议列表、可折叠/展开
 */

defineProps<{
  /** 报告数据（JSON 对象） */
  report: Record<string, any>
  /** 报告标题 */
  title?: string
}>()

/** 是否折叠 */
const collapsed = ref(false)

/**
 * 切换折叠状态
 */
function toggleCollapse() {
  collapsed.value = !collapsed.value
}

/**
 * 判断值是否为对象（用于递归渲染）
 */
function isObject(val: any): val is Record<string, any> {
  return val !== null && typeof val === 'object' && !Array.isArray(val)
}

/**
 * 判断值是否为数组
 */
function isArray(val: any): val is any[] {
  return Array.isArray(val)
}

/**
 * 判断是否为数字（用于评分渲染）
 */
function isNumeric(val: any): boolean {
  return typeof val === 'number'
}

/**
 * 判断 key 是否与评分相关
 */
function isScoreKey(key: string): boolean {
  const lowerKey = key.toLowerCase()
  return (
    lowerKey.includes('score') ||
    lowerKey.includes('评分') ||
    lowerKey.includes('得分') ||
    lowerKey.includes('rating')
  )
}

/**
 * 判断 key 是否为列表类型
 */
function isListKey(key: string): boolean {
  const lowerKey = key.toLowerCase()
  return (
    lowerKey.includes('strength') ||
    lowerKey.includes('weakness') ||
    lowerKey.includes('suggestion') ||
    lowerKey.includes('point') ||
    lowerKey.includes('优点') ||
    lowerKey.includes('缺点') ||
    lowerKey.includes('建议') ||
    lowerKey.includes('要点')
  )
}

/**
 * 获取进度条颜色
 */
function getScoreColor(score: number): string {
  if (score >= 80) return '#0F6E56'
  if (score >= 60) return '#BA7517'
  return '#A32D2D'
}
</script>

<template>
  <div class="report-card">
    <!-- 报告头部：标题 + 折叠按钮 -->
    <div v-if="title" class="report-header card" @click="toggleCollapse">
      <div class="flex-between">
        <div class="flex gap-sm">
          <el-icon :size="18" color="#534AB7"><Document /></el-icon>
          <span class="report-title">{{ title }}</span>
        </div>
        <el-icon :size="16" class="collapse-icon" :class="{ collapsed: collapsed }">
          <ArrowDown />
        </el-icon>
      </div>
    </div>

    <!-- 报告内容 -->
    <div v-show="!collapsed" class="report-body">
      <div v-for="(value, key) in report" :key="key" class="report-section">
        <!-- 跳过 title 字段（已在头部显示） -->
        <template v-if="key !== 'title'">
          <!-- 评分字段：进度条 -->
          <div v-if="isScoreKey(key) && isNumeric(value)" class="report-score">
            <div class="flex-between mb-sm">
              <span class="score-label">{{ key }}</span>
              <span class="score-value" :style="{ color: getScoreColor(value) }">
                {{ value }}分
              </span>
            </div>
            <el-progress
              :percentage="Math.min(value, 100)"
              :color="getScoreColor(value)"
              :stroke-width="8"
            />
          </div>

          <!-- 列表字段 -->
          <div v-else-if="isListKey(key) && isArray(value)" class="report-list">
            <div class="list-label">{{ key }}</div>
            <ul class="list-items">
              <li v-for="(item, idx) in value" :key="idx" class="list-item">
                <span class="list-marker">{{ idx + 1 }}</span>
                <span v-if="isObject(item)">
                  <template v-for="(iv, ik) in item" :key="ik">
                    <strong v-if="ik === 'title' || ik === 'name'">{{ iv }}</strong>
                    <span v-else>{{ iv }}</span>
                    <br v-if="ik === 'title' || ik === 'name'" />
                  </template>
                </span>
                <span v-else>{{ item }}</span>
              </li>
            </ul>
          </div>

          <!-- 嵌套对象 → 递归渲染 -->
          <div v-else-if="isObject(value)" class="report-nested">
            <div class="nested-label">{{ key }}</div>
            <ReportCard :report="value" />
          </div>

          <!-- 数组（非特殊列表） -->
          <div v-else-if="isArray(value)" class="report-array">
            <div class="array-label">{{ key }}</div>
            <div v-for="(item, idx) in value" :key="idx" class="array-item">
              <template v-if="isObject(item)">
                <ReportCard :report="item" />
              </template>
              <span v-else>{{ item }}</span>
            </div>
          </div>

          <!-- 普通字段 -->
          <div v-else class="report-field">
            <span class="field-label">{{ key }}</span>
            <span class="field-value">{{ value }}</span>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.report-card {
  width: 100%;
}

/* ========== 报告头部 ========== */
.report-header {
  padding: 10px 16px;
  cursor: pointer;
  transition: background 0.2s;
}

.report-header:hover {
  background: var(--color-card-hover);
}

.report-title {
  font-size: var(--font-md);
  font-weight: 600;
  color: var(--color-text);
}

.collapse-icon {
  transition: transform 0.3s ease;
  color: var(--color-text-secondary);
}

.collapse-icon.collapsed {
  transform: rotate(-90deg);
}

/* ========== 报告内容 ========== */
.report-body {
  padding: var(--spacing-md);
  background: var(--color-card);
  border: 1px solid var(--color-border-light);
  border-top: none;
  border-radius: 0 0 var(--radius-md) var(--radius-md);
}

.report-section {
  margin-bottom: var(--spacing-sm);
}

.report-section:last-child {
  margin-bottom: 0;
}

/* ========== 评分 ========== */
.score-label {
  font-size: var(--font-sm);
  color: var(--color-text-secondary);
}

.score-value {
  font-size: var(--font-lg);
  font-weight: 700;
}

/* ========== 列表 ========== */
.list-label {
  font-size: var(--font-sm);
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--spacing-sm);
}

.list-items {
  list-style: none;
  padding: 0;
}

.list-item {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-sm);
  padding: 6px 0;
  font-size: var(--font-sm);
  color: var(--color-text-secondary);
  border-bottom: 1px solid var(--color-border-light);
}

.list-item:last-child {
  border-bottom: none;
}

.list-marker {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  color: var(--color-primary);
  background: var(--color-primary-lighter);
  border-radius: var(--radius-round);
}

/* ========== 嵌套对象 ========== */
.nested-label {
  font-size: var(--font-sm);
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--spacing-xs);
}

/* ========== 数组 ========== */
.array-label {
  font-size: var(--font-sm);
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--spacing-xs);
}

.array-item {
  padding: var(--spacing-xs) 0;
}

/* ========== 普通字段 ========== */
.report-field {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-md);
  padding: 4px 0;
}

.field-label {
  font-size: var(--font-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
  min-width: 80px;
  flex-shrink: 0;
}

.field-value {
  font-size: var(--font-sm);
  color: var(--color-text);
  word-break: break-word;
}
</style>
