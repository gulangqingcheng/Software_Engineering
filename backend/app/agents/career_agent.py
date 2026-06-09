"""
职业规划 Agent（扩展模块）
负责为用户提供职业发展建议和规划
"""

from app.agents.base_agent import AgentInput, AgentOutput, BaseAgent


class CareerAgent(BaseAgent):
    """
    职业规划 Agent
    
    功能（后续迭代实现）：
    1. 根据用户背景推荐职业方向
    2. 分析技能差距并给出学习路径
    3. 提供行业趋势和薪资参考
    4. 面试准备建议
    """

    def __init__(self):
        super().__init__(name="career_agent")

    async def execute(self, agent_input: AgentInput) -> AgentOutput:
        """
        执行职业规划分析
        
        Args:
            agent_input: 包含用户的背景信息和问题
            
        Returns:
            AgentOutput: 包含职业建议的输出
        """
        content = agent_input.content

        # TODO: 获取用户简历信息（如有）
        # from app.database import SessionLocal
        # from app.models.resume import Resume
        # db = SessionLocal()
        # latest_resume = db.query(Resume).filter(
        #     Resume.user_id == agent_input.user_id
        # ).order_by(Resume.created_at.desc()).first()

        # TODO: RAG 检索职业规划相关知识
        # from app.services.rag_service import RAGService
        # rag = RAGService()
        # knowledge = await rag.search(f"职业规划 {content}")

        # TODO: 调用 LLM 生成职业规划建议
        # from app.services.llm_service import LLMService
        # llm = LLMService()
        # prompt = f"""作为职业规划顾问，请根据以下用户问题提供建议：
        # 用户问题：{content}
        # {"用户简历背景：" + resume.parsed_content if resume else ""}
        # {"相关知识库：" + knowledge if knowledge else ""}
        # 请从以下维度提供建议：
        # 1. 职业方向分析
        # 2. 技能提升路径
        # 3. 面试准备策略
        # 4. 行业趋势参考"""
        # advice = await llm.chat(prompt)

        return AgentOutput(
            content=(
                f"职业规划功能开发中。"
                f"完成后将提供：职业方向分析、技能差距评估、学习路径推荐、行业趋势参考。"
            ),
            agent_name=self.name,
            metadata={
                "status": "placeholder",
            },
        )
