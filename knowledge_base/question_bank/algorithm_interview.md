# 算法面试高频题精讲

## 算法面试的核心策略

算法面试不是考你背答案，而是考察你的**分析思路**和**编码能力**。推荐解题步骤：

1. **理解题目**：复述题目，确认输入输出、边界条件、数据范围
2. **暴力解法**：先给出 O(n^2) 或更差的方案，展示你能快速想到解
3. **优化思路**：分析瓶颈在哪，用什么数据结构或算法优化
4. **编码实现**：边写边解释思路，注意变量命名和代码可读性
5. **检查验证**：用示例数据走一遍，检查边界条件
6. **复杂度分析**：时间复杂度 + 空间复杂度

## 必刷数据结构

### 数组与双指针

**两数之和**（LeetCode #1）

思路：哈希表，一次遍历。对每个数 num，检查 target - num 是否在哈希表中。

```python
def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        if target - num in seen:
            return [seen[target - num], i]
        seen[num] = i
```

时间 O(n)，空间 O(n)

**三数之和**（LeetCode #15）

思路：排序 + 固定一个数 + 双指针。注意去重。

**盛最多水的容器**（LeetCode #11）

思路：左右指针从两端收缩，每次移动较短的那端。

**接雨水**（LeetCode #42）

思路：双指针或单调栈。双指针解法：左右最大高度取较小值减去当前高度。

### 链表

**反转链表**（LeetCode #206）

```python
def reverse_list(head):
    prev = None
    while head:
        nxt = head.next
        head.next = prev
        prev = head
        head = nxt
    return prev
```

**链表中环的检测**（LeetCode #141）

思路：快慢指针。快指针走两步，慢指针走一步，相遇则有环。

**LRU 缓存**（LeetCode #146）

思路：哈希表 + 双向链表。get O(1)，put O(1)。

### 二叉树

**二叉树的最大深度**（LeetCode #104）

```python
def max_depth(root):
    if not root:
        return 0
    return 1 + max(max_depth(root.left), max_depth(root.right))
```

**层序遍历**（LeetCode #102）

思路：BFS，用队列，每层记录节点数量。

**二叉树的最近公共祖先**（LeetCode #236）

思路：后序遍历。如果当前节点是 p 或 q，直接返回。如果左右子树都找到，当前就是最近公共祖先。

### 栈与队列

**有效的括号**（LeetCode #20）

思路：栈。左括号入栈，右括号出栈匹配。

**用栈实现队列**（LeetCode #232）

思路：两个栈。一个输入栈，一个输出栈。

**滑动窗口最大值**（LeetCode #239）

思路：单调队列（双端队列）。维护一个递减队列，队首始终是最大值。

### 哈希表

**字母异位词分组**（LeetCode #49）

思路：排序后的字符串作为哈希 key，或字符频率计数作为 key。

**最长连续序列**（LeetCode #128）

思路：用 set 存储所有数，对每个数检查 num-1 是否在 set 中（不在则为起点），然后向后延伸。

### 动态规划

动态规划的核心：**定义状态 → 状态转移方程 → 初始化 → 遍历顺序**

**爬楼梯**（LeetCode #70）

状态：dp[i] = 到达第 i 阶的方法数
转移：dp[i] = dp[i-1] + dp[i-2]

**最长递增子序列**（LeetCode #300）

状态：dp[i] = 以 nums[i] 结尾的 LIS 长度
转移：dp[i] = max(dp[j] + 1) for j < i and nums[j] < nums[i]

**编辑距离**（LeetCode #72）

状态：dp[i][j] = word1[0:i] 和 word2[0:j] 的最小编辑次数
转移：
- word1[i-1] == word2[j-1]: dp[i][j] = dp[i-1][j-1]
- 否则: dp[i][j] = min(插入, 删除, 替换) + 1

**0-1 背包问题**

状态：dp[i][w] = 前 i 个物品、容量 w 时的最大价值
转移：dp[i][w] = max(dp[i-1][w], dp[i-1][w-weight[i]] + value[i])

**完全背包问题**

与 0-1 背包的区别：每个物品可以选多次。遍历顺序改为正序。

### 排序算法

**快速排序**（面试最常手撕）

```python
def quick_sort(nums, left, right):
    if left >= right:
        return
    pivot = nums[(left + right) // 2]
    i, j = left, right
    while i <= j:
        while nums[i] < pivot: i += 1
        while nums[j] > pivot: j -= 1
        if i <= j:
            nums[i], nums[j] = nums[j], nums[i]
            i += 1
            j -= 1
    quick_sort(nums, left, j)
    quick_sort(nums, i, right)
```

**归并排序**

稳定的 O(n log n) 排序，分治思想。常用于求逆序对、外部排序。

### 回溯算法

**全排列**（LeetCode #46）

```python
def permute(nums):
    result = []
    def backtrack(path, used):
        if len(path) == len(nums):
            result.append(path[:])
            return
        for i in range(len(nums)):
            if used[i]:
                continue
            used[i] = True
            path.append(nums[i])
            backtrack(path, used)
            path.pop()
            used[i] = False
    backtrack([], [False]*len(nums))
    return result
```

**N 皇后**（LeetCode #51）

经典回溯，按行放置皇后，检查列和对角线冲突。

### 图算法

**BFS（广度优先搜索）**：求最短路径（无权图）
**DFS（深度优先搜索）**：连通性、拓扑排序、环检测
**并查集**：朋友圈、最小生成树（Kruskal）
**Dijkstra**：单源最短路径（有权图，非负权）

## 刷题策略建议

### 按类型刷题顺序

1. 数组 + 双指针（1 周）
2. 链表（3 天）
3. 栈和队列（3 天）
4. 二叉树（1 周）
5. 哈希表（3 天）
6. 动态规划（2 周）
7. 回溯（1 周）
8. 图算法（1 周）
9. 高级数据结构（堆、字典树、线段树）

### 按难度分配

- Easy（60%）：建立信心，熟悉 API
- Medium（35%）：面试主力题
- Hard（5%）：拓展思维，面试加分项

### 时间管理

- 面试中一道题最多 20-25 分钟
- 前 5 分钟思考和讨论，15 分钟编码，5 分钟检查
- 如果 10 分钟没有思路，主动和面试官讨论换方向
