"""
contests.py — Contest, Problem, Submission, and Leaderboard APIs.
"""
import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Optional

log = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db, Contest, Problem, Submission, User, ContestStatus, Verdict, Difficulty
from auth import get_current_user, require_admin
from executor import execute
from llm import generate_problem


router = APIRouter(tags=["Contests"])


# ── Pydantic Schemas ────────────────────────────────────────────────────────
class ContestCreate(BaseModel):
    title:       str
    description: str = ""
    start_time:  datetime
    end_time:    datetime

class ContestOut(BaseModel):
    id:          int
    title:       str
    description: str
    start_time:  datetime
    end_time:    datetime
    status:      str
    problem_count: int = 0

    class Config:
        from_attributes = True

class GenerateProblemRequest(BaseModel):
    topic:      str
    difficulty: str  # easy | medium | hard

class ProblemOut(BaseModel):
    id:             int
    contest_id:     int
    title:          str
    description:    str
    difficulty:     str
    topic:          str
    constraints:    str
    examples:       str   # JSON string
    test_cases:     Optional[str] = "[]"
    func_sig_py:    str
    func_sig_c:     str
    func_sig_java:  str
    driver_py:      str
    driver_c:       str
    driver_java:    str
    time_limit_ms:  int
    memory_limit_mb: int
    base_score:     int

    class Config:
        from_attributes = True

class SubmitRequest(BaseModel):
    problem_id: int
    language:   str
    code:       str   # user's solution function only

class SubmissionOut(BaseModel):
    id:           int
    verdict:      str
    passed_cases: int
    total_cases:  int
    score:        float
    execution_ms: float
    stderr:       str

    class Config:
        from_attributes = True

class LeaderboardEntry(BaseModel):
    rank:       int
    username:   str
    score:      float
    passed:     int
    total:      int
    submitted_at: datetime


# ── Helpers ──────────────────────────────────────────────────────────────────
def _sync_contest_status(contest: Contest, db: Session) -> Contest:
    """Update contest status based on current time."""
    now = datetime.utcnow()
    new_status = contest.status
    if now >= contest.start_time and now < contest.end_time:
        new_status = ContestStatus.live
    elif now >= contest.end_time:
        new_status = ContestStatus.ended
    else:
        new_status = ContestStatus.scheduled

    if new_status != contest.status:
        contest.status = new_status
        db.commit()
    return contest


def _wrap_code(language: str, user_code: str, problem: Problem) -> str:
    """Wrap user's solution function with the problem's driver code."""
    if language == "python":
        return f"{user_code}\n\n{problem.driver_py}"
    elif language == "c":
        # C: prepend includes, user code, then main driver
        return f"#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n\n{user_code}\n\n{problem.driver_c}"
    elif language == "java":
        # Java: wrap user method inside class Main
        indented = "\n    ".join(user_code.strip().splitlines())
        return f"import java.util.Scanner;\npublic class Main {{\n    {indented}\n\n    {problem.driver_java}\n}}"
    raise HTTPException(400, "Unsupported language")


def _score_submission(passed: int, total: int, base_score: int,
                       submitted_at: datetime, start_time: datetime, end_time: datetime) -> float:
    """Score = correctness ratio * base * time_bonus."""
    if total == 0 or passed == 0:
        return 0.0
    correctness = passed / total
    duration = max((end_time - start_time).total_seconds(), 1)
    elapsed  = (submitted_at - start_time).total_seconds()
    time_bonus = max(0.0, 1.0 - elapsed / duration)
    return round(correctness * base_score * (0.7 + 0.3 * time_bonus), 2)


# ── Admin: Contest Management ─────────────────────────────────────────────
@router.post("/admin/contests", response_model=ContestOut)
def create_contest(req: ContestCreate, db: Session = Depends(get_db),
                   admin: User = Depends(require_admin)):
    c = Contest(title=req.title, description=req.description,
                start_time=req.start_time, end_time=req.end_time,
                created_by=admin.id)
    db.add(c); db.commit(); db.refresh(c)
    c = _sync_contest_status(c, db)
    return ContestOut(id=c.id, title=c.title, description=c.description,
                      start_time=c.start_time, end_time=c.end_time, status=c.status.value)


