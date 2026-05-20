"""
executor.py — Core Docker-based code execution engine.

Workflow:
  1. Generate a unique UUID workspace folder.
  2. Save submitted code to the correct filename.
  3. (Optional) Compile via Docker container.
  4. Run the program via Docker container.
  5. Collect stdout / stderr / exit code.
  6. Delete the workspace folder.
  7. Return structured result dict.
"""

import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from languages import get_language_config

# ── Configuration ─────────────────────────────────────────────────────────────

DOCKER_IMAGE = "code-executor:latest"
BASE_WORKSPACE = Path(tempfile.gettempdir()) / "code_executor_workspaces"
COMPILE_TIMEOUT = 15   # seconds
RUN_TIMEOUT = 10       # seconds

# Resource caps applied to every container
DOCKER_RESOURCE_FLAGS = [
    "--memory", "128m",
    "--cpus", "0.5",
    "--network", "none",   # no internet
    "--pids-limit", "64",  # no fork bombs
]

# ── Helpers ───────────────────────────────────────────────────────────────────


def _ensure_base_workspace() -> None:
    """Create the shared workspace parent directory if absent."""
    BASE_WORKSPACE.mkdir(parents=True, exist_ok=True)


def generate_workspace() -> Path:
    """
    Create and return a unique, isolated working directory for one execution.
    Named after a UUID to prevent path collisions.
    """
    _ensure_base_workspace()
    workspace = BASE_WORKSPACE / str(uuid.uuid4())
    workspace.mkdir(parents=True)
    return workspace


def save_code(workspace: Path, filename: str, code: str) -> Path:
    """
    Write *code* into *workspace/filename*.
    Returns the full path to the saved file.
    """
    filepath = workspace / filename
    filepath.write_text(code, encoding="utf-8")
    return filepath


def _build_docker_cmd(workspace: Path, cmd: list[str], stdin_data: str = "") -> list[str]:
    """
    Build a 'docker run' command that:
    - mounts *workspace* as /workspace (read-write)
    - runs as non-root 'runner' user
    - auto-removes the container on exit
    - applies resource limits
    - passes *cmd* as the entrypoint
    """
    # On Windows, Docker Desktop accepts Windows paths — convert to posix-style
    workspace_str = str(workspace).replace("\\", "/")

    docker_cmd = [
        "docker", "run",
        "--rm",                        # auto-delete container
        "-i",                          # keep stdin open (for piping input)
        "--workdir", "/workspace",
        "-v", f"{workspace_str}:/workspace:rw",
        "--user", "runner",
        *DOCKER_RESOURCE_FLAGS,
        DOCKER_IMAGE,
        *cmd,
    ]
    return docker_cmd


def run_in_docker(
    workspace: Path,
    cmd: list[str],
    timeout: int,
    stdin_data: str = "",
) -> dict:
    """
    Run *cmd* inside an ephemeral Docker container with the workspace mounted.

    Returns a dict:
        {
            "stdout":    str,
            "stderr":    str,
            "exit_code": int,
            "timed_out": bool,
        }
    """
    docker_cmd = _build_docker_cmd(workspace, cmd)
    try:
        result = subprocess.run(
            docker_cmd,
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": f"Execution timed out after {timeout} seconds.",
            "exit_code": -1,
            "timed_out": True,
        }
    except FileNotFoundError:
        return {
            "stdout": "",
            "stderr": "Docker not found. Ensure Docker Desktop is running.",
            "exit_code": -2,
            "timed_out": False,
        }


def cleanup_workspace(workspace: Path) -> None:
    """Recursively delete the workspace folder."""
    try:
        shutil.rmtree(workspace, ignore_errors=True)
    except Exception:
        pass  # best-effort


# ── Main Entry Point ──────────────────────────────────────────────────────────


def execute(language: str, code: str, stdin: str = "") -> dict:
    """
    Full execution pipeline for a code submission.

    Parameters
    ----------
    language : str
        One of 'python', 'c', 'java'.
    code : str
        Source code to run.
    stdin : str
        Optional standard input to feed the program.

    Returns
    -------
    dict with keys:
        language    – echoed back
        stdout      – program output
        stderr      – compiler or runtime error text
        exit_code   – final exit code (compile or run)
        error       – high-level label: None | "Compilation Error" |
                      "Runtime Error" | "Timeout" | "System Error"
    """
    workspace: Optional[Path] = None
    try:
        # 1. Get language config
        config = get_language_config(language)

        # 2. Generate isolated workspace
        workspace = generate_workspace()

        # 3. Save code
        save_code(workspace, config["filename"], code)

        # 4. Compile step (if required)
        if config["compile"]:
            compile_result = run_in_docker(
                workspace,
                config["compile"],
                timeout=COMPILE_TIMEOUT,
            )

            # Non-zero exit == compilation failed
            if compile_result["exit_code"] != 0:
                return {
                    "language": language,
                    "stdout": "",
                    "stderr": compile_result["stderr"] or compile_result["stdout"],
                    "exit_code": compile_result["exit_code"],
                    "error": "Timeout" if compile_result["timed_out"] else "Compilation Error",
                }

        # 5. Run step
        run_result = run_in_docker(
            workspace,
            config["run"],
            timeout=RUN_TIMEOUT,
            stdin_data=stdin,
        )

        # 6. Determine error label
        if run_result["timed_out"]:
            error_label = "Timeout"
        elif run_result["exit_code"] != 0:
            error_label = "Runtime Error"
        else:
            error_label = None

        return {
            "language": language,
            "stdout": run_result["stdout"],
            "stderr": run_result["stderr"],
            "exit_code": run_result["exit_code"],
            "error": error_label,
        }

    except ValueError as exc:
        # Unsupported language
        return {
            "language": language,
            "stdout": "",
            "stderr": str(exc),
            "exit_code": -3,
            "error": "System Error",
        }

    except Exception as exc:
        return {
            "language": language,
            "stdout": "",
            "stderr": f"Internal error: {exc}",
            "exit_code": -4,
            "error": "System Error",
        }

    finally:
        # 7. Always clean up the workspace
        if workspace:
            cleanup_workspace(workspace)
