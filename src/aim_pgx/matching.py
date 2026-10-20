"""Match reported patient facts to CPIC recommendation records."""

from .errors import AppError
from .models import AlleleResult, Alternatives, Evidence, Finding, PatientCase
from .scope import validate_scope


def match_patient(case: PatientCase, evidence: Evidence) -> Finding:
    validate_scope(case)
    missing = []
    for label, result in [("HLA-B*15:02", case.hla_b_1502), ("HLA-A*31:01", case.hla_a_3101)]:
        if result == AlleleResult.UNKNOWN:
            missing.append(f"Reported {label} test result")

    # HLA-B-positive guidance applies regardless of HLA-A result or alternatives.
    # HLA-A-positive guidance otherwise has distinct alternative-treatment conditions.
    alternatives_matter = (
        case.hla_a_3101 == AlleleResult.POSITIVE and case.hla_b_1502 != AlleleResult.POSITIVE
    )
    unresolved = []
    if alternatives_matter and case.alternatives == Alternatives.UNKNOWN:
        populations = ["CBZ naive", "CBZ-no alternatives"]
        missing.append("Clinician-reported availability of alternative agents")
        unresolved.append(
            "Alternative agents available versus unavailable: both conditional branches are shown."
        )
    elif case.alternatives == Alternatives.UNAVAILABLE:
        populations = ["CBZ-no alternatives"]
    else:
        # For other result combinations these populations have the same source recommendation.
        populations = ["CBZ naive"]

    def key(allele: str, result: AlleleResult) -> str:
        return "No Result" if result == AlleleResult.UNKNOWN else f"{allele} {result.value}"

    lookup = {
        "HLA-A": key("*31:01", case.hla_a_3101),
        "HLA-B": key("*15:02", case.hla_b_1502),
    }
    recommendations = []
    if case.hla_a_3101 == case.hla_b_1502 == AlleleResult.UNKNOWN:
        status = "needs_information"
        summary = "No reported genetic results are available for patient-specific matching."
    else:
        for population in populations:
            candidates = [
                row
                for row in evidence.bundle.recommendations
                if row.population.strip() == population and row.lookupkey == lookup
            ]
            if len(candidates) != 1:
                raise AppError(
                    "no_matching_evidence" if not candidates else "ambiguous_evidence",
                    "The retrieved evidence does not provide one matching record for "
                    f"{population} and {lookup}. No prescribing finding was produced.",
                )
            recommendations.extend(candidates)

        if unresolved:
            status = "needs_information"
            summary = (
                "Conditional CPIC guidance found; alternative-treatment availability is unknown."
            )
        elif missing and case.hla_b_1502 == AlleleResult.POSITIVE:
            status = "matched_with_missing"
            summary = "HLA-B-positive guidance applies despite the missing HLA-A result."
        elif missing:
            status = "partial"
            summary = "CPIC No Result guidance is shown; genetic coverage remains incomplete."
        else:
            status = "matched"
            summary = (
                "CPIC guidance matched to the reported results and first-time treatment context."
            )

    return Finding(
        case=case,
        status=status,
        summary=summary,
        missing_information=missing,
        unresolved_conditions=unresolved,
        recommendations=recommendations,
        evidence=evidence,
    )
