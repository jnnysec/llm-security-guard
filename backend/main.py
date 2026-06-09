from fastapi import FastAPI
from pydantic import BaseModel
from backend.filter import filter_input
from backend.auditor import audit_output
from backend.redteam import red_team_test, add_template, list_templates
from backend.db import cursor, conn

app = FastAPI()

class PromptRequest(BaseModel):
    prompt: str

@app.post("/filter")
def api_filter(req: PromptRequest):
    safe, reason = filter_input(req.prompt)
    # 记录日志
    cursor.execute(
        "INSERT INTO request_logs(prompt, safe, reason) VALUES (%s,%s,%s)",
        (req.prompt, safe, reason)
    )
    conn.commit()
    return {"safe": safe, "reason": reason}

@app.post("/audit")
def api_audit(req: PromptRequest):
    result = audit_output(req.prompt)
    cursor.execute(
        "UPDATE request_logs SET output_score=%s, output_issues=%s WHERE prompt=%s",
        (result["score"], ",".join(result["issues"]), req.prompt)
    )
    conn.commit()
    return result

@app.get("/redteam")
def api_redteam():
    models = ["Qwen", "Llama", "GLM"]
    df = red_team_test(models)
    return df.to_dict(orient="records")

@app.post("/template")
def api_add_template(req: PromptRequest):
    add_template(req.prompt)
    return {"status": "ok", "templates": list_templates()}

@app.get("/templates")
def api_list_templates():
    return {"templates": list_templates()}
