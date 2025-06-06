from typing import Type, Dict, Any, Optional, Union, Set, get_origin, get_args
import logging
logger = logging.getLogger(__name__)
from pydantic import BaseModel

def generate_model_description(model: Type[BaseModel]) -> str:
    """
    Generate a string description of a Pydantic model's fields and their types.

    This function takes a Pydantic model class and returns a string that describes
    the model's fields and their respective types. The description includes handling
    of complex types such as `Optional`, `List`, and `Dict`, as well as nested Pydantic
    models.
    """

    def describe_field(field_type):
        origin = get_origin(field_type)
        args = get_args(field_type)

        if origin is Union or (origin is None and len(args) > 0):
            # Handle both Union and the new '|' syntax
            non_none_args = [arg for arg in args if arg is not type(None)]
            if len(non_none_args) == 1:
                return f"Optional[{describe_field(non_none_args[0])}]"
            else:
                return f"Optional[Union[{', '.join(describe_field(arg) for arg in non_none_args)}]]"
        elif origin is list:
            return f"List[{describe_field(args[0])}]"
        elif origin is dict:
            key_type = describe_field(args[0])
            value_type = describe_field(args[1])
            return f"Dict[{key_type}, {value_type}]"
        elif isinstance(field_type, type) and issubclass(field_type, BaseModel):
            return generate_model_description(field_type)
        elif hasattr(field_type, "__name__"):
            return field_type.__name__
        else:
            return str(field_type)

    fields = model.model_fields
    field_descriptions = [
        f'"{name}": {describe_field(field.annotation)}'
        for name, field in fields.items()
    ]
    return "{\n  " + ",\n  ".join(field_descriptions) + "\n}"


class SchemaConversionError(Exception):
    """Exceção específica para erros de conversão de schema."""
    pass

def convert_to_openai_tool(
        pydantic_model: Type[BaseModel],
        tool_name: Optional[str] = None,
        tool_description: Optional[str] = None,
        max_recursion_depth: int = 10
) -> Dict[str, Any]:
    """
    Converte um modelo Pydantic para ferramenta OpenAI com tratamento robusto.

    Args:
        pydantic_model: O modelo Pydantic que define a estrutura esperada
        tool_name: Nome personalizado para a ferramenta (opcional)
        tool_description: Descrição personalizada para a ferramenta (opcional)
        max_recursion_depth: Limite máximo de recursão para evitar stack overflow

    Returns:
        Dict contendo a definição da ferramenta no formato OpenAI function calling

    Raises:
        SchemaConversionError: Em caso de erro na conversão do schema
        ValueError: Se o input não for um modelo Pydantic válido
    """

    # Validação de entrada
    if not _is_valid_pydantic_model(pydantic_model):
        raise ValueError(
            f"Input deve ser uma subclasse de BaseModel. Recebido: {type(pydantic_model)}"
        )

    try:
        # Gerar nomes padrão
        model_name = pydantic_model.__name__
        default_tool_name = tool_name or f"parse_{model_name.lower()}"
        default_description = tool_description or f"Parse and structure data according to {model_name} schema"

        # Converter para schema OpenAI com detecção de ciclos
        converter = PydanticToOpenAIConverter(max_recursion_depth)
        schema = converter.convert(pydantic_model)

        # Validar schema resultante
        _validate_openai_schema(schema)

        # Criar definição da ferramenta
        function_definition = {
            "type": "function",
            "function": {
                "name": default_tool_name,
                "description": default_description,
                "parameters": schema
            }
        }

        return function_definition

    except Exception as e:
        logger.error(f"Erro ao converter modelo {pydantic_model.__name__}: {str(e)}")
        raise SchemaConversionError(f"Falha na conversão do schema: {str(e)}") from e


