import logging
from abc import ABC, abstractmethod
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

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

    @abstractmethod
    def _process_tool_calls(self, response):
        """
        Processa as chamadas de ferramenta da resposta.
        Deve ser implementado por subclasses para lidar com ferramentas específicas.
        """
        pass

    def _get_response(self, user_input: str):
        """Constrói a mensagem, envia ao modelo e atualiza o contexto."""
        messages = self._build_messages(user_input)
        response = self.client.send_messages(messages, self.tools)
        self._log_response(user_input, response)
        self._update_context(user_input, response)
        return response

    def _log_response(self, user_input, response):
        """Registra as informações relevantes da resposta do agente."""
        logger.info("Entrada do usuário: %s", user_input)
        logger.info("Resposta recebida: %s", response)

        if hasattr(response, 'tool_calls') and response.tool_calls:
            logger.info("Chamadas de ferramenta detectadas:")
            for call in response.tool_calls:
                logger.info("Função: %s, Argumentos: %s", call.function.name, call.function.arguments)
        else:
            logger.warning("Nenhuma chamada de ferramenta detectada.")

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