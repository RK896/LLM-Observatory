import time
from dataclasses import dataclass

from agent.planner import plan
from agent.searcher import SearchResult, search
from agent.synthesizer import synthesize
from observability.metrics import record_run_error, record_run_latency
from observability.tracing import get_tracer, init_tracing


@dataclass(frozen=True)
class RunResult:
    question: str
    sub_questions: list[str]
    search_results: list[SearchResult]
    answer: str
    latency_ms: float


def run(question: str) -> RunResult:
    """Execute a full research agent run for the given question."""
    init_tracing()
    tracer = get_tracer()

    with tracer.trace("research_agent.run", service="llm-agent-observatory", resource=question) as root_span:
        root_span.set_tag("query", question)
        start = time.monotonic()

        try:
            sub_questions = plan(question)

            all_results: list[SearchResult] = []
            for sub_q in sub_questions:
                results = search(sub_q)
                all_results.extend(results)

            answer = synthesize(question, all_results)

            latency_ms = (time.monotonic() - start) * 1000
            root_span.set_tag("success", True)
            root_span.set_tag("latency_ms", latency_ms)
            root_span.set_tag("sub_question_count", len(sub_questions))
            root_span.set_tag("total_sources", len(all_results))

            record_run_latency(latency_ms)

            return RunResult(
                question=question,
                sub_questions=sub_questions,
                search_results=all_results,
                answer=answer,
                latency_ms=latency_ms,
            )

        except Exception as exc:
            error_type = type(exc).__name__
            root_span.set_tag("success", False)
            root_span.set_tag("error_type", error_type)
            root_span.error = 1
            record_run_error(error_type)
            raise
