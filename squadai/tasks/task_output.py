import json
import uuid
from typing import Optional, Dict, Any
from .output_format import OutputFormat

from pydantic import (
    UUID4,
    BaseModel,
    Field
)



class TaskOutput(BaseModel):
    """Class that represents the result of a task."""

    description: str = Field(description="Description of the task")
    name: Optional[str] = Field(description="Name of the task", default=None)
    expected_output: Optional[str] = Field(
        description="Expected output of the task", default=None
    )
    raw: str = Field(description="Raw output of the task", default="")
    pydantic: Optional[BaseModel] = Field(
        description="Pydantic output of task", default=None
    )
    json_dict: Optional[Dict[str, Any]] = Field(
        description="JSON dictionary of task", default=None
    )
    agent: str = Field(description="Agent that executed the task")
    output_format: OutputFormat = Field(
        description="Output format of the task", default=OutputFormat.RAW
    )
    id: UUID4 = Field(
        default_factory=uuid.uuid4,
        frozen=True,
        description="Unique identifier for the object, not set by user.",
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert json_output and pydantic_output to a dictionary."""
        output_dict = {}
        if self.json_dict:
            output_dict.update(self.json_dict)
        elif self.pydantic:
            output_dict.update(self.pydantic.model_dump())
        return output_dict

    @property
    def json(self) -> Optional[str]:
        if self.output_format != OutputFormat.JSON:
            raise ValueError(
                """
                Invalid output format requested.
                If you would like to access the JSON output,
                please make sure to set the output_json property for the task
                """
            )

        return json.dumps(self.json_dict)

    def __str__(self) -> str:
        if self.pydantic:
            return str(self.pydantic)
        if self.json_dict:
            return str(self.json_dict)
        return self.raw