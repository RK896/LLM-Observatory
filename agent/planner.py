import json
import os
import time
from dataclasses import dataclass

from ddtrace.llmobs import LLMObs
from openai import OpenAI

from observability.metrics import record_completion_tokens, record_llm_cost, record_prompt_tokens
from observability.tracing import get_tracer

STEP = "planner"
MODEL = "gpt-4o-mini"

_COST_PER_PROMPT_TOKEN = 0.15 / 1_000_000
_COST_PER_COMPLETION_TOKEN = 0.60 / 1_000_000

_SYSTEM_PROMPT = (
    "You are a research planning assistant. "
    "Given a user question, decompose it into 2-3 specific, searchable sub-questions. "
    'Respond ONLY with valid JSON in this format: {"sub_questions": ["...", "..."]}'
)


@dataclass(frozen=True)
class PlanResult:
    sub_questions: list[str]
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float


def plan(question: str) -> PlanResult:
    """Break a user question into 2–3 targeted sub-questions."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    tracer = get_tracer()

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    with tracer.trace("agent.plan", service="llm-agent-observatory", resource=question) as apm_span:
        with LLMObs.llm(model_name=MODEL, name="planner.llm", model_provider="openai") as llm_span:
            start = time.monotonic()
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.3,
            )
            latency_ms = (time.monotonic() - start) * 1000

            content = response.choices[0].message.content
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens

            LLMObs.annotate(
                span=llm_span,
                input_data=messages,
                output_data=[{"role": "assistant", "content": content}],
                metadata={"temperature": 0.3, "latency_ms": latency_ms},
            )

        sub_questions = json.loads(content)["sub_questions"]
        cost = (
            prompt_tokens * _COST_PER_PROMPT_TOKEN
            + completion_tokens * _COST_PER_COMPLETION_TOKEN
        )

        apm_span.set_tag("sub_question_count", len(sub_questions))
        apm_span.set_tag("prompt_tokens", prompt_tokens)
        apm_span.set_tag("completion_tokens", completion_tokens)
        apm_span.set_tag("cost_usd", cost)

        record_prompt_tokens(prompt_tokens, step=STEP)
        record_completion_tokens(completion_tokens, step=STEP)
        record_llm_cost(cost, step=STEP)

        return PlanResult(
            sub_questions=sub_questions,
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost,
        )
