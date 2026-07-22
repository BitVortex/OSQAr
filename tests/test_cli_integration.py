from __future__ import annotations

from pathlib import Path

from tools.osqar_cli import main


FIXTURES = Path(__file__).parent / "fixtures"


def test_top_level_cli_propagates_traceability_input_error() -> None:
    rc = main(["traceability", str(FIXTURES / "needs" / "empty.json")])
    assert rc == 2


def test_top_level_cli_propagates_checksum_manifest_error() -> None:
    rc = main(
        [
            "checksum",
            "verify",
            "--root",
            str(FIXTURES / "checksums" / "root"),
            "--manifest",
            str(FIXTURES / "checksums" / "malformed.SHA256SUMS"),
        ]
    )
    assert rc == 2
