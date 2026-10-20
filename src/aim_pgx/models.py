"""Data structures for patient facts, CPIC records, and matched findings."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AlleleResult(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    UNKNOWN = "unknown"


class Alternatives(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class PatientCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    age: int = Field(strict=True, ge=0, le=120)
    medication: str = Field(min_length=1)
    first_time_use: Annotated[bool, Field(strict=True)] | None
    hla_b_1502: AlleleResult
    hla_a_3101: AlleleResult
    alternatives: Alternatives


class CPICRecord(BaseModel):
    # Keep extra source fields, rather than discarding parts of the retrieved evidence.
    model_config = ConfigDict(extra="allow", strict=True)


class Drug(CPICRecord):
    drugid: str
    name: str
    guidelineid: int
    version: int


class Guideline(CPICRecord):
    id: int
    name: str
    genes: list[str]
    url: str
    version: int


class Recommendation(CPICRecord):
    id: int
    guidelineid: int
    drugid: str
    lookupkey: dict[str, str]
    population: str
    drugrecommendation: str = Field(min_length=1)
    implications: dict[str, str]
    classification: str = Field(min_length=1)
    comments: str | None
    version: int


class Publication(CPICRecord):
    id: int
    guidelineid: int
    title: str
    year: int
    pmid: str
    version: int


class EvidenceBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    retrieved_at: datetime
    request_urls: list[str]
    drug: Drug
    guideline: Guideline
    recommendations: list[Recommendation] = Field(min_length=1)
    publications: list[Publication] = Field(min_length=1)

    @model_validator(mode="after")
    def consistent_records(self):
        if self.retrieved_at.tzinfo is None:
            raise ValueError("retrieved_at must contain a timezone")
        if len(self.request_urls) != 4 or any(
            not url.startswith("https://api.cpicpgx.org/v1/") for url in self.request_urls
        ):
            raise ValueError("Expected four public CPIC source URLs")
        if self.drug.drugid != "RxNorm:2002" or self.drug.name != "carbamazepine":
            raise ValueError("Evidence does not describe carbamazepine")
        if self.guideline.id != self.drug.guidelineid:
            raise ValueError("Drug and guideline identifiers disagree")
        if not {"HLA-A", "HLA-B"}.issubset(self.guideline.genes):
            raise ValueError("Guideline must include both HLA genes")
        seen_ids, seen_keys = set(), set()
        for row in self.recommendations:
            if row.drugid != self.drug.drugid or row.guidelineid != self.guideline.id:
                raise ValueError("Recommendation is linked to different evidence")
            for gene, allele in [("HLA-A", "*31:01"), ("HLA-B", "*15:02")]:
                if row.lookupkey.get(gene) not in {
                    f"{allele} positive",
                    f"{allele} negative",
                    "No Result",
                }:
                    raise ValueError(f"Unrecognized {gene} recommendation lookup key")
            if set(row.lookupkey) != {"HLA-A", "HLA-B"}:
                raise ValueError("Unexpected recommendation genes")
            population = row.population.strip()
            if population not in {"CBZ naive", "CBZ-no alternatives", "CBZ use >3mos"}:
                raise ValueError(f"Unrecognized treatment context: {population}")
            key = (population, tuple(sorted(row.lookupkey.items())))
            if row.id in seen_ids or key in seen_keys:
                raise ValueError("Duplicate or conflicting recommendation records")
            seen_ids.add(row.id)
            seen_keys.add(key)
        if any(p.guidelineid != self.guideline.id for p in self.publications):
            raise ValueError("Publication is linked to another guideline")
        return self


class Evidence(BaseModel):
    mode: Literal["live", "snapshot"]
    bundle: EvidenceBundle
    snapshot_path: str | None = None


class Finding(BaseModel):
    case: PatientCase
    status: Literal["matched", "matched_with_missing", "partial", "needs_information"]
    summary: str
    missing_information: list[str]
    unresolved_conditions: list[str]
    recommendations: list[Recommendation]
    evidence: Evidence
