# LLM Agent Observatory

A research agent fully instrumented with **Datadog LLM Observability** and **APM**. The agent answers natural language questions by breaking them into sub-questions, searching the web in parallel, and synthesizing a final answer — while emitting traces, spans, and custom metrics at every step.

## Architecture

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────┐
│                  Research Agent                  │
│                                                  │
│  ┌──────────┐   ┌──────────┐   ┌─────────────┐ │
│  │  Planner │──▶│ Searcher │──▶│ Synthesizer │ │
│  │  (LLM)   │   │ (Tavily) │   │    (LLM)    │ │
│  └──────────┘   └──────────┘   └─────────────┘ │
│       │               │               │          │
│       └───────────────┴───────────────┘          │
│                       │                          │
│              Datadog APM Spans                   │
│              LLM Observability                   │
│              Custom Metrics (DogStatsD)          │
└─────────────────────────────────────────────────┘
                        │
                        ▼
              Datadog Dashboard
```

### Agent Steps

1. **Planner** — GPT-4o-mini breaks the user question into 2–3 targeted sub-questions
2. **Searcher** — Tavily web search per sub-question, returns top results with content
3. **Synthesizer** — GPT-4o-mini reads all search results and writes a cited final answer

Each step is a traced span. The full run is one root trace visible in Datadog APM.

## Tech Stack

| Layer | Tool |
|-------|------|
| Language | Python 3.11+ |
| LLM | OpenAI GPT-4o-mini |
| Web search | Tavily API |
| Observability | Datadog ddtrace + LLM Observability |
| Metrics | DogStatsD |
| Web UI | FastAPI + Jinja2 |
| Packaging | Docker + docker-compose |

## Datadog Integration

### APM Traces

| Span | Tags |
|------|------|
| `research_agent.run` | `query`, `success`, `latency_ms` |
| `agent.plan` | `sub_question_count`, `prompt_tokens` |
| `agent.search` | `query`, `result_count`, `latency_ms` |
| `agent.synthesize` | `completion_tokens`, `cost_usd` |

### LLM Observability

Every LLM call is captured with:
- Full input/output messages
- Token counts (prompt + completion)
- Model name and provider
- Error classification on failure

### Custom Metrics (DogStatsD)

| Metric | Type | Description |
|--------|------|-------------|
| `agent.run.latency_ms` | Gauge | End-to-end latency per run |
| `agent.llm.cost_usd` | Gauge | Estimated cost per LLM call |
| `agent.llm.tokens.prompt` | Count | Prompt tokens per call |
| `agent.llm.tokens.completion` | Count | Completion tokens per call |
| `agent.search.result_count` | Gauge | Tavily results returned per search |
| `agent.run.error` | Count | Failed runs, tagged by error type |

## Project Structure

```
llm-agent-observatory/
├── agent/
│   ├── planner.py          # LLM call: question → sub-questions
│   ├── searcher.py         # Tavily: sub-question → search results
│   ├── synthesizer.py      # LLM call: results → final answer
│   └── runner.py           # Orchestrates steps, owns root trace
├── observability/
│   ├── tracing.py          # ddtrace setup and span helpers
│   └── metrics.py          # DogStatsD custom metric helpers
├── api/
│   └── app.py              # FastAPI app, POST /query endpoint
├── templates/
│   └── index.html          # Query form and result display
├── tests/
│   ├── test_planner.py
│   ├── test_searcher.py
│   ├── test_synthesizer.py
│   └── test_runner.py
├── docker-compose.yml      # App + Datadog Agent sidecar
├── Dockerfile
└── .env.example
```

## Setup

### Prerequisites

- Docker and docker-compose
- Datadog account ([free trial](https://www.datadoghq.com/))
- OpenAI API key
- Tavily API key

### Quick Start

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd llm-agent-observatory

# 2. Copy and fill in environment variables
cp .env.example .env
# Edit .env with your API keys

# 3. Start everything
docker-compose up

# 4. Open the UI
open http://localhost:8000
```

### Local Development (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env

# Run the app
uvicorn api.app:app --reload --port 8000
```

### Running Tests

```bash
pytest tests/ --cov=agent --cov=observability --cov-report=term-missing
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `TAVILY_API_KEY` | Tavily search API key |
| `DD_API_KEY` | Datadog API key |
| `DD_SITE` | Datadog site (default: `datadoghq.com`) |
| `DD_SERVICE` | Service name shown in APM (default: `llm-agent-observatory`) |
| `DD_ENV` | Environment tag (default: `local`) |
| `DD_VERSION` | Version tag (default: `1.0.0`) |

## Cost Estimate

At GPT-4o-mini pricing ($0.15 / 1M input tokens, $0.60 / 1M output tokens), a typical query costs approximately **$0.001–$0.004** depending on sub-question count and result verbosity.
