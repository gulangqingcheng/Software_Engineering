"""
AI 面试官模块

负责生成面试问题、进行追问判断，支持根据用户前置条件生成问题。
"""

import json
from typing import Any, Optional

from app.config import settings


class InterviewAgent:
    """
    AI 面试官代理
    
    根据目标岗位、面试类型和难度生成问题，并支持追问。
    """

    DIMENSIONS = {
        "岗位相关性": 18,
        "技术深度": 24,
        "逻辑结构": 18,
        "案例与结果": 18,
        "表达沟通": 12,
        "时间控制": 10,
    }

    QUESTION_TEMPLATES = {
        "technical": [
            {
                "template": "请介绍你在{position}方向最有代表性的项目，以及你承担的核心职责。",
                "question_type": "project",
                "expected_points": ["项目背景", "技术选型", "个人贡献", "结果复盘"],
            },
            {
                "template": "在{position}工作中遇到复杂问题时，你通常如何定位原因并验证解决方案？",
                "question_type": "problem_solving",
                "expected_points": ["问题定位", "分析思路", "验证方法", "复盘总结"],
            },
            {
                "template": "请结合实例说明你如何保证交付质量，并处理性能、稳定性或可维护性问题。",
                "question_type": "quality_assurance",
                "expected_points": ["质量保障", "性能优化", "稳定性", "可维护性"],
            },
            {
                "template": "如果需要你从零设计一个与{position}相关的功能，你会如何拆解需求和制定方案？",
                "question_type": "system_design",
                "expected_points": ["需求分析", "方案设计", "技术选型", "实施计划"],
            },
            {
                "template": "请谈谈你近期学习的一项与{position}相关的新技术，以及它适合解决什么问题。",
                "question_type": "learning",
                "expected_points": ["技术理解", "适用场景", "实践经验", "价值评估"],
            },
        ],
        "behavioral": [
            {
                "template": "请介绍一次你主动推动团队目标达成的经历。",
                "question_type": "initiative",
                "expected_points": ["目标设定", "行动过程", "团队协作", "成果达成"],
            },
            {
                "template": "请描述一次你与团队成员意见不一致的情况，以及你如何处理。",
                "question_type": "conflict_resolution",
                "expected_points": ["冲突分析", "沟通方式", "解决方案", "结果反思"],
            },
            {
                "template": "请分享一次你面对紧迫期限时安排优先级的经历。",
                "question_type": "prioritization",
                "expected_points": ["优先级判断", "计划安排", "执行过程", "结果评估"],
            },
            {
                "template": "请说明一次失败或失误给你带来的经验。",
                "question_type": "failure_learning",
                "expected_points": ["问题分析", "原因反思", "改进措施", "经验总结"],
            },
            {
                "template": "你为什么希望从事{position}相关工作，未来的成长目标是什么？",
                "question_type": "career_goals",
                "expected_points": ["动机分析", "岗位匹配", "目标设定", "计划路径"],
            },
        ],
        "comprehensive": [
            {
                "template": "请做一个简短的自我介绍，并说明你与{position}岗位的匹配点。",
                "question_type": "self_introduction",
                "expected_points": ["背景介绍", "核心优势", "岗位匹配", "个人特质"],
            },
            {
                "template": "请介绍一个最能体现你解决问题能力的项目经历。",
                "question_type": "problem_solving",
                "expected_points": ["问题描述", "分析过程", "解决方案", "成果展示"],
            },
            {
                "template": "面对不熟悉的任务时，你会如何快速学习并交付结果？",
                "question_type": "learning_ability",
                "expected_points": ["学习方法", "资源利用", "实践过程", "成果产出"],
            },
            {
                "template": "请描述你如何与团队协作并保证信息同步。",
                "question_type": "team_collaboration",
                "expected_points": ["沟通机制", "协作方式", "信息同步", "冲突处理"],
            },
            {
                "template": "你对{position}岗位的核心能力有哪些理解？",
                "question_type": "position_understanding",
                "expected_points": ["能力认知", "技术要求", "软技能", "发展方向"],
            },
        ],
    }

    DIFFICULTY_LABELS = {
        "easy": "基础",
        "medium": "进阶",
        "hard": "深入",
    }

    def __init__(self):
        self.client = None

    def _llm_enabled(self) -> bool:
        """检查是否配置了 LLM API Key"""
        api_key = (settings.LLM_API_KEY or "").strip()
        return bool(api_key and api_key != "your-api-key-here")

    def _call_llm_json(self, system_prompt: str, user_prompt: str, max_tokens: int = 1600) -> Optional[dict[str, Any]]:
        """调用大模型获取 JSON 响应"""
        if not self._llm_enabled():
            return None

        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=settings.LLM_API_KEY,
                base_url=settings.LLM_BASE_URL.rstrip("/"),
                timeout=settings.LLM_TIMEOUT,
            )
            response = client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=min(settings.LLM_TEMPERATURE, 0.4),
                max_tokens=min(settings.LLM_MAX_TOKENS, max_tokens),
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            return json.loads(content)
        except Exception as exc:
            print(f"[AI面试] 大模型调用失败，使用本地规则降级: {exc}")
            return None

    def generate_question(
        self,
        target_position: str,
        interview_type: str,
        difficulty: str,
        question_index: int,
        previous_answers: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """
        生成面试问题
        
        Args:
            target_position: 目标岗位
            interview_type: 面试类型 (technical/behavioral/comprehensive)
            difficulty: 难度 (easy/medium/hard)
            question_index: 题目序号
            previous_answers: 之前的回答列表（用于追问判断）
        
        Returns:
            问题信息字典，包含 question, question_type, difficulty, expected_points, is_follow_up
        """
        templates = self.QUESTION_TEMPLATES.get(interview_type, self.QUESTION_TEMPLATES["comprehensive"])
        template_info = templates[(question_index - 1) % len(templates)]
        
        difficulty_label = self.DIFFICULTY_LABELS.get(difficulty, "进阶")
        question_text = f"第 {question_index} 题（{difficulty_label}）：{template_info['template'].format(position=target_position)}"

        return {
            "question": question_text,
            "question_type": template_info["question_type"],
            "difficulty": difficulty,
            "expected_points": template_info["expected_points"],
            "is_follow_up": False,
        }

    def should_follow_up(self, question: str, answer: str, answer_duration_seconds: Optional[int] = None) -> bool:
        """
        判断是否需要追问
        
        Args:
            question: 原始问题
            answer: 用户回答
            answer_duration_seconds: 回答时长
            
        Returns:
            是否需要追问
        """
        answer_length = len(answer.strip())
        
        # 回答过短，需要追问
        if answer_length < 40:
            return True
        
        # 回答中包含"可能"、"大概"、"一般"等模糊词汇，需要追问
        vague_words = ("可能", "大概", "一般", "差不多", "还行", "还好", "应该")
        if any(word in answer for word in vague_words):
            return True
        
        # 回答时长过短（少于30秒），可能回答不够充分
        if answer_duration_seconds and answer_duration_seconds < 30:
            return True
        
        return False

    def generate_follow_up_question(self, original_question: str, answer: str) -> Optional[dict[str, Any]]:
        """
        生成追问问题
        
        Args:
            original_question: 原始问题
            answer: 用户回答
            
        Returns:
            追问问题信息，如果不需要追问则返回 None
        """
        if not self.should_follow_up(original_question, answer):
            return None

        # 尝试使用大模型生成追问
        if self._llm_enabled():
            system_prompt = """你是一位专业的面试官。根据候选人的回答，生成一个针对性的追问问题，帮助深入了解候选人能力。
只输出 JSON，格式：{"question": "追问问题"}"""
            user_prompt = f"""原始问题：{original_question}
候选人回答：{answer}

请生成一个追问问题，用于进一步了解候选人的能力或经历。"""
            
            data = self._call_llm_json(system_prompt, user_prompt)
            if data and data.get("question"):
                return {
                    "question": data["question"],
                    "question_type": "follow_up",
                    "difficulty": "medium",
                    "expected_points": ["深入分析", "细节补充"],
                    "is_follow_up": True,
                }

        # 兜底追问
        follow_up_templates = [
            "能否请你举一个具体的例子来说明？",
            "在这个过程中，你遇到了哪些挑战，是如何解决的？",
            "你提到的这个点很有趣，能否展开讲讲？",
            "这个项目的最终结果如何，有什么量化指标吗？",
            "在这个场景下，你为什么选择这种方案而不是其他方案？",
        ]
        
        # 根据回答内容选择合适的追问
        answer_lower = answer.lower()
        if "项目" in answer or "负责" in answer:
            template = "这个项目的最终结果如何，有什么量化指标吗？"
        elif "方案" in answer or "设计" in answer:
            template = "在这个场景下，你为什么选择这种方案而不是其他方案？"
        else:
            template = follow_up_templates[(len(answer) // 20) % len(follow_up_templates)]

        return {
            "question": template,
            "question_type": "follow_up",
            "difficulty": "medium",
            "expected_points": ["深入分析", "细节补充"],
            "is_follow_up": True,
        }

    def is_interview_complete(
        self,
        question_count: int,
        answered_count: int,
        session_status: str,
    ) -> bool:
        """
        判断面试是否结束
        
        Args:
            question_count: 设定的题目数量
            answered_count: 已回答的题目数量
            session_status: 当前会话状态
            
        Returns:
            是否结束
        """
        # 如果会话已标记为结束，则结束
        if session_status == "finished":
            return True
        
        # 如果已回答题目数量达到设定数量，则结束
        if answered_count >= question_count:
            return True
        
        return False
