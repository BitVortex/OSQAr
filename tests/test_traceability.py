import json
import os
from pathlib import Path

from tools import traceability_check


FIXTURES = Path(__file__).parent / "fixtures"


def test_traceability_rejects_empty_needs(capsys):
    result = traceability_check.cli([str(FIXTURES / "needs" / "empty.json")])

    assert result == 2
    assert "no needs" in capsys.readouterr().err.lower()


def test_traceability_rejects_duplicate_ids(capsys):
    result = traceability_check.cli(
        [str(FIXTURES / "needs" / "duplicate-ids.json")]
    )

    assert result == 2
    assert "duplicate need id: REQ_DUP" in capsys.readouterr().err


def test_traceability_rejects_need_without_id(capsys):
    result = traceability_check.cli(
        [str(FIXTURES / "needs" / "missing-id.json")]
    )

    assert result == 2
    assert "missing a non-empty id" in capsys.readouterr().err


def test_traceability_invalidates_stale_report_before_malformed_input(
    tmp_path: Path,
) -> None:
    needs = tmp_path / "needs.json"
    needs.write_text("not json\n", encoding="utf-8")
    report = tmp_path / "report.json"
    report.write_text(
        '{"schema":"osqar.traceability-report.v1","status":"PASS"}\n',
        encoding="utf-8",
    )

    result = traceability_check.cli(
        [str(needs), "--json-report", str(report)]
    )

    assert result == 2
    assert not report.exists()


def test_traceability_rejects_report_alias_to_input(
    tmp_path: Path, capsys
) -> None:
    needs = tmp_path / "needs.json"
    original = json.dumps({"needs": [{"id": "REQ_1", "links": []}]})
    needs.write_text(original, encoding="utf-8")

    result = traceability_check.cli(
        [str(needs), "--json-report", str(needs)]
    )

    assert result == 2
    assert "aliases needs input" in capsys.readouterr().err
    assert needs.read_text(encoding="utf-8") == original


def test_traceability_report_replace_failure_leaves_no_report(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    needs = tmp_path / "needs.json"
    needs.write_text(
        json.dumps({"needs": [{"id": "REQ_1", "links": []}]}),
        encoding="utf-8",
    )
    report = tmp_path / "report.json"
    monkeypatch.setattr(
        traceability_check.os,
        "replace",
        lambda *_args: (_ for _ in ()).throw(OSError("replace denied")),
    )

    result = traceability_check.cli(
        [str(needs), "--json-report", str(report)]
    )

    assert result == 2
    assert "replace denied" in capsys.readouterr().err
    assert not report.exists()
    assert not list(tmp_path.glob(".report.json.*.tmp"))


def test_traceability_rejects_symlink_and_hardlink_report_aliases(
    tmp_path: Path, capsys
) -> None:
    for alias_kind in ("symlink", "hardlink"):
        case = tmp_path / alias_kind
        case.mkdir()
        needs = case / "needs.json"
        needs.write_text(
            json.dumps({"needs": [{"id": "REQ_1", "links": []}]}),
            encoding="utf-8",
        )
        original = needs.read_bytes()
        report = case / "report.json"
        if alias_kind == "symlink":
            report.symlink_to(needs)
        else:
            os.link(needs, report)

        result = traceability_check.cli(
            [str(needs), "--json-report", str(report)]
        )

        assert result == 2
        assert "aliases needs input" in capsys.readouterr().err
        assert needs.read_bytes() == original


def test_traceability_failed_unlink_poisons_stale_report(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    needs = tmp_path / "needs.json"
    needs.write_text("not json\n", encoding="utf-8")
    report = tmp_path / "report.json"
    report.write_text(
        '{"schema":"osqar.traceability-report.v1","status":"PASS"}\n',
        encoding="utf-8",
    )
    original_unlink = Path.unlink

    def deny_report_unlink(path: Path, *args, **kwargs):
        if path == report:
            raise PermissionError("unlink denied")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", deny_report_unlink)

    result = traceability_check.cli(
        [str(needs), "--json-report", str(report)]
    )

    assert result == 2
    assert "unlink denied" in capsys.readouterr().err
    assert report.read_text(encoding="utf-8").startswith("OSQAR INVALID")
