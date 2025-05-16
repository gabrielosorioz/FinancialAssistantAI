from typing import Dict, List, Any, Optional, Type
from datetime import datetime
from pydantic import BaseModel, Field, UUID4
import uuid
#
# from squadai.agents import BaseAgent
# from squadai.tasks import Task
from squadai.tools import BaseTool, ToolCall


class ToolUsage(BaseModel):
    """
    Classe que registra e gerencia o uso de ferramentas durante a execução de tarefas.
    Permite rastrear quais ferramentas foram usadas, com quais argumentos e quais resultados foram obtidos.
    """
    id: UUID4 = Field(default_factory=uuid.uuid4, frozen=True)
    task_id: Optional[UUID4] = Field(description="Task Related to the use of tools", default=None)
    agent_id: Optional[UUID4] = Field(description="Agent who executed the tool", default=None)
    tool_calls: List[ToolCall] = Field(default_factory=[], description="List of tools called")
    created_at: datetime = Field(default_factory=datetime.now, description="Date and time of usage")

    @property
    def tool_names(self) -> List[str]:
        """Lista com os nomes das ferramentas usadas."""
        return [call.tool_name for call in self.tool_calls]

    @property
    def summary(self) -> Dict[str, Any]:
        """Resumo do uso de ferramentas em formato de dicionário."""
        return {
            "id": str(self.id),
            "task_id": str(self.task_id) if self.task_id else None,
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "tool_calls": [
                {
                    "tool_name": call.tool_name,
                    "arguments": call.arguments,
                    "result_type": type(call.result).__name__,
                    "result": call.result,
                    "success": True if call.result is not None else False
                }
                for call in self.tool_calls
            ],
            "created_at": self.created_at.isoformat(),
            "total_calls": len(self.tool_calls)
        }

    def add_tool_call(self, tool_call: ToolCall) -> None:
        """Adiciona uma chamada de ferramenta ao registro."""
        self.tool_calls.append(tool_call)

    def get_results_by_tool(self, tool_name: str) -> List[Any]:
        """Retorna todos os resultados de chamadas para uma ferramenta específica."""
        return [call.result for call in self.tool_calls if call.tool_name == tool_name]

    def get_last_result(self, tool_name: Optional[str] = None) -> Any:
        """Retorna o resultado da última chamada de ferramenta (ou da ferramenta específica)."""
        if not self.tool_calls:
            return None

        if tool_name:
            filtered_calls = [call for call in self.tool_calls if call.tool_name == tool_name]
            return filtered_calls[-1].result if filtered_calls else None

        return self.tool_calls[-1].result

    def has_tool_call(self, tool_name: str) -> bool:
        """Verifica se uma ferramenta específica foi chamada."""
        return any(call.tool_name == tool_name for call in self.tool_calls)

    def filter_successful_calls(self) -> List[ToolCall]:
        """Retorna apenas as chamadas de ferramentas que foram bem-sucedidas (com resultados não nulos)."""
        return [call for call in self.tool_calls if call.result is not None]

    def to_dict(self) -> Dict[str, Any]:
        """Converte o registro de uso de ferramentas para um dicionário."""
        return {
            "id": str(self.id),
            "task_id": str(self.task_id) if self.task_id else None,
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "tool_calls": [
                {
                    "tool_name": call.tool_name,
                    "arguments": call.arguments,
                    "result": call.result
                }
                for call in self.tool_calls
            ],
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_tool_calls(cls,
                        tool_calls: List[ToolCall],
                        task_id: Optional[UUID4] = None,
                        agent_id: Optional[UUID4] = None) -> "ToolUsage":
        """Cria um objeto ToolUsage a partir de uma lista de ToolCalls."""
        return cls(
            task_id=task_id,
            agent_id=agent_id,
            tool_calls=tool_calls
        )