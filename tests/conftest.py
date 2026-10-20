import json
from pathlib import Path

import pytest

from aim_pgx.models import Evidence, EvidenceBundle, PatientCase

FIXTURE = Path(__file__).parent / "fixtures" / "cpic_carbamazepine.json"


@pytest.fixture
def raw_bundle():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture
def evidence():
    return Evidence(
        mode="snapshot",
        bundle=EvidenceBundle.model_validate_json(FIXTURE.read_text(encoding="utf-8")),
        snapshot_path=str(FIXTURE),
    )


@pytest.fixture
def case():
    return PatientCase(
        case_id="fictional-test",
        age=34,
        medication="carbamazepine",
        first_time_use=True,
        hla_b_1502="negative",
        hla_a_3101="negative",
        alternatives="unknown",
    )
