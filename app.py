import os
from openai import OpenAI
from dotenv import load_dotenv
from agents import TaskCoordinatorAgent
# Carrega variáveis de ambiente
load_dotenv()
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
BASE_URL = "https://api.deepseek.com/v1"

class OpenAIClient:
    """Cliente para comunicação com a API OpenAI."""

    def __init__(self, api_key, base_url):
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def send_messages(self, messages, tools):
        """Envia uma mensagem ao modelo e captura a resposta."""
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools
        )
        return response.choices[0].message


if __name__ == "__main__":

    llmClient = OpenAIClient(
        api_key=DEEPSEEK_API_KEY,
        base_url=BASE_URL
    )

    TaskCoordinatorAgent(llmClient).process("Recebi R$ 3.000 de salário ontem e gastei R$ 200 com supermercado hoje.")