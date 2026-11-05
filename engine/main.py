import os
import re
import secrets
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel, Field

APP_NAME = "Raymond AI Command Engine"
WORKSPACE_ROOT = Path(os.getenv("WORKSPACE_ROOT", "/tmp/raymond-ai-workspaces")).resolve()
WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)

app = FastAPI(title=APP_NAME, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Dashboard-Token"],
)

class CommandRequest(BaseModel):
    command: str = Field(min_length=3, max_length=12000)
    project: str = Field(default="raymond-project", min_length=1, max_length=60)

class CommandResponse(BaseModel):
    status: str
    message: str
    project: str
    files: list[str] = []

def safe_project_name(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "-", value).strip("-_")
    if not cleaned:
        raise HTTPException(status_code=400, detail="Invalid project name")
    return cleaned[:60]

def get_workspace(project: str) -> Path:
    path = (WORKSPACE_ROOT / safe_project_name(project)).resolve()
    if WORKSPACE_ROOT not in path.parents:
        raise HTTPException(status_code=400, detail="Invalid workspace path")
    path.mkdir(parents=True, exist_ok=True)
    return path

def require_dashboard_token(token: str | None) -> None:
    expected = os.getenv("DASHBOARD_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Engine is not configured: DASHBOARD_TOKEN is missing")
    if not token or not secrets.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="Unauthorised dashboard")

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": APP_NAME, "version": "0.1.0"}

@app.post("/command", response_model=CommandResponse)
def execute_command(
    request: CommandRequest,
    x_dashboard_token: str | None = Header(default=None),
) -> CommandResponse:
    require_dashboard_token(x_dashboard_token)

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=503, detail="AI provider is not configured. Add OPENAI_API_KEY to Render environment variables.")

    # This first scaffold deliberately reports setup status rather than pretending
    # to have generated or deployed a website. The file-writing agent and guarded
    # FTP deployment will be added and tested in the next implementation step.
    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    workspace = get_workspace(request.project)

    try:
        response = client.responses.create(
            model=model,
            instructions=(
                "You are Raymond AI, a website-building assistant. "
                "Analyse the user's website request and return a concise implementation plan. "
                "Do not claim that files were created, tests passed, or deployment happened. "
                "No tools are enabled in this initial scaffold."
            ),
            input=request.command,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI provider request failed: {type(exc).__name__}: {exc}") from exc

    return CommandResponse(
        status="planning",
        message=response.output_text or "The AI received the command but returned no text.",
        project=workspace.name,
        files=[],
    )
