"""The typed contract of arkitekt's public surface, as a type checker sees it.

Each ``tests/typing/*_cases.py`` file is checked by basedpyright, not run: a line
ending in ``# expect-error`` must be reported, and every other line must not.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

CASES = sorted((Path(__file__).parent / "typing").glob("*_cases.py"))


@pytest.mark.parametrize("cases", CASES, ids=[c.stem for c in CASES])
def test_the_cases_type_check_as_annotated(cases: Path) -> None:
    binary = shutil.which("basedpyright") or str(Path(sys.executable).parent / "basedpyright")
    if not Path(binary).exists():
        pytest.skip("basedpyright is not installed")

    expected = {
        number
        for number, line in enumerate(cases.read_text().splitlines(), start=1)
        if line.rstrip().endswith("# expect-error")
    }
    # The interpreter running the tests, so the cases see the arkitekt under test.
    result = subprocess.run(
        [binary, "--pythonpath", sys.executable, "--outputjson", str(cases)],
        capture_output=True,
        text=True,
    )
    report = json.loads(result.stdout)
    reported = {
        diagnostic["range"]["start"]["line"] + 1
        for diagnostic in report["generalDiagnostics"]
        if diagnostic["severity"] == "error"
    }
    assert reported == expected, [
        (d["range"]["start"]["line"] + 1, d["message"])
        for d in report["generalDiagnostics"]
        if d["severity"] == "error"
    ]
