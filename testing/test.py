from pydantic import BaseModel, Field
from tools.base import BaseTool

# 1. Define the exact input the tool expects using Pydantic
class SearchInputs(BaseModel):
    query: str = Field(description="The search query to look up on the internet.")

# 2. Inherit from BaseTool to create the actual tool
class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Use this tool to find up-to-date facts on the web."
    args_schema = SearchInputs

    # We MUST implement the run function
    def run(self, args: dict) -> str:
        query = args["query"]
        # (In a real app, you would fetch data from Google/Bing here)
        return f"Search results for '{query}': Kenya's capital is Nairobi."

# 3. Create and use the tool safely!
search_tool = WebSearchTool()

# If the AI sends a good input:
output, success = search_tool.safe_run({"query": "capital of Kenya"})
print(success)  # Output: True
print(output)   # Output: Search results for 'capital of Kenya': Kenya's capital is Nairobi.

# If the AI sends a bad input (e.g., missing the required 'query' key):
output, success = search_tool.safe_run({"wrong_key": "hello"})
print(success)  # Output: False
print(output)   # Output: Tool error: 1 validation error for SearchInputs...
