<template>
  <div class="user-manage">
    <el-page-header title="后台管理" @back="$router.push('/admin')">
      <template #content>
        <span class="page-title">用户管理</span>
      </template>
    </el-page-header>

    <div class="content">
      <!-- 搜索和操作 -->
      <el-card class="toolbar-card">
        <el-row :gutter="20" align="middle">
          <el-col :span="6">
            <el-input v-model="searchKeyword" placeholder="搜索用户名/邮箱" clearable />
          </el-col>
          <el-col :span="4">
            <el-select v-model="roleFilter" placeholder="角色筛选" clearable>
              <el-option label="普通用户" value="user" />
              <el-option label="管理员" value="admin" />
            </el-select>
          </el-col>
          <el-col :span="2">
            <el-button type="primary" @click="fetchUsers">搜索</el-button>
          </el-col>
        </el-row>
      </el-card>

      <!-- 用户表格 -->
      <el-card>
        <el-table :data="users" v-loading="loading" style="width: 100%">
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="username" label="用户名" width="120" />
          <el-table-column prop="email" label="邮箱" />
          <el-table-column prop="role" label="角色" width="100">
            <template #default="{ row }">
              <el-tag :type="row.role === 'admin' ? 'danger' : 'info'" size="small">
                {{ roleMap[row.role] }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="updated_at" label="最后活跃" width="180" />
          <el-table-column prop="created_at" label="注册时间" width="180" />
          <el-table-column label="操作" width="150">
            <template #default="{ row }">
              <el-button
                size="small"
                type="primary"
                link
                @click="handleRoleChange(row, row.role === 'admin' ? 'user' : 'admin')"
              >
                {{ row.role === 'admin' ? '设为用户' : '设为管理员' }}
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="pagination">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="10"
            :total="totalUsers"
            layout="prev, pager, next"
            @current-change="fetchUsers"
          />
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getAdminUsersApi, updateAdminUserRoleApi, type AdminUserItem } from '@/api/admin'

const searchKeyword = ref('')
const roleFilter = ref('')
const currentPage = ref(1)
const totalUsers = ref(0)
const loading = ref(false)

const roleMap: Record<string, string> = {
  user: '普通用户',
  admin: '管理员',
}

const users = ref<AdminUserItem[]>([])

async function fetchUsers() {
  loading.value = true
  try {
    const res = await getAdminUsersApi({
      page: currentPage.value,
      page_size: 10,
      keyword: searchKeyword.value || undefined,
      role: roleFilter.value || undefined,
    })
    users.value = res.data.items
    totalUsers.value = res.data.total
  } finally {
    loading.value = false
  }
}

async function handleRoleChange(row: AdminUserItem, role: string) {
  await updateAdminUserRoleApi(row.id, role)
  ElMessage.success('角色已更新')
  fetchUsers()
}

onMounted(() => {
  fetchUsers()
})
</script>

<style scoped>
.user-manage { padding: 20px; }
.page-title { font-size: 16px; font-weight: 500; }
.content { margin-top: 20px; }
.toolbar-card { margin-bottom: 20px; }
.pagination { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
