from typing import Optional, List, Any

from squadai.agents import BaseAgent
from squadai.agents.agent_executor import AgentExecutor
from squadai.tasks import Task, TaskOutput, OutputFormat
from squadai.tools import BaseTool
from squadai.utils import generate_model_description
from squadai.utils.prompts import Prompts


class Agent(BaseAgent):

    def execute_task(self,
                     task: Task,
                     tools: Optional[List[BaseTool]] = None
    ) -> TaskOutput:
        """Execute a task with the agent.

        Args:
            task: Task to execute.
            tools: Tools to use for the task.

        Returns:
            Output of the agent
        """
        task_prompt = task.prompt()

        if task.output_json or task.output_pydantic:
            # Generate the schema based on the output format
            if task.output_json:
                schema = generate_model_description(task.output_json)
                task_prompt += "\n" + self.i18n.slice(
                    "formatted_task_instructions"
                ).format(output_format=OutputFormat.JSON,
                         output_scheme=schema
                )

            elif task.output_pydantic:
                schema = generate_model_description(task.output_json)
                formatted_task_instructions = """
                                    Retornar uma resposta estritamente:
                                    com o seguinte ``scheme`` (formato): {output_format}
                                    """
                task_prompt += "\n" + formatted_task_instructions.format(
                    output_format=schema
                )
        tools = tools or self.tools or []
        self.create_agent_executor(tools=tools, task=task)

        response = self._execute(task_prompt=task_prompt)
        # Cria e retorna um TaskOutput baseado na resposta e formato esperado
        output_format = OutputFormat.RAW

        output = TaskOutput(
            description=task.description,
            name=task.name,
            expected_output=task.expected_output,
            raw=response.content if hasattr(response, 'content') else str(response),
            agent=str(self.id),
            output_format=output_format,
        )

        # Se houver tool_usages no agent_executor, adiciona-os ao TaskOutput
        # if hasattr(self.agent_executor, 'tool_usages') and self.agent_executor.tool_usages:
        #     output.tool_usages = self.agent_executor.tool_usages
        task.output = output
        return output;

    def create_agent_executor(
            self, tools: Optional[List[BaseTool]] = None,
            task: Task = None
    ) -> None:
        """Create an agent executor for the agent.

        Returns:
            An instance of the AgentExecutor class.
        """

        _tools: List[BaseTool] = tools or self.tools or []

        prompt = Prompts(
            agent=self,
            i18n=self.i18n,
            use_system_prompt=self.use_system_prompt
        ).task_execution()

        self.agent_executor = AgentExecutor(
            llm=self.llm,
            task=task,
            agent=self,
            tools=_tools,
            prompt=prompt,
            memory=self.memory
        )

    def _execute(self,
                 task_prompt: str,
    ) -> str:
        """Execute a task without a timeout.

               Args:
                   task_prompt: The prompt to send to the agent.
                   task: The task being executed.

               Returns:
                   The output of the agent.
       """
        return self.agent_executor.invoke(
            {
                "input": task_prompt
            }
        )
