"""
录音分析 Agent
使用 DashScope Paraformer-v2 进行语音转文字，然后用 DeepSeek 分析面试表现

转写流程：
1. 通过 DashScope getPolicy API 上传本地文件到临时 OSS → 获取 oss:// URL
2. 通过 RESTful API 提交异步转写任务（RESTful API 支持 oss:// URL）
3. 轮询 RESTful API 等待任务完成
4. 下载 transcription_url JSON 解析转写结果 → DeepSeek LLM 分析

注意：
- Python SDK 的 Transcription.async_call() 不支持 oss:// URL（会 FILE_403_FORBIDDEN）
- 但 RESTful API 支持 oss:// URL（DashScope 后端有内部 OSS 访问权限）
- 所以必须用 RESTful API（httpx 直接调用）而非 SDK 的 Transcription 类
- ⚠️ RESTful API 必须携带两个关键请求头（SDK 内部自动添加，手动调用需自己加）：
  1. X-DashScope-Async: enable → 否则走同步模式，免费套餐不支持同步 → 403
  2. X-DashScope-OssResourceResolve: enable → 否则后端无法解析 oss:// URL → FILE_DOWNLOAD_FAILED
- ⚠️ 查询任务状态（/api/v1/tasks/{task_id}）应使用 POST 方法而非 GET
"""

import asyncio
import json
import os
import re
from typing import Any

import httpx

from app.agents.base_agent import AgentInput, AgentOutput, BaseAgent
from app.config import settings

# DashScope RESTful API 基础地址
DASHSCOPE_BASE = "https://dashscope.aliyuncs.com/api/v1"

# 面试录音分析系统提示词
INTERVIEW_ANALYSIS_SYSTEM_PROMPT = """你是一位资深的面试辅导专家，请对以下面试录音转写文本进行多维度分析。

请使用 **Markdown 格式** 直接输出分析报告，不要输出 JSON。报告结构如下：

## 📊 综合评分

| 评估维度 | 得分 | 满分 |
|---------|------|------|
| 流畅度 | X | 10 |
| 逻辑清晰度 | X | 10 |
| 专业深度 | X | 10 |
| 表达技巧 | X | 10 |
| **总分** | **X** | **40** |

## 🗣️ 语速分析

- 音频时长：X 秒
- 文本字数：约 X 字
- 估算语速：约 X 字/分钟（中文正常语速 200-250 字/分钟）

## ✅ 关键信息点

- 要点1
- 要点2
- 要点3

## ⚠️ 不足之处

- 不足点1
- 不足点2

## 💡 改进建议

1. 建议一
2. 建议二
3. 建议三

## 📋 面试官提问整理

| 序号 | 面试问题 | 题目类型 |
|------|---------|---------|
| 1 | ... | 技术/行为/综合 |

## 📝 综合分析

详细的综合分析文字...

注意：
- 语速根据文本长度和音频时长估算
- 提取面试官提出的问题
- 建议要具体可操作"""


