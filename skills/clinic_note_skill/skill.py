"""
Skill: clinic_note_skill
=========================
Converts one or more rows from the PIMA Indians Diabetes Dataset
into formatted PDF clinical notes — one PDF per patient.

Registered as an ADK-compatible tool so any agent in the pipeline
can call it natively without subprocess wiring.

Functions exposed as tools:
    - generate_note_from_row   : single patient dict → PDF path
    - generate_notes_from_csv  : full CSV path → list of PDF paths
"""

import json
import os
from typing import Optional

from .pdf_generator import build_patient_pdf, build_styles, process_csv

# Absolute path to project root — works regardless of who runs it or from where
_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
_DEFAULT_OUTPUT_DIR = os.path.join(_PROJECT_ROOT, "outputs")
_DEFAULT_CSV_PATH   = os.path.join(_PROJECT_ROOT, "diabetes_updated.csv")

# ──────────────────────────────────────────────────────────────────
# TOOL 1 — Single patient
# ──────────────────────────────────────────────────────────────────

def generate_note_from_row(
    patient_data: dict,
    output_dir: str = _DEFAULT_OUTPUT_DIR,
    patient_id: Optional[int] = None,
) -> dict:
    """
    Generate a PDF clinical note for a single diabetes patient.

    Use this tool when you have one patient's data as a dictionary
    and want to produce a formatted clinical PDF note for that patient.

    Args:
        patient_data: Dictionary containing the patient's PIMA fields:
            - Pregnancies (int)         : number of pregnancies
            - Glucose (float)           : plasma glucose mg/dL (2-hr OGTT)
            - BloodPressure (float)     : diastolic blood pressure mm Hg
            - Insulin (float)           : 2-hr serum insulin µU/mL
            - BMI (float)               : body mass index kg/m²
            - Age (int)                 : age in years
            - Outcome (int)             : 1 = diabetic, 0 = not diabetic
        output_dir: Directory path to write the PDF file.
        patient_id: Optional numeric ID; auto-assigned from hash if omitted.

    Returns:
        dict with keys:
            - success (bool)    : True if PDF was created successfully
            - pdf_path (str)    : absolute path to the generated PDF
            - patient_id (int)  : the ID used for this patient
            - error (str)       : error message if success is False
    """
    try:
        os.makedirs(output_dir, exist_ok=True)
        styles = build_styles()

        if patient_id is None:
            patient_id = abs(hash(json.dumps(patient_data, sort_keys=True))) % 100000

        pdf_path = os.path.join(output_dir, f"patient_{patient_id:04d}.pdf")
        build_patient_pdf(patient_id, patient_data, pdf_path, styles)

        return {
            "success": True,
            "pdf_path": os.path.abspath(pdf_path),
            "patient_id": patient_id,
            "error": None,
        }

    except Exception as e:
        return {
            "success": False,
            "pdf_path": None,
            "patient_id": patient_id,
            "error": str(e),
        }


# ──────────────────────────────────────────────────────────────────
# TOOL 2 — Batch CSV
# ──────────────────────────────────────────────────────────────────

