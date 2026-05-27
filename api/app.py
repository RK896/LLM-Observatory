import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from agent.runner import run
from observability.datadog_api import fetch_dashboard_metrics
from observability.tracing import init_tracing

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_tracing()
    yield


app = FastAPI(title="LLM Agent Observatory", lifespan=lifespan)
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "..", "templates"))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/metrics")
async def metrics():
    return JSONResponse(fetch_dashboard_metrics())


@app.post("/query")
async def query(request: Request, question: str = Form(...)):
    try:
        result = run(question)
        return JSONResponse({
            "answer": result.answer,
            "sub_questions": result.sub_questions,
            "source_count": len(result.search_results),
            "latency_ms": round(result.latency_ms, 1),
            "cost_usd": round(result.total_cost_usd, 6),
            "prompt_tokens": result.total_prompt_tokens,
            "completion_tokens": result.total_completion_tokens,
            "steps": {
                "planner": {
                    "latency_ms": round(result.planner.latency_ms, 1),
                    "prompt_tokens": result.planner.prompt_tokens,
                    "completion_tokens": result.planner.completion_tokens,
                    "cost_usd": round(result.planner.cost_usd, 6),
                },
                "search": {
                    "latency_ms": round(result.search_latency_ms, 1),
                    "result_count": len(result.search_results),
                },
                "synthesizer": {
                    "latency_ms": round(result.synthesizer.latency_ms, 1),
                    "prompt_tokens": result.synthesizer.prompt_tokens,
                    "completion_tokens": result.synthesizer.completion_tokens,
                    "cost_usd": round(result.synthesizer.cost_usd, 6),
                },
            },
        })
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)
