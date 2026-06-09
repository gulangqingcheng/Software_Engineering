<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Question } from '@/types'
import Sidebar from '@/components/Sidebar.vue'
import AppHeader from '@/components/AppHeader.vue'
import { getQuestionBankApi, deleteQuestionApi, generateQuestionsApi } from '@/api/question'

const questions = ref<Question[]>([])
const total = ref(0)
const searchKeyword = ref('')
const filterCategory = ref('')
const filterDifficulty = ref('')
const pagination = ref({ page: 1, page_size: 20 })
const loading = ref(false)
const showGenerateDialog = ref(false)
const generateForm = ref({ role: '', category: '', difficulty: 'medium' as 'easy' | 'medium' | 'hard', count: 5 })

const categoryOptions = [
  { label: '全部', value: '' },
  { label: '前端开发', value: 'frontend' },
  { label: '后端开发', value: 'backend' },
  { label: '算法', value: 'algorithm' },
  { label: '系统设计', value: 'system_design' },
  { label: '数据库', value: 'database' },
  { label: '行为面试', value: 'behavioral' },
]

const difficultyOptions = [
  { label: '全部', value: '' },
  { label: '简单', value: 'easy' },
  { label: '中等', value: 'medium' },
  { label: '困难', value: 'hard' },
]

async function fetchQuestions() {
  loading.value = true
  try {
    const res = await getQuestionBankApi({
      ...pagination.value,
      keyword: searchKeyword.value || undefined,
      category: filterCategory.value || undefined,
      difficulty: filterDifficulty.value || undefined,
    })
    const pageData: any = res.data
    questions.value = pageData.items || pageData.data || []
    total.value = pageData.total || 0
  } catch {
    ElMessage.error('加载面试题失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.value.page = 1
  fetchQuestions()
}

function handlePageChange(page: number) {
  pagination.value.page = page
  fetchQuestions()
}

async function handleDelete(question: Question) {
  try {
    await ElMessageBox.confirm(`确定要删除题目“${question.question.substring(0, 30)}...”吗？`, '确认删除', { type: 'warning' })
    await deleteQuestionApi(question.id)
    ElMessage.success('删除成功')
    fetchQuestions()
  } catch {
    // canceled
  }
}

async function handleGenerate() {
  if (!generateForm.value.role) {
    ElMessage.warning('请输入目标岗位')
    return
  }
  loading.value = true
  try {
    await generateQuestionsApi({
      role: generateForm.value.role,
      category: generateForm.value.category || undefined,
      difficulty: generateForm.value.difficulty,
      count: generateForm.value.count,
    })
    ElMessage.success('面试题生成成功')
    showGenerateDialog.value = false
    fetchQuestions()
  } catch {
    ElMessage.error('生成面试题失败')
  } finally {
    loading.value = false
  }
}

onMounted(fetchQuestions)
</script>

<template>
  <div class="admin-layout">
    <Sidebar />
    <div class="admin-main">
      <AppHeader />
      <div class="admin-content">
        <div class="page-header flex-between">
          <h2 class="page-title">题库管理</h2>
          <el-button type="primary" :icon="'MagicStick'" @click="showGenerateDialog = true">AI 生成面试题</el-button>
        </div>

        <div class="search-bar card mb-md">
          <div class="flex gap-md" style="flex-wrap: wrap">
            <el-input v-model="searchKeyword" placeholder="搜索题目关键词..." :prefix-icon="'Search'" clearable style="width: 280px" @keyup.enter="handleSearch" @clear="handleSearch" />
            <el-select v-model="filterCategory" placeholder="分类筛选" clearable style="width: 160px" @change="handleSearch"><el-option v-for="opt in categoryOptions" :key="opt.value" :label="opt.label" :value="opt.value" /></el-select>
            <el-select v-model="filterDifficulty" placeholder="难度筛选" clearable style="width: 140px" @change="handleSearch"><el-option v-for="opt in difficultyOptions" :key="opt.value" :label="opt.label" :value="opt.value" /></el-select>
            <el-button type="primary" @click="handleSearch">搜索</el-button>
          </div>
        </div>

        <div class="card">
          <el-table :data="questions" v-loading="loading" stripe style="width: 100%">
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="question" label="题目" min-width="300" show-overflow-tooltip />
            <el-table-column prop="category" label="分类" width="120"><template #default="{ row }"><el-tag size="small">{{ row.category }}</el-tag></template></el-table-column>
            <el-table-column prop="difficulty" label="难度" width="100"><template #default="{ row }"><el-tag size="small" :type="row.difficulty === 'easy' ? 'success' : row.difficulty === 'medium' ? 'warning' : 'danger'">{{ row.difficulty === 'easy' ? '简单' : row.difficulty === 'medium' ? '中等' : '困难' }}</el-tag></template></el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="160" />
            <el-table-column label="操作" width="120" fixed="right"><template #default="{ row }"><el-button link type="primary" size="small">编辑</el-button><el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button></template></el-table-column>
          </el-table>
          <div class="flex-center mt-md"><el-pagination v-model:current-page="pagination.page" :page-size="pagination.page_size" :total="total" layout="prev, pager, next" background @current-change="handlePageChange" /></div>
        </div>

        <el-dialog v-model="showGenerateDialog" title="AI 生成面试题" width="500px">
          <el-form :model="generateForm" label-width="100px">
            <el-form-item label="目标岗位" required><el-input v-model="generateForm.role" placeholder="如：高级前端工程师" /></el-form-item>
            <el-form-item label="题目分类"><el-select v-model="generateForm.category" placeholder="不限分类" style="width: 100%"><el-option v-for="opt in categoryOptions.filter(o => o.value)" :key="opt.value" :label="opt.label" :value="opt.value" /></el-select></el-form-item>
            <el-form-item label="题目难度"><el-select v-model="generateForm.difficulty" style="width: 100%"><el-option label="简单" value="easy" /><el-option label="中等" value="medium" /><el-option label="困难" value="hard" /></el-select></el-form-item>
            <el-form-item label="生成数量"><el-input-number v-model="generateForm.count" :min="1" :max="20" style="width: 100%" /></el-form-item>
          </el-form>
          <template #footer><el-button @click="showGenerateDialog = false">取消</el-button><el-button type="primary" :loading="loading" @click="handleGenerate">开始生成</el-button></template>
        </el-dialog>
      </div>
    </div>
  </div>
</template>

<style scoped>
.admin-layout { display: flex; height: 100%; overflow: hidden; }
.admin-main { flex: 1; display: flex; flex-direction: column; min-width: 0; overflow: hidden; }
.admin-content { flex: 1; overflow-y: auto; padding: var(--spacing-lg); background: var(--color-bg); }
.page-header { margin-bottom: var(--spacing-lg); }
.page-title { font-size: var(--font-xxl); font-weight: 700; color: var(--color-text); }
.search-bar { padding: var(--spacing-md); }
</style>
