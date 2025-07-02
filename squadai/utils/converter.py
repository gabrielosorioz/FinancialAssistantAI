from typing import Set, get_origin, get_args
import logging
logger = logging.getLogger(__name__)
from typing import Type, Any, Dict, Union, List, Optional
import json
import logging
from pydantic import BaseModel, Field, ValidationError
from squadai.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)

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

                    openai_schema["properties"][field_name] = {
                        "type": "string",
                        "description": f"Campo com erro de conversão: {str(e)}"
                    }

            return openai_schema

        finally:
            self.current_depth -= 1

    def _resolve_field_schema(self, field_schema: Dict[str, Any], definitions: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve schema de campo com detecção de ciclos."""


        if "$ref" in field_schema:
            ref_path = field_schema["$ref"]
            ref_name = ref_path.split("/")[-1]


            if ref_name in self.visited_refs:
                logger.warning(f"Ciclo detectado em $ref: {ref_name}")
                return {
                    "type": "object",
                    "description": f"Referência circular detectada para {ref_name}"
                }

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


class PydanticParsingError(Exception):
    """Exceção específica para erros de parsing do PydanticParserTool."""
    pass




class PydanticParserTool(BaseTool):
    """
    Ferramenta para parsear dados não estruturados em objetos Pydantic validados.
    """

    target_model: Type[BaseModel] = Field(exclude=True)

    def __init__(self, target_model: Type[BaseModel], **kwargs):
        if not self._is_valid_pydantic_model(target_model):
            raise ValueError(f"target_model deve ser uma subclasse de BaseModel. Recebido: {type(target_model)}")

        model_name = target_model.__name__
        default_kwargs = {
            "name": kwargs.get("name", f"parse_{model_name.lower()}"),
            "description": kwargs.get("description",
                                      f"Parse and validate data according to {model_name} schema. "
                                      f"Converts unstructured data into structured {model_name} objects with validation."),
            "target_model": target_model
        }
        default_kwargs.update(kwargs)
        super().__init__(**default_kwargs)

    def _run(self, **kwargs) -> Dict[str, Any]:
        """
        Executa o parsing dos dados recebidos.
        """
        try:
            logger.info(f"Iniciando parsing com dados: {kwargs}")

            if not kwargs:
                raise PydanticParsingError("Nenhum dado recebido para parsing")

            strict_mode = kwargs.pop('strict_mode', False)
            return_dict = kwargs.pop('return_dict', False)

            processed_data = self._prepare_data_for_model(kwargs)

            model_instance = self._parse_to_model(processed_data, strict_mode)

            if return_dict:
                return model_instance.model_dump()
            else:
                return model_instance

        except Exception as e:
            logger.error(f"Erro no parsing: {str(e)}")
            raise PydanticParsingError(f"Falha no parsing: {str(e)}") from e

    def _prepare_data_for_model(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepara os dados recebidos com sanitização robusta.
        """
        # Se recebemos dados em string JSON, fazer parse
        if len(kwargs) == 1 and isinstance(list(kwargs.values())[0], str):
            single_value = list(kwargs.values())[0]
            try:
                parsed_data = json.loads(single_value)
                return self._sanitize_data_recursively(parsed_data)
            except json.JSONDecodeError:
                # Se não é JSON válido, tratar como string simples
                pass

        # Sanitizar dados recebidos
        return self._sanitize_data_recursively(kwargs)

    def _sanitize_data_recursively(self, data: Any) -> Any:
        """Sanitiza dados recursivamente para garantir compatibilidade."""
        if isinstance(data, dict):
            return {k: self._sanitize_data_recursively(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_data_recursively(item) for item in data]
        elif isinstance(data, str):
            # Tentar converter strings que parecem números
            if data.isdigit():
                return int(data)
            try:
                if '.' in data and data.replace('.', '').replace('-', '').isdigit():
                    return float(data)
            except:
                pass
            return data
        else:
            return data

    def _parse_to_model(self, data: Dict[str, Any], strict_mode: bool) -> BaseModel:
        """Faz o parsing dos dados para o modelo target."""
        try:
            return self.target_model.model_validate(data)
        except ValidationError as e:
            if strict_mode:
                error_details = self._format_validation_error(e, data)
                raise PydanticParsingError(f"Validação falhou em modo estrito: {error_details}") from e

            # Tentar recuperação
            return self._parse_with_recovery(data, e)

    def _parse_with_recovery(self, data: Dict[str, Any], original_error: ValidationError) -> BaseModel:
        """Tenta parsing com estratégia de recuperação defensiva."""
        logger.info(f"Iniciando recuperação para erros: {len(original_error.errors())} encontrados")

        # Estratégia 1: Limpar dados baseado nos erros específicos
        try:
            cleaned_data = self._clean_and_fix_data_defensively(data, original_error)
            return self.target_model.model_validate(cleaned_data)
        except ValidationError as e:
            logger.warning(f"Estratégia 1 falhou: {e}")

        # Estratégia 2: Usar apenas campos válidos + valores padrão
        try:
            safe_data = self._create_safe_data_from_model(data)
            return self.target_model.model_validate(safe_data)
        except ValidationError as e:
            logger.warning(f"Estratégia 2 falhou: {e}")

        # Estratégia 3: Criar instância mínima válida
        try:
            minimal_data = self._create_minimal_valid_instance()
            return self.target_model.model_validate(minimal_data)
        except ValidationError as final_error:
            error_details = self._format_validation_error(final_error, data)
            raise PydanticParsingError(
                f"Todas as estratégias de recuperação falharam: {error_details}"
            ) from final_error

    def _clean_and_fix_data_defensively(self, data: Dict[str, Any], validation_error: ValidationError) -> Dict[
        str, Any]:
        """Limpa dados com estratégia defensiva - remove campos problemáticos ao invés de tentar consertá-los."""
        cleaned_data = {}
        model_schema = self.target_model.model_json_schema()
        model_properties = model_schema.get("properties", {})
        required_fields = model_schema.get("required", [])

        # Mapear erros por campo
        error_fields = set()
        for error in validation_error.errors():
            field_path = error.get("loc", ())
            if field_path:
                error_fields.add(field_path[0])

        # Processar cada campo do modelo
        for field_name, field_schema in model_properties.items():
            if field_name in error_fields:
                # Campo com erro - tentar recuperação cautelosa
                if field_name in data:
                    converted_value = self._convert_field_value(data[field_name], field_schema)
                    if converted_value is not None:
                        cleaned_data[field_name] = converted_value
                    elif field_name in required_fields:
                        # Campo obrigatório - usar valor padrão
                        cleaned_data[field_name] = self._get_default_value_for_field(field_name, field_schema)
                elif field_name in required_fields:
                    # Campo obrigatório ausente
                    cleaned_data[field_name] = self._get_default_value_for_field(field_name, field_schema)
            else:
                # Campo sem erro - copiar se existir
                if field_name in data:
                    cleaned_data[field_name] = data[field_name]

        return cleaned_data

    def _create_safe_data_from_model(self, original_data: Dict[str, Any]) -> Dict[str, Any]:
        """Cria dados seguros usando apenas campos compatíveis + valores padrão."""
        safe_data = {}
        model_schema = self.target_model.model_json_schema()
        model_properties = model_schema.get("properties", {})
        required_fields = model_schema.get("required", [])

        for field_name, field_schema in model_properties.items():
            if field_name in original_data:

                converted = self._convert_field_value(original_data[field_name], field_schema)
                if converted is not None:
                    safe_data[field_name] = converted
                else:
                    safe_data[field_name] = self._get_default_value_for_field(field_name, field_schema)
            else:
                if field_name in required_fields:
                    safe_data[field_name] = self._get_default_value_for_field(field_name, field_schema)

        return safe_data

    def _create_minimal_valid_instance(self) -> Dict[str, Any]:
        """Cria instância mínima válida apenas com campos obrigatórios."""
        model_schema = self.target_model.model_json_schema()
        model_properties = model_schema.get("properties", {})
        required_fields = model_schema.get("required", [])

        minimal_data = {}
        for field_name in required_fields:
            if field_name in model_properties:
                minimal_data[field_name] = self._get_default_value_for_field(
                    field_name,
                    model_properties[field_name]
                )

        return minimal_data

    def _clean_and_fix_data(self, data: Dict[str, Any], validation_error: ValidationError) -> Dict[str, Any]:
        """Limpa e corrige dados com base nos erros de validação."""
        cleaned_data = data.copy()
        model_schema = self.target_model.model_json_schema()
        model_properties = model_schema.get("properties", {})

        for error in validation_error.errors():
            field_path = error.get("loc", ())
            error_type = error.get("type", "")

            if not field_path:
                continue

            field_name = field_path[0] if field_path else None

            try:
                if error_type == "missing":
                    if field_name in model_properties:
                        default_value = self._get_default_value_for_field(field_name, model_properties[field_name])
                        if default_value is not None:
                            cleaned_data[field_name] = default_value

                elif error_type in ["type_error", "value_error"]:
                    if field_name and field_name in cleaned_data:
                        field_schema = model_properties.get(field_name, {})
                        converted_value = self._convert_field_value(cleaned_data[field_name], field_schema)
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
        """Obtém valor padrão simples para um campo baseado apenas no tipo."""
        field_type = field_schema.get("type", "string")

        default_values = {
            "string": "",
            "integer": 0,
            "number": 0.0,
            "boolean": False,
            "array": [],
            "object": {}
        }

        return default_values.get(field_type, "")

    def _convert_field_value(self, value: Any, field_schema: Dict[str, Any]) -> Optional[Any]:
        """Converte valor para o tipo esperado com tratamento robusto de erros."""
        expected_type = field_schema.get("type", "string")

        if expected_type == "string" and isinstance(value, str):
            return value
        elif expected_type == "integer" and isinstance(value, int):
            return value
        elif expected_type == "number" and isinstance(value, (int, float)):
            return value
        elif expected_type == "boolean" and isinstance(value, bool):
            return value
        elif expected_type == "array" and isinstance(value, list):
            return value
        elif expected_type == "object" and isinstance(value, dict):
            return value

        try:
            if expected_type == "string":
                return str(value) if value is not None else ""

            elif expected_type == "integer":
                if isinstance(value, str):

                    cleaned = value.strip()
                    if cleaned.isdigit() or (cleaned.startswith('-') and cleaned[1:].isdigit()):
                        return int(cleaned)
                    try:
                        return int(float(cleaned))
                    except (ValueError, OverflowError):
                        return 0  # Valor padrão seguro
                elif isinstance(value, float):
                    return int(value)
                elif isinstance(value, bool):
                    return int(value)
                return 0

            elif expected_type == "number":
                if isinstance(value, str):
                    cleaned = value.strip().replace(',', '.')  # Tratar vírgula como decimal
                    try:
                        return float(cleaned)
                    except (ValueError, OverflowError):
                        return 0.0
                elif isinstance(value, (int, bool)):
                    return float(value)
                return 0.0

            elif expected_type == "boolean":
                if isinstance(value, str):
                    return value.lower().strip() in ("true", "1", "yes", "on", "sim", "verdadeiro")
                elif isinstance(value, (int, float)):
                    return bool(value)
                return False

            elif expected_type == "array":
                if isinstance(value, str):
                    # Tentar parsear como JSON
                    try:
                        parsed = json.loads(value)
                        return parsed if isinstance(parsed, list) else [parsed]
                    except json.JSONDecodeError:
                        # Dividir por vírgula como fallback
                        return [item.strip() for item in value.split(',') if item.strip()]
                elif value is None:
                    return []
                else:
                    return [value]

            elif expected_type == "object":
                if isinstance(value, str):
                    try:
                        parsed = json.loads(value)
                        return parsed if isinstance(parsed, dict) else {}
                    except json.JSONDecodeError:
                        return {}
                elif value is None:
                    return {}
                return {}

        except Exception as e:
            logger.warning(f"Erro na conversão de {value} para {expected_type}: {str(e)}")

        # Valores padrão seguros por tipo
        safe_defaults = {
            "string": "",
            "integer": 0,
            "number": 0.0,
            "boolean": False,
            "array": [],
            "object": {}
        }

        return safe_defaults.get(expected_type, None)

    def _format_validation_error(self, error: ValidationError, original_data: Dict[str, Any]) -> str:
        """Formata erro de validação."""
        error_messages = []
        for err in error.errors():
            field_path = " -> ".join(str(loc) for loc in err.get("loc", []))
            error_type = err.get("type", "unknown")
            message = err.get("msg", "Erro de validação")
            error_messages.append(f"Campo '{field_path}': {message} (tipo: {error_type})")
        return "; ".join(error_messages)

    @staticmethod
    def _is_valid_pydantic_model(obj: Any) -> bool:
        """Verifica se é um modelo Pydantic válido."""
        try:
            return (isinstance(obj, type) and issubclass(obj, BaseModel) and hasattr(obj, 'model_json_schema'))
        except TypeError:
            return False

    def _create_schema_from_signature(self) -> Type[BaseModel]:
        """
        Cria schema baseado diretamente no target_model.
        """
        from pydantic import create_model

        # Obter todos os campos do modelo target
        model_fields = self.target_model.model_fields

        schema_fields = {}

        for field_name, field_info in model_fields.items():
            is_required = field_info.is_required()

            if is_required:
                schema_fields[field_name] = (field_info.annotation, Field(..., description=f"Campo {field_name}"))
            else:
                default_value = field_info.get_default(call_default_factory=True)
                schema_fields[field_name] = (
                field_info.annotation, Field(default_value, description=f"Campo {field_name}"))

        schema_name = f"{self.__class__.__name__}Schema"
        return create_model(schema_name, **schema_fields)

    def to_openai_function(self):
        """
        Converte para função OpenAI usando o target_model diretamente.
        """
        return convert_to_openai_tool(self.target_model, self.name, self.description)
