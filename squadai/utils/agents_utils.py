from typing import List, Any, Optional, Dict

from squadai.tools import BaseTool


def parse_tools(tools: List[BaseTool]) -> List[Dict[str,Any]]:
    """
    Valida e formata as ferramentas para uso com o LLM.

    Este método garante que todas as ferramentas sejam instâncias válidas de BaseTool
    e as converte para o formato esperado pelo LLM (ex: função chamável da OpenAI).

    Args:
        tools: Lista de ferramentas a serem preparadas.

    Returns:
        Lista de ferramentas formatadas para o LLM.
    """
    parsed_tools = []

    for tool in tools:
        if not isinstance(tool, BaseTool):
            raise ValueError(f"Ferramenta inválida: {tool}. Todas devem ser instâncias de BaseTool.")
        try:
            parsed_tool: Dict[str,Any] = tool.to_openai_function()
            parsed_tools.append(parsed_tool)
        except Exception as e:
            print(f"Erro ao formatar ferramenta {tool.name}: {e}")

    return parsed_tools


def format_message_for_llm(prompt: str,
                           role: str = "user",
                           tool_call_id: Optional[str] = None) -> Dict[str, str]:

    prompt = prompt.rstrip()
    message = {"role": role,"content": prompt}

    if role == "tool" and tool_call_id:
        message["tool_call_id"] = tool_call_id

    return message


def render_text_description_and_args(
        tools: List[BaseTool],
) -> str:
    """Render the tool name, description, and args in plain text.

        search: This tool is used for search, args: {"query": {"type": "string"}}
        calculator: This tool is used for math, \
        args: {"expression": {"type": "string"}}
    """
    tool_strings = []
    for tool in tools:
        tool_strings.append(tool.description)

    return "\n".join(tool_strings)