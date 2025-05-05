import os
from dotenv import load_dotenv
from openai import OpenAI
from typing import Any
from .base_llm import BaseLLM
from pydantic import Field


class DeepSeekLLM(BaseLLM):
    """Cliente para comunicação com a API OpenAI."""
    base_url: str = "https://api.deepseek.com/v1"
    api_key: str = os.getenv('DEEPSEEK_API_KEY')

    # Use Field to exclude the client from serialization
    llm_client: Any = Field(default=None, exclude=True)

    def __init__(self, **data):
        super().__init__(**data)
        load_dotenv()
        self.llm_client = OpenAI(
            api_key="sk-fa1a818e89cc472a986029a27740052f",
            base_url=self.base_url
        )

    def call(self, messages, tools) -> Any:
        response = self.llm_client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools
        )
        return response.choices[0].message