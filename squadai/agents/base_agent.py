import uuid
from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel, UUID4, Field, InstanceOf
from squadai.tasks import Task
from squadai.tools import BaseTool
from squadai.llm import BaseLLM
from squadai.utils import I18N


class BaseAgent(ABC,BaseModel):
    id: UUID4 = Field(default_factory=uuid.uuid4, frozen=True)
    role: str
    backstory: str
    goal: str
    tools: Optional[List[BaseTool]]
    memory: bool
    verbose: bool
    llm: BaseLLM
    agent_executor: InstanceOf = Field(
        default=None, description="An instance of the CrewAgentExecutor class."
    )
    i18n: I18N = Field(default=I18N(), description="Internationalization settings.")
    use_system_prompt: Optional[bool] = False
    @abstractmethod
    def execute_task(
            self,
            task: Optional[Task] = None,
            tools: Optional[List[BaseTool]] = None,
            user_prompt: Optional[str] = None

    ) -> str:
        """Execute a task with the agent.
                Args:
                    task: Task to execute.
                    tools: Tools to use for the task.
                    user_prompt: User prompt
                Returns:
                    Output of the agent
                """
        pass

    @abstractmethod
    def create_agent_executor(self, tools=None) -> None:
        pass