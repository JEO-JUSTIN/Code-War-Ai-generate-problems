"""
llm.py — Problem generation using the Hugging Face Inference API.

Approach:
  Phase 1 → Ask the LLM for: problem statement, a working Python solution,
             driver code, function signatures, AND pre-computed test cases
             (input + expected_output pairs).  The LLM provides both.
  Phase 2 → Run the solution locally to VERIFY the expected outputs.
             If a test case passes verification → keep the LLM value.
             If local run differs → prefer local (it's more reliable).
             If local run crashes → still keep the LLM value as fallback.
             This means we ALWAYS get test cases, and they're as accurate
             as possible, even if Phase 2 partially fails.

Error philosophy:
  - Every failure is caught and wrapped in a clear ValueError.
  - No bare exceptions ever bubble up to crash the server.
  - Phase 2 failures never block saving — we fall back to LLM values.
"""
import os
import json
import logging
import asyncio
import re
import subprocess
import sys
import tempfile
import textwrap
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

log = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────────

HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_MODEL = "Qwen/Qwen2.5-Coder-32B-Instruct"

_PYTHON = sys.executable

_client = None

def _get_client():
    global _client
    if _client is None:
        if not HF_TOKEN:
            raise ValueError(
                "HF_TOKEN is not set. Add it to your .env file: HF_TOKEN=hf_..."
            )
        from huggingface_hub import InferenceClient
        _client = InferenceClient(token=HF_TOKEN, timeout=120)
    return _client


# ── Prompt ───────────────────────────────────────────────────────────────────

def _build_prompt(topic: str, difficulty: str) -> str:
    return f"""You are an expert competitive programming problem setter.
Generate a COMPLETELY NEW {difficulty} difficulty problem about: {topic}

IMPORTANT: Your response must be ONLY a valid JSON object — no markdown, no extra text.
DO NOT copy the examples from the template below. Create your own problem, solution, and test cases tailored specifically to '{topic}'.

Return exactly this JSON structure (fill in all values appropriately for your new problem):
{{
  "title": "Short Problem Title",
  "description": "Clear problem statement with Input Format and Output Format sections",
  "constraints": "1 <= n <= 1000, time limit 2s",
  "examples": [
    {{"input": "5", "output": "25", "explanation": "5 squared is 25"}}
  ],
  "solution_py": "def solution(n):\\n    return n * n",
  "func_sig_py": "def solution(n: int) -> int:\\n    pass",
  "func_sig_c":  "int solution(int n) {{\\n    \\n}}",
  "func_sig_java": "int solution(int n) {{\\n    \\n}}",
  "driver_py":   "import sys\\nn = int(sys.stdin.read().strip())\\nprint(solution(n))",
  "driver_c":    "int main() {{\\n    int n;\\n    scanf(\\"%d\\", &n);\\n    printf(\\"%d\\\\n\\", solution(n));\\n    return 0;\\n}}",
  "driver_java": "public static void main(String[] args) {{\\n    java.util.Scanner sc = new java.util.Scanner(System.in);\\n    int n = sc.nextInt();\\n    System.out.println(new Main().solution(n));\\n}}",
  "test_cases": [
    {{"input": "1",   "expected_output": "1"}},
    {{"input": "2",   "expected_output": "4"}},
    {{"input": "3",   "expected_output": "9"}},
    {{"input": "5",   "expected_output": "25"}},
    {{"input": "0",   "expected_output": "0"}},
    {{"input": "10",  "expected_output": "100"}},
    {{"input": "7",   "expected_output": "49"}},
    {{"input": "15",  "expected_output": "225"}},
    {{"input": "100", "expected_output": "10000"}},
    {{"input": "42",  "expected_output": "1764"}}
  ],
  "time_limit_ms": 2000,
  "memory_limit_mb": 256,
  "base_score": 100
}}

CRITICAL RULES:
1. solution_py MUST be a complete, correct Python function named `solution`.
2. driver_py reads from stdin, calls solution(), prints the result. It is concatenated AFTER solution_py.
3. CRITICAL: test_cases MUST have EXACTLY 10 entries. DO NOT skip, omit, or shorten test cases under any circumstances. Each entry has "input" (raw stdin string) and "expected_output" (what solution_py produces for that input).
4. The "input" strings in test_cases MUST match the format that driver_py expects from stdin.
5. Run through each test case in your head to verify the expected_output is correct before including it.
6. Return ONLY the JSON — absolutely no markdown fences, no text before or after.
7. YOU MUST NOT SKIP THE TEST CASES SECTIONS EVER. INCLUDE EXACTLY 10 TEST CASES OR YOU FAIL."""


