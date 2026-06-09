# Vue3 前端面试高频题

## Vue3 核心特性

### Q1: Vue3 相比 Vue2 有哪些重大变化？

1. **Composition API**：替代 Options API，逻辑复用更灵活
2. **响应式系统重写**：用 Proxy 替代 Object.defineProperty，支持动态属性、数组索引监听
3. **Teleport 组件**：允许将组件渲染到 DOM 中的任意位置
4. **Fragment**：模板不再需要单一根元素
5. **更好的 TypeScript 支持**：源码用 TypeScript 重写
6. **Tree-shaking 优化**：按需引入，打包体积更小
7. **性能提升**：虚拟 DOM 重写，编译时优化（静态提升、Patch Flag）

### Q2: ref 和 reactive 的区别

- **ref**：适合基本类型（string/number/boolean），访问需要 .value，模板中自动解包
- **reactive**：适合对象/数组，直接访问属性，不能解构（会失去响应性）
- 推荐统一使用 ref，避免 reactive 的解构陷阱

```javascript
const count = ref(0)
count.value++ // JS 中需要 .value

const state = reactive({ name: 'Alice', age: 20 })
state.name = 'Bob' // 直接访问
const { name } = state // 失去响应性！需要 toRefs()
```

### Q3: Vue3 生命周期钩子

setup() 中使用：onBeforeMount、onMounted、onBeforeUpdate、onUpdated、onBeforeUnmount、onUnmounted

```javascript
import { onMounted, ref } from 'vue'

export default {
  setup() {
    const data = ref(null)
    onMounted(async () => {
      data.value = await fetchData()
    })
    return { data }
  }
}
```

### Q4: computed 和 watch 的区别和使用场景

- **computed**：有缓存的计算属性，依赖不变不会重新计算，必须有返回值，适合派生数据
- **watch**：监听数据变化执行副作用，无返回值，适合异步操作（API 调用）
- **watchEffect**：自动追踪依赖，立即执行一次，适合简单副作用

### Q5: Vue3 的组件通信方式

1. **Props / Emit**：父子组件基础通信
2. **Provide / Inject**：跨层级通信（祖先 → 后代）
3. **Pinia / Vuex**：全局状态管理
4. **EventBus**：兄弟组件通信（Vue3 推荐用 mitt 库）
5. **ref 模板引用**：父组件直接调用子组件方法
6. **attrs / slots**：高级通信模式

### Q6: v-if 和 v-show 的区别

- **v-if**：条件为 false 时完全销毁和重建 DOM，切换开销大，初始渲染开销小
- **v-show**：通过 CSS display 控制显示隐藏，初始渲染开销大，切换开销小
- 频繁切换用 v-show，条件很少变化用 v-if

### Q7: Vue3 的 Diff 算法优化

Vue3 使用 Patch Flag 和静态提升优化虚拟 DOM 对比：
- **静态提升**：静态节点在编译时提升到渲染函数外部，只创建一次
- **Patch Flag**：动态节点标记哪些属性会变化，diff 时只比对变化的属性
- **Block Tree**：将模板的根节点作为 Block，只追踪其内部动态子节点

### Q8: Vue Router 导航守卫

```javascript
router.beforeEach((to, from, next) => {
  const isAuthenticated = checkAuth()
  if (to.meta.requiresAuth && !isAuthenticated) {
    next('/login')
  } else {
    next()
  }
})
```

### Q9: Pinia vs Vuex

| 特性 | Pinia | Vuex |
|------|-------|------|
| TypeScript | 完美支持 | 支持一般 |
| Mutation | 不需要 | 必须 |
| 模块化 | 天然支持（Store 即模块） | 需要手动 modules |
| 体积 | ~1KB | ~10KB |
| DevTools | 完美集成 | 支持 |
| API | 简洁直观 | 较繁琐 |

### Q10: 虚拟 DOM 和 JSX

Vue3 使用模板编译器将模板转为渲染函数，也可以直接用 JSX/TSX。
虚拟 DOM 是真实 DOM 的 JS 对象表示，通过 diff 算法最小化 DOM 操作。

## 前端面试补充知识

### 性能优化

1. **首屏优化**：路由懒加载、图片懒加载、骨架屏、SSR/SSG
2. **运行时优化**：虚拟列表（大量列表）、防抖节流、Web Worker
3. **构建优化**：Tree Shaking、代码分割、Gzip 压缩
4. **缓存策略**：HTTP 缓存、Service Worker、本地存储

### CSS 相关

1. **BFC（块级格式化上下文）**：解决 margin 塌陷、浮动高度塌陷
2. **Flex 布局**：flex-direction、justify-content、align-items
3. **Grid 布局**：二维布局方案
4. **居中方案**：Flex 居中、Grid 居中、absolute + transform
5. **响应式设计**：media query、rem/vw/vh、CSS 变量

### JavaScript 核心

1. **闭包**：函数 + 其词法环境的引用，常用于数据私有化、柯里化
2. **原型链**：对象属性查找沿原型链向上搜索
3. **事件循环**：宏任务（setTimeout）和微任务（Promise.then）的执行顺序
4. **Promise / async-await**：异步编程的解决方案
5. **ES6+**：解构赋值、展开运算符、可选链（?.）、空值合并（??）
