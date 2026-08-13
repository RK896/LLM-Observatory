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


def fetch_dashboard_metrics() -> dict:
    """Fetch all metrics needed for the dashboard charts."""
    return {
        "latency": query_metric("avg:agent.run.latency_ms{*}"),
        "cost": query_metric("sum:agent.llm.cost_usd{*}.rollup(sum, 300)"),
        "tokens_prompt": query_metric("sum:agent.llm.tokens.prompt{*}.rollup(sum, 300)"),
        "tokens_completion": query_metric("sum:agent.llm.tokens.completion{*}.rollup(sum, 300)"),
        "co2": query_metric("sum:agent.env.co2_g{*}.rollup(sum, 300)"),
        "energy": query_metric("sum:agent.env.energy_wh{*}.rollup(sum, 300)"),
    }
