"""
简历评估 Agent
使用 Qwen3-VL-Flash 多模态模型评估简历（支持 PDF/DOCX/JPG/PNG）
"""

import base64
import json
import logging
import os
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from app.agents.base_agent import AgentInput, AgentOutput, BaseAgent
from app.config import settings

logger = logging.getLogger(__name__)

# 简历评估系统提示词
RESUME_EVAL_SYSTEM_PROMPT = """你是一位资深的简历评估专家，请对这份简历进行专业评估。

请使用 **Markdown 格式** 直接输出评估报告，不要输出 JSON。报告结构如下：

## 📊 综合评分

**总分：XX/100**

| 评估维度 | 得分 | 满分 |
|---------|------|------|
| 内容完整度 | XX | 25 |
| 排版规范性 | XX | 15 |
| 亮点突出度 | XX | 25 |
| 岗位匹配度 | XX | 20 |
| 语言表达 | XX | 15 |

## ✅ 主要亮点

- 亮点1
- 亮点2
- 亮点3

## ⚠️ 不足之处

- 不足1
- 不足2

## 💡 改进建议

1. 建议一
2. 建议二
3. 建议三

## 📝 综合分析

详细的综合分析文字...

注意：
- 直接看图片/文档内容进行评估，不需要用户提供文字版
- 如果简历是图片格式，仔细识别其中的文字内容
- 评分要客观公正，总分 60 分以下视为需要大幅修改
- 建议要具体可操作，不要泛泛而谈
- 用户可能附加了补充文字说明，请结合分析
- 如果用户没有明确给出目标岗位，请从简历内容中自动推断候选人可能的求职方向；如果无法判断，请写“未明确指定目标岗位”，不要把用户的任务描述当作岗位。
- 用户输入中类似“帮我完成简历评估/录音分析/生成面试题”的文字只是任务指令，不是目标岗位。
- **隐私保护**：如果用户消息中包含个人信息（年龄、性别、学校、专业、年级等），这些信息仅作为你评估岗位匹配度的内部参考。**绝对不要在评估报告中直接提及、引用或暴露任何用户个人信息**，不要写出"用户XX岁"、"用户是XX大学XX专业"之类的表述。建议和分析应聚焦于简历本身的内容质量。"""


