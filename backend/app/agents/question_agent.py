"""
面试题生成 Agent
使用 Tavily 搜索 + ChromaDB RAG + DeepSeek 生成高质量面试题
"""

import ast
import json
import logging
import re
from typing import Any

import httpx

from app.agents.base_agent import AgentInput, AgentOutput, BaseAgent
from app.config import settings

logger = logging.getLogger(__name__)

# 面试题生成系统提示词
QUESTION_GEN_SYSTEM_PROMPT = """你是一位资深的技术面试官，擅长根据岗位方向和难度级别生成高质量的面试题。

生成面试题时请遵循以下原则：
1. 题目要贴近实际面试场景，考察候选人真正的能力
2. 每道题都要有明确的考察点
3. 参考答案要详细，包含核心思路和关键代码/步骤
4. 难度分级要准确：
   - easy：基础知识、概念理解
   - medium：项目经验、方案设计、中等复杂度算法
   - hard：系统设计、复杂架构决策、深度技术问题
5. 题目类型可以包括：技术知识、场景设计、行为面试、方案对比

请以 JSON 数组格式返回，每个题目包含：
```json
[
  {
    "question": "题目内容",
    "category": "分类标签",
    "difficulty": "easy/medium/hard",
    "type": "技术/行为/场景设计",
    "key_points": ["考察点1", "考察点2"],
    "reference_answer": "详细参考答案...",
    "tags": ["标签1", "标签2"]
  }
]
```"""


