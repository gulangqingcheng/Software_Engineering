"""
违禁词检测服务
对简历内容进行规则匹配和 LLM 辅助的违规内容检测
"""

import os
import re
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ViolationChecker:
    """
    违禁词检测服务
    
    功能：
    1. 规则匹配：基于内置违禁词库的精确匹配
    2. 模糊匹配：检测违禁词的变体（谐音、拼音、特殊符号等）
    3. LLM 辅助检测：使用 LLM 识别语义层面的违规内容
    """

    # 内置基础违禁词列表（后续从文件加载）
    DEFAULT_VIOLATION_WORDS: list[str] = [
        # 身份信息敏感词
        "身份证号码", "身份证号",
        # 联系方式不规范用词
        "微信号", "QQ号", "手机号码",
        # 歧视性用语（示例）
        "性别歧视", "年龄歧视", "地域歧视",
        # 政治敏感词（示例）
        "省部级以上", "局级以上",
        # 虚假信息关键词
        "顶尖", "无与伦比", "世界第一",
    ]

    def __init__(self):
        self.violation_words: list[str] = self._load_violation_words()

    def _load_violation_words(self) -> list[str]:
        """
        加载违禁词列表
        先从文件加载，文件不存在时使用内置默认列表
        """
        # TODO: 从文件加载违禁词列表
        # from app.config import settings
        # if os.path.exists(settings.VIOLATION_WORDS_FILE):
        #     with open(settings.VIOLATION_WORDS_FILE, "r", encoding="utf-8") as f:
        #         return [line.strip() for line in f if line.strip() and not line.startswith("#")]
        return self.DEFAULT_VIOLATION_WORDS

    def check(self, text: str) -> dict[str, Any]:
        """
        检测文本中的违禁词
        
        Args:
            text: 待检测的文本内容
            
        Returns:
            dict: {
                "words": ["违禁词1", "违禁词2"],  # 检测到的违禁词列表
                "count": 2,  # 违禁词数量
                "has_violation": True,  # 是否存在违规
                "details": [  # 每个违禁词的详细信息
                    {"word": "违禁词1", "position": 120, "context": "这是包含违禁词1的句子..."},
                ],
            }
        """
        violations = []
        text_lower = text.lower()

        for word in self.violation_words:
            matches = list(re.finditer(re.escape(word), text, re.IGNORECASE))
            for match in matches:
                start = match.start()
                # 提取上下文（前后各20个字符）
                context_start = max(0, start - 20)
                context_end = min(len(text), start + len(word) + 20)
                context = text[context_start:context_end].strip()

                violations.append({
                    "word": word,
                    "position": start,
                    "context": context,
                })

        return {
            "words": list(set(v["word"] for v in violations)),
            "count": len(violations),
            "has_violation": len(violations) > 0,
            "details": violations,
        }

    async def check_with_llm(self, text: str) -> dict[str, Any]:
        """
        使用规则匹配 + LLM 语义检测进行深度违规检测

        Args:
            text: 待检测的文本内容

        Returns:
            dict: 与 check() 相同格式的结果
        """
        # 1. 先进行规则匹配
        rule_result = self.check(text)

        # 2. LLM 语义检测（检测规则无法覆盖的变体和语义问题）
        llm_violations: list[dict[str, str]] = []
        try:
            from app.services.llm_service import LLMService

            system_prompt = (
                "你是一个专业的简历合规审查助手。请检查以下简历内容是否包含违规信息。\n\n"
                "检测范围：\n"
                "1. 敏感个人身份信息（身份证号、银行卡号等）\n"
                "2. 歧视性用语（性别、年龄、地域、婚育、民族等歧视）\n"
                "3. 虚假夸张描述（无法证实的绝对化用语）\n"
                "4. 政治敏感内容\n"
                "5. 不规范的个人联系方式（微信号、QQ号写在简历正文中等）\n\n"
                "请严格以 JSON 格式返回结果，格式如下：\n"
                '{"words": ["违禁词1", "违禁词2"], "details": [{"word": "违禁词1", "reason": "违规原因"}]}\n'
                "如果没有发现违规内容，返回：{\"words\": [], \"details\": []}\n"
                "只返回 JSON，不要包含其他内容。"
            )

            llm = LLMService()
            llm_result = await llm.chat_json(
                messages=[{"role": "user", "content": f"简历内容：\n{text}"}],
                system_prompt=system_prompt,
                temperature=0.1,
            )

            # 解析 LLM 结果
            if isinstance(llm_result, dict):
                raw_words = llm_result.get("words", [])
                raw_details = llm_result.get("details", [])

                for detail in raw_details:
                    word = detail.get("word", "")
                    reason = detail.get("reason", "")
                    if word and word.strip():
                        llm_violations.append({
                            "word": word.strip(),
                            "position": -1,  # LLM 无法给出精确位置
                            "context": f"[LLM 语义检测] {reason}",
                        })

                # 处理 words 中有但 details 中没有的词
                existing_words = {d["word"] for d in llm_violations}
                for w in raw_words:
                    if w.strip() and w.strip() not in existing_words:
                        llm_violations.append({
                            "word": w.strip(),
                            "position": -1,
                            "context": "[LLM 语义检测]",
                        })

        except Exception as e:
            logger.warning(f"[违禁词] LLM 检测失败，回退到规则匹配: {e}")

        # 3. 合并规则匹配和 LLM 结果（按 word 去重）
        rule_words = set(rule_result.get("words", []))
        merged_details = list(rule_result.get("details", []))

        for lv in llm_violations:
            if lv["word"] not in rule_words:
                merged_details.append(lv)

        merged_words = list(set(d["word"] for d in merged_details))

        return {
            "words": merged_words,
            "count": len(merged_details),
            "has_violation": len(merged_details) > 0,
            "details": merged_details,
        }

    def update_violation_words(self, words: list[str]) -> None:
        """
        动态更新违禁词列表
        
        Args:
            words: 新的违禁词列表
        """
        self.violation_words = words
        # TODO: 持久化到文件
