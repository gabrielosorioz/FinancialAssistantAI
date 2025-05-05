from typing import Optional, Any

from pydantic import BaseModel, Field

from squadai.agents import BaseAgent
from squadai.utils import I18N


class Prompts(BaseModel):
    """Manages and generates prompts for a generic agent."""
    i18n: I18N = Field(default=I18N())
    use_system_prompt: Optional[bool] = False
    agent: BaseAgent

    def task_execution(self) -> dict[str,str]:
        """Generate a standard prompt for task execution."""
        slices = ["role_playing"]
        system = self._build_prompt(slices)
        slices.append("task")

        return {
            "system": system,
            "user": self._build_prompt(["task"]),
            "prompt": self._build_prompt(slices)
        }

    def _build_prompt(self,components: list[str]) -> str:
        prompt_parts = [self.i18n.slice(component) for component in components]
        prompt = "".join(prompt_parts)

        prompt: str = (
            prompt.replace("{role}", self.agent.role)
            .replace("{backstory}", self.agent.backstory)
            .replace("{goal}", self.agent.goal)
        )
        return prompt


