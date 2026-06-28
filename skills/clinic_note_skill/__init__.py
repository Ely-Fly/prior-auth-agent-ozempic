"""
clinic_note_skill
=================
ADK-compatible skill that converts PIMA diabetes patient data
into formatted PDF clinical notes — one PDF per patient.

Exposes two tools:
    generate_note_from_row    — single patient dict  → PDF
    generate_notes_from_csv   — full dataset CSV     → batch of PDFs

Example (inside an ADK agent):
    from skills.clinic_note_skill import generate_note_from_row

    result = generate_note_from_row(
        patient_data={
            "Pregnancies": 6, "Glucose": 148, "BloodPressure": 72,
            "Insulin": 0, "BMI": 33.6, "Age": 50, "Outcome": 1,
        },
        output_dir="./outputs",
        patient_id=1,
    )
    print(result["pdf_path"])
"""

from .skill import (
    generate_note_from_row, 
    generate_notes_from_csv,
    generate_note_for_patient_id,
)

__all__ = ["generate_note_from_row", "generate_notes_from_csv","generate_note_for_patient_id",]
