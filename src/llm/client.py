"""
大模型统一客户端 - 支持 OpenAI / Claude / 本地模型
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class LLMClient:
    """大模型统一调用客户端"""

    PROVIDERS = ["openai", "anthropic", "local"]

    def __init__(self, provider: str = None, model: str = None):
        self.provider = provider or os.getenv("LLM_PROVIDER", "openai")
        self.model = model or os.getenv("LLM_MODEL", "gpt-4")
        self.logger = logging.getLogger(self.__class__.__name__)
        self._client = None
        self._init_client()

    def _init_client(self):
        """初始化模型客户端"""
        if self.provider == "openai":
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                self.logger.info(f"Initialized OpenAI client with model {self.model}")
            except ImportError:
                self.logger.error("openai package not installed. Run: pip install openai")

        elif self.provider == "anthropic":
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
                self.logger.info(f"Initialized Anthropic client with model {self.model}")
            except ImportError:
                self.logger.error("anthropic package not installed. Run: pip install anthropic")

        elif self.provider == "local":
            self.logger.info("Local model mode - using Ollama or vLLM")
            # TODO: 实现本地模型连接

    async def analyze(self, prompt: str, system_prompt: str = None) -> str:
        """
        调用大模型进行分析

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
        Returns:
            模型输出文本
        """
        if self._client is None:
            raise RuntimeError(f"LLM client not initialized for provider: {self.provider}")

        if self.provider == "openai":
            return await self._call_openai(prompt, system_prompt)
        elif self.provider == "anthropic":
            return await self._call_anthropic(prompt, system_prompt)
        else:
            raise NotImplementedError(f"Provider {self.provider} not implemented")

    async def _call_openai(self, prompt: str, system_prompt: str = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
        )
        return response.choices[0].message.content

    async def _call_anthropic(self, prompt: str, system_prompt: str = None) -> str:
        response = self._client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt or "你是一个专业的供应链风险分析专家。",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
