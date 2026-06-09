<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageTopHeader from '@/components/PageTopHeader.vue'
import type { DuplicateQuestionGroup, Question } from '@/types'
import {
  createQuestionApi,
  deleteQuestionApi,
  getDuplicateQuestionsApi,
  getQuestionBankApi,
  resolveDuplicateQuestionApi,
  updateQuestionApi,
} from '@/api/question'

const questions = ref<Question[]>([])
const total = ref(0)
const loading = ref(false)
const exporting = ref(false)
const dialogVisible = ref(false)
const duplicateDialogVisible = ref(false)
const editingId = ref<number | null>(null)
const searchKeyword = ref('')
const pagination = reactive({ page: 1, page_size: 20 })
const duplicateGroups = ref<DuplicateQuestionGroup[]>([])
const duplicateSelections = reactive<Record<string, number>>({})

const form = reactive({
  question: '',
  reference_answer: '',
  category: 'general',
  difficulty: 'medium' as 'easy' | 'medium' | 'hard',
  tagsText: '',
})

const categoryOptions = [
  { label: '综合', value: 'general' },
  { label: '前端', value: 'frontend' },
  { label: '后端', value: 'backend' },
  { label: '算法', value: 'algorithm' },
  { label: '系统设计', value: 'system_design' },
  { label: '数据库', value: 'database' },
  { label: '网络', value: 'network' },
  { label: '行为面试', value: 'behavioral' },
  { label: '项目经历', value: 'project' },
]

const sourceMap: Record<string, string> = {
  ai_generated: 'AI生成',
  collected: '录音收录',
  user_uploaded: '手动维护',
  system: '系统题库',
}

async function fetchQuestions() {
  loading.value = true
  try {
    const res = await getQuestionBankApi({ ...pagination, mine: true, keyword: searchKeyword.value || undefined })
    const pageData: any = res.data
    questions.value = pageData.items || pageData.data || []
    total.value = pageData.total || 0
    await fetchDuplicateGroups()
  } finally {
    loading.value = false
  }
}

async function fetchDuplicateGroups() {
  const res = await getDuplicateQuestionsApi()
  duplicateGroups.value = res.data || []
}

function resetForm() {
  editingId.value = null
  form.question = ''
  form.reference_answer = ''
  form.category = 'general'
  form.difficulty = 'medium'
  form.tagsText = ''
}

function parseEmbeddedQuestion(row: Question) {
  const candidates = [row.question, row.reference_answer, row.answer]
  for (const value of candidates) {
    const text = String(value || '').trim()
    if (!text || (!text.startsWith('[') && !text.startsWith('{'))) continue
    try {
      const parsed = JSON.parse(text)
      const item = Array.isArray(parsed) ? parsed[0] : parsed
      if (item && typeof item === 'object') return item as Record<string, any>
    } catch {
      // ignore legacy malformed rows
    }
  }
  return null
}

function getQuestionText(row: Question) {
  const embedded = parseEmbeddedQuestion(row)
  return String(embedded?.question || row.question || '')
}

function getAnswerText(row: Question) {
  const embedded = parseEmbeddedQuestion(row)
  return String(embedded?.reference_answer || embedded?.answer || row.reference_answer || row.answer || '')
}

function openCreateDialog() {
  resetForm()
  dialogVisible.value = true
}

function openEditDialog(row: Question) {
  const embedded = parseEmbeddedQuestion(row)
  editingId.value = row.id
  form.question = getQuestionText(row)
  form.reference_answer = getAnswerText(row)
  form.category = embedded?.category || row.category || 'general'
  form.difficulty = embedded?.difficulty || row.difficulty || 'medium'
  const tags = embedded?.tags || row.tags || []
  form.tagsText = Array.isArray(tags) ? tags.join(', ') : String(tags)
  dialogVisible.value = true
}

async function saveQuestion() {
  if (!form.question.trim()) {
    ElMessage.warning('请输入题目')
    return
  }
  const payload = {
    question: form.question.trim(),
    reference_answer: form.reference_answer.trim() || undefined,
    category: form.category,
    difficulty: form.difficulty,
    tags: form.tagsText.split(',').map(tag => tag.trim()).filter(Boolean),
  }
  if (editingId.value) {
    await updateQuestionApi(editingId.value, payload)
    ElMessage.success('题目已更新')
  } else {
    await createQuestionApi(payload as any)
    ElMessage.success('题目已新增')
  }
  dialogVisible.value = false
  fetchQuestions()
}

async function removeQuestion(row: Question) {
  await ElMessageBox.confirm(`确定删除题目“${getQuestionText(row).slice(0, 30)}...”吗？`, '确认删除', { type: 'warning' })
  await deleteQuestionApi(row.id)
  ElMessage.success('题目已删除')
  fetchQuestions()
}

