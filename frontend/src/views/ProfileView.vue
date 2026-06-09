<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import PageTopHeader from '@/components/PageTopHeader.vue'
import { useAuthStore } from '@/stores/auth'
import type { UserInfo } from '@/types'
import {
  getProfileApi,
  updateProfileApi,
  changePasswordApi,
  changeUsernameApi,
  uploadAvatarApi,
  toggleAiUseApi,
} from '@/api/profile'

type TabKey = 'account' | 'profile' | 'security'

const authStore = useAuthStore()
const activeTab = ref<TabKey>('account')
const userInfo = ref<UserInfo | null>(null)
const profileSaving = ref(false)
const avatarUploading = ref(false)
const avatarInputRef = ref<HTMLInputElement | null>(null)
const avatarTimestamp = ref(Date.now())
const usernameDialogVisible = ref(false)
const newUsername = ref('')
const usernameSubmitting = ref(false)
const passwordDialogVisible = ref(false)
const passwordSubmitting = ref(false)
const aiToggling = ref(false)

const navItems = [
  { key: 'account' as const, label: '账号信息', icon: 'User' },
  { key: 'profile' as const, label: '个人信息', icon: 'EditPen' },
  { key: 'security' as const, label: '账号安全', icon: 'Lock' },
]

const profileForm = reactive({
  age: null as number | null,
  gender: '',
  major: '',
  grade: '',
  university: '',
  education_level: '',
  degree: '',
  graduation_year: '',
  target_position: '',
  target_city: '',
  skills: '',
  certificates: '',
  internship_experience: '',
})

const passwordForm = reactive({ old_password: '', new_password: '', confirm_password: '' })

watch(() => authStore.user?.avatar_url, () => { avatarTimestamp.value = Date.now() })

const avatarUrl = computed(() => {
  const url = userInfo.value?.avatar_url || authStore.currentUser?.avatar_url || ''
  if (!url) return ''
  return url.includes('?') ? `${url}&t=${avatarTimestamp.value}` : `${url}?t=${avatarTimestamp.value}`
})

const aiSwitchValue = computed({
  get: () => userInfo.value?.profile?.allow_ai_use ?? true,
  set: (val: boolean) => handleToggleAi(val),
})

async function loadUserInfo() {
  try {
    const res = await getProfileApi()
    userInfo.value = res.data
    const p = res.data.profile
    if (p) {
      profileForm.age = p.age ?? null
      profileForm.gender = p.gender ?? ''
      profileForm.major = p.major ?? ''
      profileForm.grade = p.grade ?? ''
      profileForm.university = p.university ?? ''
      profileForm.education_level = p.education_level ?? ''
      profileForm.degree = p.degree ?? ''
      profileForm.graduation_year = p.graduation_year ?? ''
      profileForm.target_position = p.target_position ?? ''
      profileForm.target_city = p.target_city ?? ''
      profileForm.skills = p.skills ?? ''
      profileForm.certificates = p.certificates ?? ''
      profileForm.internship_experience = p.internship_experience ?? ''
    }
  } catch {
    ElMessage.error('加载个人信息失败')
  }
}

async function handleSaveProfile() {
  profileSaving.value = true
  try {
    await updateProfileApi({ ...profileForm, age: profileForm.age ?? undefined })
    ElMessage.success('个人资料保存成功')
    await loadUserInfo()
  } catch {
    ElMessage.error('保存失败，请重试')
  } finally {
    profileSaving.value = false
  }
}

function handleAvatarClick() {
  avatarInputRef.value?.click()
}

async function handleAvatarChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (!['image/jpeg', 'image/png', 'image/gif', 'image/webp'].includes(file.type)) {
    ElMessage.error('仅支持 JPG、PNG、GIF、WebP 格式的头像')
    input.value = ''
    return
  }
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.error('头像文件不能超过 5MB')
    input.value = ''
    return
  }
  avatarUploading.value = true
  try {
    const res = await uploadAvatarApi(file)
    if (authStore.user) {
      authStore.user.avatar_url = res.data.avatar_url
      localStorage.setItem('user', JSON.stringify(authStore.user))
    }
    if (userInfo.value) userInfo.value.avatar_url = res.data.avatar_url
    avatarTimestamp.value = Date.now()
    ElMessage.success('头像上传成功')
  } catch {
    ElMessage.error('头像上传失败')
  } finally {
    avatarUploading.value = false
    input.value = ''
  }
}

