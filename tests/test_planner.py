import json
from unittest.mock import MagicMock, patch

import pytest

from agent.planner import plan


def _make_openai_response(sub_questions: list[str]) -> MagicMock:
    content = json.dumps({"sub_questions": sub_questions})
    choice = MagicMock()
    choice.message.content = content
    resp = MagicMock()
    resp.choices = [choice]
    resp.usage.prompt_tokens = 50
    resp.usage.completion_tokens = 30
    return resp


@patch("agent.planner.record_llm_cost")
@patch("agent.planner.record_completion_tokens")
@patch("agent.planner.record_prompt_tokens")
@patch("agent.planner.LLMObs.llm")
@patch("agent.planner.get_tracer")
@patch("agent.planner.OpenAI")
def test_plan_returns_sub_questions(mock_openai, mock_tracer, mock_llmobs, *metric_mocks):
    expected = ["What causes inflation?", "How does the Fed respond to inflation?"]
    mock_openai.return_value.chat.completions.create.return_value = _make_openai_response(expected)

    mock_span = MagicMock()
    mock_tracer.return_value.trace.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_tracer.return_value.trace.return_value.__exit__ = MagicMock(return_value=False)
    mock_llmobs.return_value.__enter__ = MagicMock(return_value=MagicMock())
    mock_llmobs.return_value.__exit__ = MagicMock(return_value=False)

    result = plan("What is inflation and how is it controlled?")

    assert result.sub_questions == expected
    assert result.prompt_tokens == 50
    assert result.completion_tokens == 30
    assert result.cost_usd > 0


@patch("agent.planner.record_llm_cost")
@patch("agent.planner.record_completion_tokens")
@patch("agent.planner.record_prompt_tokens")
@patch("agent.planner.LLMObs.llm")
@patch("agent.planner.get_tracer")
@patch("agent.planner.OpenAI")
def test_plan_emits_metrics(mock_openai, mock_tracer, mock_llmobs, mock_prompt, mock_completion, mock_cost):
    mock_openai.return_value.chat.completions.create.return_value = _make_openai_response(["q1", "q2"])

    mock_span = MagicMock()
    mock_tracer.return_value.trace.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_tracer.return_value.trace.return_value.__exit__ = MagicMock(return_value=False)
    mock_llmobs.return_value.__enter__ = MagicMock(return_value=MagicMock())
    mock_llmobs.return_value.__exit__ = MagicMock(return_value=False)

    plan("test question")

    mock_prompt.assert_called_once_with(50, step="planner")
    mock_completion.assert_called_once_with(30, step="planner")
    mock_cost.assert_called_once()


@patch("agent.planner.record_llm_cost")
@patch("agent.planner.record_completion_tokens")
@patch("agent.planner.record_prompt_tokens")
@patch("agent.planner.LLMObs.llm")
@patch("agent.planner.get_tracer")
@patch("agent.planner.OpenAI")
def test_plan_sets_apm_tags(mock_openai, mock_tracer, mock_llmobs, *metric_mocks):
    mock_openai.return_value.chat.completions.create.return_value = _make_openai_response(["q1", "q2", "q3"])

    mock_span = MagicMock()
    mock_tracer.return_value.trace.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_tracer.return_value.trace.return_value.__exit__ = MagicMock(return_value=False)
    mock_llmobs.return_value.__enter__ = MagicMock(return_value=MagicMock())
    mock_llmobs.return_value.__exit__ = MagicMock(return_value=False)

    plan("test question")

    mock_span.set_tag.assert_any_call("sub_question_count", 3)
