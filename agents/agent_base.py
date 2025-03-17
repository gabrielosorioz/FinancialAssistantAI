from abc import ABC, abstractmethod

class Agent(ABC):
    """Classe base para agentes inteligentes."""

    def __init__(self, client, prompt: str, tools: list, store_context: bool = False, initial_context: list = None):
        """
        Inicializa o agente com os parâmetros necessários.

        Args:
            client: Instância do cliente OpenAI.
            prompt: Prompt do agente.
            tools: Lista de ferramentas associadas ao agente.
            store_context: Define se o agente deve armazenar contexto.
            initial_context: Lista inicial de mensagens de contexto.
        """
        self.client = client
        self.prompt = prompt
        self.tools = tools
        self.store_context = store_context
        self.context = initial_context if initial_context is not None else []

    @abstractmethod
    def process(self, user_input: str):
        """Processa a entrada do usuário e retorna a resposta."""
        pass

    def _build_messages(self, user_input: str):
        """Monta a lista de mensagens a serem enviadas ao modelo."""
        messages = [{"role": "system", "content": self.prompt}]

        if self.store_context:
            messages.extend(self.context)

        messages.append({"role": "user", "content": user_input})
        return messages

    def _update_context(self, user_input: str, response):
        """Atualiza o contexto armazenado, se ativado."""
        if self.store_context:
            self.context.append({"role": "user", "content": user_input})
            if hasattr(response, "content"):
                self.context.append({"role": "assistant", "content": response.content})

    def clear_context(self):
        """Limpa o contexto armazenado."""
        self.context = []