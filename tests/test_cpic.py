import json

import httpx
import pytest
from pydantic import ValidationError

from aim_pgx.cpic import CPICClient, load_snapshot, save_snapshot
from aim_pgx.errors import AppError
from aim_pgx.models import EvidenceBundle


def payload(raw, request):
    table = request.url.path.rsplit("/", 1)[1]
    return {
        "drug": [raw["drug"]],
        "guideline": [raw["guideline"]],
        "recommendation": raw["recommendations"],
        "publication": raw["publications"],
    }[table]


def test_live_client_links_records_and_keeps_provenance(raw_bundle):
    requests = []

    def handler(request):
        requests.append(request)
        assert request.extensions["timeout"]["read"] == 10
        return httpx.Response(200, json=payload(raw_bundle, request))

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = CPICClient(client).retrieve("  CARBAMAZEPINE  ")
    assert result.mode == "live"
    assert len(requests) == 4
    assert requests[1].url.params["id"] == "eq.100423"
    assert requests[2].url.params["drugid"] == "eq.RxNorm:2002"
    assert result.bundle.recommendations[0].model_dump() == raw_bundle["recommendations"][0]
    assert result.bundle.retrieved_at.tzinfo is not None
    assert result.bundle.request_urls == [str(r.url) for r in requests]


@pytest.mark.parametrize("failure", ["timeout", "503", "429"])
def test_transient_failure_retried_once(raw_bundle, failure):
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        if calls == 1:
            if failure == "timeout":
                raise httpx.ReadTimeout("timeout", request=request)
            return httpx.Response(int(failure))
        return httpx.Response(200, json=payload(raw_bundle, request))

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert CPICClient(client).retrieve("carbamazepine").bundle.drug.drugid == "RxNorm:2002"
    assert calls == 5


@pytest.mark.parametrize("status,expected_calls", [(503, 2), (429, 2), (404, 1)])
def test_permanent_failure_is_explicit(status, expected_calls):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(AppError) as error:
            CPICClient(client).retrieve("carbamazepine")
    assert error.value.code == "evidence_unavailable"
    assert len(calls) == expected_calls


@pytest.mark.parametrize(
    "response,code",
    [
        (httpx.Response(200, json=[]), "empty_evidence"),
        (httpx.Response(200, json={}), "invalid_evidence"),
        (httpx.Response(200, text="not JSON"), "invalid_evidence"),
        (httpx.Response(200, json=[{}]), "invalid_evidence"),
        (httpx.Response(200, json=[{}, {}]), "ambiguous_evidence"),
    ],
)
def test_unexpected_responses(response, code):
    with httpx.Client(transport=httpx.MockTransport(lambda request: response)) as client:
        with pytest.raises(AppError) as error:
            CPICClient(client).retrieve("carbamazepine")
    assert error.value.code == code


def test_partial_response_rejected(raw_bundle):
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                206, json=[raw_bundle["drug"]], headers={"content-range": "0-0/2"}
            )
        )
    ) as client:
        with pytest.raises(AppError, match="incomplete result range"):
            CPICClient(client).retrieve("carbamazepine")


@pytest.mark.parametrize("field", ["lookupkey", "population", "drugrecommendation", "comments"])
def test_required_recommendation_fields(raw_bundle, field):
    del raw_bundle["recommendations"][0][field]
    with pytest.raises(ValidationError):
        EvidenceBundle.model_validate(raw_bundle)


@pytest.mark.parametrize("change", ["duplicate", "context", "gene", "link"])
def test_conflicting_or_new_evidence_fails_closed(raw_bundle, change):
    row = raw_bundle["recommendations"][0]
    if change == "duplicate":
        raw_bundle["recommendations"].append(row)
    elif change == "context":
        row["population"] = "unexpected new context"
    elif change == "gene":
        row["lookupkey"]["HLA-A"] = "unexpected result"
    else:
        row["guidelineid"] = 999
    with pytest.raises(ValidationError):
        EvidenceBundle.model_validate(raw_bundle)


def test_snapshot_round_trip_is_explicit_and_preserves_date(evidence, tmp_path):
    path = tmp_path / "saved.json"
    live = evidence.model_copy(update={"mode": "live", "snapshot_path": None})
    save_snapshot(live, path)
    restored = load_snapshot(path, "carbamazepine")
    assert restored.mode == "snapshot"
    assert restored.bundle == live.bundle
    with pytest.raises(AppError, match="Only a successful live"):
        save_snapshot(restored, tmp_path / "resaved.json")
    with pytest.raises(AppError, match="Cannot save snapshot"):
        save_snapshot(live, path)


def test_invalid_snapshot_never_becomes_live(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({}), encoding="utf-8")
    with pytest.raises(AppError) as error:
        load_snapshot(path, "carbamazepine")
    assert error.value.code == "invalid_snapshot"