function openUsernameDialog() {
  newUsername.value = userInfo.value?.username || authStore.currentUser?.username || ''
  usernameDialogVisible.value = true
}

async function handleChangeUsername() {
  const username = newUsername.value.trim()
  if (!username) {
    ElMessage.warning('用户名不能为空')
    return
  }
  usernameSubmitting.value = true
  try {
    const res = await changeUsernameApi({ new_username: username })
    authStore.user = res.data as any
    localStorage.setItem('user', JSON.stringify(res.data))
    userInfo.value = res.data
    ElMessage.success('用户名修改成功')
    usernameDialogVisible.value = false
  } catch {
    ElMessage.error('用户名修改失败')
  } finally {
    usernameSubmitting.value = false
  }
}

function openPasswordDialog() {
  passwordForm.old_password = ''
  passwordForm.new_password = ''
  passwordForm.confirm_password = ''
  passwordDialogVisible.value = true
}

async function handleChangePassword() {
  if (!passwordForm.old_password) {
    ElMessage.warning('请输入旧密码')
    return
  }
  if (passwordForm.new_password.length < 6) {
    ElMessage.warning('新密码长度不能少于 6 位')
    return
  }
  if (passwordForm.new_password !== passwordForm.confirm_password) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  passwordSubmitting.value = true
  try {
    await changePasswordApi({ old_password: passwordForm.old_password, new_password: passwordForm.new_password })
    ElMessage.success('密码修改成功，请重新登录')
    passwordDialogVisible.value = false
    setTimeout(() => authStore.logout(), 1200)
  } catch {
    ElMessage.error('密码修改失败，请检查旧密码是否正确')
  } finally {
    passwordSubmitting.value = false
  }
}

async function handleToggleAi(val: boolean) {
  aiToggling.value = true
  try {
    await toggleAiUseApi({ allow_ai_use: val })
    if (userInfo.value?.profile) userInfo.value.profile.allow_ai_use = val
    ElMessage.success(val ? '已开启 AI 个性化' : '已关闭 AI 个性化')
  } catch {
    ElMessage.error('设置失败')
  } finally {
    aiToggling.value = false
  }
}

onMounted(loadUserInfo)
</script>

