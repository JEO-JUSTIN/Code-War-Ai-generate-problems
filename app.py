"""
app.py — FastAPI entry point for CodeWar contest platform.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from database import init_db
from executor import execute
from languages import LANGUAGES
import auth
import contests

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# ── App setup ──────────────────────────────────────────────────────────────────
app = FastAPI(
    title="CodeWar — Contest Platform",
    description="Intra-department coding contest with LLM-generated problems and Docker execution.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Serve frontend static files ────────────────────────────────────────────────
frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

# ── Startup ────────────────────────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    init_db()
    # Auto-create admin account if none exists
    from database import SessionLocal, User, UserRole
    from auth import hash_password
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.role == UserRole.admin).first():
            admin = User(
                username="admin",
                email="admin@codewar.local",
                password_hash=hash_password("admin123"),
                role=UserRole.admin,
            )
            db.add(admin)
            db.commit()
            print("✅ Default admin created — username: admin | password: admin123")
    finally:
        db.close()


# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(contests.router)


# ── Legacy /execute endpoint (kept for backward compat with standalone runner) ─
from pydantic import BaseModel, Field
from typing import Optional
import time

class ExecuteRequest(BaseModel):
    language: str
    code:     str
    stdin:    Optional[str] = ""

class ExecuteResponse(BaseModel):
    language:         str
    stdout:           str
    stderr:           str
    exit_code:        int
    error:            Optional[str]
    execution_time_ms: float

@app.post("/execute", response_model=ExecuteResponse, tags=["Execution"])
async def execute_code(request: ExecuteRequest):
    if not request.code.strip():
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Code must not be empty.")
    start  = time.perf_counter()
    result = execute(language=request.language, code=request.code, stdin=request.stdin or "")
    ms     = (time.perf_counter() - start) * 1000
    return ExecuteResponse(
        language=result["language"], stdout=result["stdout"],
        stderr=result["stderr"],    exit_code=result["exit_code"],
        error=result["error"],      execution_time_ms=round(ms, 2),
    )

@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok"}

@app.get("/languages", tags=["System"])
async def list_languages():
    return {lang: {"filename": cfg["filename"], "needs_compile": cfg["compile"] is not None}
            for lang, cfg in LANGUAGES.items()}
