<template>
  <div class="agent-monitor">
    <el-page-header title="后台管理" @back="$router.push('/admin')">
      <template #content>
        <span class="page-title">Agent 监控</span>
      </template>
    </el-page-header>

    <div class="content">
      <!-- Agent 统计概览 -->
      <el-row :gutter="20" class="stats-row">
        <el-col :span="6" v-for="stat in agentStats" :key="stat.name">
          <el-card shadow="hover" class="stat-card">
            <div class="stat-name">{{ stat.name }}</div>
            <div class="stat-value">{{ stat.calls }}次</div>
            <div class="stat-detail">
              <span>成功率: </span>
              <span :class="stat.successRate >= 95 ? 'success' : 'warning'">{{ stat.successRate }}%</span>
            </div>
            <div class="stat-detail">
              <span>平均耗时: {{ stat.avgLatency }}ms</span>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- Token 消耗图表 -->
      <el-row :gutter="20" class="chart-row">
        <el-col :span="12">
          <el-card>
            <template #header><span>Token 消耗趋势</span></template>
            <div class="chart-placeholder">
              <span>Token 消耗折线图（接入 ECharts 后展示）</span>
            </div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card>
            <template #header><span>Agent 调用分布</span></template>
            <div class="chart-placeholder">
              <span>调用分布饼图（接入 ECharts 后展示）</span>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 调用日志 -->
      <el-card>
        <template #header>
          <div class="card-header">
            <span>最近调用日志</span>
            <el-select v-model="agentFilter" placeholder="筛选Agent" clearable style="width: 160px">
              <el-option label="全部" value="" />
              <el-option label="简历评估" value="resume_agent" />
              <el-option label="录音分析" value="recording_agent" />
              <el-option label="面试题生成" value="question_agent" />
              <el-option label="职业规划" value="career_agent" />
              <el-option label="主Agent" value="orchestrator" />
            </el-select>
          </div>
        </template>
        <el-table :data="filteredLogs" style="width: 100%">
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="agentName" label="Agent" width="120">
            <template #default="{ row }">
              <el-tag size="small">{{ agentNameMap[row.agentName] || row.agentName }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="inputTokens" label="输入Token" width="100" />
          <el-table-column prop="outputTokens" label="输出Token" width="100" />
          <el-table-column prop="latencyMs" label="耗时(ms)" width="100" />
          <el-table-column prop="status" label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
                {{ row.status === 'success' ? '成功' : '失败' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="errorMsg" label="错误信息" />
          <el-table-column prop="createdAt" label="时间" width="180" />
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { getAgentLogsApi, getAgentStatsApi } from '@/api/admin'

const agentFilter = ref('')

const agentNameMap: Record<string, string> = {
  orchestrator: '主Agent',
  resume_agent: '简历评估',
  recording_agent: '录音分析',
  question_agent: '面试题生成',
  career_agent: '职业规划',
}

const agentStats = ref<{ name: string; calls: number; successRate: number; avgLatency: number }[]>([])

const logs = ref<any[]>([])

const filteredLogs = computed(() => {
  if (!agentFilter.value) return logs.value
  return logs.value.filter(l => l.agentName === agentFilter.value)
})

async function fetchAgentData() {
  const [statsRes, logsRes] = await Promise.all([
    getAgentStatsApi(),
    getAgentLogsApi({ page: 1, page_size: 50, agent_name: agentFilter.value || undefined }),
  ])
  agentStats.value = (statsRes.data || []).map(item => ({
    name: agentNameMap[item.agent_name] || item.agent_name,
    calls: item.calls,
    successRate: item.success_rate,
    avgLatency: item.avg_latency_ms,
  }))
  logs.value = (logsRes.data || []).map(item => ({
    id: item.id,
    agentName: item.agent_name,
    inputTokens: item.input_tokens || 0,
    outputTokens: item.output_tokens || 0,
    latencyMs: item.latency_ms || 0,
    status: item.status,
    errorMsg: item.error_msg || '',
    createdAt: item.created_at,
  }))
}

watch(agentFilter, fetchAgentData)

onMounted(() => {
  fetchAgentData()
})
</script>

<style scoped>
.agent-monitor { padding: 20px; }
.page-title { font-size: 16px; font-weight: 500; }
.content { margin-top: 20px; }
.stats-row { margin-bottom: 20px; }
.stat-card { text-align: center; }
.stat-name { font-size: 13px; color: #5F5E5A; margin-bottom: 8px; }
.stat-value { font-size: 24px; font-weight: 500; color: #534AB7; }
.stat-detail { font-size: 12px; color: #888; margin-top: 4px; }
.success { color: #0F6E56; }
.warning { color: #BA7517; }
.chart-row { margin-bottom: 20px; }
.chart-placeholder { height: 200px; display: flex; align-items: center; justify-content: center; color: #888; background: #f9f9f9; border-radius: 8px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
