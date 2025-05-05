import os
from dotenv import load_dotenv
from openai import OpenAI
from typing import Any
from pydantic import Field

from .base_llm import BaseLLM


class DeepSeekLLM(BaseLLM):
    """Cliente para comunicação com a API OpenAI compatível (DeepSeek)."""
    base_url: str = "https://api.deepseek.com/v1"
    api_key: str = Field(default=None, exclude=True)
    llm_client: Any = Field(default=None, exclude=True)

    def __init__(self, **data):
        load_dotenv()
        data.setdefault("api_key", os.getenv("DEEPSEEK_API_KEY"))

        if not data["api_key"]:
            raise ValueError("DEEPSEEK_API_KEY não encontrado no ambiente.")

        super().__init__(**data)

        self.llm_client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    def call(self, messages, tools=None) -> Any:
        response = self.llm_client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools or []
        )
        return response.choices[0].message