<template>
  <div class="profile-page">
    <PageTopHeader title="个人中心" show-questions-entry />
    <div class="profile-body">
      <aside class="profile-nav">
        <div v-for="item in navItems" :key="item.key" class="nav-item" :class="{ active: activeTab === item.key }" @click="activeTab = item.key">
          <el-icon :size="18"><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </div>
      </aside>

      <main class="profile-content">
        <div v-if="activeTab === 'account'" class="tab-content">
          <h2 class="content-title">账号信息</h2>
          <el-card class="info-card" shadow="never">
            <div class="avatar-section">
              <div class="avatar-wrapper" @click="handleAvatarClick">
                <el-avatar :size="80" :src="avatarUrl" :style="{ backgroundColor: '#534AB7' }">{{ authStore.currentUser?.username?.charAt(0)?.toUpperCase() || 'U' }}</el-avatar>
                <div class="avatar-overlay" :class="{ uploading: avatarUploading }">
                  <el-icon :size="20" v-if="!avatarUploading"><Camera /></el-icon>
                  <el-icon :size="20" class="is-loading" v-else><Loading /></el-icon>
                </div>
              </div>
              <span class="avatar-hint">点击更换头像（JPG/PNG/GIF/WebP，5MB 内）</span>
            </div>
          </el-card>
          <el-card class="info-card" shadow="never">
            <div class="info-list">
              <div class="info-item"><span class="info-label">用户名</span><span class="info-value">{{ userInfo?.username }}</span><el-button size="small" text type="primary" @click="openUsernameDialog">修改</el-button></div>
              <div class="info-item"><span class="info-label">邮箱</span><span class="info-value">{{ userInfo?.email || '未设置' }}</span></div>
              <div class="info-item"><span class="info-label">角色</span><el-tag size="small" :type="authStore.isAdmin ? 'danger' : 'info'">{{ authStore.isAdmin ? '管理员' : '普通用户' }}</el-tag></div>
              <div class="info-item"><span class="info-label">注册时间</span><span class="info-value">{{ userInfo?.created_at ? new Date(userInfo.created_at).toLocaleDateString('zh-CN') : '-' }}</span></div>
            </div>
          </el-card>
        </div>

        <div v-if="activeTab === 'profile'" class="tab-content">
          <h2 class="content-title">个人信息</h2>
          <el-card class="info-card" shadow="never">
            <div class="info-item ai-item">
              <div class="ai-info">
                <span class="info-label strong">允许 AI 使用我的个人信息</span>
                <span class="ai-desc">开启后，AI 会结合学历、专业、目标岗位、技能和经历给出更个性化的建议。</span>
              </div>
              <el-switch v-model="aiSwitchValue" :loading="aiToggling" active-color="#534AB7" size="large" />
            </div>
          </el-card>

          <h2 class="content-title small-title">求职信息</h2>
          <el-card class="info-card" shadow="never">
            <el-form :model="profileForm" label-width="82px" label-position="left" class="profile-form">
              <el-row :gutter="20">
                <el-col :span="12"><el-form-item label="年龄"><el-input-number v-model="profileForm.age" :min="1" :max="120" placeholder="请输入年龄" controls-position="right" style="width: 100%" /></el-form-item></el-col>
                <el-col :span="12"><el-form-item label="性别"><el-select v-model="profileForm.gender" placeholder="请选择性别" clearable style="width: 100%"><el-option label="男" value="male" /><el-option label="女" value="female" /><el-option label="其他" value="other" /></el-select></el-form-item></el-col>
                <el-col :span="12"><el-form-item label="学校"><el-input v-model="profileForm.university" placeholder="请输入学校名称" /></el-form-item></el-col>
                <el-col :span="12"><el-form-item label="年级"><el-input v-model="profileForm.grade" placeholder="如：大四、研二" /></el-form-item></el-col>
                <el-col :span="12"><el-form-item label="学历"><el-select v-model="profileForm.education_level" placeholder="请选择学历" clearable style="width: 100%"><el-option label="专科" value="专科" /><el-option label="本科" value="本科" /><el-option label="硕士" value="硕士" /><el-option label="博士" value="博士" /><el-option label="其他" value="其他" /></el-select></el-form-item></el-col>
                <el-col :span="12"><el-form-item label="学位"><el-input v-model="profileForm.degree" placeholder="如：工学学士" /></el-form-item></el-col>
                <el-col :span="12"><el-form-item label="毕业年份"><el-input v-model="profileForm.graduation_year" placeholder="如：2026" /></el-form-item></el-col>
                <el-col :span="12"><el-form-item label="专业"><el-input v-model="profileForm.major" placeholder="请输入专业名称" /></el-form-item></el-col>
                <el-col :span="12"><el-form-item label="目标岗位"><el-input v-model="profileForm.target_position" placeholder="如：中药研发、Java 后端" /></el-form-item></el-col>
                <el-col :span="12"><el-form-item label="目标城市"><el-input v-model="profileForm.target_city" placeholder="如：杭州、上海" /></el-form-item></el-col>
              </el-row>
              <el-form-item label="技能"><el-input v-model="profileForm.skills" placeholder="用逗号分隔，如 Python、数据分析" /></el-form-item>
              <el-form-item label="证书"><el-input v-model="profileForm.certificates" placeholder="如：英语四级、执业药师资格" /></el-form-item>
              <el-form-item label="经历摘要"><el-input v-model="profileForm.internship_experience" type="textarea" :rows="3" placeholder="填写实习、项目、竞赛、科研经历摘要" /></el-form-item>
              <el-form-item><el-button type="primary" :loading="profileSaving" @click="handleSaveProfile">{{ profileSaving ? '保存中...' : '保存信息' }}</el-button></el-form-item>
            </el-form>
          </el-card>
        </div>

        <div v-if="activeTab === 'security'" class="tab-content">
          <h2 class="content-title">账号安全</h2>
          <el-card class="info-card" shadow="never">
            <div class="security-item">
              <div class="security-info"><span class="security-label">登录密码</span><span class="security-desc">修改后需要重新登录</span></div>
              <el-button size="small" type="primary" plain @click="openPasswordDialog">修改密码</el-button>
            </div>
          </el-card>
        </div>
      </main>
    </div>

    <input ref="avatarInputRef" type="file" accept="image/jpeg,image/png,image/gif,image/webp" style="display: none" @change="handleAvatarChange" />

    <el-dialog v-model="usernameDialogVisible" title="修改用户名" width="420px" :close-on-click-modal="false">
      <el-form label-width="80px"><el-form-item label="新用户名"><el-input v-model="newUsername" placeholder="请输入新用户名" :minlength="3" :maxlength="64" /></el-form-item></el-form>
      <template #footer><el-button @click="usernameDialogVisible = false">取消</el-button><el-button type="primary" :loading="usernameSubmitting" @click="handleChangeUsername">确认修改</el-button></template>
    </el-dialog>

    <el-dialog v-model="passwordDialogVisible" title="修改密码" width="420px" :close-on-click-modal="false">
      <el-form label-width="80px">
        <el-form-item label="旧密码"><el-input v-model="passwordForm.old_password" type="password" placeholder="请输入旧密码" show-password /></el-form-item>
        <el-form-item label="新密码"><el-input v-model="passwordForm.new_password" type="password" placeholder="请输入新密码（至少6位）" show-password /></el-form-item>
        <el-form-item label="确认密码"><el-input v-model="passwordForm.confirm_password" type="password" placeholder="再次输入新密码" show-password /></el-form-item>
      </el-form>
      <template #footer><el-button @click="passwordDialogVisible = false">取消</el-button><el-button type="primary" :loading="passwordSubmitting" @click="handleChangePassword">确认修改</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.profile-page { display: flex; flex-direction: column; height: 100%; overflow: hidden; }
