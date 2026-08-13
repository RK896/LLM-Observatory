import os
from datadog import DogStatsd

_statsd = DogStatsd(
    host=os.getenv("DD_AGENT_HOST", "localhost"),
    port=int(os.getenv("DD_DOGSTATSD_PORT", "8125")),
    namespace="agent",
    constant_tags=[
        f"service:{os.getenv('DD_SERVICE', 'llm-agent-observatory')}",
        f"env:{os.getenv('DD_ENV', 'local')}",
        f"version:{os.getenv('DD_VERSION', '1.0.0')}",
    ],
)


def record_run_latency(latency_ms: float) -> None:
    _statsd.gauge("run.latency_ms", latency_ms)


def record_llm_cost(cost_usd: float, *, step: str) -> None:
    _statsd.gauge("llm.cost_usd", cost_usd, tags=[f"step:{step}"])


def record_prompt_tokens(count: int, *, step: str) -> None:
    _statsd.increment("llm.tokens.prompt", count, tags=[f"step:{step}"])


def record_completion_tokens(count: int, *, step: str) -> None:
    _statsd.increment("llm.tokens.completion", count, tags=[f"step:{step}"])


def record_environmental_impact(energy_wh: float, co2_grams: float, water_ml: float) -> None:
    _statsd.gauge("env.energy_wh", energy_wh)
    _statsd.gauge("env.co2_g", co2_grams)
    _statsd.gauge("env.water_ml", water_ml)


def record_search_result_count(count: int) -> None:
    _statsd.gauge("search.result_count", count)


def record_run_error(error_type: str) -> None:
    _statsd.increment("run.error", tags=[f"error_type:{error_type}"])
