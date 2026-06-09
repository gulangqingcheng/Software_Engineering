<template>
  <div class="knowledge-manage">
    <el-page-header title="后台管理" @back="$router.push('/admin')">
      <template #content>
        <span class="page-title">知识库管理</span>
      </template>
    </el-page-header>

    <div class="content">
      <!-- 知识库概览 -->
      <el-row :gutter="20" class="stats-row">
        <el-col :span="8">
          <el-card shadow="hover">
            <el-statistic title="面试宝典文档" :value="guideCount" />
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover">
            <el-statistic title="题库题目" :value="questionCount" />
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover">
            <el-statistic title="向量总数" :value="vectorCount" />
          </el-card>
        </el-col>
      </el-row>

      <!-- 上传知识文档 -->
      <el-card class="upload-card">
        <template #header>
          <div class="card-header">
            <span>上传知识文档</span>
            <el-button type="primary" size="small">上传文档</el-button>
          </div>
        </template>
        <el-upload
          drag
          action="/api/v1/admin/knowledge/upload"
          :headers="uploadHeaders"
          :show-file-list="false"
          accept=".txt,.md,.pdf"
          :on-success="handleUploadSuccess"
        >
          <div class="upload-area">
            <span>将面试宝典文档拖拽到此处，或点击上传</span>
            <span class="upload-tip">支持 .txt、.md、.pdf 格式</span>
          </div>
        </el-upload>
      </el-card>

      <!-- 文档列表 -->
      <el-card>
        <template #header>
          <div class="card-header">
            <span>已有文档</span>
            <el-input
              v-model="searchKeyword"
              placeholder="搜索文档"
              style="width: 200px"
              clearable
            />
          </div>
        </template>
        <el-table :data="filteredDocs" style="width: 100%">
          <el-table-column prop="title" label="文档标题" />
          <el-table-column prop="category" label="分类" width="120" />
          <el-table-column prop="chunks" label="分块数" width="100" />
          <el-table-column prop="status" label="向量化状态" width="120">
            <template #default="{ row }">
              <el-tag :type="row.status === 'completed' ? 'success' : 'warning'" size="small">
                {{ row.status === 'completed' ? '已完成' : '处理中' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="createdAt" label="上传时间" width="180" />
          <el-table-column label="操作" width="150">
            <template #default>
              <el-button size="small" type="danger" link>删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getAdminDashboardApi, getKnowledgeStatsApi } from '@/api/admin'

const guideCount = ref(0)
const questionCount = ref(0)
const vectorCount = ref(0)
const searchKeyword = ref('')
const uploadHeaders = computed(() => ({
  Authorization: `Bearer ${localStorage.getItem('access_token') || ''}`,
}))

const docs = ref([
  { id: 1, title: '技术面试技巧指南', category: '面试技巧', chunks: 45, status: 'completed', createdAt: '2026-05-20 10:00:00' },
  { id: 2, title: 'STAR法则详解', category: '行为面试', chunks: 28, status: 'completed', createdAt: '2026-05-20 10:00:00' },
  { id: 3, title: 'Java高频面试题200道', category: '技术题库', chunks: 120, status: 'processing', createdAt: '2026-05-21 14:30:00' },
])

const filteredDocs = computed(() => {
  if (!searchKeyword.value) return docs.value
  return docs.value.filter(d => d.title.includes(searchKeyword.value))
})

async function fetchStats() {
  const [kbRes, dashboardRes] = await Promise.all([getKnowledgeStatsApi(), getAdminDashboardApi()])
  guideCount.value = kbRes.data.file_count
  vectorCount.value = kbRes.data.vector_count
  questionCount.value = dashboardRes.data.total_questions
}

function handleUploadSuccess() {
  ElMessage.success('知识库已更新')
  fetchStats()
}

onMounted(() => {
  fetchStats()
})
</script>

<style scoped>
.knowledge-manage { padding: 20px; }
.page-title { font-size: 16px; font-weight: 500; }
.content { margin-top: 20px; }
.stats-row { margin-bottom: 20px; }
.upload-card { margin-bottom: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.upload-area { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 40px 0; color: #5F5E5A; }
.upload-tip { font-size: 12px; color: #888; }
</style>
