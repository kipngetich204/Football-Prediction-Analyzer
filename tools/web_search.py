from pydantic import BaseModel
from ddgs import DDGS
from .base import BaseTool


class WebSearchArgs(BaseModel):
    query: str
    num_results: int = 5


class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Search the web for current information. Use for facts, news, or anything requiring live data."
    args_schema = WebSearchArgs

    def run(self, args: dict) -> str:
        query = args["query"]
        num_results = args.get("num_results", 5)

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=num_results))

        if not results:
            return "No results found."

        formatted = []
        for r in results:
            formatted.append(f"Title: {r['title']}\nURL: {r['href']}\nSnippet: {r['body']}\n")

        return "\n---\n".join(formatted)