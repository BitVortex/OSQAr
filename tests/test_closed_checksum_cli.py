from __future__ import annotations

from pathlib import Path

from tools.osqar_cli import main


def test_checksum_cli_exposes_closed_set_verification(tmp_path: Path) -> None:
    (tmp_path / "declared.txt").write_text("declared\n", encoding="utf-8")
    manifest = tmp_path / "SHA256SUMS"
    assert main(["checksum", "generate", "--root", str(tmp_path), "--output", str(manifest)]) == 0
    (tmp_path / "unexpected.txt").write_text("unexpected\n", encoding="utf-8")

    rc = main(
        [
            "checksum",
            "verify",
            "--root",
            str(tmp_path),
            "--manifest",
            str(manifest),
            "--closed-set",
        ]
    )

    assert rc == 1