def generate_notes_from_csv(
    csv_path: str = _DEFAULT_CSV_PATH,
    output_dir: str = _DEFAULT_OUTPUT_DIR,
    merge: bool = False,
    limit: Optional[int] = None,
) -> dict:
    """
    Generate PDF clinical notes for all patients in a PIMA diabetes CSV file.

    Use this tool when you have a full dataset CSV and want to batch-produce
    one clinical PDF note per patient row. Each patient gets their own
    separate PDF file. Optionally merges all notes into a single combined PDF.

    Args:
        csv_path:   Path to the PIMA diabetes CSV file.
                    Expected columns: Pregnancies, Glucose, BloodPressure,
                    Insulin, BMI, Age, Outcome.
        output_dir: Directory to write PDF files into.
        merge:      If True, also produce a single merged PDF of all notes.
        limit:      Process only the first N rows (useful for testing).

    Returns:
        dict with keys:
            - success (bool)        : True if batch completed without fatal error
            - total_processed (int) : number of patient PDFs generated
            - pdf_paths (list[str]) : list of absolute paths to each PDF
            - merged_pdf (str|None) : path to merged PDF, or None if not requested
            - errors (list[str])    : any per-patient errors encountered
            - error (str|None)      : fatal error message if success is False
    """
    try:
        if not os.path.exists(csv_path):
            return {
                "success": False,
                "total_processed": 0,
                "total_skipped": 0,
                "skipped_patient_ids": [],
                "pdf_paths": [],
                "merged_pdf": None,
                "errors": [],
                "error": f"CSV file not found: {csv_path}",
            }

        generated, merged_path, skipped = process_csv(
            csv_path=csv_path,
            output_dir=output_dir,
            merge=merge,
            limit=limit,
        )

        return {
            "success": True,
            "total_processed": len(generated),
            "total_skipped": len(skipped),
            "skipped_patient_ids": skipped,
            "pdf_paths": [os.path.abspath(p) for p in generated],
            "merged_pdf": os.path.abspath(merged_path) if merged_path else None,
            "errors": [],
            "error": None,
        }

    except Exception as e:
        return {
            "success": False,
            "total_processed": 0,
            "pdf_paths": [],
            "merged_pdf": None,
            "errors": [],
            "error": str(e),
        }
# ──────────────────────────────────────────────────────────────────
# TOOL 3 — LOOKING UP A SINGLE PATIENT BY THEIR PATIENT ID FROM CSV
# ──────────────────────────────────────────────────────────────────
def generate_note_for_patient_id(
    patient_id: str,
    csv_path: str = _DEFAULT_CSV_PATH,
    output_dir: str = _DEFAULT_OUTPUT_DIR,
) -> dict:
    """
    Generate a PDF prior authorization clinical note for a specific patient 
    by looking up their Patient ID in the CSV file.

    Use this tool when the user asks to generate a note for a specific patient
    by their ID (e.g. "generate a note for patient 93810").
    This tool searches the CSV for that patient and generates their note.

    Args:
        patient_id: The Patient ID to look up (e.g. "93810")
        csv_path: Path to the diabetes CSV file to search in
        output_dir: Directory to write the PDF file into

    Returns:
        dict with keys:
            - success (bool)    : True if PDF was created successfully
            - pdf_path (str)    : absolute path to the generated PDF
            - patient_id (int)  : the ID used for this patient
            - error (str)       : error message if success is False
    """
    import pandas as pd
    from .pdf_generator import(
        build_patient_pdf, build_styles, check_ozempic_eligibility
    )
    try:
        os.makedirs(output_dir, exist_ok=True)

        if not os.path.exists(csv_path):
            return {
                "success": False,
                "pdf_path": None,
                "patient_id": patient_id,
                "error": f"CSV file not found: {csv_path}",
            }
        
        df = pd.read_csv(csv_path)

        # Support both string and integer Patient ID matching
        df["PatientID"] = df["PatientID"].astype(str)
        match = df[df["PatientID"] == str(patient_id)]

        if match.empty:
            return {
                "success": False,
                "pdf_path": None,
                "patient_id": patient_id,
                "error": f"Patient ID {patient_id} not found in {csv_path}",
            }

        row = match.iloc[0].to_dict()
        outcome = int(float(row.get("Outcome",-1)))
        bmi = float(row.get("BMI",0.0))

        eligible, indication = check_ozempic_eligibility(outcome,bmi)

        if not eligible:
            return {
                "success": False,
                "pdf_path": None,
                "patient_id": patient_id,
                "indication": "ineligible",
                "error": (
                    f"Patient {patient_id} does not meet Ozempic eligibility criteria."
                    f"Outcome={outcome}, BMI={bmi:.1f}."
                    f"No prior authorization note generated."
                ),
            }

        styles = build_styles()
        row_index = match.index[0]+1
        pdf_path = os.path.join(output_dir, f"patient_{patient_id}.pdf")
        build_patient_pdf(row_index, row, pdf_path, styles)

        return {
            "success": True,
            "pdf_path": os.path.abspath(pdf_path),
            "patient_id": patient_id,
            "indication": indication,
            "error": None,
        }

    except Exception as e:
        return {
            "success": False,
            "pdf_path": None,
            "patient_id": patient_id,
            "indication": None,
            "error": str(e),
        }