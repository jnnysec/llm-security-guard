from fastapi import FastAPI
from pydantic import BaseModel
from backend.filter import filter_input
from backend.auditor import audit_output
from backend.redteam import red_team_test

app = FastAPI()

class PromptRequest(BaseModel):
    prompt: str

@app.post("/filter")
def api_filter(req: PromptRequest):
    safe, reason = filter_input(req.prompt)
    return {"safe": safe, "reason": reason}

@app.post("/audit")
def api_audit(req: PromptRequest):
    return audit_output(req.prompt)

@app.get("/redteam")
def api_redteam():
    models = ["Qwen", "Llama", "GLM"]
    df = red_team_test(models)
    return df.to_dict(orient="records")
