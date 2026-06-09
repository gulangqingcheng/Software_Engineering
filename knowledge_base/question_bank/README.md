# 面试题库

## 数据格式
JSON Lines 格式，每行一个面试题：

```json
{"question": "请介绍一下Spring Boot的自动装配原理", "category": "技术-Java-Spring", "difficulty": "medium", "reference_answer": "Spring Boot自动装配通过@EnableAutoConfiguration注解实现..."}
{"question": "请描述一次你解决团队冲突的经历", "category": "行为-团队协作", "difficulty": "medium", "reference_answer": "使用STAR法则回答..."}
```

## 字段说明
| 字段 | 类型 | 说明 |
|------|------|------|
| question | string | 面试题目 |
| category | string | 分类（技术-方向-细分 / 行为-类型 / 场景-类型） |
| difficulty | string | 难度：easy / medium / hard |
| reference_answer | string | 参考答案 |
| tags | array | 标签列表（可选） |
| source | string | 来源（可选） |
