import os
import time
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


@dataclass(frozen=True)
class SearchRun:
    results: list[SearchResult]
    latency_ms: float


def search(sub_question: str) -> SearchRun:
    """Search the web for a sub-question and return the top results."""
    client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    tracer = get_tracer()

    with tracer.trace("agent.search", service="llm-agent-observatory", resource=sub_question) as span:
        start = time.monotonic()
        response = client.search(
            query=sub_question,
            max_results=MAX_RESULTS,
            search_depth="basic",
        )
        latency_ms = (time.monotonic() - start) * 1000

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
        span.set_tag("latency_ms", latency_ms)

        record_search_result_count(len(results))

        return SearchRun(results=results, latency_ms=latency_ms)
