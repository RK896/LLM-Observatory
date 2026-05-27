import os
import time
from dataclasses import dataclass

from ddtrace.llmobs import LLMObs
from openai import OpenAI

from agent.searcher import SearchResult
from observability.metrics import record_completion_tokens, record_llm_cost, record_prompt_tokens
from observability.tracing import get_tracer

STEP = "synthesizer"
MODEL = "gpt-4o-mini"

_COST_PER_PROMPT_TOKEN = 0.15 / 1_000_000
_COST_PER_COMPLETION_TOKEN = 0.60 / 1_000_000

_SYSTEM_PROMPT = (
    "You are a research assistant. Given a question and web search results, "
    "write a clear, accurate answer using the provided sources. "
    "Cite sources inline as [1], [2], etc. based on the order they appear in the context."
)


@dataclass(frozen=True)
class SynthResult:
    answer: str
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float


def _format_context(results: list[SearchResult]) -> str:
    sections = []
    for i, r in enumerate(results, start=1):
        sections.append(f"[{i}] {r.title}\nURL: {r.url}\n{r.content}")
    return "\n\n".join(sections)


def synthesize(question: str, results: list[SearchResult]) -> SynthResult:
    """Synthesize a final answer from search results."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    tracer = get_tracer()

    context = _format_context(results)
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Question: {question}\n\nSources:\n{context}",
        },
    ]

    with tracer.trace("agent.synthesize", service="llm-agent-observatory", resource=question) as apm_span:
        with LLMObs.llm(model_name=MODEL, name="synthesizer.llm", model_provider="openai") as llm_span:
            start = time.monotonic()
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.5,
            )
            latency_ms = (time.monotonic() - start) * 1000

            content = response.choices[0].message.content
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens

            LLMObs.annotate(
                span=llm_span,
                input_data=messages,
                output_data=[{"role": "assistant", "content": content}],
                metadata={"temperature": 0.5, "latency_ms": latency_ms, "source_count": len(results)},
            )

        cost = (
            prompt_tokens * _COST_PER_PROMPT_TOKEN
            + completion_tokens * _COST_PER_COMPLETION_TOKEN
        )

        apm_span.set_tag("prompt_tokens", prompt_tokens)
        apm_span.set_tag("completion_tokens", completion_tokens)
        apm_span.set_tag("cost_usd", cost)
        apm_span.set_tag("source_count", len(results))

        record_prompt_tokens(prompt_tokens, step=STEP)
        record_completion_tokens(completion_tokens, step=STEP)
        record_llm_cost(cost, step=STEP)

        return SynthResult(
            answer=content,
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost,
        )