function openDuplicateDialog() {
  duplicateGroups.value.forEach((group) => {
    if (!duplicateSelections[group.question]) duplicateSelections[group.question] = group.items[0]?.id
  })
  duplicateDialogVisible.value = true
}

async function resolveDuplicateGroup(group: DuplicateQuestionGroup) {
  const keepId = duplicateSelections[group.question]
  if (!keepId) {
    ElMessage.warning('请选择要保留的题目记录')
    return
  }
  await resolveDuplicateQuestionApi({ keep_id: keepId, remove_ids: group.items.filter(item => item.id !== keepId).map(item => item.id) })
  ElMessage.success('重复题目已处理')
  await fetchQuestions()
  if (!duplicateGroups.value.length) duplicateDialogVisible.value = false
}

function handleSearch() {
  pagination.page = 1
  fetchQuestions()
}

function handlePageChange(page: number) {
  pagination.page = page
  fetchQuestions()
}

function escapeXml(value: unknown) {
  return String(value ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&apos;')
}

function formatTags(tags?: string[]) {
  return Array.isArray(tags) ? tags.join(', ') : ''
}

const crcTable = (() => {
  const table = new Uint32Array(256)
  for (let i = 0; i < 256; i += 1) {
    let c = i
    for (let k = 0; k < 8; k += 1) c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1)
    table[i] = c >>> 0
  }
  return table
})()

function crc32(bytes: Uint8Array) {
  let crc = 0xffffffff
  for (let i = 0; i < bytes.length; i += 1) crc = crcTable[(crc ^ bytes[i]) & 0xff] ^ (crc >>> 8)
  return (crc ^ 0xffffffff) >>> 0
}

function writeUint16(target: number[], value: number) { target.push(value & 0xff, (value >>> 8) & 0xff) }
function writeUint32(target: number[], value: number) { target.push(value & 0xff, (value >>> 8) & 0xff, (value >>> 16) & 0xff, (value >>> 24) & 0xff) }

function concatBytes(parts: Uint8Array[]) {
  const result = new Uint8Array(parts.reduce((sum, part) => sum + part.length, 0))
  let offset = 0
  for (const part of parts) { result.set(part, offset); offset += part.length }
  return result
}

function createZip(entries: { name: string; content: string }[]) {
  const encoder = new TextEncoder()
  const parts: Uint8Array[] = []
  const centralParts: Uint8Array[] = []
  let offset = 0
  for (const entry of entries) {
    const nameBytes = encoder.encode(entry.name)
    const contentBytes = encoder.encode(entry.content)
    const crc = crc32(contentBytes)
    const local: number[] = []
    writeUint32(local, 0x04034b50); writeUint16(local, 20); writeUint16(local, 0); writeUint16(local, 0); writeUint16(local, 0); writeUint16(local, 0)
    writeUint32(local, crc); writeUint32(local, contentBytes.length); writeUint32(local, contentBytes.length); writeUint16(local, nameBytes.length); writeUint16(local, 0)
    const localHeader = concatBytes([new Uint8Array(local), nameBytes, contentBytes])
    parts.push(localHeader)
    const central: number[] = []
    writeUint32(central, 0x02014b50); writeUint16(central, 20); writeUint16(central, 20); writeUint16(central, 0); writeUint16(central, 0); writeUint16(central, 0); writeUint16(central, 0)
    writeUint32(central, crc); writeUint32(central, contentBytes.length); writeUint32(central, contentBytes.length); writeUint16(central, nameBytes.length); writeUint16(central, 0); writeUint16(central, 0); writeUint16(central, 0); writeUint16(central, 0); writeUint32(central, 0); writeUint32(central, offset)
    centralParts.push(concatBytes([new Uint8Array(central), nameBytes]))
    offset += localHeader.length
  }
  const centralDirectory = concatBytes(centralParts)
  const end: number[] = []
  writeUint32(end, 0x06054b50); writeUint16(end, 0); writeUint16(end, 0); writeUint16(end, entries.length); writeUint16(end, entries.length); writeUint32(end, centralDirectory.length); writeUint32(end, offset); writeUint16(end, 0)
  return concatBytes([...parts, centralDirectory, new Uint8Array(end)])
}

function cell(value: unknown) {
  return `<c t="inlineStr"><is><t>${escapeXml(value)}</t></is></c>`
}

