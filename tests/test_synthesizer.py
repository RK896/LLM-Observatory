from unittest.mock import MagicMock, patch

import pytest

from agent.searcher import SearchResult
from agent.synthesizer import _format_context, synthesize


def _make_results(n: int = 2) -> list[SearchResult]:
    return [
        SearchResult(title=f"Title {i}", url=f"https://example.com/{i}", content=f"Content {i}")
        for i in range(n)
    ]


def _make_openai_response(content: str) -> MagicMock:
    choice = MagicMock()
    choice.message.content = content
    resp = MagicMock()
    resp.choices = [choice]
    resp.usage.prompt_tokens = 200
    resp.usage.completion_tokens = 80
    return resp


def test_format_context_numbers_sources():
    results = _make_results(2)
    ctx = _format_context(results)
    assert "[1]" in ctx
    assert "[2]" in ctx
    assert "https://example.com/0" in ctx


def test_format_context_empty():
    assert _format_context([]) == ""


@patch("agent.synthesizer.record_llm_cost")
@patch("agent.synthesizer.record_completion_tokens")
@patch("agent.synthesizer.record_prompt_tokens")
@patch("agent.synthesizer.LLMObs.llm")
@patch("agent.synthesizer.get_tracer")
@patch("agent.synthesizer.OpenAI")
def test_synthesize_returns_answer(mock_openai, mock_tracer, mock_llmobs, *metric_mocks):
    expected = "This is the final answer."
    mock_openai.return_value.chat.completions.create.return_value = _make_openai_response(expected)

    mock_span = MagicMock()
    mock_tracer.return_value.trace.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_tracer.return_value.trace.return_value.__exit__ = MagicMock(return_value=False)
    mock_llmobs.return_value.__enter__ = MagicMock(return_value=MagicMock())
    mock_llmobs.return_value.__exit__ = MagicMock(return_value=False)

    result = synthesize("What is inflation?", _make_results())

    assert result == expected


@patch("agent.synthesizer.record_llm_cost")
@patch("agent.synthesizer.record_completion_tokens")
@patch("agent.synthesizer.record_prompt_tokens")
@patch("agent.synthesizer.LLMObs.llm")
@patch("agent.synthesizer.get_tracer")
@patch("agent.synthesizer.OpenAI")
def test_synthesize_emits_metrics(mock_openai, mock_tracer, mock_llmobs, mock_prompt, mock_completion, mock_cost):
    mock_openai.return_value.chat.completions.create.return_value = _make_openai_response("answer")

    mock_span = MagicMock()
    mock_tracer.return_value.trace.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_tracer.return_value.trace.return_value.__exit__ = MagicMock(return_value=False)
    mock_llmobs.return_value.__enter__ = MagicMock(return_value=MagicMock())
    mock_llmobs.return_value.__exit__ = MagicMock(return_value=False)

    synthesize("test question", _make_results())

    mock_prompt.assert_called_once_with(200, step="synthesizer")
    mock_completion.assert_called_once_with(80, step="synthesizer")
    mock_cost.assert_called_once()
