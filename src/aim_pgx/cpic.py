"""Live CPIC retrieval, explicit snapshots, and source validation."""

from datetime import UTC, datetime
from pathlib import Path

import httpx
from pydantic import ValidationError

from .errors import AppError
from .models import Drug, Evidence, EvidenceBundle, Guideline, Publication, Recommendation
from .scope import supported_medication

BASE_URL = "https://api.cpicpgx.org/v1/"


class CPICClient:
    def __init__(self, client: httpx.Client):
        self.client = client

    def _get(self, table: str, params: dict[str, str]) -> tuple[list[dict], str]:
        request = self.client.build_request(
            "GET",
            BASE_URL + table,
            params=params,
            timeout=10.0,
            headers={"Accept": "application/json"},
        )
        for attempt in range(2):
            try:
                response = self.client.send(request)
                if response.status_code in {429, 500, 502, 503, 504} and attempt == 0:
                    response.close()
                    continue
                response.raise_for_status()
                break
            except httpx.TransportError as exc:
                if attempt == 0:
                    continue
                raise AppError(
                    "evidence_unavailable", f"CPIC request failed: {request.url}"
                ) from exc
            except httpx.HTTPStatusError as exc:
                raise AppError(
                    "evidence_unavailable",
                    f"CPIC returned HTTP {exc.response.status_code}: {request.url}",
                ) from exc
        try:
            rows = response.json()
        except ValueError as exc:
            raise AppError("invalid_evidence", "CPIC returned invalid JSON.") from exc
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise AppError("invalid_evidence", "Expected a CPIC array of records.")
        if not rows:
            raise AppError("empty_evidence", f"CPIC returned no records: {request.url}")
        # PostgREST may paginate results: never interpret a truncated response as complete evidence.
        content_range = response.headers.get("content-range", "")
        if response.status_code == 206 or (
            "/" in content_range and content_range.rsplit("/", 1)[1] not in {"*", str(len(rows))}
        ):
            raise AppError("invalid_evidence", "CPIC returned an incomplete result range.")
        return rows, str(request.url)

    def retrieve(self, medication: str) -> Evidence:
        name = supported_medication(medication)
        try:
            drugs, drug_url = self._get("drug", {"name": f"eq.{name}"})
            if len(drugs) != 1:
                raise AppError("ambiguous_evidence", "Expected one carbamazepine drug record.")
            drug = Drug.model_validate(drugs[0])
            guidelines, guideline_url = self._get("guideline", {"id": f"eq.{drug.guidelineid}"})
            if len(guidelines) != 1:
                raise AppError("ambiguous_evidence", "Expected one linked guideline record.")
            rows, recommendation_url = self._get("recommendation", {"drugid": f"eq.{drug.drugid}"})
            publications, publication_url = self._get(
                "publication", {"guidelineid": f"eq.{drug.guidelineid}"}
            )
            bundle = EvidenceBundle(
                retrieved_at=datetime.now(UTC),
                request_urls=[drug_url, guideline_url, recommendation_url, publication_url],
                drug=drug,
                guideline=Guideline.model_validate(guidelines[0]),
                recommendations=[Recommendation.model_validate(row) for row in rows],
                publications=[Publication.model_validate(row) for row in publications],
            )
        except ValidationError as exc:
            raise AppError("invalid_evidence", f"CPIC response failed validation: {exc}") from exc
        return Evidence(mode="live", bundle=bundle)


def load_snapshot(path: Path, medication: str) -> Evidence:
    supported_medication(medication)
    try:
        bundle = EvidenceBundle.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise AppError("invalid_snapshot", f"Cannot load validated CPIC snapshot: {exc}") from exc
    return Evidence(mode="snapshot", bundle=bundle, snapshot_path=str(path))


def save_snapshot(evidence: Evidence, path: Path) -> None:
    if evidence.mode != "live":
        raise AppError(
            "invalid_snapshot", "Only a successful live retrieval can create a snapshot."
        )
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Avoid overwriting an earlier point-in-time evidence record.
        with path.open("x", encoding="utf-8") as output:
            output.write(evidence.bundle.model_dump_json(indent=2) + "\n")
    except OSError as exc:
        raise AppError("snapshot_write_failed", f"Cannot save snapshot: {exc}") from exc
