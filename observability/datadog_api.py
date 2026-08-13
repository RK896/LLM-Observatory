import os
import time

import httpx


def _headers() -> dict:
    return {
        "DD-API-KEY": os.getenv("DD_API_KEY", ""),
        "DD-APPLICATION-KEY": os.getenv("DD_APP_KEY", ""),
    }


def _api_url(path: str) -> str:
    site = os.getenv("DD_SITE", "datadoghq.com")
    return f"https://api.{site}{path}"


def query_metric(query: str, hours: int = 48) -> list[tuple[float, float]]:
    """Return (unix_timestamp, value) pairs for a Datadog metric query."""
    now = int(time.time())
    start = now - hours * 3600

    try:
        resp = httpx.get(
            _api_url("/api/v1/query"),
            headers=_headers(),
            params={"from": start, "to": now, "query": query},
            timeout=8.0,
        )
        resp.raise_for_status()
    except Exception:
        return []

    series = resp.json().get("series", [])
    if not series:
        return []

    return [
        (point[0] / 1000, round(point[1], 4))
        for point in series[0].get("pointlist", [])
        if point[1] is not None
    ]


DASHBOARD_WINDOW_HOURS = 24 * 7
_ROLLUP_SECONDS = 600  # fine buckets so each query (or close burst) becomes its own point
_MAX_CHART_POINTS = 20  # charts show the most recent N active buckets, not a fixed timeline


def _recent(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Keep only the most recent active buckets — empty ones are already filtered out."""
    return points[-_MAX_CHART_POINTS:]


def fetch_dashboard_metrics() -> dict:
    """Fetch all metrics needed for the dashboard charts."""
    hours = DASHBOARD_WINDOW_HOURS
    rollup = _ROLLUP_SECONDS
    return {
        "latency": _recent(query_metric(f"avg:agent.run.latency_ms{{*}}.rollup(avg, {rollup})", hours=hours)),
        "cost": _recent(query_metric(f"sum:agent.llm.cost_usd{{*}}.rollup(sum, {rollup})", hours=hours)),
        "tokens_prompt": _recent(query_metric(f"sum:agent.llm.tokens.prompt{{*}}.rollup(sum, {rollup})", hours=hours)),
        "tokens_completion": _recent(query_metric(f"sum:agent.llm.tokens.completion{{*}}.rollup(sum, {rollup})", hours=hours)),
        "co2": _recent(query_metric(f"sum:agent.env.co2_g{{*}}.rollup(sum, {rollup})", hours=hours)),
        "energy": _recent(query_metric(f"sum:agent.env.energy_wh{{*}}.rollup(sum, {rollup})", hours=hours)),
    }
