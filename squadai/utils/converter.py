from typing import Optional, Type, Union, get_args, get_origin
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