import os
from openai import OpenAI
from dotenv import load_dotenv
from agents import ExpenseExtractorAgent, FeedbackAgent
from agents.expense_extractor import ProcessResult
from repository import UserRepository,ExpenseRepository

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

    user_repo = UserRepository()
    expense_repo = ExpenseRepository()
    user = user_repo.get_by_id(1)

    if not user:
        user = user_repo.create(name="João", email="joao@example.com")

    client = OpenAIClient(DEEPSEEK_API_KEY, BASE_URL)
    expense_ext_agent = ExpenseExtractorAgent(client=client, user=user)


    result: ProcessResult = expense_ext_agent.process("Gastei 30,,50 fastfood 10 99 coca cola e 30 20 baseado")

    print(FeedbackAgent.generate_feedback(result))

    if result.expenses:
        for expense in result.expenses:
            expense_repo.create(expense,user)
    elif result.response:
        print(f"Resposta do agente: {result.response}")