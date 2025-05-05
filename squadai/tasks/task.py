import uuid
from typing import Optional, Type, Dict, Union, Any, List
from pydantic import BaseModel, Field, UUID4
from .task_output import TaskOutput
from squadai.utils.string_utils import interpolate_only
from ..utils import I18N


class Task(BaseModel):
    name: Optional[str] = Field(default=None)
    description: str = Field(description="Description of the actual task.")
    expected_output: str = Field(
        description="Clear definition of expected output for the task."
    )
    output_json: Optional[Type[BaseModel]] = Field(
        description="A Pydantic model to be used to create a JSON output.",
        default=None,
    )
    output_pydantic: Optional[Type[BaseModel]] = Field(
        description="A Pydantic model to be used to create a Pydantic output.",
        default=None,
    )
    output: Optional[TaskOutput] = Field(
        description="Task output, it's final result after being executed", default=None
    )
    id: UUID4 = Field(
        default_factory=uuid.uuid4,
        frozen=True,
        description="Unique identifier for the object, not set by user.",
    )
    i18n: I18N = I18N()

    def prompt(self) -> str:
        """Prompt the task.

        Returns:
            Prompt of the task.
        """
        tasks_slices = [self.description]

        output = self.i18n.slice("task_expected_output").format(
            expected_output=self.expected_output
        )
        tasks_slices = [self.description, output]
        return "\n".join(tasks_slices)

    def interpolate_inputs(self,
                           inputs: Dict[str, Union[str, int, float, Dict[str, Any], List[Any]]]) -> None:
        """
            Interpolate inputs into the task description
             and expected output
        """
        if not inputs:
            return

        try:
            self.description = interpolate_only(input_string=self.description, inputs=inputs)
        except KeyError as e:
            raise ValueError(
                f"Missing required template variable '{e.args[0]}' in description"
            ) from e
        except ValueError as e:
            raise ValueError(f"Error interpolating description: {str(e)}") from e
        try:
            self.expected_output = interpolate_only(
                input_string=self.expected_output, inputs=inputs
            )
        except (KeyError, ValueError) as e:
            raise ValueError(f"Error interpolating expected_output: {str(e)}") from e







