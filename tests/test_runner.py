from unittest.mock import MagicMock, patch

import pytest

from agent.planner import PlanResult
from agent.runner import RunResult, run
from agent.searcher import SearchResult, SearchRun
from agent.synthesizer import SynthResult


def _make_plan_result(sub_questions: list[str]) -> PlanResult:
    return PlanResult(
        sub_questions=sub_questions,
        latency_ms=120.0,
        prompt_tokens=50,
        completion_tokens=30,
        cost_usd=0.0001,
    )


def _make_search_run() -> SearchRun:
    return SearchRun(
        results=[SearchResult(title="T", url="https://example.com", content="C")],
        latency_ms=300.0,
    )


def _make_synth_result(answer: str = "Final answer.") -> SynthResult:
    return SynthResult(
        answer=answer,
        latency_ms=800.0,
        prompt_tokens=200,
        completion_tokens=80,
        cost_usd=0.0002,
    )


def _mock_root_span(mock_tracer) -> MagicMock:
    mock_span = MagicMock()
    mock_tracer.return_value.trace.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_tracer.return_value.trace.return_value.__exit__ = MagicMock(return_value=False)
    return mock_span


@patch("agent.runner.record_environmental_impact")
@patch("agent.runner.record_run_error")
@patch("agent.runner.record_run_latency")
@patch("agent.runner.init_tracing")
@patch("agent.runner.synthesize")
@patch("agent.runner.search")
@patch("agent.runner.plan")
@patch("agent.runner.get_tracer")
def test_run_returns_result(mock_tracer, mock_plan, mock_search, mock_synthesize, *_):
    mock_plan.return_value = _make_plan_result(["sub-q 1", "sub-q 2"])
    mock_search.return_value = _make_search_run()
    mock_synthesize.return_value = _make_synth_result()
    _mock_root_span(mock_tracer)

    result = run("What is machine learning?")

    assert isinstance(result, RunResult)
    assert result.answer == "Final answer."
    assert result.sub_questions == ["sub-q 1", "sub-q 2"]
    assert len(result.search_results) == 2  # 2 sub-questions × 1 result each


@patch("agent.runner.record_environmental_impact")
@patch("agent.runner.record_run_error")
@patch("agent.runner.record_run_latency")
@patch("agent.runner.init_tracing")
@patch("agent.runner.synthesize")
@patch("agent.runner.search")
@patch("agent.runner.plan")
@patch("agent.runner.get_tracer")
def test_run_calls_search_per_sub_question(mock_tracer, mock_plan, mock_search, mock_synthesize, *_):
    mock_plan.return_value = _make_plan_result(["q1", "q2", "q3"])
    mock_search.return_value = _make_search_run()
    mock_synthesize.return_value = _make_synth_result("answer")
    _mock_root_span(mock_tracer)

    run("question")

    assert mock_search.call_count == 3


@patch("agent.runner.record_environmental_impact")
@patch("agent.runner.record_run_error")
@patch("agent.runner.record_run_latency")
@patch("agent.runner.init_tracing")
@patch("agent.runner.synthesize")
@patch("agent.runner.search")
@patch("agent.runner.plan")
@patch("agent.runner.get_tracer")
def test_run_records_error_and_reraises(mock_tracer, mock_plan, mock_search, mock_synthesize, mock_init, mock_latency, mock_error, mock_env):
    mock_plan.side_effect = ValueError("API key missing")
    mock_span = _mock_root_span(mock_tracer)

    with pytest.raises(ValueError, match="API key missing"):
        run("test question")

    mock_error.assert_called_once_with("ValueError")
    mock_span.set_tag.assert_any_call("success", False)


@patch("agent.runner.record_environmental_impact")
@patch("agent.runner.record_run_error")
@patch("agent.runner.record_run_latency")
@patch("agent.runner.init_tracing")
@patch("agent.runner.synthesize")
@patch("agent.runner.search")
@patch("agent.runner.plan")
@patch("agent.runner.get_tracer")
def test_run_emits_latency_metric(mock_tracer, mock_plan, mock_search, mock_synthesize, mock_init, mock_latency, *_):
    mock_plan.return_value = _make_plan_result(["q1"])
    mock_search.return_value = _make_search_run()
    mock_synthesize.return_value = _make_synth_result("answer")
    _mock_root_span(mock_tracer)

    run("question")

    mock_latency.assert_called_once()
    latency_arg = mock_latency.call_args[0][0]
    assert latency_arg >= 0


@patch("agent.runner.record_environmental_impact")
@patch("agent.runner.record_run_error")
@patch("agent.runner.record_run_latency")
@patch("agent.runner.init_tracing")
@patch("agent.runner.synthesize")
@patch("agent.runner.search")
@patch("agent.runner.plan")
@patch("agent.runner.get_tracer")
def test_run_estimates_environmental_impact(mock_tracer, mock_plan, mock_search, mock_synthesize, mock_init, mock_latency, mock_error, mock_env):
    mock_plan.return_value = _make_plan_result(["q1"])
    mock_search.return_value = _make_search_run()
    mock_synthesize.return_value = _make_synth_result("answer")
    mock_span = _mock_root_span(mock_tracer)

    result = run("question")

    assert result.environment.energy_wh > 0
    assert result.environment.co2_grams > 0
    assert result.environment.water_ml > 0

    mock_env.assert_called_once_with(
        result.environment.energy_wh,
        result.environment.co2_grams,
        result.environment.water_ml,
    )
    mock_span.set_tag.assert_any_call("energy_wh", result.environment.energy_wh)
    mock_span.set_tag.assert_any_call("co2_g", result.environment.co2_grams)
