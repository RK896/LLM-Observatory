import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from agent.runner import run
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


@app.post("/query")
async def query(request: Request, question: str = Form(...)):
    try:
        result = run(question)
        return JSONResponse({
            "answer": result.answer,
            "sub_questions": result.sub_questions,
            "source_count": len(result.search_results),
            "latency_ms": round(result.latency_ms, 1),
        })
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)
