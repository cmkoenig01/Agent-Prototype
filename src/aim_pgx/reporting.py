"""Turn a structured finding into a readable terminal report."""

from .models import Evidence, Finding

SCOPE_NOTE = (
    "This finding describes the checked genetic guidance only. It does not establish overall "
    "medication suitability or prescribe an alternative treatment."
)
CONTEXT_LABELS = {
    "CBZ naive": "First-time carbamazepine treatment",
    "CBZ-no alternatives": "No alternative agents available (first-time treatment)",
}


def evidence_header(evidence: Evidence, *, details: bool) -> list[str]:
    bundle = evidence.bundle
    lines = [
        f"Evidence mode: {evidence.mode.upper()}",
        f"Retrieved at (UTC): {bundle.retrieved_at.isoformat()}",
        f"Guideline source: {bundle.guideline.url}",
    ]
    if evidence.mode == "snapshot":
        lines.append(
            f"SAVED RESPONSE; no live CPIC request was made. File: {evidence.snapshot_path}"
        )
    if details:
        lines.extend(
            [
                f"Drug: {bundle.drug.name} ({bundle.drug.drugid}), version {bundle.drug.version}",
                f"Guideline: {bundle.guideline.name} (ID {bundle.guideline.id}, "
                f"version {bundle.guideline.version})",
            ]
        )
        for pub in bundle.publications:
            lines.append(
                f"Publication: {pub.title} ({pub.year}); https://pubmed.ncbi.nlm.nih.gov/{pub.pmid}/"
            )
        lines.extend(f"Request source: {url}" for url in bundle.request_urls)
    return lines


def format_finding(finding: Finding, *, details: bool = False) -> str:
    case = finding.case
    lines = [
        "PHARMACOGENETIC ASSESSMENT (fictional case)",
        f"Case: {case.case_id} | age {case.age} | medication {case.medication}",
        f"First-time treatment: {case.first_time_use} | alternatives: {case.alternatives.value}",
        f"Reported HLA-B*15:02: {case.hla_b_1502.value}",
        f"Reported HLA-A*31:01: {case.hla_a_3101.value}",
        f"Status: {finding.status}",
        finding.summary,
        "Missing information: " + ("; ".join(finding.missing_information) or "None for this scope"),
        "Unresolved conditions: " + ("; ".join(finding.unresolved_conditions) or "None"),
    ]
    for row in finding.recommendations:
        lines.extend(
            [
                "",
                f"CPIC record {row.id} | strength: {row.classification}",
                f"Context: {CONTEXT_LABELS[row.population.strip()]}",
                f"CPIC recommendation (source text): {row.drugrecommendation}",
            ]
        )
        if details:
            lines.extend(
                [
                    f"Source lookup key: {row.lookupkey}",
                    f"Source population: {row.population.strip()} | version: {row.version}",
                    f"Implications: {row.implications}",
                    f"Source comments: {row.comments}",
                ]
            )
    if not finding.recommendations:
        lines.append("No patient-specific recommendation selected.")
    lines.extend(["", *evidence_header(finding.evidence, details=details), "", SCOPE_NOTE])
    return "\n".join(lines)
