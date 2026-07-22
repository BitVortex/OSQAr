from __future__ import annotations

import subprocess
from pathlib import Path

from tools import osqar_cli_util


def test_run_propagates_child_exit_code(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 17),
    )

    assert osqar_cli_util.run(["failing-tool"], cwd=tmp_path) == 17


def test_run_returns_127_when_tool_is_missing(tmp_path: Path, monkeypatch, capsys) -> None:
    def missing(*args, **kwargs):
        raise FileNotFoundError("not installed")

    monkeypatch.setattr(subprocess, "run", missing)

    assert osqar_cli_util.run(["missing-tool"], cwd=tmp_path) == 127
    assert "command not found: missing-tool" in capsys.readouterr().err


def test_run_capture_reports_missing_tool(tmp_path: Path, monkeypatch) -> None:
    def missing(*args, **kwargs):
        raise FileNotFoundError("not installed")

    monkeypatch.setattr(subprocess, "run", missing)

    rc, output = osqar_cli_util.run_capture(["missing-tool"], cwd=tmp_path)
    assert rc == 127
    assert "command not found: missing-tool" in output
