import os
from ddtrace import tracer
from ddtrace.llmobs import LLMObs

_initialized = False


def init_tracing() -> None:
    """Boot ddtrace APM and LLM Observability. Safe to call multiple times."""
    global _initialized
    if _initialized:
        return

    LLMObs.enable(
        ml_app=os.getenv("DD_SERVICE", "llm-agent-observatory"),
        integrations_enabled=False,  # we instrument manually for full control
    )
    _initialized = True


def get_tracer():
    return tracer


def annotate_llm_span(span, input_messages: list[dict], output_message: dict, model: str) -> None:
    """Attach prompt/response/model to an LLM Observability span."""
    LLMObs.annotate(
        span=span,
        input_data=input_messages,
        output_data=[output_message],
        model_name=model,
        model_provider="openai",
    )
