"""
Agent 基类模块
定义所有 Agent 必须实现的接口规范和通用功能
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AgentInput:
    """Agent 输入数据结构"""
    user_id: int
    conversation_id: int
    content: str
    message_type: str = "text"
    context: dict[str, Any] = field(default_factory=dict)
    """附加上下文信息，例如简历ID、录音ID等"""


@dataclass
class AgentOutput:
    """Agent 输出数据结构"""
    content: str
    agent_name: str
    metadata: dict[str, Any] = field(default_factory=dict)
    """输出元数据，例如意图识别结果、参考来源等"""
    tokens_used: int = 0
    latency_ms: int = 0
    status: str = "success"
    error_msg: str | None = None


class BaseAgent(ABC):
    """
    Agent 抽象基类
    所有具体 Agent 必须继承此类并实现 execute 方法
    
    职责：
    1. 定义统一的输入输出接口
    2. 提供 Agent 调用日志记录
    3. 提供 Token 消耗统计
    """

    def __init__(self, name: str):
        self.name = name
        self.total_calls: int = 0
        self.total_tokens: int = 0

    @abstractmethod
    async def execute(self, agent_input: AgentInput) -> AgentOutput:
        """
        执行 Agent 核心逻辑
        
        Args:
            agent_input: 标准化的输入数据
            
        Returns:
            AgentOutput: 标准化的输出数据
        """
        pass

    async def run(self, agent_input: AgentInput) -> AgentOutput:
        """
        运行 Agent（带日志记录和计时）
        子类不应覆盖此方法，而是实现 execute
        
        Args:
            agent_input: 标准化的输入数据
            
        Returns:
            AgentOutput: 标准化的输出数据
        """
        start_time = time.perf_counter()

        try:
            output = await self.execute(agent_input)
            output.latency_ms = int((time.perf_counter() - start_time) * 1000)

            # 更新统计信息
            self.total_calls += 1
            self.total_tokens += output.tokens_used

            await self._log_to_db(agent_input, output)

            return output

        except Exception as e:
            latency = int((time.perf_counter() - start_time) * 1000)
            output = AgentOutput(
                content=f"处理出错: {str(e)}",
                agent_name=self.name,
                latency_ms=latency,
                status="failed",
                error_msg=str(e),
            )
            await self._log_to_db(agent_input, output)
            return output

    async def _log_to_db(self, agent_input: AgentInput, output: AgentOutput):
        """将 Agent 调用记录写入数据库日志表"""
        try:
            from app.database import SessionLocal
            from app.models.agent_log import AgentLog

            db = SessionLocal()
            try:
                log = AgentLog(
                    conversation_id=agent_input.conversation_id,
                    agent_name=self.name,
                    input_tokens=None,
                    output_tokens=output.tokens_used or None,
                    latency_ms=output.latency_ms,
                    status=output.status,
                    error_msg=output.error_msg,
                )
                db.add(log)
                db.commit()
            finally:
                db.close()
        except Exception:
            # 日志写入失败不能影响主流程。
            pass

    def get_stats(self) -> dict[str, Any]:
        """获取 Agent 运行统计"""
        return {
            "name": self.name,
            "total_calls": self.total_calls,
            "total_tokens": self.total_tokens,
        }
