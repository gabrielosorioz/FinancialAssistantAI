from abc import ABC, abstractmethod
from typing import Type, Optional, Any, Dict, get_type_hints
from inspect import signature
from pydantic import BaseModel, Field, create_model


class BaseTool(BaseModel, ABC):
    """Classe base para todas as ferramentas."""
    name: str
    description: str
    args_schema: Optional[Type[BaseModel]] = None

    def __init__(self, **data):
        super().__init__(**data)

        if not hasattr(self, "args_schema") or self.args_schema is None:
            self.args_schema = self._create_schema_from_signature()
        self.validate()

    def validate(self):
        """Valida se a ferramenta está corretamente configurada."""
        assert self.name, "Nome da ferramenta é obrigatório"
        assert self.description, "Descrição da ferramenta é obrigatória"
        assert self.args_schema, "Schema de argumentos é obrigatório"

    def _create_schema_from_signature(self) -> Type[BaseModel]:
        """Cria um schema Pydantic a partir da assinatura do método _run."""
        sig = signature(self._run)
        type_hints = get_type_hints(self._run)
        fields = {}
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue

            param_type = type_hints.get(param_name, Any)
            has_default = param.default != param.empty
            default_value = ... if not has_default else param.default

            field_info = Field(
                default=default_value,
                description=f"Parâmetro {param_name} para a ferramenta {self.name}"
            )

            fields[param_name] = (param_type, field_info)

        schema_name = f"{self.__class__.__name__}Schema"
        return create_model(schema_name, **fields)

    @abstractmethod
    def _run(self, **kwargs) -> Any:
        """Implementação específica da ferramenta."""
        raise NotImplementedError("Subclasses devem implementar o método _run")

    def run(self, **kwargs) -> Any:
        validated = self.args_schema(**kwargs)

        args_for_run = {
            name: getattr(validated, name)
            for name in validated.model_fields
        }

        return self._run(**args_for_run)

    def to_openai_function(self):
        """Converte a ferramenta para o formato de function da OpenAI."""
        schema = self.args_schema.model_json_schema()

        # Flatten the schema to remove $ref and $defs
        flattened_schema = self._flatten_schema(schema)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": flattened_schema
            }
        }

    def _flatten_schema(self, schema: Dict, defs: Dict = None) -> Dict[str, Any]:
        """Achata o schema recursivamente, substituindo todas as referências."""
        if defs is None:
            defs = schema.pop('$defs', {})

        flattened = schema.copy()

        for prop_name, prop_value in flattened.get('properties', {}).items():
            if not isinstance(prop_value, dict):
                continue

            # Resolver referência direta
            if '$ref' in prop_value:
                ref_name = prop_value['$ref'].split('/')[-1]
                if ref_name in defs:
                    flattened['properties'][prop_name] = self._flatten_schema(defs[ref_name], defs)
                    continue

            if 'items' in prop_value and isinstance(prop_value['items'], dict):
                if '$ref' in prop_value['items']:
                    ref_name = prop_value['items']['$ref'].split('/')[-1]
                    if ref_name in defs:
                        prop_value['items'] = self._flatten_schema(defs[ref_name], defs)
                else:
                    prop_value['items'] = self._flatten_schema(prop_value['items'], defs)

            if 'properties' in prop_value:
                prop_value = self._flatten_schema(prop_value, defs)
                flattened['properties'][prop_name] = prop_value

        return flattened

    def model_post_init(self, __context: Any) -> None:
        self._generate_description()
        super().model_post_init(__context)

    def _generate_description(self):
        """
        Gera uma descrição detalhada da ferramenta que inclui seus argumentos.
        Este método enriquece a descrição original com informações sobre os parâmetros.
        """
        # Preserva a descrição original fornecida pelo usuário
        original_description = self.description

        # Obtém informações sobre os argumentos do schema
        args_info = []
        if self.args_schema:
            schema = self.args_schema.model_json_schema()
            properties = schema.get("properties", {})
            required = schema.get("required", [])

            for arg_name, arg_details in properties.items():
                arg_type = arg_details.get("type", "unknown")
                arg_desc = arg_details.get("description", "")
                is_required = arg_name in required
                required_mark = " (obrigatório)" if is_required else " (opcional)"

                args_info.append(f"- {arg_name}: {arg_type}{required_mark}. {arg_desc}")

        # Gera a descrição completa
        args_section = "\nArgumentos: ".join(args_info) if args_info else ""

        self.description = f"""{original_description}
        {args_section}"""