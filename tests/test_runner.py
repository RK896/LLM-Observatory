from unittest.mock import MagicMock, patch

import pytest

from agent.runner import RunResult, run
from agent.searcher import SearchResult


def _make_search_results() -> list[SearchResult]:
    return [SearchResult(title="T", url="https://example.com", content="C")]


@patch("agent.runner.record_run_error")
@patch("agent.runner.record_run_latency")
@patch("agent.runner.init_tracing")
@patch("agent.runner.synthesize")
@patch("agent.runner.search")
@patch("agent.runner.plan")
@patch("agent.runner.get_tracer")
def test_run_returns_result(mock_tracer, mock_plan, mock_search, mock_synthesize, mock_init, mock_latency, mock_error):
    mock_plan.return_value = ["sub-q 1", "sub-q 2"]
    mock_search.return_value = _make_search_results()
    mock_synthesize.return_value = "Final answer."

    mock_span = MagicMock()
    mock_tracer.return_value.trace.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_tracer.return_value.trace.return_value.__exit__ = MagicMock(return_value=False)

    result = run("What is machine learning?")

    assert isinstance(result, RunResult)
    assert result.answer == "Final answer."
    assert result.sub_questions == ["sub-q 1", "sub-q 2"]
    assert len(result.search_results) == 2  # 2 sub-questions × 1 result each


@patch("agent.runner.record_run_error")
@patch("agent.runner.record_run_latency")
@patch("agent.runner.init_tracing")
@patch("agent.runner.synthesize")
@patch("agent.runner.search")
@patch("agent.runner.plan")
@patch("agent.runner.get_tracer")
def test_run_calls_search_per_sub_question(mock_tracer, mock_plan, mock_search, mock_synthesize, *_):
    mock_plan.return_value = ["q1", "q2", "q3"]
    mock_search.return_value = _make_search_results()
    mock_synthesize.return_value = "answer"

    mock_span = MagicMock()
    mock_tracer.return_value.trace.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_tracer.return_value.trace.return_value.__exit__ = MagicMock(return_value=False)

    run("question")

    assert mock_search.call_count == 3


@patch("agent.runner.record_run_error")
@patch("agent.runner.record_run_latency")
@patch("agent.runner.init_tracing")
@patch("agent.runner.synthesize")
@patch("agent.runner.search")
@patch("agent.runner.plan")
@patch("agent.runner.get_tracer")
def test_run_records_error_and_reraises(mock_tracer, mock_plan, mock_search, mock_synthesize, mock_init, mock_latency, mock_error):
    mock_plan.side_effect = ValueError("API key missing")

    mock_span = MagicMock()
    mock_tracer.return_value.trace.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_tracer.return_value.trace.return_value.__exit__ = MagicMock(return_value=False)

    with pytest.raises(ValueError, match="API key missing"):
        run("test question")

    mock_error.assert_called_once_with("ValueError")
    mock_span.set_tag.assert_any_call("success", False)


@patch("agent.runner.record_run_error")
@patch("agent.runner.record_run_latency")
@patch("agent.runner.init_tracing")
@patch("agent.runner.synthesize")
@patch("agent.runner.search")
@patch("agent.runner.plan")
@patch("agent.runner.get_tracer")
def test_run_emits_latency_metric(mock_tracer, mock_plan, mock_search, mock_synthesize, mock_init, mock_latency, mock_error):
    mock_plan.return_value = ["q1"]
    mock_search.return_value = _make_search_results()
    mock_synthesize.return_value = "answer"

    mock_span = MagicMock()
    mock_tracer.return_value.trace.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_tracer.return_value.trace.return_value.__exit__ = MagicMock(return_value=False)

    run("question")

    mock_latency.assert_called_once()
    latency_arg = mock_latency.call_args[0][0]
    assert latency_arg >= 0
