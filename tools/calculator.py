import numexpr
from pydantic import BaseModel
from .base import BaseTool


class CalculatorArgs(BaseModel):
    expression: str


class CalculatorTool(BaseTool):
    name = "calculator"
    description = "Evaluate a math expression safely. Input must be a valid math string, e.g. '2 ** 10 + 3 * 4'."
    args_schema = CalculatorArgs

    def run(self, args: dict) -> str:
        expr = args["expression"]
        try:
            result = numexpr.evaluate(expr)
            return str(result)
        except Exception as e:
            return f"Calculation error: {e}"