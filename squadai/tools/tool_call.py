from typing import Any, Dict, List

from pydantic import BaseModel

from squadai.tools import BaseTool


class ToolCall(BaseModel):
    tool: BaseTool
    tool_name: str
    arguments: Dict[str,Any]
    result: Any

    def __str__(self):
        return (
            f"ToolCall(tool_name={self.tool_name}, "
            f"arguments={self.arguments}, result={self.result})"
        )