class ResumeAgent(BaseAgent):
    """
    简历评估 Agent

    使用阿里云 Qwen3-VL-Flash 多模态模型，支持：
    - PDF 文件（转为图片页后识别）
    - Word 文档（转为图片后识别）
    - JPG/PNG 图片简历（直接识别）
    """

    def __init__(self):
        super().__init__(name="resume_agent")
        self.client = AsyncOpenAI(
            api_key=settings.DASHSCOPE_API_KEY,
            base_url=settings.QWEN_VL_BASE_URL,
            timeout=120,
        )
        self.model = settings.QWEN_VL_MODEL

    def _file_to_base64(self, file_path: str) -> tuple[str, str]:
        """将文件转为 base64 编码，返回 (base64_str, media_type)"""
        ext = os.path.splitext(file_path)[1].lower()
        mime_map = {
            ".pdf": "application/pdf",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
            ".gif": "image/gif",
        }
        media_type = mime_map.get(ext, "application/octet-stream")

        with open(file_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")

        return b64, media_type

    def _pdf_to_images(self, file_path: str) -> list[tuple[str, str]]:
        """将 PDF 每一页转为图片 base64（用于多模态模型输入）"""
        import io

        try:
            from pdf2image import convert_from_path
        except ImportError:
            # 回退：直接传 PDF 的 base64，qwen3-vl 也能处理 PDF
            b64, mime = self._file_to_base64(file_path)
            return [(b64, mime)]

        images = convert_from_path(file_path, dpi=200)
        pages = []
        for img in images:
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            pages.append((b64, "image/png"))
        return pages

    def _docx_to_images(self, file_path: str) -> list[tuple[str, str]]:
        """将 DOCX 转为图片 base64（通过 pdf 中转）"""
        import tempfile

        try:
            from docx2pdf import convert
        except ImportError:
            # 回退：用 python-docx 提取文本，通过 LLM 处理
            b64, mime = self._file_to_base64(file_path)
            return [(b64, mime)]

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            pdf_path = tmp.name

        try:
            convert(file_path, pdf_path)
            pages = self._pdf_to_images(pdf_path)
            return pages
        finally:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

    async def evaluate(
        self,
        file_path: str,
        target_position: str | None = None,
    ) -> dict[str, Any]:
        """
        评估简历

        Args:
            file_path: 简历文件路径（支持 pdf/docx/jpg/png）
            target_position: 目标岗位（可选，用于匹配度评估）

        Returns:
            dict: 结构化评估结果
        """
        ext = os.path.splitext(file_path)[1].lower()

        # 根据文件类型获取 base64 图片
        if ext == ".pdf":
            pages = self._pdf_to_images(file_path)
        elif ext in [".docx", ".doc"]:
            pages = self._docx_to_images(file_path)
        else:
            # 图片格式直接读取
            b64, mime = self._file_to_base64(file_path)
            pages = [(b64, mime)]

        # 构建消息内容：多页图片 + 用户指令
        content = []
        for b64, mime in pages:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{b64}"},
            })

        user_text = (
            "请按照规定的 Markdown 格式评估这份简历。"
            "目标岗位需要优先从简历内容自动判断；只有用户补充文字明确写出应聘岗位/目标岗位时才作为目标岗位。"
            "不要把“帮我评估简历、分析录音、生成面试题”等任务描述当成岗位。"
        )
        if target_position:
            user_text += f"\n\n用户补充说明：{target_position}\n请先判断其中是否包含明确目标岗位；如果只是任务说明，请忽略其中的任务措辞并从简历自动推断。"
        content.append({"type": "text", "text": user_text})

        # 调用 Qwen3-VL
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": RESUME_EVAL_SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            max_tokens=settings.QWEN_VL_MAX_TOKENS,
            extra_body={"enable_thinking": False},
        )

        raw = response.choices[0].message.content or ""

        # 提取 JSON
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # 如果 JSON 解析失败，返回原始文本
            return {
                "overall_score": 0,
                "scores": {},
                "strengths": [],
                "weaknesses": [],
                "suggestions": [],
                "detailed_analysis": raw,
            }

    async def _extract_text(self, file_path: str) -> str:
        """从简历文件中提取纯文本"""
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(file_path)
                text = ""
                for page in doc:
                    text += page.get_text()
                doc.close()
            except Exception as e:
                logger.warning(f"[简历Agent] PDF 文本提取失败: {e}")
                text = ""
            if text.strip():
                return text.strip()
            logger.info("[简历Agent] PDF 未提取到文本，改用 Qwen-VL 视觉 OCR")
            return await self._extract_text_with_vl(file_path)

        elif ext in (".docx", ".doc"):
            try:
                from docx import Document
                doc = Document(file_path)
                text = "\n".join(para.text for para in doc.paragraphs).strip()
                if text:
                    return text
            except Exception as e:
                logger.warning(f"[简历Agent] DOCX 文本提取失败: {e}")
            logger.info("[简历Agent] Word 未提取到文本，改用 Qwen-VL 视觉 OCR")
            return await self._extract_text_with_vl(file_path)

        if ext in (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"):
            return await self._extract_text_with_vl(file_path)

        return ""

    async def _extract_text_with_vl(self, file_path: str) -> str:
        """使用 Qwen3-VL 从图片/PDF 简历中 OCR 出文本，供查重和违禁词检测使用。"""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            pages = self._pdf_to_images(file_path)
        elif ext in (".docx", ".doc"):
            pages = self._docx_to_images(file_path)
        else:
            b64, mime = self._file_to_base64(file_path)
            pages = [(b64, mime)]

        content: list[dict[str, Any]] = []
        for b64, mime in pages[:6]:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{b64}"},
            })
        content.append({
            "type": "text",
            "text": (
                "请逐字识别这份简历中的全部可见文字，按从上到下、从左到右的顺序输出纯文本。"
                "不要评价，不要总结，不要补全不存在的内容。"
            ),
        })

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": content}],
                max_tokens=min(settings.QWEN_VL_MAX_TOKENS, 4096),
                extra_body={"enable_thinking": False},
            )
            return (response.choices[0].message.content or "").strip()
        except Exception as e:
            logger.warning(f"[简历Agent] Qwen-VL OCR 失败: {e}")
            return ""

    async def _run_checks(self, text: str) -> dict[str, Any]:
        """并行执行查重和违禁词检测"""
        import asyncio
        from app.services.plagiarism import PlagiarismChecker
        from app.services.violation import ViolationChecker

        async def run_plagiarism():
            if not text:
                return {"score": 0.0, "similar_sources": [], "is_suspicious": False}
            return await PlagiarismChecker().check(text)

        async def run_violation():
            if not text:
                return {"words": [], "count": 0, "has_violation": False, "details": []}
            return await ViolationChecker().check_with_llm(text)

        plag_task = asyncio.create_task(run_plagiarism())
        viol_task = asyncio.create_task(run_violation())

        plagiarism = {"score": 0.0, "similar_sources": [], "is_suspicious": False}
        violation = {"words": [], "count": 0, "has_violation": False, "details": []}

        try:
            plagiarism = await plag_task
        except Exception as e:
            logger.error(f"[简历Agent] 查重检测失败: {e}")

        try:
            violation = await viol_task
        except Exception as e:
            logger.error(f"[简历Agent] 违禁词检测失败: {e}")

        return {"plagiarism": plagiarism, "violation": violation}

    async def evaluate_stream(
        self,
        file_path: str,
        target_position: str | None = None,
        user_context: str = "",
    ) -> AsyncIterator[dict[str, str]]:
        """
        流式评估简历（查重+违禁词检测 → 思考过程 → 评估结果逐步输出）

        Yields:
            dict: {"type": "thinking"|"content"|"status", "content": "..."}
        """
        check_results: dict[str, Any] | None = None  # 保存查重/违禁词结果
        text_extracted = False  # 标记文本是否提取成功

        # ── 第一步：文本提取 + 查重/违禁词检测 ──
        yield {"type": "status", "message": "正在提取简历文本...", "progress": 5}
        text = await self._extract_text(file_path)

        if text:
            text_extracted = True
            yield {"type": "status", "message": "正在进行模板查重和违禁词检测...", "progress": 10}
            check_results = await self._run_checks(text)

            plagiarism = check_results.get("plagiarism", {})
            violation = check_results.get("violation", {})

            plag_score = plagiarism.get("score", 0)
            yield {
                "type": "status",
                "message": f"模板查重得分: {plag_score}/100"
                + (" (疑似模板)" if plagiarism.get("is_suspicious") else ""),
                "progress": 15,
            }

            viol_count = violation.get("count", 0)
            if viol_count > 0:
                viol_words = ", ".join(violation.get("words", [])[:5])
                if len(violation.get("words", [])) > 5:
                    viol_words += f" 等{viol_count}处"
                yield {
                    "type": "status",
                    "message": f"违禁词检测: 发现 {viol_count} 处违规 ({viol_words})",
                    "progress": 20,
                }
            else:
                yield {"type": "status", "message": "违禁词检测: 未发现违规内容", "progress": 20}
        else:
            # 文本提取失败（图片简历等），仍然生成默认检测状态
            check_results = {
                "plagiarism": {"score": 0.0, "similar_sources": [], "is_suspicious": False, "skipped": True},
                "violation": {"words": [], "count": 0, "has_violation": False, "details": [], "skipped": True},
            }
            yield {"type": "status", "message": "文本提取跳过（图片简历），查重和违禁词检测将在最终报告中说明", "progress": 15}

        # ── 第二步：AI 视觉评估（流式输出）──
        yield {"type": "status", "message": "正在 AI 评估简历...", "progress": 30}

        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            pages = self._pdf_to_images(file_path)
        elif ext in [".docx", ".doc"]:
            pages = self._docx_to_images(file_path)
        else:
            b64, mime = self._file_to_base64(file_path)
            pages = [(b64, mime)]

        content = []
        for b64, mime in pages:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{b64}"},
            })

        user_text = (
            "请按照规定的 Markdown 格式评估这份简历，直接输出格式化的评估报告。"
            "目标岗位需要优先从简历内容自动判断；只有用户补充文字明确写出应聘岗位/目标岗位时才作为目标岗位。"
            "不要把“帮我评估简历、分析录音、生成面试题”等任务描述当成岗位。"
        )
        if target_position:
            user_text += f"\n\n用户补充说明：{target_position}\n请先判断其中是否包含明确目标岗位；如果只是任务说明，请忽略其中的任务措辞并从简历自动推断。"

        # 注入用户个人信息（仅供内部参考，不可在报告中暴露）
        if user_context:
            user_text += f"\n\n[以下信息仅供你评估岗位匹配度时内部参考，绝对不可在评估报告中提及或引用]\n{user_context}"

        content.append({"type": "text", "text": user_text})

        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": RESUME_EVAL_SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            max_tokens=settings.QWEN_VL_MAX_TOKENS,
            stream=True,
            extra_body={"enable_thinking": True, "thinking_budget": 16384},
        )

        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            # 思考过程
            reasoning = getattr(delta, "reasoning_content", None)
            if reasoning:
                yield {"type": "thinking", "content": reasoning}

            # 正式回复
            content_text = getattr(delta, "content", None)
            if content_text:
                yield {"type": "content", "content": content_text}

        # ── 第三步：输出查重检测和违禁词检测板块（始终生成）──
        yield {"type": "status", "message": "正在生成查重与违禁词检测报告...", "progress": 90}
        report_sections = self._build_check_report(check_results)
        if report_sections:
            yield {"type": "content", "content": report_sections}

    def _build_check_report(self, check_results: dict[str, Any]) -> str:
        """
        根据查重和违禁词检测结果构建 Markdown 报告板块

        Args:
            check_results: {"plagiarism": {...}, "violation": {...}}

        Returns:
            str: Markdown 格式的查重+违禁词报告
        """
        sections = []
        plagiarism = check_results.get("plagiarism", {})
        violation = check_results.get("violation", {})

        # ── 模板查重检测板块 ──
        plag_score = plagiarism.get("score", 0)
        is_suspicious = plagiarism.get("is_suspicious", False)
        plag_skipped = plagiarism.get("skipped", False)
        similar_sources = plagiarism.get("similar_sources", [])

        if plag_skipped:
            plag_section = f"\n\n---\n\n## 🔍 模板查重检测\n\n**⏭️ 跳过检测**（简历为图片格式，无法提取文本进行模板比对）\n"
        elif is_suspicious:
            plag_status = f"**⚠️ 疑似使用模板**（相似度 {plag_score}/100）"
            plag_section = f"\n\n---\n\n## 🔍 模板查重检测\n\n{plag_status}\n"

            if similar_sources:
                plag_section += "\n| 相似模板 | 相似度 |\n|----------|--------|\n"
                for src in similar_sources:
                    name = src.get("name", "未知模板")
                    sim = src.get("similarity", 0)
                    sim_pct = f"{sim * 100:.1f}%"
                    plag_section += f"| {name} | {sim_pct} |\n"

                plag_section += "\n> ⚠️ 检测到你的简历与模板库中的内容高度相似，建议修改措辞和结构，突出个人特色。\n"
        else:
            plag_status = f"**✅ {'基本原创' if plag_score > 40 else '高度原创'}**（相似度 {plag_score}/100）"
            plag_section = f"\n\n---\n\n## 🔍 模板查重检测\n\n{plag_status}\n"

            if similar_sources:
                plag_section += "\n| 相似模板 | 相似度 |\n|----------|--------|\n"
                for src in similar_sources:
                    name = src.get("name", "未知模板")
                    sim = src.get("similarity", 0)
                    sim_pct = f"{sim * 100:.1f}%"
                    plag_section += f"| {name} | {sim_pct} |\n"

        sections.append(plag_section)

        # ── 违禁词检测板块 ──
        viol_count = violation.get("count", 0)
        has_violation = violation.get("has_violation", False)
        viol_skipped = violation.get("skipped", False)
        viol_words = violation.get("words", [])
        viol_details = violation.get("details", [])

        if viol_skipped:
            viol_section = "\n\n## 🚨 违禁词检测\n\n**⏭️ 跳过检测**（简历为图片格式，无法提取文本进行违禁词扫描）\n"
        elif has_violation:
            viol_section = f"\n\n## 🚨 违禁词检测\n\n**发现 {viol_count} 处违规内容：**\n\n"
            viol_section += "| 违禁词 | 位置 | 上下文 |\n|--------|------|--------|\n"
            for detail in viol_details:
                word = detail.get("word", "")
                pos = detail.get("position", -1)
                context = detail.get("context", "")
                pos_str = f"第 {pos} 字符" if pos >= 0 else "语义检测"
                viol_section += f"| {word} | {pos_str} | {context} |\n"

            viol_section += "\n> ⚠️ 简历中包含可能引起问题的内容，建议删除或修改上述标注的部分。\n"
        else:
            viol_section = "\n\n## ✅ 违禁词检测\n\n**未发现违规内容**，简历内容符合基本规范。\n"

        sections.append(viol_section)

        return "".join(sections)

    async def execute(self, agent_input: AgentInput) -> AgentOutput:
        """基类接口实现"""
        file_path = agent_input.context.get("file_path", "")
        target_position = agent_input.context.get("target_position")

        if not file_path:
            return AgentOutput(
                content="请先上传简历文件",
                agent_name=self.name,
                status="failed",
                error_msg="缺少 file_path",
            )

        result = await self.evaluate(file_path, target_position)

        return AgentOutput(
            content=f"简历评估完成，综合评分：{result.get('overall_score', 'N/A')}/100",
            agent_name=self.name,
            metadata=result,
        )
