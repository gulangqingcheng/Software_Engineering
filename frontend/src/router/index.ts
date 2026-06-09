import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Chat',
    component: () => import('@/views/ChatView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { guest: true },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { guest: true },
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/ProfileView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/my-questions',
    name: 'MyQuestions',
    component: () => import('@/views/MyQuestionsView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/interview',
    name: 'Interview',
    component: () => import('@/views/InterviewView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/admin',
    name: 'AdminDashboard',
    component: () => import('@/views/admin/DashboardView.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
    path: '/admin/questions',
    name: 'QuestionManage',
    component: () => import('@/views/admin/QuestionManage.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
    path: '/admin/knowledge',
    name: 'KnowledgeManage',
    component: () => import('@/views/admin/KnowledgeManage.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
    path: '/admin/users',
    name: 'UserManage',
    component: () => import('@/views/admin/UserManage.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
    path: '/admin/agents',
    name: 'AgentMonitor',
    component: () => import('@/views/admin/AgentMonitor.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

function getDebugQuery() {
  const params = new URLSearchParams(window.location.search)
  const keepPanel = params.get('debug-panel') === '1' || sessionStorage.getItem('app-debug-panel') === '1'
  if (!keepPanel) return {}

  return {
    'debug-panel': '1',
    'debug-theme': params.get('debug-theme') || localStorage.getItem('app-theme') || 'light',
  }
}

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('access_token')
  const isLoggedIn = !!token

  const userStr = localStorage.getItem('user')
  let isAdmin = false
  if (userStr) {
    try {
      const user = JSON.parse(userStr)
      isAdmin = user.role === 'admin'
    } catch {
      // Ignore malformed local user cache.
    }
  }

  if (to.meta.requiresAuth && !isLoggedIn) {
    next({
      name: 'Login',
      query: {
        redirect: to.fullPath,
        ...getDebugQuery(),
      },
    })
    return
  }

  if (to.meta.guest && isLoggedIn) {
    next({ name: 'Chat' })
    return
  }

  if (to.meta.requiresAdmin && !isAdmin) {
    next({ name: 'Chat' })
    return
  }

  next()
})

export default router
