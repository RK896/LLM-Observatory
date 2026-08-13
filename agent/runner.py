import time
from dataclasses import dataclass

from agent.environment import EnvironmentalImpact, estimate_impact
from agent.planner import PlanResult, plan
from agent.searcher import SearchResult, SearchRun, search
from agent.synthesizer import SynthResult, synthesize
from observability.metrics import record_environmental_impact, record_run_error, record_run_latency
from observability.tracing import get_tracer, init_tracing


@dataclass(frozen=True)
class StepStats:
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float


@dataclass(frozen=True)
class RunResult:
    question: str
    sub_questions: list[str]
    search_results: list[SearchResult]
    answer: str
    latency_ms: float
    planner: StepStats
    search_latency_ms: float
    synthesizer: StepStats
    environment: EnvironmentalImpact

    @property
    def total_cost_usd(self) -> float:
        return self.planner.cost_usd + self.synthesizer.cost_usd

    @property
    def total_prompt_tokens(self) -> int:
        return self.planner.prompt_tokens + self.synthesizer.prompt_tokens

    @property
    def total_completion_tokens(self) -> int:
        return self.planner.completion_tokens + self.synthesizer.completion_tokens


def run(question: str) -> RunResult:
    """Execute a full research agent run for the given question."""
    init_tracing()
    tracer = get_tracer()

    with tracer.trace("research_agent.run", service="llm-agent-observatory", resource=question) as root_span:
        root_span.set_tag("query", question)
        start = time.monotonic()

        try:
            plan_result: PlanResult = plan(question)

            search_start = time.monotonic()
            all_results: list[SearchResult] = []
            for sub_q in plan_result.sub_questions:
                run: SearchRun = search(sub_q)
                all_results.extend(run.results)
            search_latency_ms = (time.monotonic() - search_start) * 1000

            synth_result: SynthResult = synthesize(question, all_results)

            latency_ms = (time.monotonic() - start) * 1000
            total_cost = plan_result.cost_usd + synth_result.cost_usd
            impact = estimate_impact(
                prompt_tokens=plan_result.prompt_tokens + synth_result.prompt_tokens,
                completion_tokens=plan_result.completion_tokens + synth_result.completion_tokens,
            )

            root_span.set_tag("success", True)
            root_span.set_tag("latency_ms", latency_ms)
            root_span.set_tag("sub_question_count", len(plan_result.sub_questions))
            root_span.set_tag("total_sources", len(all_results))
            root_span.set_tag("total_cost_usd", total_cost)
            root_span.set_tag("energy_wh", impact.energy_wh)
            root_span.set_tag("co2_g", impact.co2_grams)
            root_span.set_tag("water_ml", impact.water_ml)

            record_run_latency(latency_ms)
            record_environmental_impact(impact.energy_wh, impact.co2_grams, impact.water_ml)

            return RunResult(
                question=question,
                sub_questions=plan_result.sub_questions,
                search_results=all_results,
                answer=synth_result.answer,
                latency_ms=latency_ms,
                planner=StepStats(
                    latency_ms=plan_result.latency_ms,
                    prompt_tokens=plan_result.prompt_tokens,
                    completion_tokens=plan_result.completion_tokens,
                    cost_usd=plan_result.cost_usd,
                ),
                search_latency_ms=search_latency_ms,
                synthesizer=StepStats(
                    latency_ms=synth_result.latency_ms,
                    prompt_tokens=synth_result.prompt_tokens,
                    completion_tokens=synth_result.completion_tokens,
                    cost_usd=synth_result.cost_usd,
                ),
                environment=impact,
            )

        except Exception as exc:
            error_type = type(exc).__name__
            root_span.set_tag("success", False)
            root_span.set_tag("error_type", error_type)
            root_span.error = 1
            record_run_error(error_type)
            raise
