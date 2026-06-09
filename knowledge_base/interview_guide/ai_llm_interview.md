# AI/大模型面试专题

## 大语言模型基础

### Transformer 架构核心

Transformer 由 Vaswani 等人在 2017 年的 "Attention is All You Need" 论文中提出，已成为现代 AI 的基础架构。

**核心组件：**
- **Self-Attention**：计算序列中每个位置与其他所有位置的关联度
- **Multi-Head Attention**：多头注意力，捕获不同子空间的信息
- **Feed-Forward Network**：两层全连接网络 + ReLU 激活
- **Positional Encoding**：位置编码（正弦/余弦函数或可学习位置向量）
- **Layer Normalization**：层归一化，稳定训练
- **Residual Connection**：残差连接，缓解梯度消失

**Attention 计算公式：**
Attention(Q, K, V) = softmax(QK^T / sqrt(d_k)) * V

其中 Q（Query）、K（Key）、V（Value）是输入的线性变换，d_k 是 Key 的维度。

### RAG（检索增强生成）

**为什么需要 RAG？**
- LLM 存在知识截止日期（训练数据之后的事件不知道）
- LLM 可能产生幻觉（编造不存在的知识）
- 企业需要让 LLM 基于私有数据回答问题

**RAG 核心流程：**
1. **文档处理**：文档 → 分块 → 向量化
2. **存储**：向量 + 元数据写入向量数据库（ChromaDB / Milvus / Pinecone）
3. **检索**：用户提问 → 向量化 → 在向量库中搜索相似文档
4. **生成**：检索到的文档作为上下文 → 拼入 Prompt → LLM 生成回答

**Embedding 模型选择：**
- BGE 系列（BAAI）：中文场景首选，bge-small-zh-v1.5 轻量高效
- text2vec：国产优秀中文 Embedding 模型
- OpenAI text-embedding-3：英文场景效果好

**向量数据库对比：**

| 特性 | ChromaDB | Milvus | FAISS | Pinecone |
|------|----------|--------|-------|----------|
| 部署方式 | 本地/嵌入式 | 分布式 | 本地库 | 云服务 |
| 规模 | 中小 | 大规模 | 中等 | 大规模 |
| 易用性 | 高 | 中 | 高 | 高 |
| 适用场景 | 开发/原型 | 生产环境 | 离线搜索 | 快速上手 |

### Prompt Engineering（提示工程）

**核心技巧：**

1. **系统提示词**：定义 AI 的角色、行为规则
2. **Few-Shot 示例**：提供 2-3 个输入输出示例
3. **思维链（Chain of Thought）**：要求 AI 逐步推理
4. **角色扮演**：设定专家身份提高回答质量

**面试中常见 Prompt 设计题：**
"如何设计一个面试官 AI 的系统提示词？"

```python
SYSTEM_PROMPT = """你是一位经验丰富的技术面试官，正在对应聘者进行{position}岗位的面试。

面试要求：
1. 每次只问一个问题，等候选人回答后再问下一个
2. 根据候选人的回答调整问题难度
3. 关注候选人的思考过程，而不只是答案正确性
4. 对回答给出简短的评价和追问
5. 在面试结束时给出总体评价

候选人简历摘要：
{resume_summary}
"""
```

### LangChain / Agent 框架

**LangChain 核心组件：**
- **LLM Wrapper**：统一 LLM 调用接口
- **Chain**：多个操作串联的执行链
- **Memory**：对话历史管理
- **Tool**：外部工具调用（搜索、计算器、数据库）
- **Agent**：让 LLM 自主决定调用哪些工具

**Agent vs Chain 的区别：**
- Chain：预定义的执行流程，确定性
- Agent：LLM 根据输入动态决策，非确定性

### 向量检索与相似度计算

**余弦相似度（Cosine Similarity）：**
sim(A, B) = (A · B) / (||A|| * ||B||)
范围 [-1, 1]，归一化后范围 [0, 1]
最适合文本语义相似度计算

**欧氏距离（Euclidean Distance）：**
d(A, B) = sqrt(sum((a_i - b_i)^2))
值越小越相似

**文档分块策略：**
- 固定长度分块：简单但不考虑语义边界
- 递归字符分块：按段落 → 句子 → 字符逐级切分（推荐）
- 语义分块：用 Embedding 检测语义转折点
- Sliding Window：固定长度 + 重叠（保持上下文连贯）

## AI 项目实战面试题

### Q: 如何评估一个 RAG 系统的效果？

评估维度：
1. **检索质量**：召回率（Relevance）、MRR（平均倒数排名）
2. **生成质量**：忠实度（Faithfulness）、回答相关性
3. **端到端**：用户满意度、回答准确率

常用工具：RAGAS 评估框架、TruLens

### Q: 如何处理 LLM 的幻觉问题？

1. RAG 检索增强：提供真实上下文
2. 温度参数调低（0.1-0.3）
3. 在 Prompt 中明确要求"不确定时说不知道"
4. 交叉验证：多个 LLM 对比
5. 人类在环（Human-in-the-loop）：关键输出人工审核

### Q: Embedding 模型如何选择？

考虑因素：
- 语言：中文 → BGE / text2vec
- 部署：本地 → sentence-transformers / ONNX
- 性能 vs 效果：small 模型快但效果略差
- 维度：512 维（bge-small）vs 1024 维（bge-base）vs 768 维（bge-large）

### Q: 向量数据库的 HNSW 索引原理

HNSW（Hierarchical Navigable Small World）是一种近似最近邻搜索算法：
- 多层图结构，上层稀疏、下层密集
- 搜索时从顶层入口开始，逐层向下贪心搜索
- 时间复杂度接近 O(log n)，准确率可通过参数调优
- 参数：M（每层最大连接数）、efConstruction（构建时搜索宽度）、efSearch（查询时搜索宽度）