class PydanticToOpenAIConverter:
    """Conversor com detecção de ciclos e limite de recursão."""

    def __init__(self, max_depth: int = 10):
        self.max_depth = max_depth
        self.visited_refs: Set[str] = set()
        self.current_depth = 0

    def convert(self, model: Type[BaseModel]) -> Dict[str, Any]:
        """Converte modelo Pydantic para schema OpenAI."""
        self.visited_refs.clear()
        self.current_depth = 0

        try:
            # Obter schema JSON do Pydantic
            pydantic_schema = model.model_json_schema()
            return self._convert_schema(pydantic_schema, pydantic_schema.get("$defs", {}))
        except Exception as e:
            raise SchemaConversionError(f"Erro ao gerar schema do modelo: {str(e)}") from e

    def _convert_schema(self, schema: Dict[str, Any], definitions: Dict[str, Any]) -> Dict[str, Any]:
        """Converte schema recursivamente com proteção contra ciclos."""

        # Verificar limite de recursão
        if self.current_depth > self.max_depth:
            logger.warning(f"Limite de recursão atingido ({self.max_depth})")
            return {"type": "object", "description": "Schema truncado devido ao limite de recursão"}

        self.current_depth += 1

        try:
            # Schema base OpenAI
            openai_schema = {
                "type": "object",
                "properties": {},
                "required": []
            }

            # Processar propriedades
            properties = schema.get("properties", {})
            required_fields = schema.get("required", [])

            for field_name, field_info in properties.items():
                try:
                    # Resolver campo com detecção de ciclos
                    resolved_field = self._resolve_field_schema(field_info, definitions)
                    openai_schema["properties"][field_name] = resolved_field

                    # Adicionar aos campos obrigatórios
                    if field_name in required_fields:
                        openai_schema["required"].append(field_name)

                except Exception as e:
                    logger.warning(f"Erro ao processar campo '{field_name}': {str(e)}")
                    # Fallback para string em caso de erro
                    openai_schema["properties"][field_name] = {
                        "type": "string",
                        "description": f"Campo com erro de conversão: {str(e)}"
                    }

            return openai_schema

        finally:
            self.current_depth -= 1

    def _resolve_field_schema(self, field_schema: Dict[str, Any], definitions: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve schema de campo com detecção de ciclos."""

        # Tratar referências ($ref)
        if "$ref" in field_schema:
            ref_path = field_schema["$ref"]
            ref_name = ref_path.split("/")[-1]

            # Detectar ciclo
            if ref_name in self.visited_refs:
                logger.warning(f"Ciclo detectado em $ref: {ref_name}")
                return {
                    "type": "object",
                    "description": f"Referência circular detectada para {ref_name}"
                }

            # Processar referência
            if ref_name in definitions:
                self.visited_refs.add(ref_name)
                try:
                    resolved = self._resolve_field_schema(definitions[ref_name], definitions)
                    return resolved
                finally:
                    self.visited_refs.discard(ref_name)
            else:
                logger.warning(f"Referência não encontrada: {ref_name}")
                return {"type": "string", "description": f"Referência não resolvida: {ref_name}"}

        # Tratar arrays
        if field_schema.get("type") == "array":
            return self._handle_array_schema(field_schema, definitions)

        # Tratar objetos com propriedades (modelos aninhados)
        if field_schema.get("type") == "object" and "properties" in field_schema:
            return self._handle_object_schema(field_schema, definitions)

        # Tratar Enums
        if "enum" in field_schema:
            return self._handle_enum_schema(field_schema)

        # Tratar Union/anyOf/oneOf
        if any(key in field_schema for key in ["anyOf", "oneOf", "allOf"]):
            return self._handle_union_schema(field_schema, definitions)

        # Tipos básicos - limpar campos desnecessários
        return {
            k: v for k, v in field_schema.items()
            if k not in ["$ref", "title", "$defs"]
        }

    def _handle_array_schema(self, schema: Dict[str, Any], definitions: Dict[str, Any]) -> Dict[str, Any]:
        """Trata schemas de array."""
        result = {"type": "array"}

        if "items" in schema:
            try:
                result["items"] = self._resolve_field_schema(schema["items"], definitions)
            except Exception as e:
                logger.warning(f"Erro ao processar items do array: {str(e)}")
                result["items"] = {"type": "string"}

        if "description" in schema:
            result["description"] = schema["description"]

        return result

    def _handle_object_schema(self, schema: Dict[str, Any], definitions: Dict[str, Any]) -> Dict[str, Any]:
        """Trata schemas de objeto aninhado."""
        result = {
            "type": "object",
            "properties": {}
        }

        # Processar propriedades
        for prop_name, prop_schema in schema.get("properties", {}).items():
            try:
                result["properties"][prop_name] = self._resolve_field_schema(prop_schema, definitions)
            except Exception as e:
                logger.warning(f"Erro ao processar propriedade '{prop_name}': {str(e)}")
                result["properties"][prop_name] = {"type": "string"}

        # Campos obrigatórios
        if "required" in schema:
            result["required"] = schema["required"]

        # Descrição
        if "description" in schema:
            result["description"] = schema["description"]

        return result

    def _handle_enum_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Trata schemas de Enum."""
        result = {
            "type": "string",
            "enum": schema["enum"]
        }

        if "description" in schema:
            result["description"] = schema["description"]

        return result

    def _handle_union_schema(self, schema: Dict[str, Any], definitions: Dict[str, Any]) -> Dict[str, Any]:
        """Trata schemas de Union (anyOf/oneOf)."""

        # Para anyOf/oneOf, usar o primeiro tipo válido como fallback
        union_types = schema.get("anyOf", schema.get("oneOf", schema.get("allOf", [])))

        if not union_types:
            return {"type": "string", "description": "Union type sem opções válidas"}

        # Tentar usar o primeiro tipo não-null
        for union_type in union_types:
            if union_type.get("type") != "null":
                try:
                    return self._resolve_field_schema(union_type, definitions)
                except Exception:
                    continue

        # Fallback para string
        return {
            "type": "string",
            "description": f"Union type com {len(union_types)} opções"
        }


def _is_valid_pydantic_model(obj: Any) -> bool:
    """Verifica se o objeto é um modelo Pydantic válido."""
    try:
        return (
                isinstance(obj, type) and
                issubclass(obj, BaseModel) and
                hasattr(obj, 'model_json_schema')
        )
    except TypeError:
        return False


def _validate_openai_schema(schema: Dict[str, Any]) -> None:
    """Valida se o schema está no formato correto para OpenAI."""
    required_keys = ["type", "properties"]

    for key in required_keys:
        if key not in schema:
            raise SchemaConversionError(f"Schema inválido: chave '{key}' ausente")

    if schema["type"] != "object":
        raise SchemaConversionError(f"Schema deve ter type='object', encontrado: {schema['type']}")

    if not isinstance(schema["properties"], dict):
        raise SchemaConversionError("Propriedades do schema devem ser um dicionário")
