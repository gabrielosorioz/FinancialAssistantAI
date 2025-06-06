from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel


class BaseLLM(BaseModel,ABC):
    @abstractmethod
    def call(self, messages, tools,**kwargs) -> Any:
        pass
