"""Supported medication, patient age, and treatment history."""

from .errors import AppError
from .models import PatientCase


def supported_medication(medication: str) -> str:
    normalized = medication.strip().casefold()
    if normalized in {
        "glp-1",
        "glp1",
        "glp-1 agonist",
        "glp-1 receptor agonist",
        "anticonvulsant",
        "anticonvulsants",
        "antiepileptic",
        "anti-seizure medication",
    }:
        raise AppError("underspecified_medication", "Specify a medication, not a drug class.")
    if normalized != "carbamazepine":
        raise AppError("unsupported_medication", "This prototype supports only carbamazepine.")
    return normalized


def validate_scope(case: PatientCase) -> None:
    supported_medication(case.medication)
    if case.age < 18:
        raise AppError("unsupported_patient", "This prototype is limited to fictional adults.")
    if case.first_time_use is not True:
        raise AppError(
            "unsupported_treatment_history",
            "First-time carbamazepine treatment must be explicitly confirmed.",
        )
