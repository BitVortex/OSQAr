from __future__ import annotations

import argparse
from pathlib import Path

from tools import osqar_cmd_sign
from tools.osqar_cli import main


def test_shipment_verify_rejects_missing_shipment(tmp_path: Path) -> None:
    assert main(["shipment", "verify", "--shipment", str(tmp_path / "missing")]) == 2


def test_baseline_diff_rejects_missing_baselines(tmp_path: Path) -> None:
    assert (
        main(
            [
                "baseline",
                "diff",
                "old",
                "new",
                "--project",
                str(tmp_path),
            ]
        )
        == 2
    )


def test_sign_verify_rejects_missing_manifest(tmp_path: Path) -> None:
    assert main(["sign", "verify", "--manifest", str(tmp_path / "missing")]) == 2


def test_signing_reports_missing_external_tool(tmp_path: Path, monkeypatch) -> None:
    manifest = tmp_path / "SHA256SUMS"
    manifest.write_text("payload", encoding="utf-8")
    monkeypatch.setattr(osqar_cmd_sign, "_find_gpg", lambda: None)

    args = argparse.Namespace(manifest=str(manifest), signature=None)
    assert osqar_cmd_sign.cmd_verify(args) == 2