# ── JSON Extraction & Repair ──────────────────────────────────────────────────

def _extract_json(text: str) -> str:
    """Strip markdown fences and extract the first complete JSON object."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence:
        return fence.group(1).strip()
    start = text.find("{")
    end   = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]
    return text


def _repair_truncated_json(text: str) -> str:
    """
    Attempt to repair a JSON string cut off mid-stream (e.g. due to max_tokens).
    Two-pass strategy:
      Pass 1 — close any open strings/arrays/objects.
      Pass 2 — strip back to last safe boundary then re-close.
    """
    def _close_structures(fragment: str) -> str:
        stack, in_string, escape_next = [], False, False
        for ch in fragment:
            if escape_next:
                escape_next = False
                continue
            if ch == "\\" and in_string:
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch in ('{', '['):
                stack.append(ch)
            elif ch in ('}', ']') and stack:
                stack.pop()
        tail = '"' if in_string else ''
        for opener in reversed(stack):
            tail += '}' if opener == '{' else ']'
        return fragment + tail

    candidate = _close_structures(text)
    try:
        json.loads(candidate)
        log.info("[llm] Truncated JSON repaired (pass 1).")
        return candidate
    except json.JSONDecodeError:
        pass

    stripped = text.rstrip()
    while stripped and stripped[-1] not in (',', '{', '['):
        stripped = stripped[:-1]
    if stripped and stripped[-1] == ',':
        stripped = stripped[:-1]
    if not stripped:
        return text

    candidate2 = _close_structures(stripped)
    try:
        json.loads(candidate2)
        log.info("[llm] Truncated JSON repaired (pass 2).")
        return candidate2
    except json.JSONDecodeError:
        return text


# ── Local Execution (Phase 2 — Verification Only) ────────────────────────────

def _run_solution_locally(solution_py: str, driver_py: str,
                           stdin_text: str, timeout: int = 10) -> str:
    """
    Run solution_py + driver_py in a subprocess with stdin_text.
    Returns stripped stdout.
    Raises RuntimeError with a clear message on any failure.
    """
    if not solution_py or not driver_py:
        raise RuntimeError("solution_py or driver_py is empty.")

    full_code = textwrap.dedent(solution_py).strip() + "\n\n" + textwrap.dedent(driver_py).strip()
    tmp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(full_code)
            tmp_path = f.name

        proc = subprocess.run(
            [_PYTHON, tmp_path],
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"Exit code {proc.returncode}: {proc.stderr.strip()[:200]}"
            )
        return proc.stdout.strip()

    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Timed out (>{timeout}s) for input: {stdin_text!r}")
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Unexpected error: {exc}") from exc
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def _verify_and_fix_test_cases(solution_py: str, driver_py: str,
                                test_cases: list) -> list:
    """
    Phase 2 (verification only):
    For each LLM-supplied test case, run the solution locally.
    - If local output matches LLM expected_output → keep as-is.
    - If local output differs → replace expected_output with local result
      (local execution is more reliable than LLM arithmetic).
    - If local run crashes → keep the LLM expected_output as fallback.
    ALWAYS returns the same number of test cases. Never drops entries.
    Never raises.
    """
    verified = []
    corrected = 0
    fallback  = 0

    for tc in test_cases:
        raw_input       = str(tc.get("input", ""))
        llm_expected    = str(tc.get("expected_output", "")).strip()
        try:
            local_output = _run_solution_locally(solution_py, driver_py, raw_input)
            if local_output != llm_expected:
                log.info(
                    "[llm] Corrected test case input=%r: LLM said %r, local says %r",
                    raw_input[:40], llm_expected, local_output
                )
                corrected += 1
            verified.append({"input": raw_input, "expected_output": local_output})
        except RuntimeError as exc:
            log.warning(
                "[llm] Verification failed for input=%r (%s) — keeping LLM value %r",
                raw_input[:40], exc, llm_expected
            )
            fallback += 1
            verified.append({"input": raw_input, "expected_output": llm_expected})
        except Exception as exc:
            log.error("[llm] Unexpected error verifying input=%r: %s", raw_input[:40], exc)
            fallback += 1
            verified.append({"input": raw_input, "expected_output": llm_expected})

    log.info(
        "[llm] Test case verification: %d exact, %d corrected, %d fallback (LLM value kept)",
        len(verified) - corrected - fallback, corrected, fallback
    )
    return verified


# ── Main Entry Point ──────────────────────────────────────────────────────────

async def generate_problem(topic: str, difficulty: str) -> dict:
    """
    Call Hugging Face to generate a problem + test cases, then verify them.
    Returns a dict ready to be stored in the database.
    Raises ValueError with a human-readable message on any unrecoverable failure.
    """
    if not topic or not topic.strip():
        raise ValueError("Topic must not be empty.")
    if difficulty not in ("easy", "medium", "hard"):
        raise ValueError("Difficulty must be 'easy', 'medium', or 'hard'.")

    prompt = _build_prompt(topic.strip(), difficulty)

    # ── Phase 1: LLM call ────────────────────────────────────────────────────
    def _call_hf():
        import time
        client = _get_client()
        for attempt in range(3):
            try:
                response = client.chat_completion(
                    model=HF_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a competitive programming problem setter. "
                                "Respond with a single valid JSON object only — "
                                "no markdown, no explanation, no extra text whatsoever."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=6000,
                )
                return response.choices[0].message["content"]
            except Exception as exc:
                if attempt < 2 and ("504" in str(exc) or "503" in str(exc) or "timeout" in str(exc).lower()):
                    log.warning(f"[llm] HF API error: {exc}. Retrying ({attempt+1}/3)...")
                    time.sleep(2 ** attempt)
                    continue
                raise ValueError(
                    f"Hugging Face API call failed: {type(exc).__name__}: {exc}"
                ) from exc

    loop = asyncio.get_event_loop()

    try:
        raw_text = await loop.run_in_executor(None, _call_hf)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"LLM executor error: {exc}") from exc

    if not raw_text or not raw_text.strip():
        raise ValueError("LLM returned an empty response. Try again.")

    # ── Parse JSON with repair fallback ──────────────────────────────────────
    raw = _extract_json(raw_text)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("[llm] Initial JSON parse failed — attempting repair...")
        raw = _repair_truncated_json(raw)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"LLM returned invalid JSON that could not be repaired ({exc}). "
                f"Raw response (first 400 chars):\n{raw_text[:400]}"
            )

    if not isinstance(data, dict):
        raise ValueError("LLM response parsed but is not a JSON object.")

    # ── Validate required keys ────────────────────────────────────────────────
    required = ["title", "description", "solution_py", "driver_py",
                "func_sig_py", "test_cases"]
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(
            f"LLM response is missing required keys: {missing}. Try regenerating."
        )

    solution_py = str(data.get("solution_py", "")).strip()
    driver_py   = str(data.get("driver_py",   "")).strip()
    test_cases  = data.get("test_cases", [])

    if not solution_py:
        raise ValueError("LLM returned an empty solution_py.")
    if not driver_py:
        raise ValueError("LLM returned an empty driver_py.")
    if not isinstance(test_cases, list) or len(test_cases) == 0:
        raise ValueError(
            "LLM returned no test_cases. "
            "This can happen when the response was truncated. Try regenerating."
        )

    # Ensure each test case has required fields; drop malformed ones
    valid_cases = [
        tc for tc in test_cases
        if isinstance(tc, dict) and "input" in tc and "expected_output" in tc
    ]
    if len(valid_cases) == 0:
        raise ValueError(
            "LLM test_cases are malformed (missing input/expected_output keys). "
            "Try regenerating."
        )

    # Pad to 10 if fewer provided by duplicating with varied inputs won't work —
    # just keep what we have; partial credit grading still works fine.
    log.info(
        "[llm] LLM provided %d valid test cases for '%s' (%s).",
        len(valid_cases), data.get("title", "?"), difficulty
    )

    # ── Phase 2: Verify / correct expected outputs locally ───────────────────
    def _verify():
        return _verify_and_fix_test_cases(solution_py, driver_py, valid_cases)

    try:
        verified_cases = await loop.run_in_executor(None, _verify)
    except Exception as exc:
        # Phase 2 failure must never block saving — use LLM values as-is
        log.error("[llm] Phase 2 verification crashed unexpectedly: %s", exc)
        verified_cases = valid_cases

    data["test_cases"]            = verified_cases
    data["reference_solution_py"] = solution_py

    log.info(
        "[llm] Problem '%s' ready — %d test cases stored.",
        data.get("title", "?"), len(verified_cases)
    )
    return data
