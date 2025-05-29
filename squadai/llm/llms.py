from dotenv import load_dotenv
from litellm import completion
from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper
from litellm.types.utils import ModelResponse
from .base_llm import BaseLLM
load_dotenv(override=True)

class DeepSeekLLM(BaseLLM):

    def call(self, messages, tools) ->  ModelResponse | CustomStreamWrapper:
        response = completion(
            model="deepseek/deepseek-chat",
            messages=messages,
            tools=tools,
        )
        return response