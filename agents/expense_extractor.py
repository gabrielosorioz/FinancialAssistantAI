from . import Agent
from models import Expense
import json

class ExpenseExtractorAgent(Agent):
    """Agente especializado em extração de despesas."""

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
                                    "value": {"type": "number", "description": "Valor gasto"},
                                    "category": {"type": "string", "description": "Categoria da despesa"}
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

    def __init__(self, client, user, store_context=False, initial_context=None):
        """Inicializa o agente com um cliente e um usuário específico."""
        super().__init__(
            client,
            self.SYSTEM_PROMPT,
            self.TOOLS,
            store_context,
            initial_context
        )
        self.user = user  # Armazena o usuário associado

    def process(self, user_input: str):
        """Extrai as despesas da entrada do usuário e vincula ao usuário do agente."""
        messages = self._build_messages(user_input)
        response = self.client.send_messages(messages, self.tools)
        self._update_context(user_input, response)

        if response.tool_calls:
            json_data = json.loads(response.tool_calls[0].function.arguments)

            expenses = [
                Expense.from_dict(expense_dict, self.user)
                for expense_dict in json_data["expenses"]
            ]
            return expenses

        return []