.profile-body { display: flex; flex: 1; min-height: 0; overflow: hidden; }
.profile-nav { width: 190px; flex-shrink: 0; background: var(--color-card); border-right: 1px solid var(--color-border-light); padding: var(--spacing-md) 0; display: flex; flex-direction: column; gap: 4px; }
.nav-item { display: flex; align-items: center; gap: var(--spacing-sm); padding: 12px var(--spacing-lg); cursor: pointer; transition: all 0.2s; color: var(--color-text-secondary); font-size: var(--font-sm); border-left: 3px solid transparent; }
.nav-item:hover { background: var(--color-bg); color: var(--color-text); }
.nav-item.active { color: var(--color-primary); background: var(--color-primary-lighter); border-left-color: var(--color-primary); font-weight: 500; }
.profile-content { flex: 1; min-width: 0; overflow-y: auto; background: radial-gradient(circle at 50% 0, rgba(83, 74, 183, 0.06), transparent 34%), var(--color-bg); }
.tab-content { max-width: 640px; margin: 0 auto; padding: 32px var(--spacing-lg) 56px; }
.content-title { font-size: var(--font-title); font-weight: 700; color: var(--color-text); margin: 0 0 var(--spacing-lg); }
.small-title { margin-top: var(--spacing-xl); }
.info-card { margin-bottom: var(--spacing-md); border: 1px solid var(--color-border-light); border-radius: var(--radius-lg); overflow: hidden; }
.info-card :deep(.el-card__body) { padding: 20px; }
.avatar-section { display: flex; flex-direction: column; align-items: center; gap: var(--spacing-sm); padding: var(--spacing-md) 0; }
.avatar-wrapper { position: relative; cursor: pointer; border-radius: 50%; }
.avatar-overlay { position: absolute; inset: 0; border-radius: 50%; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; color: #fff; opacity: 0; transition: opacity .2s; }
.avatar-overlay.uploading, .avatar-wrapper:hover .avatar-overlay { opacity: 1; }
.avatar-hint { font-size: var(--font-xs); color: var(--color-text-placeholder); text-align: center; }
.info-list { display: flex; flex-direction: column; gap: 16px; }
.info-item { display: flex; align-items: center; gap: var(--spacing-sm); }
.info-label { font-size: var(--font-sm); color: var(--color-text-secondary); min-width: 64px; }
.info-label.strong, .strong { font-weight: 500; color: var(--color-text); }
.info-value { font-size: var(--font-sm); color: var(--color-text); flex: 1; }
.ai-item { align-items: flex-start; justify-content: space-between; }
.ai-info { flex: 1; display: flex; flex-direction: column; gap: 4px; margin-right: var(--spacing-lg); }
.ai-desc { font-size: var(--font-xs); color: var(--color-text-placeholder); line-height: 1.5; }
.security-item { display: flex; align-items: center; justify-content: space-between; padding: 8px 0; }
.security-info { display: flex; flex-direction: column; gap: 4px; }
.security-label { font-size: var(--font-sm); font-weight: 500; color: var(--color-text); }
.security-desc { font-size: var(--font-xs); color: var(--color-text-placeholder); }
.profile-form { max-height: calc(100% - 48px); overflow-y: auto; padding-right: 4px; }
.profile-form :deep(.el-form-item) { margin-bottom: 16px; }
@media (max-width: 768px) { .profile-nav { width: 150px; } .tab-content { padding: 24px var(--spacing-md); } }
</style>