class RecordingAgent(BaseAgent):
    """
    录音分析 Agent

    工作流程：
    1. 上传本地音视频文件到 DashScope 临时 OSS（getPolicy）
    2. 使用 RESTful API 提交 Paraformer-v2 异步转写（支持 oss:// URL）
    3. 轮询 RESTful API 等待任务完成
    4. 使用 DeepSeek LLM 分析转写文本，给出多维度评估
    """

    def __init__(self):
        super().__init__(name="recording_agent")
        self._headers = {
            "Authorization": f"Bearer {settings.DASHSCOPE_API_KEY}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",  # 异步模式（不传则走同步，免费套餐不支持同步 → 403）
            "X-DashScope-OssResourceResolve": "enable",  # 解析 oss:// URL（不传 → FILE_DOWNLOAD_FAILED）
        }

    async def _upload_file_to_oss(self, file_path: str) -> str:
        """
        上传本地音视频文件到 DashScope 临时 OSS 存储

        步骤：
        1. GET /api/v1/uploads?action=getPolicy 获取上传凭证
        2. POST 到 OSS（multipart/form-data）上传文件
        3. 返回 oss:// 格式的 URL（RESTful API 可识别）

        Args:
            file_path: 本地音视频文件路径

        Returns:
            str: oss:// 格式的文件 URL
        """
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        print(f"[录音Agent] 上传文件: {file_name} ({file_size / 1024 / 1024:.1f}MB)")

        # 步骤1：获取上传凭证
        async with httpx.AsyncClient(timeout=30) as client:
            policy_resp = await client.get(
                f"{DASHSCOPE_BASE}/uploads",
                headers={"Authorization": f"Bearer {settings.DASHSCOPE_API_KEY}"},
                params={
                    "action": "getPolicy",
                    "model": settings.PARAFOUNDER_MODEL,
                },
            )

        if policy_resp.status_code != 200:
            raise RuntimeError(
                f"获取上传凭证失败 ({policy_resp.status_code}): {policy_resp.text}"
            )

        policy_data = policy_resp.json()["data"]
        upload_host = policy_data["upload_host"]
        upload_dir = policy_data["upload_dir"]

        # 步骤2：上传文件到 OSS
        key = f"{upload_dir}/{file_name}"

        with open(file_path, "rb") as f:
            file_data = f.read()

        async with httpx.AsyncClient(timeout=300) as client:
            upload_resp = await client.post(
                upload_host,
                data={
                    "OSSAccessKeyId": policy_data["oss_access_key_id"],
                    "Signature": policy_data["signature"],
                    "policy": policy_data["policy"],
                    "x-oss-object-acl": policy_data["x_oss_object_acl"],
                    "x-oss-forbid-overwrite": policy_data["x_oss_forbid_overwrite"],
                    "key": key,
                    "success_action_status": "200",
                },
                files={
                    "file": (file_name, file_data),
                },
            )

        if upload_resp.status_code != 200:
            raise RuntimeError(
                f"上传文件到 OSS 失败 ({upload_resp.status_code}): {upload_resp.text}"
            )

        # 返回 oss:// 格式（RESTful API 支持，Python SDK 不支持）
        oss_url = f"oss://{key}"
        print(f"[录音Agent] 文件上传成功: {oss_url}")
        return oss_url

    async def _submit_transcription_task(self, oss_url: str) -> str:
        """
        通过 RESTful API 提交异步转写任务

        RESTful API 支持 oss:// URL，而 Python SDK 不支持

        Args:
            oss_url: oss:// 格式的文件 URL

        Returns:
            str: task_id
        """
        print(f"[录音Agent] 提交异步转写任务 (RESTful API): model={settings.PARAFOUNDER_MODEL}")

        payload = {
            "model": settings.PARAFOUNDER_MODEL,
            "input": {
                "file_urls": [oss_url],
            },
            "parameters": {
                "language_hints": ["zh", "en"],
            },
        }

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{DASHSCOPE_BASE}/services/audio/asr/transcription",
                headers=self._headers,
                json=payload,
            )

        if resp.status_code != 200:
            raise RuntimeError(
                f"提交转写任务失败 ({resp.status_code}): {resp.text}"
            )

        data = resp.json()
        task_id = data["output"]["task_id"]
        task_status = data["output"]["task_status"]
        print(f"[录音Agent] 任务已提交, task_id={task_id}, 状态={task_status}")
        return task_id

    async def _wait_for_transcription(self, task_id: str) -> dict[str, Any]:
        """
        轮询 RESTful API 等待转写任务完成

        Args:
            task_id: 转写任务 ID

        Returns:
            dict: 转写结果 JSON（包含 results 数组）
        """
        import asyncio

        print(f"[录音Agent] 等待转写任务完成（可能需要数分钟）...")
        max_attempts = 120  # 最多等待 10 分钟（每 5 秒查一次）
        poll_interval = 5

        for attempt in range(max_attempts):
            await asyncio.sleep(poll_interval)

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{DASHSCOPE_BASE}/tasks/{task_id}",
                    headers=self._headers,
                )

            if resp.status_code != 200:
                print(f"[录音Agent] 查询任务状态失败 ({resp.status_code})，继续轮询...")
                continue

            data = resp.json()
            task_status = data["output"]["task_status"]
            print(f"[录音Agent] 轮询 {attempt + 1}/{max_attempts}: task_id={task_id}, 状态={task_status}")

            if task_status in ("SUCCEEDED", "FAILED"):
                return data

        raise RuntimeError(f"转写任务超时（等待超过 {max_attempts * poll_interval} 秒）")

    async def transcribe(self, file_path: str) -> dict[str, Any]:
        """
        使用 Paraformer-v2 异步转写音视频文件

        流程：
        1. 上传文件到 OSS → 获取 oss:// URL
        2. 通过 RESTful API 提交异步转写任务
        3. 轮询等待任务完成
        4. 下载 transcription_url JSON 解析转写文本

        Args:
            file_path: 音视频文件路径

        Returns:
            dict: {"text": "...", "segments": [...], "duration_seconds": int}
        """
        # 步骤1：上传文件到 OSS
        oss_url = await self._upload_file_to_oss(file_path)

        # 步骤2：提交转写任务
        task_id = await self._submit_transcription_task(oss_url)

        # 步骤3：轮询等待结果
        result_data = await self._wait_for_transcription(task_id)

        task_status = result_data["output"]["task_status"]
        if task_status != "SUCCEEDED":
            message = result_data["output"].get("message", "未知错误")
            raise RuntimeError(f"转写任务失败: {task_status} - {message}")

        # 步骤4：解析结果，获取 transcription_url
        results = result_data["output"].get("results", [])
        if not results:
            raise RuntimeError("转写任务成功但无结果数据")

        first_result = results[0]
        subtask_status = first_result.get("subtask_status", "")

        if subtask_status == "FAILED":
            code = first_result.get("code", "")
            message = first_result.get("message", "")
            raise RuntimeError(f"转写子任务失败: code={code}, message={message}")

        transcription_url = first_result.get("transcription_url", "")
        if not transcription_url:
            raise RuntimeError("转写结果中无 transcription_url")

        # 步骤5：异步下载并解析转写结果 JSON
        print(f"[录音Agent] 转写任务完成，正在下载转写结果...")
        trans_result = await self._parse_and_download_transcription(transcription_url)

        print(f"[录音Agent] 转写完成, 文本长度={len(trans_result['text'])}")
        return trans_result

    async def _parse_and_download_transcription(self, transcription_url: str) -> dict[str, Any]:
        """
        下载并解析转写结果 JSON

        Args:
            transcription_url: 转写结果 JSON 下载地址

        Returns:
            dict: {"text": "...", "segments": [...], "duration_seconds": int}
        """
        if not transcription_url:
            return {"text": "", "segments": [], "duration_seconds": 0}

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                trans_resp = await client.get(transcription_url)
            trans_resp.raise_for_status()
            trans_data = trans_resp.json()
        except Exception as e:
            print(f"[录音Agent] 获取转写结果失败: {e}")
            return {"text": "", "segments": [], "duration_seconds": 0}

        full_text = ""
        segments = []
        duration_seconds = 0

        for item in trans_data.get("transcripts", []):
            text = item.get("text", "")
            full_text += text
            sentences = item.get("sentences", [])
            for s in sentences:
                end_ms = s.get("end_time", 0)
                if end_ms > duration_seconds * 1000:
                    duration_seconds = end_ms / 1000.0
                segments.append({
                    "start": s.get("begin_time", 0) / 1000.0,
                    "end": end_ms / 1000.0,
                    "text": s.get("text", ""),
                })

        return {
            "text": full_text,
            "segments": segments,
            "duration_seconds": int(duration_seconds),
        }

    async def analyze_transcript(
        self,
        transcript: str,
        duration_seconds: int,
        user_context: str = "",
    ) -> dict[str, Any]:
        """
        使用 DeepSeek 分析转写文本

        Args:
            transcript: 转写文本
            duration_seconds: 音视频时长（秒）

        Returns:
            dict: 分析结果
        """
        from app.services.llm_service import LLMService

        llm = LLMService()

        # 估算语速
        char_count = len(transcript.replace(" ", "").replace("\n", ""))
        speech_rate = round(char_count / (duration_seconds / 60)) if duration_seconds > 0 else 0

        reference_context = await self._build_reference_context(transcript)

        user_message = (
            f"请分析以下面试录音转写文本，按照规定的 Markdown 格式直接输出分析报告。\n\n"
            f"音频时长：{duration_seconds} 秒（约 {duration_seconds // 60} 分 {duration_seconds % 60} 秒）\n"
            f"文本字数：约 {char_count} 字\n"
            f"估算语速：约 {speech_rate} 字/分钟\n\n"
            f"转写文本：\n{transcript}"
        )

        if reference_context:
            user_message += (
                "\n\n以下是从本地面试宝典/题库和公开资料检索到的参考内容。"
                "请据此判断回答准确性，并在报告中指出哪些回答充分、哪些需要补充：\n"
                f"{reference_context}"
            )

        # 注入用户个人信息
        if user_context:
            user_message += f"\n\n{user_context}"

        raw = await llm.chat(
            messages=[{"role": "user", "content": user_message}],
            system_prompt=INTERVIEW_ANALYSIS_SYSTEM_PROMPT,
        )

        return {
            "analysis_text": raw,
            "speech_rate": speech_rate,
        }

    async def _build_reference_context(self, transcript: str) -> str:
        """检索本地知识库和公开资料，供录音答案准确性比对使用。"""
        parts: list[str] = []
        try:
            from app.services.rag_service import RAGService

            rag = RAGService()
            rag_results = await rag.search(transcript[:1000], top_k=5, threshold=0.35)
            if rag_results:
                parts.append("=== 本地面试宝典/题库参考 ===")
                for i, item in enumerate(rag_results, 1):
                    parts.append(f"资料{i}：{item.get('content', '')}")
        except Exception:
            pass

        if settings.TAVILY_API_KEY:
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(
                        "https://api.tavily.com/search",
                        json={
                            "api_key": settings.TAVILY_API_KEY,
                            "query": f"{transcript[:300]} 面试题 答案",
                            "max_results": 3,
                            "include_answer": True,
                            "search_depth": "basic",
                        },
                    )
                if resp.status_code == 200:
                    results = resp.json().get("results", [])
                    if results:
                        parts.append("=== 互联网公开答案参考 ===")
                        for i, item in enumerate(results, 1):
                            parts.append(
                                f"资料{i}：{item.get('title', '')}\n"
                                f"URL：{item.get('url', '')}\n"
                                f"{item.get('content', '')}"
                            )
            except Exception:
                pass

        return "\n\n".join(parts)

    async def _extract_questions(self, transcript: str) -> list[dict[str, Any]]:
        """从转写文本中抽取真实面试题，用于自动沉淀到题库。"""
        if not transcript.strip():
            return []

        try:
            from app.services.llm_service import LLMService

            llm = LLMService()
            raw = await llm.chat(
                messages=[{
                    "role": "user",
                    "content": (
                        "请从下面的面试录音转写中抽取面试官提出的真实问题，以及候选人紧随其后的回答。"
                        "只返回 JSON 数组，每项包含 question、reference_answer、category、difficulty、tags。"
                        "reference_answer 必须填写录音中候选人对该题的回答；如果没有明确回答则填空字符串。"
                        "category 必须是 general/frontend/backend/algorithm/system_design/database/network/behavioral/project 之一；"
                        "difficulty 必须是 easy/medium/hard。\n\n"
                        f"{transcript[:6000]}"
                    ),
                }],
                temperature=0,
                max_tokens=1200,
            )
            if "```json" in raw:
                raw = raw.split("```json", 1)[1].split("```", 1)[0].strip()
            elif "```" in raw:
                raw = raw.split("```", 1)[1].split("```", 1)[0].strip()
            data = json.loads(raw)
            if isinstance(data, dict):
                data = data.get("questions", [])
            if isinstance(data, list):
                return [q for q in data if isinstance(q, dict) and q.get("question")]
        except Exception:
            pass

        candidates = []
        matches = list(re.finditer(r"([^。！？\n]{6,80}[？?])", transcript))
        for index, match in enumerate(matches):
            q = match.group(1).strip()
            if q:
                answer_start = match.end()
                answer_end = matches[index + 1].start() if index + 1 < len(matches) else min(len(transcript), answer_start + 500)
                answer = transcript[answer_start:answer_end].strip(" \n。！？")
                candidates.append({
                    "question": q,
                    "reference_answer": answer,
                    "category": "general",
                    "difficulty": "medium",
                    "tags": ["recording", "collected"],
                })
        return candidates[:10]

    async def _save_collected_questions(
        self,
        questions: list[dict[str, Any]],
        user_id: int | None = None,
    ) -> list[int]:
        """把录音中抽取的真实面试题写入题库和 RAG。"""
        if not questions:
            return []

        from app.agents.question_agent import QuestionAgent

        agent = QuestionAgent()
        saved_ids: list[int] = []
        for q in questions:
            category = q.get("category") or "general"
            difficulty = q.get("difficulty") or "medium"
            ids = await agent.save_to_db(
                questions=[q],
                category=category,
                difficulty=difficulty,
                source="collected",
                user_id=user_id,
            )
            saved_ids.extend(ids)

        try:
            from app.services.rag_service import RAGService

            rag = RAGService()
            await rag.add_documents(
                documents=[q.get("question", "") for q in questions],
                metadatas=[
                    {
                        "category": q.get("category") or "general",
                        "difficulty": q.get("difficulty") or "medium",
                        "source": "recording_collected",
                    }
                    for q in questions
                ],
            )
        except Exception:
            pass

        return saved_ids

    async def process(
        self,
        file_path: str,
        user_context: str = "",
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """
        完整处理流程：上传 → ASR 转写 → LLM 分析
        
        Args:
            file_path: 音视频文件路径
            user_context: 用户个人信息上下文（可选）
        
        Returns:
            dict: 包含转写和分析结果的完整数据
        """
        # 步骤1：语音转文字
        trans_result = await self.transcribe(file_path)

        # 步骤2：分析转写文本
        duration = trans_result.get("duration_seconds", 0) or 60

        analysis = await self.analyze_transcript(
            trans_result["text"],
            duration,
            user_context,
        )
        collected_questions = await self._extract_questions(trans_result["text"])
        saved_question_ids = await self._save_collected_questions(collected_questions, user_id=user_id)

        return {
            "transcript": trans_result["text"],
            "transcription": trans_result["text"],
            "segments": trans_result["segments"],
            "duration_seconds": trans_result.get("duration_seconds", 0),
            "analysis": {
                **analysis,
                "collected_questions": collected_questions,
                "saved_question_ids": saved_question_ids,
            },
        }

    async def execute(self, agent_input: AgentInput) -> AgentOutput:
        """基类接口实现"""
        file_path = agent_input.context.get("file_path", "")

        if not file_path:
            return AgentOutput(
                content="请先上传录音文件",
                agent_name=self.name,
                status="failed",
                error_msg="缺少 file_path",
            )

        result = await self.process(file_path)

        return AgentOutput(
            content="录音分析完成",
            agent_name=self.name,
            metadata=result,
        )
