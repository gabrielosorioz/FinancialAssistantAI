import json
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
BASE_URL = "https://api.deepseek.com/v1"

class OpenAIClient:
    def __init__(self, api_key, base_url):
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def send_messages(self, messages, tools):
        """Envia uma mensagem ao modelo e captura a resposta."""
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools
        )
        return response.choices[0].message  # Retorna a mensagem gerada

class ExpenseExtractor:
    VALID_CATEGORIES = [
        "Alimentação", "Transporte", "Lazer", "Contas", "Vestuário", "Saúde", "Educação", "Delivery",
        "Assinaturas", "Moradia", "Saúde e Educação", "IPTU e IPVA", "Apostas Online", "Animais de Estimação",
        "Outros", "Supermercado", "Beleza e Cuidados Pessoais", "Seguros", "Presentes e Doações",
        "Eletrônicos e Tecnologia", "Mobilidade Urbana", "Impostos e Taxas", "Investimentos", "Eventos e Festas",
        "Serviços Domésticos", "Combustível", "Cultura e Arte", "Esportes", "Viagens", "Serviços Financeiros",
        "Serviços de Streaming e Entretenimento", "Serviços de Saúde Complementar", "Serviços de Limpeza e Higiene",
        "Serviços de Transporte de Cargas", "Serviços de Tecnologia e Informática"
    ]

    SYSTEM_PROMPT = f"""
    Você é um assistente especializado na extração de dados financeiros a partir de mensagens de texto.
    Sua tarefa é identificar e extrair informações de despesas com as seguintes categorias válidas: {', '.join(VALID_CATEGORIES)}
    e retornar uma resposta estritamente no formato JSON. Para cada despesa identificada,
    crie um objeto JSON com os seguintes campos:

    description: Uma string que descreve o item da despesa.
    value: Um número (float) representando o valor gasto.
    category: Uma string que indica a categoria da despesa.
    """

    TOOLS = [
        {
            "type": "function",
            "function": {
                "name": "parse_expense",
                "description": "Extrai informações sobre gastos de uma mensagem e retorna um JSON estruturado.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expenses": {
                            "type": "array",
                            "description": "Lista de gastos extraídos",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "description": {"type": "string", "description": "Descrição do item da despesa"},
                                    "value": {"type": "number",
                                              "description": "Valor gasto (número de ponto flutuante)"},
                                    "category": {"type": "string", "description": "Categoria da despesa."}
                                },
                                "required": ["description", "value", "category"]
                            }
                        }
                    },
                    "required": ["expenses"]
                }
            }
        }
    ]

    def __init__(self, client):
        self.client = client

    def extract_expenses(self, user_message):
        """Extrai as despesas de um texto de entrada."""
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]

        response_message = self.client.send_messages(messages, self.TOOLS)

        if response_message.tool_calls:
            json_data = json.loads(response_message.tool_calls[0].function.arguments)
            expenses = [Expense.from_dict(expense_dict) for expense_dict in json_data["expenses"]]
            return expenses

        return {"expenses": []}

class ExpenseFileHandler:
    @staticmethod
    def save_to_json(expenses, filename="expenses.json"):
        """Salva os dados extraídos em um arquivo JSON."""
        expenses_dict = {"expenses": [expense.to_dict() for expense in expenses]}
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(expenses_dict, file, ensure_ascii=False, indent=2)

    @staticmethod
    def print_expenses(expenses):
        """Imprime os gastos extraídos."""
        print("Arquivo 'expenses.json' gerado com os seguintes dados:")
        for expense in expenses:
            print(
                f"- Descrição: {expense.description}, Valor: R$ {expense.value}, Categoria: {expense.category}")

class Expense:
    def __init__(self, description, value, category):
        self.description = description
        self.value = float(value)  # Garantindo que o valor seja um float
        self.category = category

    def __repr__(self):
        return f"Expense(description='{self.description}', value={self.value}, category='{self.category}')"

    def to_dict(self):
        """Converte o objeto Expense para um dicionário."""
        return {
            "description": self.description,
            "value": self.value,
            "category": self.category
        }

    @classmethod
    def from_dict(cls, expense_dict):
        """Cria um objeto Expense a partir de um dicionário."""
        return cls(
            description=expense_dict["description"],
            value=expense_dict["value"],
            category=expense_dict["category"]
        )

if __name__ == "__main__":

    client = OpenAIClient(DEEPSEEK_API_KEY, BASE_URL)
    extractor = ExpenseExtractor(client)
    file_handler = ExpenseFileHandler()

    user_message = "Gastei 200 reais no supermercado."
    expenses = extractor.extract_expenses(user_message)

    file_handler.save_to_json(expenses)
    file_handler.print_expenses(expenses)