@router.get("/admin/contests", response_model=List[ContestOut])
def admin_list_contests(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    contests = db.query(Contest).all()
    result = []
    for c in contests:
        c = _sync_contest_status(c, db)
        result.append(ContestOut(
            id=c.id, title=c.title, description=c.description,
            start_time=c.start_time, end_time=c.end_time, status=c.status.value,
            problem_count=len(c.problems)
        ))
    return result


@router.post("/admin/contests/{contest_id}/problems/generate", response_model=ProblemOut)
async def generate_and_add_problem(contest_id: int, req: GenerateProblemRequest,
                                   db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    contest = db.query(Contest).filter(Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(404, "Contest not found")

    # ── Call LLM — all errors are wrapped as ValueError inside generate_problem
    try:
        data = await generate_problem(req.topic, req.difficulty)
    except ValueError as exc:
        # Clean, user-readable error — do NOT let it become a 500
        log.warning("[generate_problem] ValueError: %s", exc)
        raise HTTPException(422, detail=str(exc))
    except Exception as exc:
        # Truly unexpected — log the full traceback but return a safe 502
        log.exception("[generate_problem] Unexpected error for topic=%r difficulty=%r",
                      req.topic, req.difficulty)
        raise HTTPException(502, detail=f"Problem generation failed. Please try again. ({type(exc).__name__})")

    # ── Save to DB — guard against bad data from the LLM ──────────────────
    try:
        problem = Problem(
            contest_id=contest_id,
            title=data.get("title", "Untitled")[:256],
            description=data.get("description", ""),
            difficulty=req.difficulty,
            topic=req.topic,
            constraints=data.get("constraints", ""),
            examples=json.dumps(data.get("examples", [])),
            test_cases=json.dumps(data.get("test_cases", [])),
            func_sig_py=data.get("func_sig_py", "def solution():\n    pass"),
            func_sig_c=data.get("func_sig_c", "int solution() {\n    \n}"),
            func_sig_java=data.get("func_sig_java", "int solution() {\n    \n}"),
            driver_py=data.get("driver_py", ""),
            driver_c=data.get("driver_c", ""),
            driver_java=data.get("driver_java", ""),
            reference_solution_py=data.get("reference_solution_py", ""),
            time_limit_ms=int(data.get("time_limit_ms", 2000)),
            memory_limit_mb=int(data.get("memory_limit_mb", 256)),
            base_score=int(data.get("base_score", 100)),
            order_index=len(contest.problems),
        )
        db.add(problem)
        db.commit()
        db.refresh(problem)
        return problem
    except Exception as exc:
        db.rollback()
        log.exception("[generate_problem] DB save failed")
        raise HTTPException(500, detail=f"Problem was generated but could not be saved: {type(exc).__name__}")


@router.delete("/admin/contests/{contest_id}/problems/{problem_id}")
def delete_problem(contest_id: int, problem_id: int,
                   db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    p = db.query(Problem).filter(Problem.id == problem_id, Problem.contest_id == contest_id).first()
    if not p:
        raise HTTPException(404, "Problem not found")
    db.delete(p); db.commit()
    return {"detail": "deleted"}


# ── Admin: Update Problem Testcases ──────────────────────────────────────────
class TestCase(BaseModel):
    input: str
    expected_output: str

class UpdateTestCasesRequest(BaseModel):
    test_cases: List[TestCase]

@router.put("/admin/contests/{contest_id}/problems/{problem_id}/testcases")
def update_testcases(
    contest_id: int,
    problem_id: int,
    req: UpdateTestCasesRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Update the test cases for a problem. Accepts a list of testcases with input/expected_output.
    """
    p = db.query(Problem).filter(
        Problem.id == problem_id, Problem.contest_id == contest_id
    ).first()
    if not p:
        raise HTTPException(404, "Problem not found")
    
    # Validate test cases
    if not req.test_cases:
        raise HTTPException(400, "At least one test case is required")
    
    # Convert to JSON format expected by the system
    test_cases_json = json.dumps([{
        "input": tc.input,
        "expected_output": tc.expected_output
    } for tc in req.test_cases])
    
    p.test_cases = test_cases_json
    db.commit()
    db.refresh(p)
    
    return {
        "detail": f"Updated {len(req.test_cases)} test cases",
        "total_cases": len(req.test_cases)
    }


# ── Student: Contest & Problem Access ─────────────────────────────────────────
@router.get("/contests", response_model=List[ContestOut])
def list_contests(db: Session = Depends(get_db)):
    contests = db.query(Contest).order_by(Contest.start_time.desc()).all()
    result = []
    for c in contests:
        c = _sync_contest_status(c, db)
        result.append(ContestOut(
            id=c.id, title=c.title, description=c.description,
            start_time=c.start_time, end_time=c.end_time, status=c.status.value,
            problem_count=len(c.problems)
        ))
    return result


@router.get("/contests/{contest_id}", response_model=ContestOut)
def get_contest(contest_id: int, db: Session = Depends(get_db)):
    c = db.query(Contest).filter(Contest.id == contest_id).first()
    if not c:
        raise HTTPException(404, "Contest not found")
    c = _sync_contest_status(c, db)
    return ContestOut(id=c.id, title=c.title, description=c.description,
                      start_time=c.start_time, end_time=c.end_time, status=c.status.value,
                      problem_count=len(c.problems))


@router.get("/contests/{contest_id}/problems", response_model=List[ProblemOut])
def get_problems(contest_id: int, db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
    contest = db.query(Contest).filter(Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(404, "Contest not found")
    contest = _sync_contest_status(contest, db)
    if contest.status == ContestStatus.scheduled and current_user.role != "admin":
        raise HTTPException(403, "Contest has not started yet")
    return db.query(Problem).filter(Problem.contest_id == contest_id).order_by(Problem.order_index).all()


@router.get("/contests/{contest_id}/problems/{problem_id}", response_model=ProblemOut)
def get_problem(contest_id: int, problem_id: int, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    contest = db.query(Contest).filter(Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(404, "Contest not found")
    contest = _sync_contest_status(contest, db)
    if contest.status == ContestStatus.scheduled and current_user.role != "admin":
        raise HTTPException(403, "Contest has not started yet")
    p = db.query(Problem).filter(Problem.id == problem_id, Problem.contest_id == contest_id).first()
    if not p:
        raise HTTPException(404, "Problem not found")
    return p


# ── Student: Custom Input Runner ──────────────────────────────────────────────
class RunCustomRequest(BaseModel):
    problem_id: int
    language:   str
    code:       str   # user solution code only
    custom_input: str # raw stdin string to test against

class RunCustomResponse(BaseModel):
    your_output:     str
    expected_output: str   # from reference solution
    match:           bool
    stderr:          str
    error:           Optional[str]


@router.post("/contests/{contest_id}/run-custom", response_model=RunCustomResponse)
async def run_custom_input(
    contest_id: int,
    req: RunCustomRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Run user's code AND the reference solution on a custom input.
    This endpoint NEVER raises a 500 — all errors are returned as safe
    RunCustomResponse payloads so the frontend always gets a valid response.
    """
    # ── Look up problem ────────────────────────────────────────────────────
    try:
        problem = db.query(Problem).filter(
            Problem.id == req.problem_id, Problem.contest_id == contest_id
        ).first()
    except Exception as exc:
        log.exception("[run-custom] DB query failed")
        return RunCustomResponse(
            your_output="", expected_output="", match=False,
            stderr="", error=f"Database error: {type(exc).__name__}"
        )

    if not problem:
        raise HTTPException(404, "Problem not found")

    loop = asyncio.get_event_loop()
    your_output = ""
    user_stderr = ""
    user_error  = None

    # ── Run user's code via Docker ─────────────────────────────────────────
    try:
        full_code = _wrap_code(req.language, req.code, problem)
        user_result = await loop.run_in_executor(
            None, lambda: execute(language=req.language, code=full_code, stdin=req.custom_input)
        )
        your_output = (user_result.get("stdout") or "").strip()
        user_stderr = (user_result.get("stderr") or "").strip()
        user_error  = user_result.get("error")   # "Compilation Error", "Timeout", etc.
    except HTTPException:
        raise   # language validation errors (400) — surface these directly
    except Exception as exc:
        log.exception("[run-custom] User code execution failed")
        user_error  = f"Execution error: {type(exc).__name__}: {exc}"

    # ── Run reference solution locally to get expected answer ──────────────
    expected_output = ""
    if problem.reference_solution_py and problem.driver_py:
        from llm import _run_solution_locally
        try:
            expected_output = await loop.run_in_executor(
                None,
                lambda: _run_solution_locally(
                    problem.reference_solution_py,
                    problem.driver_py,
                    req.custom_input,
                )
            )
        except RuntimeError as exc:
            log.warning("[run-custom] Reference solution error for input %r: %s",
                        req.custom_input[:50], exc)
            expected_output = "(Could not compute expected output for this input)"
        except Exception as exc:
            log.exception("[run-custom] Unexpected reference solution error")
            expected_output = "(Reference solution unavailable)"
    else:
        expected_output = "(No reference solution stored for this problem)"

    return RunCustomResponse(
        your_output=your_output,
        expected_output=expected_output,
        match=(your_output == expected_output and bool(your_output)),
        stderr=user_stderr[:50000],   # cap to 50k so the payload doesn't explode
        error=user_error,
    )


# ── Student: Submission & Judging ─────────────────────────────────────────────
@router.post("/contests/{contest_id}/submit", response_model=SubmissionOut)
async def submit(contest_id: int, req: SubmitRequest,
                 db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    contest = db.query(Contest).filter(Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(404, "Contest not found")
    contest = _sync_contest_status(contest, db)
    if contest.status != ContestStatus.live:
        raise HTTPException(403, "Contest is not currently active")

    problem = db.query(Problem).filter(
        Problem.id == req.problem_id, Problem.contest_id == contest_id
    ).first()
    if not problem:
        raise HTTPException(404, "Problem not found")

    # Build full runnable code
    try:
        full_code = _wrap_code(req.language, req.code, problem)
    except Exception as e:
        raise HTTPException(400, str(e))

    # Run against all test cases (one by one — sequential to avoid hammering Docker)
    test_cases = json.loads(problem.test_cases or "[]")
    passed = 0
    last_stderr = ""
    total_ms = 0.0
    overall_verdict = Verdict.accepted

    for tc in test_cases:
        result = execute(language=req.language, code=full_code, stdin=tc["input"])
        total_ms += result.get("execution_time_ms", 0)

        if result.get("error") == "Compilation Error":
            overall_verdict = Verdict.compilation_error
            last_stderr = result.get("stderr", "")
            break
        elif result.get("error") == "Timeout":
            overall_verdict = Verdict.time_limit_exceeded
            break
        elif result.get("error") == "Runtime Error":
            overall_verdict = Verdict.runtime_error
            last_stderr = result.get("stderr", "")
            # Continue running other test cases to give partial credit
        else:
            actual   = result.get("stdout", "").strip()
            expected = str(tc["expected_output"]).strip()
            if actual == expected:
                passed += 1
            else:
                overall_verdict = Verdict.wrong_answer
                last_stderr = result.get("stderr", "")

    # Determine final verdict
    if overall_verdict == Verdict.accepted and passed < len(test_cases):
        overall_verdict = Verdict.wrong_answer

    score = _score_submission(
        passed, len(test_cases), problem.base_score,
        datetime.utcnow(), contest.start_time, contest.end_time
    )

    sub = Submission(
        user_id=current_user.id,
        problem_id=problem.id,
        contest_id=contest_id,
        language=req.language,
        code=req.code,
        verdict=overall_verdict,
        passed_cases=passed,
        total_cases=len(test_cases),
        score=score,
        execution_ms=round(total_ms, 2),
        stderr=last_stderr[:50000],
    )
    db.add(sub); db.commit(); db.refresh(sub)
    return sub


@router.get("/contests/{contest_id}/submissions", response_model=List[SubmissionOut])
def my_submissions(contest_id: int, problem_id: Optional[int] = None,
                   db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(Submission).filter(
        Submission.contest_id == contest_id,
        Submission.user_id == current_user.id
    )
    if problem_id:
        q = q.filter(Submission.problem_id == problem_id)
    return q.order_by(Submission.submitted_at.desc()).all()


# ── Leaderboard ────────────────────────────────────────────────────────────────
@router.get("/contests/{contest_id}/leaderboard", response_model=List[LeaderboardEntry])
def leaderboard(contest_id: int, db: Session = Depends(get_db)):
    contest = db.query(Contest).filter(Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(404, "Contest not found")

    # Best submission per user per problem (max score)
    from sqlalchemy import func
    best = (
        db.query(
            Submission.user_id,
            func.max(Submission.score).label("best_score"),
            func.max(Submission.passed_cases).label("best_passed"),
            func.max(Submission.total_cases).label("total"),
            func.min(Submission.submitted_at).label("first_ac"),
        )
        .filter(Submission.contest_id == contest_id)
        .group_by(Submission.user_id, Submission.problem_id)
        .subquery()
    )

    agg = (
        db.query(
            best.c.user_id,
            func.sum(best.c.best_score).label("total_score"),
            func.sum(best.c.best_passed).label("total_passed"),
            func.max(best.c.total).label("total_cases"),
            func.max(best.c.first_ac).label("last_sub"),
        )
        .group_by(best.c.user_id)
        .order_by(func.sum(best.c.best_score).desc(), func.max(best.c.first_ac).asc())
        .all()
    )

    entries = []
    for rank, row in enumerate(agg, 1):
        user = db.query(User).filter(User.id == row.user_id).first()
        entries.append(LeaderboardEntry(
            rank=rank,
            username=user.username if user else "Unknown",
            score=round(row.total_score or 0, 2),
            passed=row.total_passed or 0,
            total=row.total_cases or 0,
            submitted_at=row.last_sub or datetime.utcnow(),
        ))
    return entries