class QuestionAgent(BaseAgent):
    """
    面试题生成 Agent

    工作流程：
    1. 使用 Tavily 搜索相关面试题/面经
    2. 使用 ChromaDB RAG 检索本地题库中的相似题目
    3. 综合 DeepSeek LLM 生成新的面试题
    """

    def __init__(self):
        super().__init__(name="question_agent")

    def _extract_json_payload(self, raw: str) -> Any | None:
        """Extract the first complete JSON object/array from an LLM response."""
        text = raw.strip()
        candidates = []

        for match in re.finditer(r"```(?:json|JSON)?\s*([\s\S]*?)```", text):
            candidates.append(match.group(1).strip())

        candidates.append(text)
        candidates.extend(self._iter_balanced_json_candidates(text))

        for candidate in candidates:
            payload = self._parse_json_candidate(candidate)
            if payload is not None:
                return payload
        return None

    def _parse_json_candidate(self, candidate: str) -> Any | None:
        """Parse JSON with safe fallbacks for common LLM formatting issues."""
        text = candidate.strip().strip("\ufeff")
        if not text:
            return None

        if text.startswith("```"):
            text = re.sub(r"^```(?:json|JSON)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text).strip()

        variants = [
            text,
            re.sub(r",\s*([}\]])", r"\1", text),
        ]
        for value in variants:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                try:
                    return json.loads(value, strict=False)
                except json.JSONDecodeError:
                    pass

        try:
            literal = ast.literal_eval(text)
            if isinstance(literal, (list, dict)):
                return literal
        except (ValueError, SyntaxError):
            return None
        return None

    def _iter_balanced_json_candidates(self, text: str) -> list[str]:
        """Return balanced object/array substrings while respecting quoted strings."""
        candidates = []
        for start, char in enumerate(text):
            if char not in "[{":
                continue
            stack: list[str] = []
            in_string = False
            quote_char = ""
            escaped = False
            for index in range(start, len(text)):
                current = text[index]
                if in_string:
                    if escaped:
                        escaped = False
                    elif current == "\\":
                        escaped = True
                    elif current == quote_char:
                        in_string = False
                    continue

                if current in ("'", '"'):
                    in_string = True
                    quote_char = current
                elif current in "[{":
                    stack.append(current)
                elif current in "]}":
                    if not stack:
                        break
                    opener = stack[-1]
                    if (opener == "[" and current != "]") or (opener == "{" and current != "}"):
                        break
                    stack.pop()
                    if not stack:
                        candidates.append(text[start:index + 1])
                        break
        return candidates

    def _question_items_from_payload(self, payload: Any) -> list[Any]:
        """Normalize wrapper formats such as {"questions": [...]} to a list."""
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("questions", "items", "data", "result"):
                value = payload.get(key)
                if isinstance(value, list):
                    return value
            return [payload]
        return []

    def _normalize_text(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, (list, tuple)):
            scalar_items = [str(item).strip() for item in value if not isinstance(item, (dict, list, tuple))]
            if len(scalar_items) == len(value):
                return "\n".join(f"- {item}" for item in scalar_items if item)
        if isinstance(value, dict):
            for key in ("reference_answer", "answer", "content", "text", "description"):
                if value.get(key):
                    return self._normalize_text(value.get(key))
        return json.dumps(value, ensure_ascii=False, indent=2)

    def _normalize_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in re.split(r"[,，;；\n]", value) if item.strip()]
        if isinstance(value, (list, tuple)):
            normalized = [self._normalize_text(item) for item in value]
            return [item for item in normalized if item]
        return [self._normalize_text(value)]

    async def _tavily_search(
        self,
        query: str,
        max_results: int = 5,
    ) -> list[dict[str, str]]:
        """
        使用 Tavily 搜索 API 获取面试相关内容

        Args:
            query: 搜索关键词
            max_results: 最大返回结果数

        Returns:
            list[dict]: [{"title": "...", "content": "...", "url": "..."}]
        """
        if not settings.TAVILY_API_KEY:
            return []

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": settings.TAVILY_API_KEY,
                        "query": f"{query} 面试题 面经 面试准备",
                        "max_results": max_results,
                        "include_answer": True,
                        "search_depth": "advanced",
                    },
                )

            if resp.status_code != 200:
                logger.warning("Tavily search returned status %s", resp.status_code)
                return []
        except httpx.HTTPError as e:
            logger.warning("Tavily search failed, continuing without web references: %s", e)
            return []
        except Exception as e:
            logger.warning("Unexpected Tavily search error, continuing without web references: %s", e)
            return []

        try:
            data = resp.json()
        except ValueError as e:
            logger.warning("Tavily search returned invalid JSON, continuing without web references: %s", e)
            return []
        results = []
        for item in data.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "content": item.get("content", ""),
                "url": item.get("url", ""),
            })

        return results

    async def _rag_search(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """
        从 ChromaDB RAG 中检索相似题目

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            list[dict]: RAG 检索结果
        """
        try:
            from app.services.rag_service import RAGService
            rag = RAGService()
            return await rag.search(query, top_k=top_k, threshold=0.3)
        except Exception:
            return []

    async def generate(
        self,
        category: str = "general",
        difficulty: str = "medium",
        count: int = 5,
        topic: str | None = None,
        resume_text: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        生成面试题

        Args:
            category: 题目分类（algorithm/frontend/backend/system_design/general）
            difficulty: 难度（easy/medium/hard）
            count: 生成数量
            topic: 具体知识点（可选，如 "链表"、"Vue3"）
            resume_text: 简历文本（可选，用于生成个性化追问）

        Returns:
            list[dict]: 生成的面试题列表
        """
        # 构建搜索关键词
        category_map = {
            "algorithm": "算法 数据结构",
            "frontend": "前端 JavaScript Vue React CSS",
            "backend": "后端 Java Python 数据库",
            "system_design": "系统设计 架构",
            "general": "综合面试",
        }
        difficulty_map = {
            "easy": "基础",
            "medium": "中等",
            "hard": "高级 深入",
        }

        search_query = f"{category_map.get(category, category)} {difficulty_map.get(difficulty, difficulty)}"
        if topic:
            search_query += f" {topic}"
        if resume_text:
            search_query += f" {resume_text[:200]}"

        # 并行搜索：Tavily + RAG
        import asyncio
        tavily_results, rag_results = await asyncio.gather(
            self._tavily_search(search_query),
            self._rag_search(search_query),
        )

        # 组装上下文
        context_parts = []

        if tavily_results:
            context_parts.append("=== 网络搜索到的面试参考资料 ===")
            for i, r in enumerate(tavily_results[:3], 1):
                context_parts.append(f"\n资料{i}: {r['title']}\nURL: {r['url']}\n{r['content']}")

        if rag_results:
            context_parts.append("\n=== 题库中相似的历史题目 ===")
            for i, r in enumerate(rag_results[:3], 1):
                context_parts.append(f"\n相似题{i}（相似度: {r['score']}）:\n{r['content']}")

        context = "\n".join(context_parts) if context_parts else ""

        # 调用 LLM 生成题目
        from app.services.llm_service import LLMService
        llm = LLMService()

        user_message = (
            f"请生成 {count} 道 {difficulty} 难度的 {category} 面试题。"
            "只返回合法 JSON 数组，不要添加 Markdown 标题、解释文字或代码块。"
        )
        if topic:
            user_message += f"主题围绕「{topic}」。"

        if resume_text and "面试录音转写内容" in resume_text[:100]:
            user_message += (
                "\n\n以下是面试录音转写内容，请优先围绕录音中已经出现的追问方向、候选人回答中的项目细节、"
                "表达漏洞和可继续深挖的点，生成相似但不完全重复的面试题：\n"
                f"{resume_text[:5000]}"
            )
        elif resume_text:
            user_message += (
                "\n\n以下是候选人的简历内容，请优先围绕其项目经历、技能栈、实习经历"
                "生成有针对性的追问，避免只出泛泛的八股题：\n"
                f"{resume_text[:5000]}"
            )

        if context:
            user_message += (
                f"\n\n以下是搜索到的参考资料，请参考但不要照搬：\n{context}\n\n"
                "如果参考了网络资料，请在对应参考答案末尾列出“参考来源：URL”。"
            )

        raw = await llm.chat(
            messages=[{"role": "user", "content": user_message}],
            system_prompt=QUESTION_GEN_SYSTEM_PROMPT,
            temperature=0.8,  # 题目生成需要一定创造性
        )

        payload = self._extract_json_payload(raw)
        if payload is None:
            questions = [{
                "question": "请围绕本次材料进行结构化追问，并说明考察目的。",
                "category": category,
                "difficulty": difficulty,
                "type": "技术",
                "key_points": [],
                "reference_answer": raw,
                "tags": [category, difficulty],
            }]
        else:
            questions = self._question_items_from_payload(payload)

        normalized_questions = []
        for item in questions:
            if not isinstance(item, dict):
                continue
            normalized_questions.append({
                "question": self._normalize_text(item.get("question") or item.get("title")),
                "category": str(item.get("category") or category),
                "difficulty": str(item.get("difficulty") or difficulty),
                "type": str(item.get("type") or "面试题"),
                "key_points": self._normalize_list(item.get("key_points") or item.get("reference_points")),
                "reference_answer": self._normalize_text(item.get("reference_answer") or item.get("answer")),
                "tags": self._normalize_list(item.get("tags")) or [category, difficulty],
            })

        if not normalized_questions:
            normalized_questions = [{
                "question": "请围绕本次材料进行结构化追问，并说明考察目的。",
                "category": category,
                "difficulty": difficulty,
                "type": "面试题",
                "key_points": [],
                "reference_answer": raw,
                "tags": [category, difficulty],
            }]

        return normalized_questions[:count]  # 确保不超出请求数量

    async def save_to_db(
        self,
        questions: list[dict[str, Any]],
        category: str,
        difficulty: str,
        source: str = "ai_generated",
        user_id: int | None = None,
    ) -> list[int]:
        """
        将生成的题目保存到数据库

        Returns:
            list[int]: 题目 ID 列表
        """
        from app.database import SessionLocal
        from app.models.question import InterviewQuestion, QuestionCategory, QuestionDifficulty, QuestionSource

        db = SessionLocal()
        try:
            saved_ids = []
            try:
                category_enum = QuestionCategory(category)
            except ValueError:
                category_enum = QuestionCategory.GENERAL
            try:
                difficulty_enum = QuestionDifficulty(difficulty)
            except ValueError:
                difficulty_enum = QuestionDifficulty.MEDIUM
            try:
                source_enum = QuestionSource(source)
            except ValueError:
                source_enum = QuestionSource.AI_GENERATED

            for q in questions:
                question_text = str(q.get("question", "")).strip()
                answer_text = str(q.get("reference_answer", "") or "").strip()
                if not question_text:
                    continue

                existing_questions = db.query(InterviewQuestion).filter(
                    InterviewQuestion.user_id == user_id,
                    InterviewQuestion.question == question_text,
                ).all()
                exact_duplicate = next(
                    (
                        item for item in existing_questions
                        if (item.reference_answer or "").strip() == answer_text
                    ),
                    None,
                )
                if exact_duplicate:
                    saved_ids.append(exact_duplicate.id)
                    continue

                question = InterviewQuestion(
                    user_id=user_id,
                    question=question_text,
                    category=category_enum,
                    difficulty=difficulty_enum,
                    reference_answer=answer_text,
                    tags=q.get("tags", [category, difficulty]),
                    source=source_enum,
                )
                db.add(question)
                db.flush()
                saved_ids.append(question.id)

            db.commit()
            return saved_ids
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    async def execute(self, agent_input: AgentInput) -> AgentOutput:
        """基类接口实现"""
        category = agent_input.context.get("category", "general")
        difficulty = agent_input.context.get("difficulty", "medium")
        count = agent_input.context.get("count", 5)
        topic = agent_input.context.get("topic")
        resume_text = agent_input.context.get("resume_text")
        user_id = agent_input.context.get("user_id") or agent_input.user_id

        questions = await self.generate(
            category=category,
            difficulty=difficulty,
            count=count,
            topic=topic,
            resume_text=resume_text,
        )
        saved_ids = await self.save_to_db(
            questions=questions,
            category=category,
            difficulty=difficulty,
            user_id=user_id,
        )

        return AgentOutput(
            content=f"成功生成 {len(questions)} 道面试题",
            agent_name=self.name,
            metadata={
                "category": category,
                "difficulty": difficulty,
                "count": len(questions),
                "questions": questions,
                "question_ids": saved_ids,
            },
        )
