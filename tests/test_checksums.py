from pathlib import Path

from tools import generate_checksums


FIXTURES = Path(__file__).parent / "fixtures" / "checksums"


def test_checksum_verify_reports_malformed_manifest(capsys):
    result = generate_checksums.cli(
        [
            "--root",
            str(FIXTURES / "root"),
            "--verify",
            str(FIXTURES / "malformed.SHA256SUMS"),
        ]
    )

    assert result == 2
    assert "invalid manifest line" in capsys.readouterr().err.lower()
