"""Insurance matching and denial-risk skill for clinic-note inputs."""

from __future__ import annotations

import re
from typing import Any

GLUCOSE_DIABETES_THRESHOLD = 126.0
A1C_DIABETES_THRESHOLD = 7.0
STRICT_GLUCOSE_THRESHOLD = 140.0
STRICT_A1C_THRESHOLD = 7.5
BMI_OBESITY_THRESHOLD = 30.0

POLICIES: dict[str, dict[str, Any]] = {
    "A": {
        "name": "Insurance A - Diabetes-focused policy",
        "summary": "Requires Type 2 Diabetes evidence and uncontrolled glucose or A1C.",
        "criteria": [
            "Type 2 Diabetes diagnosis or diabetes-positive status",
            "Glucose >= 126 mg/dL or A1C >= 7.0%",
            "Request for glycemic control, not weight loss alone",
            "Prior first-line therapy history or contraindication documented",
        ],
        "strictness": "medium",
    },
    "B": {
        "name": "Insurance B - Strict step therapy policy",
        "summary": "Requires diabetes evidence plus stronger lab and step-therapy support.",
        "criteria": [
            "Type 2 Diabetes diagnosis or diabetes-positive status",
            "Glucose >= 140 mg/dL or A1C >= 7.5%",
            "Prior alternatives, failed therapy, or contraindications documented",
            "Clear provider medical necessity rationale",
        ],
        "strictness": "high",
    },
    "C": {
        "name": "Insurance C - Risk-based policy",
        "summary": "Requires diabetes evidence plus an additional clinical risk factor.",
        "criteria": [
            "Type 2 Diabetes diagnosis or diabetes-positive status",
            "Glucose >= 126 mg/dL or A1C >= 7.0%",
            "Additional risk factor such as BMI >= 30, cardiovascular risk, or kidney risk",
            "Safety history reviewed",
        ],
        "strictness": "medium",
    },
    "D": {
        "name": "Insurance D - Documentation completeness policy",
        "summary": "Focuses on whether the note has enough objective evidence for review.",
        "criteria": [
            "Type 2 Diabetes diagnosis or diabetes-positive status",
            "Objective glucose or A1C documentation",
            "BMI or weight documentation",
            "Provider medical necessity rationale",
        ],
        "strictness": "low",
    },
}


def _normalize(text: str) -> str:
    return " ".join(text.replace("—", "-").replace("–", "-").split())


def _first_number(patterns: list[str], text: str) -> float | None:
    normalized = _normalize(text)
    for pattern in patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def _first_text(patterns: list[str], text: str) -> str | None:
    normalized = _normalize(text)
    for pattern in patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip(" .;:-")
    return None



def _first_line_text(patterns: list[str], text: str) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip(" .;:-")
    return None

def _has_any(text: str, phrases: list[str]) -> bool:
    normalized = _normalize(text).lower()
    return any(_normalize(phrase).lower() in normalized for phrase in phrases)


def _lab_meets_threshold(value: float | None, threshold: float) -> bool:
    return value is not None and value >= threshold


def extract_patient_case(note_text: str) -> dict[str, Any]:
    """Extract prior authorization fields from a general synthetic clinic note."""
    insurance = _first_text(
        [
            r"Insurance\s+Plan\s+([A-D])\b",
            r"Insurance\s*:\s*(?:Insurance\s*)?([A-D])\b",
            r"Payer\s*:\s*(?:Insurance\s*)?([A-D])\b",
            r"Plan\s*:\s*(?:Insurance\s*)?([A-D])\b",
        ],
        note_text,
    )
    patient_id = _first_text(
        [r"Patient\s+ID\s*:\s*(\d+)", r"Patient\s+ID\s+(\d+)"],
        note_text,
    )
    age = _first_number(
        [r"Age\s*:\s*(\d+(?:\.\d+)?)", r"Age\s+(\d+(?:\.\d+)?)\s+years"],
        note_text,
    )
    medication = _first_line_text(
        [
            r"Medication\s+requested\s*:\s*([^\n\r]+)",
            r"Requested\s+medication\s*:\s*([^\n\r]+)",
            r"Medication\s*:\s*([^\n\r]+)",
            r"Drug\s*:\s*([^\n\r]+)",
        ],
        note_text,
    )
    glucose = _first_number(
        [
            r"(?:Plasma\s+)?Glucose.*?(\d+(?:\.\d+)?)\s*mg/dL",
            r"fasting\s+glucose.*?(\d+(?:\.\d+)?)\s*mg/dL",
        ],
        note_text,
    )
    a1c = _first_number(
        [
            r"(?:Hemoglobin\s+)?A1c[^0-9]{0,20}(\d+(?:\.\d+)?)\s*%?",
            r"HbA1c[^0-9]{0,20}(\d+(?:\.\d+)?)\s*%?",
        ],
        note_text,
    )
    bmi = _first_number(
        [
            r"Body\s+Mass\s+Index\s+\(BMI\)[^0-9]{0,40}(\d+(?:\.\d+)?)",
            r"\bBMI[^0-9]{0,20}(\d+(?:\.\d+)?)",
        ],
        note_text,
    )

    diabetes_negative = _has_any(
        note_text,
        ["Diabetes Status: NEGATIVE", "No diabetes diagnosed", "No documented Type 2 diabetes"],
    )
    diabetes_positive = (
        _has_any(
            note_text,
            [
                "Diabetes Status: POSITIVE",
                "diabetes diagnosed",
                "Type 2 diabetes diagnosis",
                "Type 2 diabetes mellitus",
                "T2DM",
                "established Type 2 diabetes",
            ],
        )
        and not diabetes_negative
    )
    rationale_present = _has_any(
        note_text,
        [
            "clinical justification",
            "medically necessary",
            "medical necessity",
            "provider requests prior authorization",
            "request ozempic",
            "requested to improve glycemic control",
        ],
    )
    prior_therapy_present = _has_any(
        note_text,
        [
            "metformin",
            "failed",
            "prior medication",
            "alternative",
            "contraindicated",
            "SGLT2",
            "sulfonylurea",
            "insulin use",
            "intolerance",
        ],
    )
    safety_review_present = _has_any(
        note_text,
        ["pancreatitis", "thyroid", "MEN2", "allergy", "contraindication"],
    )
    return {
        "success": True,
        "patient": {
            "patient_id": patient_id,
            "insurance_plan": insurance,
            "age": age,
            "medication_requested": medication,
            "glucose_mg_dl": glucose,
            "a1c": a1c,
            "bmi": bmi,
            "diabetes_positive": diabetes_positive,
            "rationale_present": rationale_present,
            "prior_therapy_present": prior_therapy_present,
            "safety_review_present": safety_review_present,
        },
        "notes": [
            "Clinic notes may use varied labels; parser supports common note patterns.",
            "Glucose remains the main dataset-backed lab variable; A1C is used only when present in the note.",
        ],
    }


