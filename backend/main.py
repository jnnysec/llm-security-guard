from __future__ import annotations

import time
from typing import List, Optional

from fastapi import FastAPI, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.auditor import audit_output
from backend.db import store
from backend.filter import analyze_prompt, filter_input
from backend.providers import provider_status
from backend.redteam import add_template, list_templates, red_team_test, save_report, summarize_results

app = FastAPI(title="LLM Security Guard", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=12000)


class TemplateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=12000)
    category: str = Field(default="Custom", max_length=80)


class BlacklistRequest(BaseModel):
    word: str = Field(..., min_length=1, max_length=200)


@app.get("/health")
def health():
    return {"status": "ok", **store.health()}


@app.get("/providers")
def api_providers():
    return {"providers": provider_status()}


@app.post("/filter")
def api_filter(req: PromptRequest):
    start = time.perf_counter()
    result = analyze_prompt(req.prompt)
    latency_ms = (time.perf_counter() - start) * 1000
    log = store.log_request(
        kind="filter",
        prompt=req.prompt,
        safe=result["safe"],
        reason=result["reason"],
        risk_types=result["risk_types"],
        latency_ms=latency_ms,
    )
    return {**result, "latency_ms": round(latency_ms, 2), "log_id": log.id}


@app.post("/audit")
def api_audit(req: PromptRequest):
    start = time.perf_counter()
    result = audit_output(req.prompt)
    latency_ms = (time.perf_counter() - start) * 1000
    log = store.log_request(
        kind="audit",
        prompt=req.prompt,
        safe=result["safe"],
        reason="安全" if result["safe"] else "发现敏感信息",
        output_score=result["score"],
        output_issues=result["issues"],
        safe_text=result["safe_text"],
        latency_ms=latency_ms,
    )
    return {**result, "latency_ms": round(latency_ms, 2), "log_id": log.id}


@app.get("/metrics")
def api_metrics():
    return store.metrics()


@app.get("/logs")
def api_logs(limit: int = Query(default=100, ge=1, le=500), q: str = ""):
    return {"logs": store.recent_logs(limit=limit, query=q)}


@app.get("/logs/export")
def api_export_logs(limit: int = Query(default=100, ge=1, le=500), q: str = ""):
    csv_text = store.export_csv(limit=limit, query=q)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=llm-security-logs.csv"},
    )


@app.get("/redteam")
def api_redteam(
    models: Optional[List[str]] = Query(default=None),
    mode: str = Query(default="simulated", pattern="^(simulated|live|auto)$"),
):
    return {"mode": mode, "providers": provider_status(), "results": red_team_test(models, mode=mode)}


@app.get("/redteam/summary")
def api_redteam_summary(
    models: Optional[List[str]] = Query(default=None),
    mode: str = Query(default="simulated", pattern="^(simulated|live|auto)$"),
    save: bool = False,
):
    rows = red_team_test(models, mode=mode)
    summary = summarize_results(rows)
    report = save_report(rows, summary, mode) if save else None
    return {"mode": mode, "providers": provider_status(), "summary": summary, "results": rows, "report": report}


@app.post("/redteam/run")
def api_redteam_run(
    models: Optional[List[str]] = Query(default=None),
    mode: str = Query(default="auto", pattern="^(simulated|live|auto)$"),
    save: bool = True,
):
    rows = red_team_test(models, mode=mode)
    summary = summarize_results(rows)
    report = save_report(rows, summary, mode) if save else None
    return {"mode": mode, "providers": provider_status(), "summary": summary, "results": rows, "report": report}


@app.post("/template")
def api_add_template(req: TemplateRequest):
    item = add_template(req.prompt, req.category)
    return {"status": "ok", "template": item.__dict__, "templates": list_templates()}


@app.get("/templates")
def api_list_templates():
    return {"templates": list_templates()}


@app.get("/blacklist")
def api_blacklist():
    return {"blacklist": store.blacklist()}


@app.post("/blacklist")
def api_add_blacklist(req: BlacklistRequest):
    return {"blacklist": store.add_blacklist_word(req.word)}


__all__ = ["app", "filter_input"]
