from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from .base_tool import BaseTool


class IncomeItem(BaseModel):
    description: str = Field(..., description="Descrição da fonte de renda")
    value: float = Field(..., description="Valor recebido")
    source: str = Field(..., description="Origem da receita")
    recurring: bool = Field(False, description="Indica se é recorrente (ex: salário mensal)")
    notes: Optional[str] = Field(None, description="Observações adicionais úteis")

class IncomeItemList(BaseModel):
    incomes: List[IncomeItem] = Field(..., description="Lista de fontes de renda")


class ParserIncomeTool(BaseTool):
    name: str = "parse_income"
    description: str = "Extrai informações sobre rendimentos de uma mensagem e retorna um JSON estruturado."

    def _run(self, incomes: List[IncomeItem]) -> Dict:
        # Implementação específica
        return {"incomes": [income.model_dump() for income in incomes]}
