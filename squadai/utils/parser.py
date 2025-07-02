"""Parser para converter respostas de ferramentas OpenAI de volta para schemas Pydantic."""

import json
import logging
from typing import Any, Dict, List, Optional, Type, Union
from pydantic import BaseModel, ValidationError
logger = logging.getLogger(__name__)


class ToolParsingError(Exception):
    """Exceção específica para erros de parsing de ferramentas."""
    pass


class OpenAIToolResponseParser:
    """Parser para converter respostas de tool calling de volta para modelos Pydantic."""

    def __init__(self, pydantic_model: Type[BaseModel]):
        """
        Inicializa o parser com o modelo Pydantic alvo.

        Args:
            pydantic_model: O modelo Pydantic que define a estrutura esperada
        """
        if not self._is_valid_pydantic_model(pydantic_model):
            raise ValueError(
                f"Input deve ser uma subclasse de BaseModel. Recebido: {type(pydantic_model)}"
            )

        self.pydantic_model = pydantic_model
        self.model_name = pydantic_model.__name__

    def parse_tool_response(self, tool_arguments: Union[str, Dict[str, Any]], strict: bool = False) -> BaseModel:
        """
        Converte argumentos da ferramenta para instância do modelo Pydantic.

        Args:
            tool_arguments: Argumentos retornados pela LLM (JSON string ou dict)
            strict: Se True, comporta-se como parse_obj (sem recuperação de erros)

        Returns:
            Instância do modelo Pydantic preenchida

        Raises:
            ToolParsingError: Em caso de erro no parsing
        """
        try:
            # Converter string JSON para dict se necessário
            if isinstance(tool_arguments, str):
                try:
                    parsed_args = json.loads(tool_arguments)
                except json.JSONDecodeError as e:
                    raise ToolParsingError(f"Argumentos não são JSON válido: {str(e)}") from e
            elif isinstance(tool_arguments, dict):
                parsed_args = tool_arguments
            else:
                raise ToolParsingError(f"Argumentos devem ser string JSON ou dict. Recebido: {type(tool_arguments)}")

            # Modo estrito = como parse_obj
            if strict:
                try:
                    return self.pydantic_model.model_validate(parsed_args)
                except ValidationError as e:
                    error_details = self._format_validation_error(e, parsed_args)
                    raise ToolParsingError(f"Validação falhou: {error_details}") from e

            return self._create_model_instance(parsed_args)

        except Exception as e:
            if isinstance(e, ToolParsingError):
                raise
            raise ToolParsingError(f"Erro inesperado ao fazer parsing: {str(e)}") from e

    def parse_multiple_tool_responses(self, tool_calls: List[Dict[str, Any]]) -> List[BaseModel]:
        """
        Processa múltiplas chamadas de ferramentas.

        Args:
            tool_calls: Lista de chamadas de ferramentas da LLM

        Returns:
            Lista de instâncias do modelo Pydantic
        """
        results = []

        for i, tool_call in enumerate(tool_calls):
            try:
                # Extrair argumentos da chamada da ferramenta
                if isinstance(tool_call, dict):
                    # Formato típico: {"function": {"arguments": "..."}}
                    if "function" in tool_call and "arguments" in tool_call["function"]:
                        arguments = tool_call["function"]["arguments"]
                    # Formato alternativo: {"arguments": "..."}
                    elif "arguments" in tool_call:
                        arguments = tool_call["arguments"]
                    else:
                        logger.warning(f"Formato de tool_call não reconhecido no índice {i}: {tool_call}")
                        continue
                else:
                    logger.warning(f"Tool call no índice {i} não é um dict: {type(tool_call)}")
                    continue

                parsed_result = self.parse_tool_response(arguments)
                results.append(parsed_result)

            except Exception as e:
                logger.error(f"Erro ao processar tool call {i}: {str(e)}")
                continue

        return results

    def _create_model_instance(self, data: Dict[str, Any]) -> BaseModel:
        """
        Cria instância do modelo Pydantic com validação robusta.

        Args:
            data: Dados para popular o modelo

        Returns:
            Instância validada do modelo
        """
        try:
            # Tentar criar instância diretamente
            return self.pydantic_model.model_validate(data)

        except ValidationError as e:
            # Tentar recuperação com limpeza de dados
            cleaned_data = self._clean_and_fix_data(data, e)

            try:
                return self.pydantic_model.model_validate(cleaned_data)
            except ValidationError as retry_error:
                # Criar mensagem de erro detalhada
                error_details = self._format_validation_error(retry_error, data)
                raise ToolParsingError(
                    f"Falha na validação do modelo {self.model_name}: {error_details}"
                ) from retry_error

    def _clean_and_fix_data(self, data: Dict[str, Any], validation_error: ValidationError) -> Dict[str, Any]:
        """
        Tenta limpar e corrigir dados com base nos erros de validação.

        Args:
            data: Dados originais
            validation_error: Erro de validação original

        Returns:
            Dados limpos
        """
        cleaned_data = data.copy()

        # Obter schema do modelo para referência
        model_schema = self.pydantic_model.model_json_schema()
        model_properties = model_schema.get("properties", {})

        for error in validation_error.errors():
            field_path = error.get("loc", ())
            error_type = error.get("type", "")

            if not field_path:
                continue

            field_name = field_path[0] if field_path else None

            try:
                # Correções específicas por tipo de erro
                if error_type == "missing":
                    # Campo obrigatório ausente - usar valor padrão se disponível
                    if field_name in model_properties:
                        default_value = self._get_default_value_for_field(field_name, model_properties[field_name])
                        if default_value is not None:
                            cleaned_data[field_name] = default_value

                elif error_type in ["type_error", "value_error"]:
                    # Erro de tipo/valor - tentar conversão
                    if field_name and field_name in cleaned_data:
                        field_schema = model_properties.get(field_name, {})
                        converted_value = self._convert_field_value(
                            cleaned_data[field_name],
                            field_schema
                        )
                        if converted_value is not None:
                            cleaned_data[field_name] = converted_value

                elif error_type == "extra_forbidden":
                    if field_name and field_name in cleaned_data:
                        del cleaned_data[field_name]

            except Exception as e:
                logger.warning(f"Erro ao limpar campo '{field_name}': {str(e)}")
                continue

        return cleaned_data

    def _get_default_value_for_field(self, field_name: str, field_schema: Dict[str, Any]) -> Any:
        """Obtém valor padrão para um campo baseado no schema."""
        field_type = field_schema.get("type", "string")
        default_values = {
            "string": "",
            "integer": 0,
            "number": 0.0,
            "boolean": False,
            "array": [],
            "object": {}
        }

        return default_values.get(field_type)

    def _convert_field_value(self, value: Any, field_schema: Dict[str, Any]) -> Optional[Any]:
        """Tenta converter valor para o tipo esperado."""
        expected_type = field_schema.get("type", "string")

        try:
            if expected_type == "string" and not isinstance(value, str):
                return str(value)
            elif expected_type == "integer" and not isinstance(value, int):
                if isinstance(value, (float, str)):
                    return int(float(value))
            elif expected_type == "number" and not isinstance(value, (int, float)):
                if isinstance(value, str):
                    return float(value)
            elif expected_type == "boolean" and not isinstance(value, bool):
                if isinstance(value, str):
                    return value.lower() in ("true", "1", "yes", "on")
                return bool(value)
            elif expected_type == "array" and not isinstance(value, list):
                if isinstance(value, str):
                    # Tentar parsear como JSON
                    try:
                        parsed = json.loads(value)
                        return parsed if isinstance(parsed, list) else [parsed]
                    except:
                        return [value]
                return [value]
        except Exception:
            pass

        return None

    def _format_validation_error(self, error: ValidationError, original_data: Dict[str, Any]) -> str:
        """Formata erro de validação de forma mais legível."""
        error_messages = []

        for err in error.errors():
            field_path = " -> ".join(str(loc) for loc in err.get("loc", []))
            error_type = err.get("type", "unknown")
            message = err.get("msg", "Erro de validação")

            error_messages.append(f"Campo '{field_path}': {message} (tipo: {error_type})")

        return "; ".join(error_messages)

    def _is_valid_pydantic_model(self, obj: Any) -> bool:
        """Verifica se o objeto é um modelo Pydantic válido."""
        try:
            return (
                    isinstance(obj, type) and
                    issubclass(obj, BaseModel) and
                    hasattr(obj, 'model_json_schema')
            )
        except TypeError:
            return False


# Classe utilitária para uso mais simples
class ToolResponseParserFactory:
    """Factory para criar parsers de resposta de ferramentas."""

    @staticmethod
    def create_parser(pydantic_model: Type[BaseModel]) -> OpenAIToolResponseParser:
        """
        Cria um parser para o modelo Pydantic especificado.

        Args:
            pydantic_model: Modelo Pydantic alvo

        Returns:
            Parser configurado
        """
        return OpenAIToolResponseParser(pydantic_model)

    @staticmethod
    def parse_single_response(
            pydantic_model: Type[BaseModel],
            tool_arguments: Union[str, Dict[str, Any]]
    ) -> BaseModel:
        """
        Método de conveniência para parsing único.

        Args:
            pydantic_model: Modelo Pydantic alvo
            tool_arguments: Argumentos da ferramenta

        Returns:
            Instância do modelo preenchida
        """
        parser = ToolResponseParserFactory.create_parser(pydantic_model)
        return parser.parse_tool_response(tool_arguments)
