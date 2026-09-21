"""The typed contract of the app context, as a type checker sees it."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

CASES = Path(__file__).parent / "typing" / "app_context_cases.py"


def test_the_app_context_cases_type_check_as_annotated() -> None:
    binary = shutil.which("basedpyright") or str(Path(sys.executable).parent / "basedpyright")
    if not Path(binary).exists():
        pytest.skip("basedpyright is not installed")

    expected = {
        number
        for number, line in enumerate(CASES.read_text().splitlines(), start=1)
        if line.rstrip().endswith("# expect-error")
    }
    result = subprocess.run([binary, "--outputjson", str(CASES)], capture_output=True, text=True)
    report = json.loads(result.stdout)
    reported = {
        diagnostic["range"]["start"]["line"] + 1
        for diagnostic in report["generalDiagnostics"]
        if diagnostic["severity"] == "error"
    }
    assert reported == expected, [
        d["message"] for d in report["generalDiagnostics"] if d["severity"] == "error"
    ]
