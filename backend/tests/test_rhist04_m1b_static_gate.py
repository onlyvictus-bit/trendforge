"""R-HIST-04 M1B static migration gate (runs inside the backend suite).

The structural cutover proof lives in backend/tools/verify_m1b_cutover.py;
this test executes that exact script in a subprocess so CI enforces the gate
on every backend run. Deletion alone is not a valid migration: old
governed-path constructs must be absent AND new exact-H1 constructs must be
present.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_m1b_static_cutover_gate_passes() -> None:
    script = Path(__file__).resolve().parents[1] / "tools" / "verify_m1b_cutover.py"
    completed = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "M1B_STATIC_GATE_PASS" in completed.stdout
