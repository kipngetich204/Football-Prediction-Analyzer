from abc import ABC, abstractmethod
from pydantic import BaseModel


class BaseTool(ABC):
    name: str
    description: str
    args_schema: type[BaseModel]

    @abstractmethod
    def run(self, args: dict) -> str:
        pass

    def safe_run(self, args: dict) -> tuple[str, bool]:
        try:
            validated = self.args_schema(**args)
            return self.run(validated.model_dump()), True
        except Exception as e:
            return f"Tool error: {str(e)}", False