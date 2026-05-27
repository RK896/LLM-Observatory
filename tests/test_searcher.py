from unittest.mock import MagicMock, patch

from agent.searcher import SearchResult, search


def _make_tavily_response(n: int) -> dict:
    return {
        "results": [
            {"title": f"Title {i}", "url": f"https://example.com/{i}", "content": f"Content {i}"}
            for i in range(n)
        ]
    }


@patch("agent.searcher.record_search_result_count")
@patch("agent.searcher.get_tracer")
@patch("agent.searcher.TavilyClient")
def test_search_returns_results(mock_tavily, mock_tracer, mock_metric):
    mock_tavily.return_value.search.return_value = _make_tavily_response(3)

    mock_span = MagicMock()
    mock_tracer.return_value.trace.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_tracer.return_value.trace.return_value.__exit__ = MagicMock(return_value=False)

    results = search("What causes inflation?")

    assert len(results) == 3
    assert all(isinstance(r, SearchResult) for r in results)


@patch("agent.searcher.record_search_result_count")
@patch("agent.searcher.get_tracer")
@patch("agent.searcher.TavilyClient")
def test_search_maps_fields(mock_tavily, mock_tracer, mock_metric):
    mock_tavily.return_value.search.return_value = _make_tavily_response(1)

    mock_span = MagicMock()
    mock_tracer.return_value.trace.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_tracer.return_value.trace.return_value.__exit__ = MagicMock(return_value=False)

    results = search("test query")

    assert results[0].title == "Title 0"
    assert results[0].url == "https://example.com/0"
    assert results[0].content == "Content 0"


@patch("agent.searcher.record_search_result_count")
@patch("agent.searcher.get_tracer")
@patch("agent.searcher.TavilyClient")
def test_search_emits_metric(mock_tavily, mock_tracer, mock_metric):
    mock_tavily.return_value.search.return_value = _make_tavily_response(2)

    mock_span = MagicMock()
    mock_tracer.return_value.trace.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_tracer.return_value.trace.return_value.__exit__ = MagicMock(return_value=False)

    search("test query")

    mock_metric.assert_called_once_with(2)


@patch("agent.searcher.record_search_result_count")
@patch("agent.searcher.get_tracer")
@patch("agent.searcher.TavilyClient")
def test_search_handles_empty_results(mock_tavily, mock_tracer, mock_metric):
    mock_tavily.return_value.search.return_value = {"results": []}

    mock_span = MagicMock()
    mock_tracer.return_value.trace.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_tracer.return_value.trace.return_value.__exit__ = MagicMock(return_value=False)

    results = search("obscure query")

    assert results == []
    mock_metric.assert_called_once_with(0)
