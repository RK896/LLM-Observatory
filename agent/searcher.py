import os
from dataclasses import dataclass

from tavily import TavilyClient

from observability.metrics import record_search_result_count
from observability.tracing import get_tracer

MAX_RESULTS = 3


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    content: str


def search(sub_question: str) -> list[SearchResult]:
    """Search the web for a sub-question and return the top results."""
    client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    tracer = get_tracer()

    with tracer.trace("agent.search", service="llm-agent-observatory", resource=sub_question) as span:
        response = client.search(
            query=sub_question,
            max_results=MAX_RESULTS,
            search_depth="basic",
        )

        results = [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                content=r.get("content", ""),
            )
            for r in response.get("results", [])
        ]

        span.set_tag("query", sub_question)
        span.set_tag("result_count", len(results))

        record_search_result_count(len(results))

        return results