def list_policies() -> dict[str, Any]:
    """List available simulated insurance policies."""
    return {
        "success": True,
        "policies": {
            policy_id: {
                "name": policy["name"],
                "summary": policy["summary"],
                "strictness": policy["strictness"],
            }
            for policy_id, policy in POLICIES.items()
        },
    }


def get_policy(policy_id: str) -> dict[str, Any]:
    """Return one simulated insurance policy by ID A, B, C, or D."""
    normalized = policy_id.strip().upper()
    if normalized not in POLICIES:
        return {"success": False, "error": f"Unknown policy: {policy_id}"}
    return {"success": True, "policy_id": normalized, "policy": POLICIES[normalized]}


def evaluate_prior_authorization(note_text: str) -> dict[str, Any]:
    """Evaluate a clinic note against matched simulated insurance criteria."""
    extracted = extract_patient_case(note_text)
    patient = extracted["patient"]
    policy_id = patient["insurance_plan"]
    if not policy_id:
        return {
            "success": False,
            "error": "Insurance plan is missing from the note.",
            "extracted": patient,
        }
    policy = get_policy(policy_id)
    if not policy["success"]:
        return policy

    glucose = patient["glucose_mg_dl"]
    a1c = patient["a1c"]
    bmi = patient["bmi"]
    diabetes = bool(patient["diabetes_positive"])
    rationale = bool(patient["rationale_present"])
    prior_therapy = bool(patient["prior_therapy_present"])
    safety = bool(patient["safety_review_present"])

    passed: list[str] = []
    failed: list[str] = []
    missing: list[str] = []

    if diabetes:
        passed.append("Type 2 Diabetes / diabetes-positive status documented.")
    else:
        failed.append("No diabetes-positive status documented.")

    if glucose is None and a1c is None:
        missing.append("Objective glycemic measurement: glucose or A1C.")
    elif _lab_meets_threshold(glucose, GLUCOSE_DIABETES_THRESHOLD) or _lab_meets_threshold(a1c, A1C_DIABETES_THRESHOLD):
        value_parts = []
        if glucose is not None:
            value_parts.append(f"glucose {glucose:g} mg/dL")
        if a1c is not None:
            value_parts.append(f"A1C {a1c:g}%")
        passed.append(f"Objective glycemic evidence meets simulated threshold ({', '.join(value_parts)}).")
    else:
        failed.append("Objective glycemic evidence is below simulated diabetes threshold.")

    if bmi is None:
        missing.append("BMI measurement.")
    elif bmi >= BMI_OBESITY_THRESHOLD:
        passed.append(f"BMI {bmi:g} kg/m² documents obesity risk factor >= 30.")
    else:
        failed.append(f"BMI {bmi:g} kg/m² does not meet obesity threshold >= 30.")

    if rationale:
        passed.append("Provider medical necessity rationale is present.")
    else:
        missing.append("Provider medical necessity rationale.")

    if policy_id in {"A", "B"}:
        if prior_therapy:
            passed.append("Prior therapy, failed alternative, or contraindication is documented.")
        else:
            missing.append("Prior therapy / step therapy history.")

    if policy_id == "B":
        if _lab_meets_threshold(glucose, STRICT_GLUCOSE_THRESHOLD) or _lab_meets_threshold(a1c, STRICT_A1C_THRESHOLD):
            passed.append("Strict Insurance B lab threshold is met.")
        else:
            failed.append("Insurance B stricter lab threshold is not met or missing: glucose >= 140 mg/dL or A1C >= 7.5%.")

    if policy_id == "C":
        if safety:
            passed.append("Safety history is reviewed.")
        else:
            missing.append("Safety review: pancreatitis, thyroid cancer/MEN2, allergy, contraindications.")

    if policy_id == "D" and (glucose is not None or a1c is not None) and bmi is not None and rationale:
        passed.append("Insurance D documentation completeness criteria are mostly present.")

    if a1c is None:
        missing.append("A1C value, if required by payer.")

    risk_score = len(failed) * 2 + len(missing)
    risk_level = "high" if risk_score >= 5 else "medium" if risk_score >= 2 else "low"

    return {
        "success": True,
        "policy_id": policy_id,
        "policy": policy["policy"],
        "extracted_patient": patient,
        "criteria_passed": passed,
        "criteria_failed": failed,
        "missing_information": missing,
        "denial_risk": {
            "level": risk_level,
            "score": risk_score,
            "rationale": "Failed criteria count double; missing documentation counts once.",
        },
        "disclaimer": (
            "Prototype decision support only. Simulated policy rules are not real "
            "coverage determinations and require human review."
        ),
    }
