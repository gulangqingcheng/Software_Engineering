<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import AppHeader from '@/components/AppHeader.vue'
import Sidebar from '@/components/Sidebar.vue'
import {
  answerInterviewSessionApi,
  createInterviewSessionApi,
  finishInterviewSessionApi,
  getInterviewReportDownloadUrl,
  type InterviewReport,
  type InterviewSession,
  type InterviewTurn,
  startInterviewSessionApi,
} from '@/api/interview'

const loading = ref(false)
const downloading = ref(false)
const session = ref<InterviewSession | null>(null)
const report = ref<InterviewReport | null>(null)
const answerText = ref('')
const answerStartedAt = ref<number | null>(null)

const form = reactive({
  target_position: '前端开发工程师',
  interview_type: 'technical' as 'technical' | 'behavioral' | 'comprehensive',
  difficulty: 'medium' as 'easy' | 'medium' | 'hard',
  question_count: 5,
})

const interviewTypeOptions = [
  { label: '技术面试', value: 'technical' },
  { label: '行为面试', value: 'behavioral' },
  { label: '综合面试', value: 'comprehensive' },
]

const difficultyOptions = [
  { label: '基础', value: 'easy' },
  { label: '进阶', value: 'medium' },
  { label: '深入', value: 'hard' },
]

const dimensionMax: Record<string, number> = {
  岗位相关性: 18,
  技术深度: 24,
  逻辑结构: 18,
  案例与结果: 18,
  表达沟通: 12,
  时间控制: 10,
}

const activeTurn = computed<InterviewTurn | null>(() => {
  const turns = session.value?.turns || []
  return turns.find(item => !item.answered_at) || null
})

const answeredTurns = computed(() => {
  return (session.value?.turns || []).filter(item => item.answered_at)
})

function resetAnswerTimer() {
  answerStartedAt.value = Date.now()
}

async function createAndStartInterview() {
  if (!form.target_position.trim()) {
    ElMessage.warning('请输入目标岗位')
    return
  }

  loading.value = true
  report.value = null
  answerText.value = ''
  try {
    const created = await createInterviewSessionApi({
      title: `${form.target_position} AI面试`,
      target_position: form.target_position.trim(),
      interview_type: form.interview_type,
      difficulty: form.difficulty,
      question_count: form.question_count,
      answer_mode: 'text',
    })
    const started = await startInterviewSessionApi(created.data.id)
    session.value = started.data
    resetAnswerTimer()
    ElMessage.success('AI面试已开始')
  } finally {
    loading.value = false
  }
}

async function submitAnswer() {
  if (!session.value || !activeTurn.value) return
  if (!answerText.value.trim()) {
    ElMessage.warning('请输入回答内容')
    return
  }

  const duration = answerStartedAt.value
    ? Math.max(1, Math.round((Date.now() - answerStartedAt.value) / 1000))
    : undefined

  loading.value = true
  try {
    const res = await answerInterviewSessionApi(session.value.id, {
      answer_text: answerText.value.trim(),
      answer_duration_seconds: duration,
    })
    session.value = res.data
    answerText.value = ''
    resetAnswerTimer()
    ElMessage.success('回答已提交，评分已生成')
  } finally {
    loading.value = false
  }
}

async function finishInterview() {
  if (!session.value) return
  loading.value = true
  try {
    const res = await finishInterviewSessionApi(session.value.id)
    report.value = res.data
    session.value = {
      ...session.value,
      status: 'finished',
      total_score: res.data.total_score,
      report: res.data,
    }
    ElMessage.success('面试报告已生成')
  } finally {
    loading.value = false
  }
}

