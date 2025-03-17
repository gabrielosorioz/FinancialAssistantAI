import os
from openai import OpenAI
from dotenv import load_dotenv
from agents import ExpenseExtractorAgent
from repository import UserRepository,ExpenseRepository
from models import User, Expense

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

    # 1. Criar ou buscar um usuário
    user_repo = UserRepository()
    user = user_repo.get_by_id(1)

    if not user:
        user = user_repo.create(name="João", email="joao@example.com")
        print(f"Novo usuário criado: {user}")
    else:
        print(f"Usuário encontrado: {user}")

    client = OpenAIClient(DEEPSEEK_API_KEY, BASE_URL)
    expense_ext_agent = ExpenseExtractorAgent(client=client, user=user)

    user_message = "Gastei 200 reais no supermercado e 50 reais em transporte."
    print(f"\nProcessando mensagem: '{user_message}'")

    # 4. Processar a mensagem para extrair despesas
    expenses = expense_ext_agent.process(user_message)
    print(f"Despesas extraídas: {len(expenses)}")

    # 5. Criar repositório de despesas
    expense_repo = ExpenseRepository()

    # 6. Salvar cada despesa no banco de dados
    saved_expenses = []
    for expense in expenses:
        # Extrai os dados do objeto Expense
        expense_data = {
            "description": expense.description,
            "value": expense.value,
            "category": expense.category
        }

        # Usa o repositório para criar a despesa
        saved_expense = expense_repo.create(expense_data, user)
        saved_expenses.append(saved_expense)
        print(f"Despesa salva: {saved_expense}")

    # 7. Confirmar que todas as despesas foram salvas
    print(f"\nTotal de despesas salvas: {len(saved_expenses)}")

    all_user_expenses = user_repo.get_expenses(user.id)
    print(f"\nTodas as despesas do usuário {user.name}:")
    for i, exp in enumerate(all_user_expenses, 1):
        print(f"{i}. {exp.description}: R${exp.value:.2f} - {exp.category}")