function buildXlsxBlob(rows: Question[]) {
  const headers = ['序号', '题目', '参考答案', '分类', '难度', '来源', '标签', '创建时间']
  const sheetRows = [
    `<row r="1">${headers.map(cell).join('')}</row>`,
    ...rows.map((item, index) => `<row r="${index + 2}">${[
      index + 1,
      getQuestionText(item),
      getAnswerText(item),
      item.category,
      item.difficulty,
      sourceMap[item.source || ''] || item.source || '未知',
      formatTags(item.tags),
      item.created_at,
    ].map(cell).join('')}</row>`),
  ].join('')
  const sheet = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><cols><col min="1" max="1" width="8" customWidth="1"/><col min="2" max="2" width="60" customWidth="1"/><col min="3" max="3" width="80" customWidth="1"/><col min="4" max="8" width="18" customWidth="1"/></cols><sheetData>${sheetRows}</sheetData></worksheet>`
  const files = [
    { name: '[Content_Types].xml', content: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>` },
    { name: '_rels/.rels', content: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>` },
    { name: 'xl/workbook.xml', content: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="我的题库" sheetId="1" r:id="rId1"/></sheets></workbook>` },
    { name: 'xl/_rels/workbook.xml.rels', content: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>` },
    { name: 'xl/styles.xml', content: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts><fills count="1"><fill><patternFill patternType="none"/></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs></styleSheet>` },
    { name: 'xl/worksheets/sheet1.xml', content: sheet },
  ]
  return new Blob([createZip(files)], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
}

async function exportQuestions() {
  exporting.value = true
  try {
    const pageSize = 100
    const first = await getQuestionBankApi({ page: 1, page_size: pageSize, mine: true, keyword: searchKeyword.value || undefined })
    const firstPage: any = first.data
    const exportRows: Question[] = [...(firstPage.items || firstPage.data || [])]
    const exportTotal = firstPage.total || exportRows.length
    const totalPages = Math.ceil(exportTotal / pageSize)
    for (let page = 2; page <= totalPages; page += 1) {
      const res = await getQuestionBankApi({ page, page_size: pageSize, mine: true, keyword: searchKeyword.value || undefined })
      const pageData: any = res.data
      exportRows.push(...(pageData.items || pageData.data || []))
    }
    if (!exportRows.length) {
      ElMessage.warning('暂无可导出的题目')
      return
    }
    const url = URL.createObjectURL(buildXlsxBlob(exportRows))
    const link = document.createElement('a')
    link.href = url
    link.download = `我的题库_${new Date().toISOString().slice(0, 10)}.xlsx`
    link.click()
    URL.revokeObjectURL(url)
    ElMessage.success('题库已导出')
  } finally {
    exporting.value = false
  }
}

onMounted(fetchQuestions)
</script>

