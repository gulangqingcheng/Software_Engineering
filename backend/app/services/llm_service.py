"""
LLM 调用服务
封装 OpenAI 兼容 API 调用（DeepSeek），支持普通调用、流式调用和思考模式
"""

from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from app.config import settings


class LLMService:
    """
    LLM 调用服务

    支持 OpenAI 兼容 API（DeepSeek 等），可通过 .env 配置切换不同模型。
    支持思考模式（reasoning_content），流式输出时区分思考过程和正式回复。
    """

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            timeout=settings.LLM_TIMEOUT,
        )
        self.model = settings.LLM_MODEL_NAME
        self.thinking_enabled = settings.LLM_THINKING_ENABLED
        self.reasoning_effort = settings.LLM_REASONING_EFFORT

    def _build_extra_body(self) -> dict[str, Any]:
        """构建 DeepSeek 思考模式所需的 extra_body 参数"""
        if not self.thinking_enabled:
            return {}
        return {"thinking": {"type": "enabled"}}

    def _build_create_kwargs(
        self,
        full_messages: list[dict[str, str]],
        stream: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """构建统一的 API 调用参数

        DeepSeek 官方示例中 reasoning_effort 是顶层参数，但需要 openai>=1.66。
        为兼容当前 SDK 1.50，统一通过 extra_body 透传所有 DeepSeek 专有参数。
        """
        create_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": full_messages,
            "max_tokens": max_tokens or settings.LLM_MAX_TOKENS,
        }

        if stream:
            create_kwargs["stream"] = True

        # DeepSeek 思考模式参数（全部通过 extra_body 透传）
        if self.thinking_enabled:
            create_kwargs["extra_body"] = {
                "thinking": {"type": "enabled"},
                "reasoning_effort": self.reasoning_effort,
            }
        else:
            create_kwargs["temperature"] = temperature or settings.LLM_TEMPERATURE

        return create_kwargs

    async def chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs,
    ) -> str:
        """
        普通对话调用（非流式）

        Args:
            messages: 对话消息列表 [{"role": "user", "content": "..."}]
            system_prompt: 系统提示词
            temperature: 温度参数（越高越随机）
            max_tokens: 最大输出 Token 数

        Returns:
            str: AI 回复内容（不含思考过程）
        """
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        create_kwargs = self._build_create_kwargs(
            full_messages, stream=False, temperature=temperature, max_tokens=max_tokens
        )

        response = await self.client.chat.completions.create(**create_kwargs)

        return response.choices[0].message.content or ""

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[dict[str, str]]:
        """
        流式对话调用

        支持 DeepSeek 思考模式：
        - 思考阶段 yield {"type": "thinking", "content": "..."}
        - 回复阶段 yield {"type": "content", "content": "..."}

        Args:
            messages: 对话消息列表
            system_prompt: 系统提示词
            temperature: 温度参数
            max_tokens: 最大输出 Token 数

        Yields:
            dict: {"type": "thinking"|"content", "content": "..."}
        """
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        create_kwargs = self._build_create_kwargs(
            full_messages, stream=True, temperature=temperature, max_tokens=max_tokens
        )

        stream = await self.client.chat.completions.create(**create_kwargs)

        async for chunk in stream:
            delta = chunk.choices[0].delta

            # DeepSeek 思考模式：reasoning_content 在 delta 中
            reasoning = getattr(delta, "reasoning_content", None)
            if reasoning:
                yield {"type": "thinking", "content": reasoning}

            # 正式回复内容
            content = getattr(delta, "content", None)
            if content:
                yield {"type": "content", "content": content}

    async def chat_json(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float | None = None,
    ) -> dict | list:
        """
        对话调用并返回 JSON 格式结果

        Args:
            messages: 对话消息列表
            system_prompt: 系统提示词（会自动附加 JSON 格式要求）
            temperature: 温度参数

        Returns:
            dict | list: 解析后的 JSON 结果
        """
        import json

        json_instruction = system_prompt or ""
        json_instruction += "\n请以 JSON 格式返回结果，不要包含其他内容。"

        raw = await self.chat(
            messages=messages,
            system_prompt=json_instruction,
            temperature=temperature,
        )

        # 尝试提取 JSON（处理可能的 markdown 代码块包裹）
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        return json.loads(raw)

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        获取文本的 Embedding 向量

        Args:
            texts: 文本列表

        Returns:
            list[list[float]]: 对应的向量列表
        """
        response = await self.client.embeddings.create(
            model=settings.EMBEDDING_MODEL,
            input=texts,
        )
        return [item.embedding for item in response.data]
