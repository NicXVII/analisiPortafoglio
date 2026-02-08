"""
Integration Test Runner
=======================
Utility to run integration tests in a modular way and return a structured summary.
"""

from __future__ import annotations

import re
import subprocess
import time
from typing import Any, Dict, List, Optional


def _extract_summary(text: str) -> Optional[str]:
    """
    Extract pytest summary line like '19 passed in 24.44s'.
    Returns None if not found.
    """
    match = re.search(r"=+.*? ([0-9]+) passed.* in ([0-9.]+)s", text)
    if match:
        return f"{match.group(1)} passed in {match.group(2)}s"
    return None


def _tail_lines(text: str, max_lines: int = 20) -> List[str]:
    lines = [line for line in text.splitlines() if line.strip()]
    return lines[-max_lines:]


def run_integration_tests(
    test_path: str = "tests/integration",
    pytest_args: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Run pytest integration tests and return a structured result.
    """
    cmd = ["pytest", test_path]
    if pytest_args:
        cmd.extend(pytest_args)

    start = time.time()
    completed = subprocess.run(cmd, capture_output=True, text=True)
    duration = time.time() - start

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""

    summary = _extract_summary(stdout) or _extract_summary(stderr)

    return {
        "command": " ".join(cmd),
        "exit_code": completed.returncode,
        "passed": completed.returncode == 0,
        "duration_seconds": round(duration, 2),
        "summary": summary,
        "stdout_tail": _tail_lines(stdout),
        "stderr_tail": _tail_lines(stderr),
    }
