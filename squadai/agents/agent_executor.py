import uuid
from typing import Dict, List, Optional, Any

from pydantic import BaseModel

from squadai.agents import BaseAgent
from squadai.llm import BaseLLM
from squadai.tasks import Task
from squadai.tools import BaseTool, ToolCall, ToolUsage
from squadai.utils.agents_utils import format_message_for_llm
from squadai.utils.agents_utils import parse_tools

class AgentExecutor:
    def __init__(
        self,
        agent: BaseAgent,
        task: Task,
        llm: BaseLLM,
        prompt: dict[str, str],
        tools: List[BaseTool],
        memory: bool = False,
        messages: List[Dict[str, str]] = None,
        tool_calls: List[ToolCall] = None,
        tool_usages: List[ToolUsage] = None
    ):
        self.id = uuid.uuid4()
        self.agent = agent
        self.task = task
        self.llm = llm
        self.prompt = prompt
        self.tools = tools if tools is not None else []
        self.memory = memory
        self.messages = messages if messages is not None else []
        self.tool_calls = tool_calls if tool_calls is not None else []
        self.tool_usages = tool_usages if tool_usages is not None else []

    def invoke(self, inputs: Dict[str, str]) -> Dict[str, Any]:
        """
        Constrói a mensagem, envia ao modelo e atualiza o contexto.

        Args:
            'inputs': Dict['str','str']: Entrada do 'usuário' a ser processada

        Returns:
            Any: Resposta do modelo de linguagem
        """
        if "system" in self.prompt:
            system_prompt = self._format_prompt(self.prompt.get("system", ""), inputs)
            user_prompt = self._format_prompt(self.prompt.get("user", ""), inputs)
            self._append_message(system_prompt, role="system")
            self._append_message(user_prompt)
        try:
            parsed_tools = parse_tools(tools=self.tools)

            response = self.llm.call(
                messages=self.messages,
                tools=parsed_tools
            )

            # Adiciona a resposta como mensagem do assistente
            if hasattr(response, "content") and response.content:
                if self.memory:
                    self._append_message(response.content, role="assistant")

            # Processa chamadas de ferramentas
            if hasattr(response, 'tool_calls') and response.tool_calls:
                self._process_tool_calls(response.tool_calls)

            return response

        except Exception as e:
            raise

    def _append_message(self, text: str, role: str = "user", tool_call_id: Optional[str] = None) -> None:
        """
        Adiciona uma mensagem à lista de mensagens com o papel especificado.

        Args:
            text: Conteúdo da mensagem
            role: Papel da mensagem (user, assistant, system, tool)
            tool_call_id: ID da chamada de ferramenta (apenas para mensagens de role="tool")
        """

        if role == "tool" and not tool_call_id:
                return

        self.messages.append(format_message_for_llm(text, role=role, tool_call_id=tool_call_id))

    def clear_memory(self):
        """Limpa o contexto armazenado."""
        if self.memory:
            # Preserva a mensagem do sistema se existir
            system_message = next((msg for msg in self.messages if msg["role"] == "system"), None)
            self.messages = [system_message] if system_message else []

    def _process_tool_calls(self, tool_calls):
        """Processa as chamadas de ferramentas."""
        for call in tool_calls:
            try:
                # Encontra a ferramenta correspondente
                tool = next((t for t in self.tools if t.name == call.function.name), None)
                if not tool:
                    continue

                import json
                args = json.loads(call.function.arguments)
                result = tool.run(**args)

                tool_call = ToolCall(
                    tool= tool,
                    tool_name=call.function.name,
                    arguments=args,
                    result=result
                )
                self.tool_calls.append(tool_call)

                tool_usage = ToolUsage(
                    tool_calls=self.tool_calls,
                    agent_id=self.agent.id,
                    task_id=self.task.id
                )

                self.tool_usages.append(tool_usage)

                print(self.tool_usages[0].summary)

                result_str = json.dumps(result) if not isinstance(result, str) else result

                if self.memory:
                    self._append_message(result_str, role="tool", tool_call_id=call.id)

            except Exception as e:
                print(f"Erro {e}")

    def _format_prompt(self, prompt: str, inputs: Dict[str, str]) -> str:
        prompt = prompt.replace("{input}", inputs["input"])
        # prompt = prompt.replace("{tool_names}", inputs["tool_names"])
        # prompt = prompt.replace("{tools}", inputs["tools"])
        return prompt