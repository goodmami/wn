import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_validate_missing_file_reports_clean_error():
    missing = "does-not-exist-wn-validate.xml"
    proc = subprocess.run(
        [sys.executable, "-m", "wn", "validate", missing],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert f"cannot find file: {missing}" in proc.stderr
    assert "Traceback" not in proc.stderr