<template>
  <div class="my-question-page">
    <PageTopHeader title="我的题库" show-profile-entry />
    <main class="my-question-content">
      <div class="page-header">
        <div>
          <div class="title-row">
            <h2>我的题库</h2>
            <el-button v-if="duplicateGroups.length" class="duplicate-alert" type="warning" link :icon="'WarningFilled'" @click="openDuplicateDialog">存在重复题目！</el-button>
          </div>
          <p>查看和维护对话中根据简历、录音等生成的个性化面试题。</p>
        </div>
        <div class="page-actions"><el-button :icon="'Download'" :loading="exporting" @click="exportQuestions">导出 Excel</el-button><el-button type="primary" :icon="'Plus'" @click="openCreateDialog">新增题目</el-button></div>
      </div>

      <div class="toolbar"><el-input v-model="searchKeyword" placeholder="搜索题目或答案关键词" clearable :prefix-icon="'Search'" @keyup.enter="handleSearch" @clear="handleSearch" /><el-button type="primary" @click="handleSearch">搜索</el-button></div>

      <el-table :data="questions" v-loading="loading" stripe>
        <el-table-column label="题目" min-width="280" show-overflow-tooltip><template #default="{ row }">{{ getQuestionText(row) }}</template></el-table-column>
        <el-table-column label="答案" min-width="320" show-overflow-tooltip><template #default="{ row }">{{ getAnswerText(row) || '未填写' }}</template></el-table-column>
        <el-table-column prop="category" label="分类" width="110" />
        <el-table-column prop="difficulty" label="难度" width="100"><template #default="{ row }"><el-tag :type="row.difficulty === 'easy' ? 'success' : row.difficulty === 'hard' ? 'danger' : 'warning'" size="small">{{ row.difficulty }}</el-tag></template></el-table-column>
        <el-table-column label="来源" width="110"><template #default="{ row }">{{ sourceMap[row.source || ''] || row.source || '未知' }}</template></el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column label="操作" width="150" fixed="right"><template #default="{ row }"><el-button link type="primary" size="small" @click="openEditDialog(row)">编辑</el-button><el-button link type="danger" size="small" @click="removeQuestion(row)">删除</el-button></template></el-table-column>
      </el-table>

      <div class="pagination"><el-pagination v-model:current-page="pagination.page" :page-size="pagination.page_size" :total="total" layout="total, prev, pager, next, jumper" prev-text="上一页" next-text="下一页" background @current-change="handlePageChange" /></div>

      <el-dialog v-model="dialogVisible" :title="editingId ? '编辑题目' : '新增题目'" width="640px">
        <el-form label-width="90px">
          <el-form-item label="题目" required><el-input v-model="form.question" type="textarea" :rows="3" /></el-form-item>
          <el-form-item label="参考答案"><el-input v-model="form.reference_answer" type="textarea" :rows="6" /></el-form-item>
          <el-form-item label="分类"><el-select v-model="form.category" style="width: 100%"><el-option v-for="opt in categoryOptions" :key="opt.value" :label="opt.label" :value="opt.value" /></el-select></el-form-item>
          <el-form-item label="难度"><el-radio-group v-model="form.difficulty"><el-radio-button label="easy">简单</el-radio-button><el-radio-button label="medium">中等</el-radio-button><el-radio-button label="hard">困难</el-radio-button></el-radio-group></el-form-item>
          <el-form-item label="标签"><el-input v-model="form.tagsText" placeholder="多个标签用英文逗号分隔" /></el-form-item>
        </el-form>
        <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" @click="saveQuestion">保存</el-button></template>
      </el-dialog>

      <el-dialog v-model="duplicateDialogVisible" title="处理重复题目" width="760px">
        <div v-if="duplicateGroups.length" class="duplicate-list">
          <section v-for="group in duplicateGroups" :key="group.question" class="duplicate-group">
            <h3>{{ group.question }}</h3>
            <el-radio-group v-model="duplicateSelections[group.question]" class="duplicate-options">
              <el-radio v-for="item in group.items" :key="item.id" :label="item.id" border><div class="duplicate-option"><strong>保留记录 #{{ item.id }}</strong><span>{{ getAnswerText(item) || '未填写答案' }}</span><small>{{ sourceMap[item.source || ''] || item.source || '未知' }} · {{ item.created_at }}</small></div></el-radio>
            </el-radio-group>
            <div class="duplicate-actions"><el-button type="primary" size="small" @click="resolveDuplicateGroup(group)">保留所选，删除其他</el-button></div>
          </section>
        </div>
        <el-empty v-else description="暂无重复题目" />
      </el-dialog>
    </main>
  </div>
</template>

<style scoped>
.my-question-page { height: 100%; display: flex; flex-direction: column; background: var(--color-bg); overflow: hidden; }
.my-question-content { flex: 1; min-height: 0; overflow-y: auto; overflow-x: hidden; padding: var(--spacing-xl); }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; gap: var(--spacing-md); margin-bottom: var(--spacing-lg); }
.page-header h2 { margin: 0; font-size: var(--font-xxl); color: var(--color-text); }
.page-header p { margin: 6px 0 0; color: var(--color-text-secondary); }
.title-row { display: flex; align-items: center; gap: var(--spacing-sm); flex-wrap: wrap; }
.duplicate-alert { font-weight: 600; }
.toolbar { display: flex; gap: var(--spacing-sm); max-width: 560px; margin-bottom: var(--spacing-md); }
.page-actions { display: flex; gap: var(--spacing-sm); flex-wrap: wrap; justify-content: flex-end; }
.pagination { display: flex; justify-content: flex-end; margin-top: var(--spacing-md); padding-bottom: var(--spacing-lg); }
.duplicate-list { display: flex; flex-direction: column; gap: var(--spacing-md); max-height: 60vh; overflow: auto; }
.duplicate-group { padding: var(--spacing-md); border: 1px solid var(--color-border-light); border-radius: var(--radius-md); }
.duplicate-group h3 { margin: 0 0 var(--spacing-sm); font-size: var(--font-md); color: var(--color-text); line-height: 1.5; }
.duplicate-options { display: flex; flex-direction: column; align-items: stretch; gap: var(--spacing-sm); width: 100%; }
.duplicate-options :deep(.el-radio) { height: auto; margin-right: 0; padding: var(--spacing-sm); }
.duplicate-options :deep(.el-radio__label) { white-space: normal; width: 100%; }
.duplicate-option { display: flex; flex-direction: column; gap: 4px; line-height: 1.5; }
.duplicate-option span { color: var(--color-text); }
.duplicate-option small { color: var(--color-text-secondary); }
.duplicate-actions { display: flex; justify-content: flex-end; margin-top: var(--spacing-sm); }
@media (max-width: 768px) { .my-question-content { padding: var(--spacing-md); } .page-header, .toolbar, .page-actions { flex-direction: column; align-items: stretch; } }
</style>
