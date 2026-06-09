"""
主编排 Agent。

它只负责理解用户意图、拆分任务和选择子 Agent；具体文件解析与业务处理交给对应子 Agent。
"""

from __future__ import annotations

import json
import os
from typing import Any

from app.agents.base_agent import AgentInput, AgentOutput, BaseAgent


class OrchestratorAgent(BaseAgent):
    """智能面试助手的主 Agent。"""

    VALID_INTENTS = {
        "resume_evaluation",
        "recording_analysis",
        "question_generation",
        "career_planning",
        "interview_practice",
        "knowledge_query",
        "interview_help",
    }
    VALID_AGENTS = {"resume", "recording", "question", "general"}
    INTENT_TO_AGENT = {
        "resume_evaluation": "resume",
        "recording_analysis": "recording",
        "question_generation": "question",
        "career_planning": "general",
        "interview_practice": "general",
        "knowledge_query": "general",
        "interview_help": "general",
    }

    def __init__(self):
        super().__init__(name="orchestrator")
        self._sub_agents: dict[str, BaseAgent] = {}

    async def _get_sub_agent(self, intent: str) -> BaseAgent | None:
        agent_map = {
            "resume_evaluation": "resume_agent",
            "recording_analysis": "recording_agent",
            "question_generation": "question_agent",
            "career_planning": "career_agent",
        }

        agent_key = agent_map.get(intent)
        if not agent_key:
            return None

        if agent_key not in self._sub_agents:
            if agent_key == "resume_agent":
                from app.agents.resume_agent import ResumeAgent

                self._sub_agents[agent_key] = ResumeAgent()
            elif agent_key == "recording_agent":
                from app.agents.recording_agent import RecordingAgent

                self._sub_agents[agent_key] = RecordingAgent()
            elif agent_key == "question_agent":
                from app.agents.question_agent import QuestionAgent

                self._sub_agents[agent_key] = QuestionAgent()
            elif agent_key == "career_agent":
                from app.agents.career_agent import CareerAgent

                self._sub_agents[agent_key] = CareerAgent()

        return self._sub_agents.get(agent_key)

    def _extract_json(self, text: str) -> dict[str, Any] | None:
        raw = text.strip()
        if "```json" in raw:
            raw = raw.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in raw:
            raw = raw.split("```", 1)[1].split("```", 1)[0].strip()

        decoder = json.JSONDecoder()
        for index, char in enumerate(raw):
            if char != "{":
                continue
            try:
                data, _ = decoder.raw_decode(raw[index:])
                return data if isinstance(data, dict) else None
            except json.JSONDecodeError:
                continue
        return None

    def _file_kind(self, file_url: str) -> str:
        ext = os.path.splitext(file_url)[1].lower()
        if ext in {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".mp4", ".avi", ".mov", ".mkv", ".webm"}:
            return "recording"
        if ext in {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
            return "resume"
        return "unknown"

    def _describe_files(self, file_urls: list[str]) -> list[dict[str, Any]]:
        return [
            {
                "id": index + 1,
                "url": url,
                "ext": os.path.splitext(url)[1].lower().lstrip(".") or "unknown",
                "kind_hint": self._file_kind(url),
            }
            for index, url in enumerate(file_urls)
        ]

    def _normalize_task(
        self,
        task: dict[str, Any],
        files: list[dict[str, Any]],
        index: int,
    ) -> dict[str, Any] | None:
        agent_type = str(task.get("agent_type") or "").strip()
        intent = str(task.get("intent") or "").strip()

        if agent_type not in self.VALID_AGENTS:
            agent_type = self.INTENT_TO_AGENT.get(intent, "general")
        if intent not in self.VALID_INTENTS:
            intent = {
                "resume": "resume_evaluation",
                "recording": "recording_analysis",
                "question": "question_generation",
            }.get(agent_type, "interview_help")

        file_ids = task.get("file_ids")
        if file_ids is None and task.get("file_id") is not None:
            file_ids = [task.get("file_id")]
        if not isinstance(file_ids, list):
            file_ids = []

        selected_urls: list[str] = []
        for file_id in file_ids:
            try:
                file_index = int(file_id) - 1
            except (TypeError, ValueError):
                continue
            if 0 <= file_index < len(files):
                selected_urls.append(files[file_index]["url"])

        if not selected_urls:
            preferred_kind = {
                "resume": "resume",
                "recording": "recording",
                "question": str(task.get("file_role") or "resume"),
            }.get(agent_type, "unknown")
            for item in files:
                if item["kind_hint"] == preferred_kind:
                    selected_urls.append(item["url"])
                    break

        return {
            "id": str(task.get("id") or f"task_{index + 1}"),
            "intent": intent,
            "agent_type": agent_type,
            "title": str(task.get("title") or self._agent_title(agent_type)),
            "reason": str(task.get("reason") or f"主 Agent 选择 {self._agent_title(agent_type)} 处理该子任务。"),
            "file_ids": file_ids,
            "file_urls": selected_urls,
            "depends_on": task.get("depends_on") if isinstance(task.get("depends_on"), list) else [],
        }

    def _agent_title(self, agent_type: str) -> str:
        return {
            "resume": "简历评估 Agent",
            "recording": "录音分析 Agent",
            "question": "面试题生成 Agent",
            "general": "通用面试助手",
        }.get(agent_type, agent_type)

    def _fallback_plan(self, requested_agent: str, file_urls: list[str], reason: str) -> dict[str, Any]:
        files = self._describe_files(file_urls)
        tasks: list[dict[str, Any]] = []
        if requested_agent in self.VALID_AGENTS and requested_agent != "general":
            tasks.append({
                "intent": {
                    "resume": "resume_evaluation",
                    "recording": "recording_analysis",
                    "question": "question_generation",
                }.get(requested_agent, "interview_help"),
                "agent_type": requested_agent,
                "reason": "主 Agent 规划失败，按前端当前模块提示降级执行。",
            })
        else:
            tasks.append({
                "intent": "interview_help",
                "agent_type": "general",
                "reason": "主 Agent 规划失败，降级为通用面试助手。",
            })

        normalized = []
        for index, task in enumerate(tasks):
            normalized_task = self._normalize_task(task, files, index)
            if normalized_task:
                normalized.append(normalized_task)
        return {
            "mode": "single",
            "intent": normalized[0]["intent"],
            "agent_type": normalized[0]["agent_type"],
            "tasks": normalized,
            "reason": reason,
            "confidence": 0,
            "requested_agent": requested_agent,
            "files": files,
        }

    async def plan_route(
        self,
        content: str,
        file_url: str | None = None,
        file_urls: list[str] | None = None,
        requested_agent: str = "general",
    ) -> dict[str, Any]:
        """
        由主 Agent 生成结构化调度计划。

        返回 tasks 数组，API 层只负责按计划执行，不在入口处硬编码意图。
        """
        all_file_urls = list(file_urls or [])
        if file_url and file_url not in all_file_urls:
            all_file_urls.insert(0, file_url)
        files = self._describe_files(all_file_urls)

        try:
            from app.services.llm_service import LLMService

            llm = LLMService()
            prompt = f"""你是智能面试助手的主 Agent，只负责分析用户意图、拆分任务、选择子 Agent。
请只返回 JSON，不要输出解释文字。

可选子 Agent：
- resume：处理简历文件。权限：读取被分配的 PDF/Word/图片简历，做简历评估、模板查重、违禁词检测、优化建议。
- recording：处理录音/视频文件。权限：读取被分配的音视频，做转写、面试表现分析、回答质量评估。
- question：生成面试题。权限：读取被分配的简历文本或录音转写上下文，结合题库/联网资料生成个性化题目并写入“我的题库”。
- general：只处理纯文本咨询、职业建议、知识问答；它没有原始文件解析权限。

决策原则：
1. 以用户文字表达的任务目标为最高优先级，文件类型只是上下文。
2. 一个请求包含多个动作时，必须拆成多个 tasks，而不是丢给 general。
3. 只要任务依赖上传文件，应选择能读取该文件的专门 Agent；不要让 general 处理文件任务。
4. “分别根据简历图片和视频完成简历评估和录音分析，然后根据简历生成面试题”应拆成 resume、recording、question 三个任务。
5. 每个 task 必须写清 intent、agent_type、reason、file_ids。file_ids 使用上传文件列表里的 id。

用户文字：{content or "（空）"}
前端当前模块提示：{requested_agent or "general"}
上传文件列表：{json.dumps(files, ensure_ascii=False)}

返回 JSON 格式示例：
{{
  "mode": "multi",
  "reason": "用户同时要求简历评估、录音分析和根据简历生成面试题，因此需要编排多个子 Agent。",
  "confidence": 0.9,
  "tasks": [
    {{"id":"resume_eval","intent":"resume_evaluation","agent_type":"resume","title":"简历评估","file_ids":[1],"reason":"用户要求根据简历图片完成简历评估。"}},
    {{"id":"recording_analysis","intent":"recording_analysis","agent_type":"recording","title":"录音分析","file_ids":[2],"reason":"用户要求根据视频/录音完成面试表现分析。"}},
    {{"id":"question_generation","intent":"question_generation","agent_type":"question","title":"简历出题","file_ids":[1],"depends_on":["resume_eval"],"reason":"用户要求根据简历生成面试题。"}}
  ]
}}
"""
            result = await llm.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=800,
            )
            data = self._extract_json(result) or {}

            raw_tasks = data.get("tasks")
            if not isinstance(raw_tasks, list) or not raw_tasks:
                raw_tasks = [{
                    "intent": data.get("intent") or "interview_help",
                    "agent_type": data.get("agent_type") or "general",
                    "reason": data.get("reason") or "主 Agent 判断该请求适合交给单个子 Agent 处理。",
                    "file_ids": data.get("file_ids") or ([data.get("file_id")] if data.get("file_id") else []),
                }]

            if files and len(raw_tasks) == 1 and isinstance(raw_tasks[0], dict) and raw_tasks[0].get("agent_type") == "general":
                repair_prompt = f"""你刚才把一个带上传文件的请求分配给 general，但 general 没有原始文件解析权限。
请重新输出 JSON 调度计划，只能把需要读取文件的任务交给 resume、recording 或 question。

用户文字：{content or "（空）"}
上传文件列表：{json.dumps(files, ensure_ascii=False)}
第一次计划：{json.dumps(data, ensure_ascii=False)}

只返回 JSON，格式仍为：{{"mode":"multi","reason":"...","tasks":[{{"intent":"...","agent_type":"resume|recording|question|general","file_ids":[1],"reason":"..."}}]}}
"""
                repair_result = await llm.chat(
                    messages=[{"role": "user", "content": repair_prompt}],
                    temperature=0,
                    max_tokens=800,
                )
                repair_data = self._extract_json(repair_result) or {}
                repair_tasks = repair_data.get("tasks")
                if isinstance(repair_tasks, list) and repair_tasks:
                    raw_tasks = repair_tasks
                    data = repair_data

            tasks = [
                normalized
                for index, task in enumerate(raw_tasks)
                if isinstance(task, dict)
                for normalized in [self._normalize_task(task, files, index)]
                if normalized
            ]
            if not tasks:
                return self._fallback_plan(
                    requested_agent,
                    all_file_urls,
                    "主 Agent 未返回可执行任务，已降级处理。",
                )

            return {
                "mode": "multi" if len(tasks) > 1 else "single",
                "intent": tasks[0]["intent"] if len(tasks) == 1 else "multi_task",
                "agent_type": tasks[0]["agent_type"] if len(tasks) == 1 else "multi",
                "tasks": tasks,
                "reason": data.get("reason") or "主 Agent 已根据用户请求生成子任务编排计划。",
                "confidence": data.get("confidence", 0),
                "requested_agent": requested_agent,
                "files": files,
            }
        except Exception as exc:
            return self._fallback_plan(
                requested_agent,
                all_file_urls,
                f"主 Agent 意图规划失败，已按当前模块提示保守降级：{exc}",
            )

    async def _llm_classify_intent(self, content: str) -> str | None:
        try:
            from app.services.llm_service import LLMService

            llm = LLMService()
            prompt = f"""请判断用户消息最适合交给哪个 Agent 处理，只返回一个意图标识。
可选意图：
- resume_evaluation
- recording_analysis
- question_generation
- career_planning
- interview_practice
- knowledge_query
- interview_help

用户消息：{content}
"""
            result = await llm.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=32,
            )
            intent = result.strip().strip("`").split()[0]
            return intent if intent in self.VALID_INTENTS else None
        except Exception:
            return None

    async def _handle_direct_chat(self, agent_input: AgentInput) -> AgentOutput:
        try:
            from app.services.llm_service import LLMService
            from app.services.rag_service import RAGService

            rag = RAGService()
            docs = await rag.search(agent_input.content, top_k=4, threshold=0.35)
            context = "\n\n".join(
                f"[资料{i + 1}] {doc.get('content', '')}"
                for i, doc in enumerate(docs)
            )
            system_prompt = (
                "你是面向大学生就业场景的智能面试助手。请结合知识库资料回答，"
                "输出 Markdown，给出可执行建议；如果资料不足，请说明判断依据。"
            )
            user_message = agent_input.content
            if context:
                user_message += f"\n\n可参考的知识库资料：\n{context}"

            llm = LLMService()
            response = await llm.chat(
                messages=[{"role": "user", "content": user_message}],
                system_prompt=system_prompt,
            )
            return AgentOutput(
                content=response,
                agent_name=self.name,
                metadata={"intent": "direct_chat", "rag_hits": len(docs)},
            )
        except Exception:
            pass

        return AgentOutput(
            content=(
                "你好！我是面试助手，可以帮你：\n"
                "1. 上传简历进行评估和优化建议\n"
                "2. 上传录音/视频进行面试表现分析\n"
                "3. 生成个性化面试题\n"
                "4. 查询面试经验和知识\n"
                "5. 进行模拟面试练习\n\n"
                "请告诉我你需要什么帮助？"
            ),
            agent_name=self.name,
        )

    async def execute(self, agent_input: AgentInput) -> AgentOutput:
        intent = await self._llm_classify_intent(agent_input.content) or "interview_help"

        if intent in ["interview_help", "interview_practice", "knowledge_query"]:
            return await self._handle_direct_chat(agent_input)

        sub_agent = await self._get_sub_agent(intent)
        if sub_agent:
            return await sub_agent.run(agent_input)
        return await self._handle_direct_chat(agent_input)
