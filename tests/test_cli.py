import subprocess
import sys
from pathlib import Path

import pytest

from aim_pgx.cli import main
from aim_pgx.cpic import CPICClient, load_snapshot
from aim_pgx.errors import AppError
from aim_pgx.models import PatientCase

FIXTURE = str(Path(__file__).parent / "fixtures" / "cpic_carbamazepine.json")


def test_import_does_not_execute_teammate_script():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import aim_pgx.cli, sys; "
            "assert not {'agent', 'torch', 'transformers'} & sys.modules.keys()",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert not result.stdout


def test_live_assessment_is_default(case, evidence, capsys, monkeypatch):
    requests = []

    def retrieve(self, medication):
        requests.append(medication)
        return evidence.model_copy(update={"mode": "live", "snapshot_path": None})

    monkeypatch.setattr(CPICClient, "retrieve", retrieve)
    assert main(["--case", "examples/both_negative.json"]) == 0
    assert requests == [case.medication]
    output = capsys.readouterr().out
    assert "Evidence mode: LIVE" in output
    assert "8480095" in output
    assert "does not establish overall medication suitability" in output


def test_snapshot_is_explicit_and_never_contacts_cpic(capsys, monkeypatch):
    def must_not_retrieve(*args):
        pytest.fail("Snapshot assessment must not contact CPIC")

    monkeypatch.setattr(CPICClient, "retrieve", must_not_retrieve)
    assert main(["--case", "examples/both_negative.json", "--snapshot", FIXTURE]) == 0
    output = capsys.readouterr().out
    assert "SNAPSHOT" in output and "SAVED RESPONSE" in output
    assert "2026-10-19" in output


@pytest.mark.parametrize("details", [False, True])
def test_details_controls_source_metadata_without_changing_guidance(capsys, details):
    args = ["--case", "examples/both_negative.json", "--snapshot", FIXTURE]
    assert main(args + (["--details"] if details else [])) == 0
    output = capsys.readouterr().out
    assert "CPIC record 8480095" in output
    assert "Use carbamazepine per standard dosing guidelines." in output
    assert ("Source comments:" in output) is details
    assert ("Request source:" in output) is details
    assert ("Publication:" in output) is details


@pytest.mark.parametrize(
    "example,expected",
    [
        ("hla_b_positive", "matched"),
        ("hla_b_positive_a_unknown", "matched_with_missing"),
        ("hla_a_positive_alternatives", "matched"),
        ("hla_a_positive_no_alternatives", "matched"),
        ("hla_a_positive_alternatives_unknown", "needs_information"),
        ("both_negative", "matched"),
        ("one_result_missing", "partial"),
        ("both_results_missing", "needs_information"),
    ],
)
def test_same_command_accepts_different_patients(example, expected, capsys):
    assert main(["--case", f"examples/{example}.json", "--snapshot", FIXTURE]) == 0
    output = capsys.readouterr().out
    assert f"Status: {expected}\n" in output
    if example == "both_results_missing":
        assert "No patient-specific recommendation selected" in output
    if example == "hla_a_positive_alternatives_unknown":
        assert "8480088" in output and "8480097" in output
        assert "Unresolved conditions:" in output


@pytest.mark.parametrize(
    "example,code",
    [
        ("unsupported_medication", "unsupported_medication"),
        ("drug_class", "underspecified_medication"),
    ],
)
def test_unsupported_cases_rejected_without_network(example, code, capsys, monkeypatch):
    def must_not_retrieve(*args):
        pytest.fail("Unsupported cases must be rejected before network access")

    monkeypatch.setattr(CPICClient, "retrieve", must_not_retrieve)
    assert main(["--case", f"examples/{example}.json"]) == 2
    assert code in capsys.readouterr().err


def test_live_failure_does_not_fall_back_to_snapshot(capsys, monkeypatch):
    def unavailable(*args):
        raise AppError("evidence_unavailable", "offline")

    monkeypatch.setattr(CPICClient, "retrieve", unavailable)
    assert main(["--case", "examples/both_negative.json"]) == 2
    captured = capsys.readouterr()
    assert "evidence_unavailable" in captured.err
    assert "PHARMACOGENETIC ASSESSMENT" not in captured.out


def test_save_snapshot_keeps_real_source_provenance(evidence, tmp_path, monkeypatch):
    live = evidence.model_copy(update={"mode": "live", "snapshot_path": None})
    monkeypatch.setattr(CPICClient, "retrieve", lambda *args: live)
    path = tmp_path / "saved.json"
    assert main(["--case", "examples/both_negative.json", "--save-snapshot", str(path)]) == 0
    assert load_snapshot(path, "carbamazepine").bundle == evidence.bundle


def test_snapshot_and_save_snapshot_are_mutually_exclusive():
    with pytest.raises(SystemExit) as error:
        main(
            [
                "--case",
                "examples/both_negative.json",
                "--snapshot",
                FIXTURE,
                "--save-snapshot",
                "unused.json",
            ]
        )
    assert error.value.code == 2


@pytest.mark.parametrize("command", ["demo", "assess", "evidence"])
def test_removed_subcommands_are_rejected(command):
    with pytest.raises(SystemExit) as error:
        main([command, "--case", "examples/both_negative.json"])
    assert error.value.code == 2


def test_invalid_case_is_an_explicit_error(tmp_path, capsys):
    path = tmp_path / "invalid.json"
    path.write_text("not JSON", encoding="utf-8")
    assert main(["--case", str(path)]) == 2
    assert "invalid_case" in capsys.readouterr().err


def test_all_examples_have_valid_schema():
    for path in Path("examples").glob("*.json"):
        PatientCase.model_validate_json(path.read_text(encoding="utf-8"))
