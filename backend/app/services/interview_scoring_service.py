"""
面试评分服务

负责对用户回答进行评分，支持大模型评分和本地规则评分两种模式。
"""

import json
import re
from typing import Any, Optional

from app.config import settings
from app.models.interview import InterviewSession, InterviewTurn


class InterviewScoringService:
    """
    面试评分服务
    
    根据用户回答内容和回答时长进行多维度评分。
    """

    DIMENSIONS = {
        "岗位相关性": 18,
        "技术深度": 24,
        "逻辑结构": 18,
        "案例与结果": 18,
        "表达沟通": 12,
        "时间控制": 10,
    }

    def __init__(self):
        pass

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
            print(f"[AI面试评分] 大模型调用失败，使用本地规则降级: {exc}")
            return None

    def _clamp(self, value: float, max_value: int) -> float:
        """将值限制在 0 到 max_value 之间"""
        return round(max(0.0, min(float(value), float(max_value))), 1)

    def _score_band(self, score: float) -> str:
        """获取评分等级"""
        if score >= 85:
            return "优秀"
        if score >= 75:
            return "良好"
        if score >= 60:
            return "一般"
        return "待提升"

    def score_with_llm(
        self,
        session: InterviewSession,
        turn: InterviewTurn,
        answer_text: str,
        answer_duration_seconds: Optional[int] = None,
    ) -> Optional[dict[str, Any]]:
        """
        使用大模型进行评分
        
        Args:
            session: 面试会话
            turn: 当前题目
            answer_text: 用户回答
            answer_duration_seconds: 回答时长
            
        Returns:
            评分结果字典，如果调用失败返回 None
        """
        answer = answer_text.strip()
        if not answer:
            return None

        system_prompt = """你是一位严谨的中文技术面试官。请按固定评分量表评估候选人回答，只输出 JSON。
评分量表总分 100：
1. 岗位相关性 18 分：回答是否贴合目标岗位和问题。
2. 技术深度 24 分：是否包含准确技术点、实现思路、原因分析、取舍或验证方法。
3. 逻辑结构 18 分：是否结构清楚，是否有背景、任务、行动、结果或类似组织方式。
4. 案例与结果 18 分：是否有具体项目、个人贡献、量化结果或可验证事实。
5. 表达沟通 12 分：语言是否清晰、具体、专业。
6. 时间控制 10 分：结合回答时长判断节奏，通常 60 到 180 秒较合适，过短说明展开不足，过长说明重点不够集中。
JSON 字段：
score: 总分数字；
accuracy_score: 技术准确性得分（对应技术深度的一部分）；
structure_score: 结构得分（对应逻辑结构）；
matching_score: 岗位匹配得分（对应岗位相关性）；
expression_score: 表达得分（对应表达沟通）；
time_score: 时间控制得分；
dimensions: 对象，键必须是 岗位相关性/技术深度/逻辑结构/案例与结果/表达沟通/时间控制，值是对应得分；
evidence: 2 到 4 条评分依据；
missing_points: 2 到 4 条扣分原因；
feedback: 一段综合评价；
suggestion: 一条最优先改进建议。"""

        user_prompt = f"""目标岗位：{session.target_position}
面试类型：{session.interview_type}
难度：{session.difficulty}
问题：{turn.question}
回答：{answer}
回答时长秒数：{answer_duration_seconds or "未提供"}"""

        data = self._call_llm_json(system_prompt, user_prompt)
        if not data:
            return None

        dimensions = data.get("dimensions")
        if not isinstance(dimensions, dict):
            return None

        normalized_dimensions = {
            key: self._clamp(dimensions.get(key, 0), max_value)
            for key, max_value in self.DIMENSIONS.items()
        }

        score = round(sum(normalized_dimensions.values()), 1)
        evidence = [str(item).strip() for item in data.get("evidence", []) if str(item).strip()]
        missing_points = [str(item).strip() for item in data.get("missing_points", []) if str(item).strip()]
        feedback = str(data.get("feedback") or "").strip()
        suggestion = str(data.get("suggestion") or "").strip()

        if not feedback or not suggestion:
            return None

        return {
            "score": score,
            "accuracy_score": round(normalized_dimensions.get("技术深度", 0) * 0.6, 1),
            "structure_score": normalized_dimensions.get("逻辑结构", 0),
            "matching_score": normalized_dimensions.get("岗位相关性", 0),
            "expression_score": normalized_dimensions.get("表达沟通", 0),
            "time_score": normalized_dimensions.get("时间控制", 0),
            "dimensions": normalized_dimensions,
            "evidence": evidence[:4] or ["大模型根据评分量表完成了综合判断。"],
            "missing_points": missing_points[:4] or ["建议补充更具体的项目细节和结果数据。"],
            "feedback": feedback,
            "suggestion": suggestion,
            "source": "llm",
        }

    def score_locally(
        self,
        session: InterviewSession,
        turn: InterviewTurn,
        answer_text: str,
        answer_duration_seconds: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        使用本地规则进行评分（兜底方案）
        
        Args:
            session: 面试会话
            turn: 当前题目
            answer_text: 用户回答
            answer_duration_seconds: 回答时长
            
        Returns:
            评分结果字典
        """
        answer = answer_text.strip()
        lower_answer = answer.lower()
        length = len(answer)

        # 结构化标记词
        structure_markers = ("首先", "其次", "最后", "第一", "第二", "背景", "任务", "行动", "结果", "因此", "总结")
        tech_markers = (
            "接口", "组件", "数据库", "缓存", "并发", "性能", "安全", "测试", "部署", "日志", "异常",
            "架构", "算法", "复杂度", "索引", "事务", "状态", "模块", "封装", "优化",
            "api", "vue", "react", "spring", "mysql", "redis", "docker", "http",
        )
        evidence_markers = ("项目", "负责", "实现", "解决", "上线", "提升", "降低", "用户", "业务", "数据", "指标")
        result_patterns = re.findall(r"\d+[%\w]*|一|二|三|四|五|十|百|千|万", answer)

        # 初始化维度得分
        dimensions = {
            "岗位相关性": 7.0,
            "技术深度": 8.0,
            "逻辑结构": 6.0,
            "案例与结果": 5.0,
            "表达沟通": 6.0,
            "时间控制": 5.0,
        }

        # 岗位相关性评分
        position_keywords = [word for word in re.split(r"[\s/、，,]+", session.target_position) if word]
        if any(keyword and keyword in answer for keyword in position_keywords):
            dimensions["岗位相关性"] += 5
        if any(marker in answer for marker in ("岗位", "业务", "用户", "需求", "交付", "项目")):
            dimensions["岗位相关性"] += 4
        if length >= 80:
            dimensions["岗位相关性"] += 3

        # 技术深度评分
        tech_count = sum(marker in answer or marker in lower_answer for marker in tech_markers)
        dimensions["技术深度"] += min(tech_count * 2.8, 13)
        if any(marker in answer for marker in ("原因", "方案", "验证", "测试", "优化", "权衡")):
            dimensions["技术深度"] += 4

        # 逻辑结构评分
        structure_count = sum(marker in answer for marker in structure_markers)
        dimensions["逻辑结构"] += min(structure_count * 2.2, 9)
        if length >= 120:
            dimensions["逻辑结构"] += 3

        # 案例与结果评分
        evidence_count = sum(marker in answer for marker in evidence_markers)
        dimensions["案例与结果"] += min(evidence_count * 2.0, 8)
        dimensions["案例与结果"] += min(len(result_patterns) * 1.5, 6)

        # 表达沟通评分
        if 80 <= length <= 500:
            dimensions["表达沟通"] += 5
        elif length >= 40:
            dimensions["表达沟通"] += 3
        if "我" in answer and any(marker in answer for marker in ("会", "做", "负责", "推进", "解决")):
            dimensions["表达沟通"] += 2

        # 时间控制评分
        missing_time = ""
        if answer_duration_seconds is None:
            dimensions["时间控制"] = 6.0
            missing_time = "未记录回答时长，时间控制维度按中等水平估计。"
        elif 60 <= answer_duration_seconds <= 180:
            dimensions["时间控制"] = 10.0
            missing_time = ""
        elif 30 <= answer_duration_seconds < 60 or 180 < answer_duration_seconds <= 240:
            dimensions["时间控制"] = 8.0
            missing_time = ""
        elif 15 <= answer_duration_seconds < 30 or 240 < answer_duration_seconds <= 300:
            dimensions["时间控制"] = 5.5
            missing_time = "回答时长偏短或偏长，建议控制在 1 到 3 分钟内。"
        else:
            dimensions["时间控制"] = 3.0
            missing_time = "回答时间控制不理想，可能影响面试官对表达完整度和重点把握的判断。"

        # 限制维度得分在合理范围内
        dimensions = {key: self._clamp(value, self.DIMENSIONS[key]) for key, value in dimensions.items()}
        score = round(sum(dimensions.values()), 1)

        # 收集评分依据和缺失点
        evidence = []
        missing_points = []
        if tech_count:
            evidence.append(f"回答提到了 {tech_count} 个技术或工程关键词，体现一定技术关联。")
        else:
            missing_points.append("缺少具体技术点、方案选择或实现细节。")
        if structure_count:
            evidence.append("回答包含结构化表达信号，逻辑组织较清楚。")
        else:
            missing_points.append("回答结构不够清晰，建议按背景、任务、行动、结果展开。")
        if evidence_count or result_patterns:
            evidence.append("回答包含项目/结果相关信息，具备一定案例依据。")
        else:
            missing_points.append("缺少可验证的项目案例、数据结果或个人贡献。")
        if length < 60:
            missing_points.append("回答篇幅偏短，论证不够充分。")
        if answer_duration_seconds is not None:
            evidence.append(f"本题回答耗时 {answer_duration_seconds} 秒，已纳入时间控制评分。")
        if missing_time:
            missing_points.append(missing_time)

        if not evidence:
            evidence.append("回答完成了基本回应，但可支撑评分的具体依据较少。")
        if not missing_points:
            missing_points.append("可以进一步补充量化结果和技术权衡，提升说服力。")

        feedback = f"{self._score_band(score)}：本题总分 {score}/100，主要依据为岗位相关性、技术深度、逻辑结构、案例结果、表达沟通和时间控制六个维度。"
        suggestion = missing_points[0]

        return {
            "score": score,
            "accuracy_score": round(dimensions["技术深度"] * 0.6, 1),
            "structure_score": dimensions["逻辑结构"],
            "matching_score": dimensions["岗位相关性"],
            "expression_score": dimensions["表达沟通"],
            "time_score": dimensions["时间控制"],
            "dimensions": dimensions,
            "evidence": evidence[:4],
            "missing_points": missing_points[:4],
            "feedback": feedback,
            "suggestion": suggestion,
            "source": "local",
        }

    def score(
        self,
        session: InterviewSession,
        turn: InterviewTurn,
        answer_text: str,
        answer_duration_seconds: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        对用户回答进行评分
        
        优先使用大模型评分，如果失败则使用本地规则兜底。
        
        Args:
            session: 面试会话
            turn: 当前题目
            answer_text: 用户回答
            answer_duration_seconds: 回答时长
            
        Returns:
            评分结果字典
        """
        return self.score_with_llm(session, turn, answer_text, answer_duration_seconds) or \
               self.score_locally(session, turn, answer_text, answer_duration_seconds)

    def generate_report(self, session: InterviewSession) -> dict[str, Any]:
        """
        生成完整的面试报告
        
        Args:
            session: 面试会话
            
        Returns:
            报告字典
        """
        from datetime import datetime

        answered_turns = [turn for turn in session.turns if turn.answered_at is not None]
        turn_details = []
        
        for turn in answered_turns:
            detail = self.score(session, turn, turn.answer_text or "", turn.answer_duration_seconds)
            detail["score"] = float(turn.score or detail["score"])
            detail["feedback"] = turn.feedback or detail["feedback"]
            detail["suggestion"] = turn.suggestion or detail["suggestion"]
            turn_details.append(detail)

        scores = [float(turn.score or 0) for turn in answered_turns]
        total_score = round(sum(scores) / len(scores), 1) if scores else 0.0

        # 计算平均维度得分
        if turn_details:
            dimension_scores = {key: 0.0 for key in self.DIMENSIONS}
            for detail in turn_details:
                for key in self.DIMENSIONS:
                    dimension_scores[key] += float(detail.get("dimensions", {}).get(key, 0))
            dimension_scores = {key: round(value / len(turn_details), 1) for key, value in dimension_scores.items()}
        else:
            dimension_scores = {key: 0 for key in self.DIMENSIONS}

        # 分析优势和不足
        low_dimensions = sorted(dimension_scores.items(), key=lambda item: item[1] / self.DIMENSIONS[item[0]])[:2]
        high_dimensions = sorted(dimension_scores.items(), key=lambda item: item[1] / self.DIMENSIONS[item[0]], reverse=True)[:2]
        
        strengths = [f"{name}表现相对较好，平均得分 {score}/{self.DIMENSIONS[name]}。" for name, score in high_dimensions if score > 0]
        weaknesses = [f"{name}仍需加强，平均得分 {score}/{self.DIMENSIONS[name]}。" for name, score in low_dimensions if score > 0]
        
        if not strengths:
            strengths = ["已完成全部题目回答，具备进一步复盘和提升的基础。"]
        if not weaknesses:
            weaknesses = ["建议继续提升回答的具体案例、技术细节和结果数据。"]

        # 收集建议
        suggestions = list(dict.fromkeys(
            detail["suggestion"] for detail in turn_details if detail.get("suggestion")
        ))
        if len(suggestions) < 3:
            suggestions.extend([
                "每道题尽量说明具体场景、个人行动和最终结果。",
                "技术题回答时补充方案选择、验证方法和异常处理。",
                "准备 2 到 3 个可复用项目案例，用数据说明贡献。",
            ])
        suggestions = list(dict.fromkeys(suggestions))[:5]

        # 行动计划
        action_plan = [
            "第 1 步：整理一个最熟悉的项目，用背景、任务、行动、结果四段话讲清楚。",
            "第 2 步：为每个项目补充技术难点、方案对比、测试验证和量化结果。",
            "第 3 步：将常见问题录音练习，控制回答在 1 到 3 分钟内。",
            "第 4 步：针对低分维度重新回答本次题目，并对照评分依据自查。",
        ]

        # 整体总结
        if total_score >= 85:
            summary = "整体表现优秀，回答较完整，能体现较好的岗位匹配度和表达能力。后续重点是继续补充量化结果和技术取舍，让优势更有说服力。"
        elif total_score >= 75:
            summary = "整体表现良好，多数回答能够回应问题，但部分题目还可以补充更具体的项目细节、技术依据和结果数据。"
        elif total_score >= 60:
            summary = "整体表现一般，回答覆盖了基本方向，但技术深度、案例依据或结构化表达仍不够稳定。建议按评分维度逐项补强。"
        else:
            summary = "整体表现有较大提升空间，回答中缺少足够的具体事实和结构化论证。建议先准备标准项目案例，再进行模拟面试训练。"

        report = {
            "session_id": session.id,
            "total_score": total_score,
            "status": session.status,
            "summary": summary,
            "score_basis": "总分按六个维度综合计算：岗位相关性18分、技术深度24分、逻辑结构18分、案例与结果18分、表达沟通12分、时间控制10分。时间控制会结合每题回答秒数，通常 60 到 180 秒较合适。",
            "dimension_scores": dimension_scores,
            "turn_performance": [
                {
                    "question_index": turn.question_index,
                    "question": turn.question,
                    "answer": turn.answer_text or "",
                    "answer_duration_seconds": turn.answer_duration_seconds,
                    "score": float(turn.score or 0),
                    "dimensions": detail["dimensions"],
                    "evidence": detail["evidence"],
                    "missing_points": detail["missing_points"],
                    "feedback": turn.feedback or detail["feedback"],
                    "suggestion": turn.suggestion or detail["suggestion"],
                }
                for turn, detail in zip(answered_turns, turn_details)
            ],
            "strengths": strengths[:4],
            "weaknesses": weaknesses[:4],
            "suggestions": suggestions,
            "action_plan": action_plan,
            "generated_at": datetime.now(),
        }

        # 尝试使用大模型增强报告
        enhanced_report = self._enhance_report_with_llm(report, session)
        return enhanced_report

    def _enhance_report_with_llm(self, report: dict[str, Any], session: InterviewSession) -> dict[str, Any]:
        """
        使用大模型增强报告内容
        
        Args:
            report: 原始报告
            session: 面试会话
            
        Returns:
            增强后的报告
        """
        if not report["turn_performance"]:
            return report

        system_prompt = """你是一位中文面试辅导专家。请基于评分表和逐题记录生成详细面试报告，只输出 JSON。
必须保留客观依据，不要编造候选人未提到的经历。
JSON 字段：
summary: 3 到 5 句话整体总结；
strengths: 3 到 5 条优势；
weaknesses: 3 到 5 条不足；
suggestions: 4 到 6 条改进建议；
action_plan: 4 到 6 条后续训练计划。"""

        user_prompt = json.dumps(
            {
                "target_position": session.target_position,
                "interview_type": session.interview_type,
                "difficulty": session.difficulty,
                "score_basis": report["score_basis"],
                "total_score": report["total_score"],
                "dimension_scores": report["dimension_scores"],
                "turn_performance": report["turn_performance"],
            },
            ensure_ascii=False,
        )

        data = self._call_llm_json(system_prompt, user_prompt, max_tokens=2200)
        if not data:
            return report

        for key in ["summary", "strengths", "weaknesses", "suggestions", "action_plan"]:
            value = data.get(key)
            if key == "summary" and isinstance(value, str) and value.strip():
                report[key] = value.strip()
            elif isinstance(value, list) and value:
                report[key] = [str(item).strip() for item in value if str(item).strip()]

        return report