async function downloadReport() {
  if (!session.value) return
  downloading.value = true
  try {
    const token = localStorage.getItem('access_token')
    const response = await fetch(getInterviewReportDownloadUrl(session.value.id), {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    })
    if (!response.ok) {
      ElMessage.error('报告下载失败')
      return
    }
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${session.value.title}-面试报告.docx`
    link.click()
    URL.revokeObjectURL(url)
  } finally {
    downloading.value = false
  }
}

function scoreStatus(score?: number | null) {
  if (score == null) return 'info'
  if (score >= 85) return 'success'
  if (score >= 70) return 'warning'
  return 'danger'
}
</script>

<template>
  <div class="interview-layout">
    <AppHeader />

    <div class="interview-body">
      <Sidebar />

      <main class="interview-main">
        <section class="setup-panel">
          <div class="panel-title">
            <div>
              <h1>AI面试官</h1>
              <p>按岗位生成问题，回答后按五个维度评分，结束后生成详细报告并支持 Word 下载。</p>
            </div>
            <el-button type="primary" :loading="loading" :icon="'VideoPlay'" @click="createAndStartInterview">
              开始面试
            </el-button>
          </div>

          <el-form :model="form" class="setup-form" label-position="top">
            <el-form-item label="目标岗位">
              <el-input v-model="form.target_position" placeholder="例如：Java后端开发工程师" />
            </el-form-item>
            <el-form-item label="面试类型">
              <el-segmented v-model="form.interview_type" :options="interviewTypeOptions" />
            </el-form-item>
            <el-form-item label="难度">
              <el-segmented v-model="form.difficulty" :options="difficultyOptions" />
            </el-form-item>
            <el-form-item label="题目数量">
              <el-input-number v-model="form.question_count" :min="1" :max="10" />
            </el-form-item>
          </el-form>
        </section>

        <section v-if="session" class="workspace">
          <div class="question-panel">
            <div class="session-bar">
              <div>
                <span class="session-title">{{ session.title }}</span>
                <el-tag :type="session.status === 'finished' ? 'success' : 'primary'">
                  {{ session.status === 'finished' ? '已结束' : '进行中' }}
                </el-tag>
              </div>
              <span class="session-progress">
                {{ answeredTurns.length }} / {{ session.question_count }}
              </span>
            </div>

            <div v-if="activeTurn" class="question-box">
              <div class="question-index">第 {{ activeTurn.question_index }} 题</div>
              <p>{{ activeTurn.question }}</p>
              <el-input
                v-model="answerText"
                type="textarea"
                :autosize="{ minRows: 7, maxRows: 12 }"
                placeholder="建议按 STAR 结构回答：背景、任务、行动、结果，并补充技术细节和量化成果。"
              />
              <div class="question-actions">
                <el-button :loading="loading" type="primary" :icon="'Check'" @click="submitAnswer">
                  提交回答并评分
                </el-button>
                <el-button
                  :disabled="answeredTurns.length === 0"
                  :loading="loading"
                  :icon="'DocumentChecked'"
                  @click="finishInterview"
                >
                  结束并生成报告
                </el-button>
              </div>
            </div>

            <div v-else class="finished-box">
              <el-icon :size="42"><CircleCheck /></el-icon>
              <h2>题目已完成</h2>
              <p>点击生成报告，查看综合评分、维度分析、逐题依据和改进计划。</p>
              <el-button type="primary" :loading="loading" :icon="'DocumentChecked'" @click="finishInterview">
                生成面试报告
              </el-button>
            </div>
          </div>

          <div class="result-panel">
            <h2>评分记录</h2>
            <div v-if="answeredTurns.length === 0" class="empty-result">提交回答后，这里会显示每题评分和反馈。</div>
            <div v-for="turn in answeredTurns" :key="turn.id" class="turn-result">
              <div class="turn-head">
                <span>第 {{ turn.question_index }} 题</span>
                <el-tag :type="scoreStatus(turn.score)">{{ turn.score }}/100</el-tag>
              </div>
              <p class="feedback">{{ turn.feedback }}</p>
              <p class="suggestion">{{ turn.suggestion }}</p>
            </div>
          </div>
        </section>

        <section v-if="report" class="report-panel">
          <div class="report-header">
            <div class="report-score">
              <span>综合评分</span>
              <strong>{{ report.total_score }}</strong>
            </div>
            <div class="report-summary">
              <div class="report-title-row">
                <h2>面试报告</h2>
                <el-button :loading="downloading" :icon="'Download'" @click="downloadReport">
                  下载 Word
                </el-button>
              </div>
              <p>{{ report.summary }}</p>
              <p class="score-basis">{{ report.score_basis }}</p>
            </div>
          </div>

          <div v-if="report.dimension_scores" class="dimension-grid">
            <div v-for="(value, name) in report.dimension_scores" :key="name" class="dimension-item">
              <div class="dimension-line">
                <span>{{ name }}</span>
                <strong>{{ value }}/{{ dimensionMax[name] || 100 }}</strong>
              </div>
              <el-progress
                :percentage="Math.round((value / (dimensionMax[name] || 100)) * 100)"
                :stroke-width="8"
                :show-text="false"
              />
            </div>
          </div>

          <div class="report-columns">
            <div>
              <h3>优势</h3>
              <ul>
                <li v-for="item in report.strengths" :key="item">{{ item }}</li>
              </ul>
            </div>
            <div>
              <h3>不足</h3>
              <ul>
                <li v-for="item in report.weaknesses" :key="item">{{ item }}</li>
              </ul>
            </div>
          </div>

          <div class="turn-analysis">
            <h3>逐题评分依据</h3>
            <div v-for="item in report.turn_performance" :key="item.question_index" class="analysis-card">
              <div class="turn-head">
                <span>第 {{ item.question_index }} 题</span>
                <el-tag :type="scoreStatus(item.score)">{{ item.score }}/100</el-tag>
              </div>
              <p class="question-text">{{ item.question }}</p>
              <p class="time-text">
                回答时长：{{ item.answer_duration_seconds ?? '未记录' }} 秒
              </p>
              <div v-if="item.dimensions" class="mini-dimensions">
                <span v-for="(value, name) in item.dimensions" :key="name">{{ name }} {{ value }}/{{ dimensionMax[name] }}</span>
              </div>
              <div class="evidence-grid">
                <div>
                  <h4>评分依据</h4>
                  <ul>
                    <li v-for="evidence in item.evidence" :key="evidence">{{ evidence }}</li>
                  </ul>
                </div>
                <div>
                  <h4>扣分点</h4>
                  <ul>
                    <li v-for="point in item.missing_points" :key="point">{{ point }}</li>
                  </ul>
                </div>
              </div>
              <p class="suggestion">{{ item.suggestion }}</p>
            </div>
          </div>

          <div class="report-columns">
            <div>
              <h3>改进建议</h3>
              <ul>
                <li v-for="item in report.suggestions" :key="item">{{ item }}</li>
              </ul>
            </div>
            <div>
              <h3>训练计划</h3>
              <ol>
                <li v-for="item in report.action_plan" :key="item">{{ item }}</li>
              </ol>
            </div>
          </div>
        </section>
      </main>
    </div>
  </div>
</template>

<style scoped>
.interview-layout {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--color-bg);
}

.interview-body {
  flex: 1;
  min-height: 0;
  display: flex;
}

.interview-main {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  padding: 24px;
}

.setup-panel,
.question-panel,
.result-panel,
.report-panel {
  background: var(--color-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.setup-panel {
  padding: 20px;
  margin-bottom: 16px;
}

.panel-title,
.session-bar,
.turn-head,
.report-title-row,
.dimension-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.panel-title h1 {
  margin: 0 0 6px;
  font-size: 24px;
}

.panel-title p,
.score-basis,
.feedback,
.suggestion,
.question-text,
.time-text,
.report-summary p,
.report-panel li {
  line-height: 1.65;
  color: var(--color-text-secondary);
}

.setup-form {
  margin-top: 18px;
  display: grid;
  grid-template-columns: minmax(220px, 1.4fr) minmax(260px, 1fr) minmax(180px, 0.8fr) 140px;
  gap: 14px;
  align-items: end;
}

.workspace {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(320px, 0.85fr);
  gap: 16px;
}

.question-panel,
.result-panel {
  padding: 18px;
}

.session-title {
  font-weight: 700;
  margin-right: 10px;
}

.session-progress {
  color: var(--color-text-secondary);
  font-weight: 600;
}

.question-box {
  margin-top: 20px;
}

.question-index {
  color: var(--color-primary);
  font-weight: 700;
  margin-bottom: 8px;
}

.question-box p {
  margin: 0 0 16px;
  line-height: 1.7;
}

.question-actions {
  margin-top: 14px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.finished-box,
.empty-result {
  min-height: 220px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--color-text-secondary);
  text-align: center;
}

.result-panel h2,
.report-panel h2,
.report-panel h3,
.report-panel h4 {
  margin: 0;
}

.turn-result {
  padding: 12px 0;
  border-top: 1px solid var(--color-border-light);
}

.turn-result:first-of-type {
  border-top: 0;
}

.report-panel {
  margin-top: 16px;
  padding: 18px;
}

.report-header {
  display: grid;
  grid-template-columns: 128px minmax(0, 1fr);
  gap: 20px;
  align-items: start;
}

.report-score {
  min-height: 110px;
  border-radius: var(--radius-sm);
  background: var(--color-primary-lighter);
  color: var(--color-primary);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.report-score strong {
  font-size: 38px;
  line-height: 1;
}

.dimension-grid {
  margin-top: 18px;
  display: grid;
  grid-template-columns: repeat(5, minmax(150px, 1fr));
  gap: 12px;
}

.dimension-item,
.analysis-card {
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  padding: 12px;
}

.dimension-line {
  margin-bottom: 8px;
  font-size: var(--font-sm);
}

.report-columns,
.evidence-grid {
  margin-top: 18px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.turn-analysis {
  margin-top: 18px;
}

.analysis-card {
  margin-top: 12px;
}

.mini-dimensions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 10px 0;
}

.mini-dimensions span {
  padding: 3px 8px;
  border-radius: 4px;
  background: var(--color-bg);
  color: var(--color-text-secondary);
  font-size: var(--font-xs);
}

@media (max-width: 1100px) {
  .dimension-grid {
    grid-template-columns: repeat(2, minmax(150px, 1fr));
  }
}

@media (max-width: 980px) {
  .setup-form,
  .workspace,
  .report-header,
  .report-columns,
  .evidence-grid {
    grid-template-columns: 1fr;
  }

  .panel-title {
    flex-direction: column;
    align-items: stretch;
  }

  .dimension-grid {
    grid-template-columns: 1fr;
  }
}
</style>
