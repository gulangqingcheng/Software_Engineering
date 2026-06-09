import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import './style.css'

const app = createApp(App)

app.config.errorHandler = (error, instance, info) => {
  console.error('[Vue error]', error, info, instance)
  const componentType = (instance as any)?.type
  ;(window as any).__APP_DEBUG_REPORT__?.('vue.error', error, {
    info,
    component: componentType?.name || componentType?.__name || 'anonymous',
  })
}

// 注册 Pinia
app.use(createPinia())

// 注册 Vue Router
app.use(router)

router.onError((error) => {
  console.error('[Router error]', error)
  ;(window as any).__APP_DEBUG_REPORT__?.('router.error', error, {
    path: router.currentRoute.value.fullPath,
  })
})

// 注册 Element Plus（中文语言包）
app.use(ElementPlus, {
  locale: zhCn,
})

// 全局注册 Element Plus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.mount('#app')

setTimeout(() => {
  ;(window as any).__APP_DEBUG_CHECK__?.('vue-mounted+500ms')
}, 500)

router.isReady()
  .then(() => {
    ;(window as any).__APP_DEBUG_CHECK__?.('router-ready')
  })
  .catch((error) => {
    ;(window as any).__APP_DEBUG_REPORT__?.('router.ready.error', error)
  })
