"""
pdf_generator.py
-----------------
Core PDF generation engine for the clinic_note_skill.
Handles clinical interpretation, layout, and ReportLab rendering
for Ozempic prior authorization clinical notes.

Eligibility logic:
    Case 1 — Outcome = 1 (Diabetic)          → justify for glycemic control
    Case 2 — Outcome = 0, BMI >= 30 (Obese)  → justify for weight management
    Case 3 — Outcome = 0, BMI < 30            → skip silently, no PDF generated

Dataset expectations:
    PatientID, Insurance, Pregnancies, Glucose, BloodPressure,
    SkinThickness, Insulin, BMI, DiabetesPedigreeFunction, Age, Outcome

Imported by skill.py — not called directly.

Requirements:
    pip install reportlab pandas pypdf
"""

import json
import os
from datetime import datetime

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)
from pypdf import PdfWriter, PdfReader


# ──────────────────────────────────────────────
# 1. ELIGIBILITY CHECK
# ──────────────────────────────────────────────

def check_ozempic_eligibility(outcome: int, bmi: float) -> tuple:
    """
    Determine whether a patient qualifies for Ozempic prior authorization.

    Args:
        outcome: 1 = diabetic, 0 = not diabetic
        bmi:     Body Mass Index value

    Returns:
        Tuple of (is_eligible: bool, indication: str)
        indication is one of: 'diabetes', 'obesity', 'ineligible'
    """
    if outcome == 1:
        return True, "diabetes"
    elif outcome == 0 and bmi >= 30:
        return True, "obesity"
    else:
        return False, "ineligible"


# ──────────────────────────────────────────────
# 2. CLINICAL INTERPRETATION HELPERS
# ──────────────────────────────────────────────

def interpret_glucose(value):
    """Plasma glucose (mg/dL) after 2-hr oral glucose tolerance test."""
    if value == 0:
        return "Not recorded"
    elif value < 100:
        return f"{value} mg/dL — Normal"
    elif value < 126:
        return f"{value} mg/dL — Pre-diabetic range"
    else:
        return f"{value} mg/dL — Diabetic range (≥126 mg/dL)"


def interpret_blood_pressure(value):
    """Diastolic blood pressure (mm Hg)."""
    if value == 0:
        return "Not recorded"
    elif value <= 80:
        return f"{value} mm Hg — Normal"
    elif value <= 90:
        return f"{value} mm Hg — Stage 1 hypertension"
    else:
        return f"{value} mm Hg — Stage 2 hypertension"


def interpret_bmi(value):
    """Body Mass Index (kg/m²)."""
    if value == 0:
        return "Not recorded"
    elif value < 18.5:
        return f"{value:.1f} kg/m² — Underweight"
    elif value < 25:
        return f"{value:.1f} kg/m² — Normal weight"
    elif value < 30:
        return f"{value:.1f} kg/m² — Overweight"
    else:
        return f"{value:.1f} kg/m² — Obese (≥30 kg/m²)"


def interpret_insulin(value):
    """2-hour serum insulin (µU/mL)."""
    if value == 0:
        return "Not recorded"
    elif value < 16:
        return f"{value} µU/mL — Below normal fasting range"
    elif value <= 166:
        return f"{value} µU/mL — Within normal range"
    else:
        return f"{value} µU/mL — Elevated (possible insulin resistance)"


def interpret_outcome(value):
    """Binary diabetes diagnosis."""
    return "POSITIVE — Diabetes diagnosed" if value == 1 else "NEGATIVE — No diabetes diagnosed"


def build_ozempic_justification(indication: str, glucose: float, bmi: float) -> str:
    """
    Build a patient-specific clinical justification paragraph for Ozempic.

    Args:
        indication: 'diabetes' or 'obesity'
        glucose:    patient's plasma glucose value
        bmi:        patient's BMI value

    Returns:
        Justification text string tailored to this patient's data.
    """
    if indication == "diabetes":
        glucose_note = (
            f"a plasma glucose of {glucose:.0f} mg/dL indicating inadequate glycemic control"
            if glucose > 0 else "documented plasma glucose findings"
        )
        bmi_note = (
            f", in conjunction with a BMI of {bmi:.1f} kg/m²"
            if bmi >= 25 else ""
        )
        return (
            f"After reviewing this patient's medical history and diagnostic findings, "
            f"prescribing Ozempic (semaglutide) is clinically necessary. The patient "
            f"presents with a confirmed Type 2 diabetes diagnosis, {glucose_note}"
            f"{bmi_note}. Ozempic (semaglutide) is indicated as an adjunct to diet "
            f"and exercise to improve glycemic control in adults with Type 2 diabetes "
            f"mellitus, and is medically necessary for this patient's ongoing care."
        )
    else:  # obesity
        return (
            f"After reviewing this patient's medical history and diagnostic findings, "
            f"prescribing Ozempic (semaglutide) is clinically necessary. While this "
            f"patient does not present with a Type 2 diabetes diagnosis, a BMI of "
            f"{bmi:.1f} kg/m² meets the clinical threshold for obesity (≥30 kg/m²). "
            f"Ozempic (semaglutide) is indicated for chronic weight management in "
            f"adults with obesity as an adjunct to a reduced-calorie diet and increased "
            f"physical activity, and is medically necessary for this patient's care."
        )


# ──────────────────────────────────────────────
# 3. STYLE DEFINITIONS
# ──────────────────────────────────────────────

def build_styles():
    """Return a dict of custom ReportLab paragraph styles."""
    return {
        "doc_title": ParagraphStyle(
            "doc_title",
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=colors.HexColor("#1a3a5c"),
            spaceBefore=0,
            spaceAfter=2,
            alignment=TA_LEFT,
        ),
        "doc_subtitle": ParagraphStyle(
            "doc_subtitle",
            fontName="Helvetica",
            fontSize=9,
            textColor=colors.HexColor("#4a6fa5"),
            spaceBefore=0,
            spaceAfter=4,
            alignment=TA_LEFT,
        ),
        "section_heading": ParagraphStyle(
            "section_heading",
            fontName="Helvetica-Bold",
            fontSize=9.5,
            textColor=colors.HexColor("#1a3a5c"),
            spaceBefore=0,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body",
            fontName="Helvetica",
            fontSize=9,
            textColor=colors.HexColor("#222222"),
            spaceAfter=3,
            leading=13,
        ),
        "justification_box": ParagraphStyle(
            "justification_box",
            fontName="Helvetica",
            fontSize=9,
            textColor=colors.HexColor("#0d2b45"),
            leading=14,
            spaceAfter=0,
        ),
        "diagnosis_positive": ParagraphStyle(
            "diagnosis_positive",
            fontName="Helvetica-Bold",
            fontSize=9.5,
            textColor=colors.HexColor("#8b0000"),
            spaceAfter=0,
        ),
        "diagnosis_negative": ParagraphStyle(
            "diagnosis_negative",
            fontName="Helvetica-Bold",
            fontSize=9.5,
            textColor=colors.HexColor("#1a5c2a"),
            spaceAfter=0,
        ),
        "footer": ParagraphStyle(
            "footer",
            fontName="Helvetica",
            fontSize=7.5,
            textColor=colors.HexColor("#888888"),
            spaceAfter=0,
            alignment=TA_CENTER,
        ),
    }


# ──────────────────────────────────────────────
# 4. TABLE STYLE HELPERS
# ──────────────────────────────────────────────

def _row_table_style():
    """Alternating-row style for simple label/value tables."""
    return TableStyle([
        ("FONTNAME",       (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",       (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE",       (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",      (0, 0), (0, -1),  colors.HexColor("#1a3a5c")),
        ("TEXTCOLOR",      (1, 0), (1, -1),  colors.HexColor("#333333")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1),
         [colors.HexColor("#f7fafd"), colors.HexColor("#edf2f8")]),
        ("BOX",            (0, 0), (-1, -1), 0.5, colors.HexColor("#c0cfe0")),
        ("INNERGRID",      (0, 0), (-1, -1), 0.3, colors.HexColor("#d0dcea")),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
        ("LEFTPADDING",    (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 8),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
    ])


def _lab_table_style():
    """Style for the lab measurements table with a distinct header row."""
    return TableStyle([
        # Header row
        ("BACKGROUND",     (0, 0), (-1, 0),  colors.HexColor("#1a3a5c")),
        ("TEXTCOLOR",      (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",       (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",       (0, 0), (-1, 0),  9),
        ("TOPPADDING",     (0, 0), (-1, 0),  6),
        ("BOTTOMPADDING",  (0, 0), (-1, 0),  6),
        # Data rows
        ("FONTNAME",       (0, 1), (0, -1),  "Helvetica-Bold"),
        ("FONTNAME",       (1, 1), (1, -1),  "Helvetica"),
        ("FONTSIZE",       (0, 1), (-1, -1), 9),
        ("TEXTCOLOR",      (0, 1), (0, -1),  colors.HexColor("#1a3a5c")),
        ("TEXTCOLOR",      (1, 1), (1, -1),  colors.HexColor("#333333")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.HexColor("#f7fafd"), colors.HexColor("#edf2f8")]),
        ("BOX",            (0, 0), (-1, -1), 0.5, colors.HexColor("#c0cfe0")),
        ("INNERGRID",      (0, 0), (-1, -1), 0.3, colors.HexColor("#d0dcea")),
        ("TOPPADDING",     (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 1), (-1, -1), 5),
        ("LEFTPADDING",    (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 8),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
    ])


def _section_divider(W):
    """Light divider used between sections."""
    return HRFlowable(
        width=W, thickness=0.5,
        color=colors.HexColor("#c0cfe0"),
        spaceBefore=10, spaceAfter=6,
    )


# ──────────────────────────────────────────────
# 5. PDF BUILDER FOR ONE PATIENT
# ──────────────────────────────────────────────

def build_patient_pdf(patient_id: int, row: dict, output_path: str, styles: dict):
    """
    Generate a single-page PDF prior authorization clinical note.

    Layout (top to bottom):
        Title + subtitle
        ── divider ──
        1. Patient Demographics
        ── divider ──
        2. Insurance Information
        ── divider ──
        3. Vital Signs & Laboratory Measurements
        ── divider ──
        4. Diagnosis
        ── divider ──
        5. Clinical Justification (shaded box)
        ── footer ──

    Args:
        patient_id:  Row index (used for PDF filename only).
        row:         dict of column → value for this patient.
        output_path: Full file path to write the PDF.
        styles:      dict of ParagraphStyle objects from build_styles().
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
    )

    story = []
    W = letter[0] - 1.5 * inch  # usable content width

    # ── Extract values ──
    raw_patient_id  = str(row.get("PatientID", f"{patient_id:04d}"))
    insurance       = str(row.get("Insurance", "N/A")).strip()
    outcome         = int(float(row.get("Outcome", -1)))
    bmi             = float(row.get("BMI", 0.0))
    glucose         = float(row.get("Glucose", 0))
    bp              = float(row.get("BloodPressure", 0))
    insulin         = float(row.get("Insulin", 0))
    age             = int(float(row.get("Age", 0)))
    pregnancies     = int(float(row.get("Pregnancies", 0)))

    _, indication = check_ozempic_eligibility(outcome, bmi)

    # ── TITLE ──
    story.append(Paragraph(
        "PRIOR AUTHORIZATION CLINICAL NOTE",
        styles["doc_title"],
    ))
    story.append(Paragraph(
        "Medication: Ozempic (Semaglutide)",
        styles["doc_subtitle"],
    ))
    story.append(HRFlowable(
        width=W, thickness=2,
        color=colors.HexColor("#1a3a5c"),
        spaceBefore=2, spaceAfter=10,
    ))

    # ── SECTION 1: PATIENT DEMOGRAPHICS ──
    story.append(KeepTogether([
        Paragraph("1.  PATIENT DEMOGRAPHICS", styles["section_heading"]),
        Table(
            [
                ["Patient ID",            raw_patient_id],
                ["Age",                   f"{age} years"],
                ["Sex",                   "Female"],
                ["Number of Pregnancies", str(pregnancies)],
            ],
            colWidths=[2.4 * inch, 4.6 * inch],
            style=_row_table_style(),
        ),
    ]))

    # ── SECTION 2: INSURANCE INFORMATION ──
    story.append(_section_divider(W))
    story.append(KeepTogether([
        Paragraph("2.  INSURANCE INFORMATION", styles["section_heading"]),
        Table(
            [
                ["Insurance Plan", insurance],
            ],
            colWidths=[2.4 * inch, 4.6 * inch],
            style=_row_table_style(),
        ),
    ]))

    # ── SECTION 3: VITAL SIGNS & LAB MEASUREMENTS ──
    story.append(_section_divider(W))
    story.append(KeepTogether([
        Paragraph("3.  VITAL SIGNS & LABORATORY MEASUREMENTS", styles["section_heading"]),
        Table(
            [
                ["Measurement",                 "Value & Clinical Interpretation"],
                ["Plasma Glucose (2-hr OGTT)",  interpret_glucose(glucose)],
                ["Diastolic Blood Pressure",     interpret_blood_pressure(bp)],
                ["2-Hr Serum Insulin",           interpret_insulin(insulin)],
                ["Body Mass Index (BMI)",        interpret_bmi(bmi)],
            ],
            colWidths=[2.4 * inch, 4.6 * inch],
            style=_lab_table_style(),
        ),
    ]))

    # ── SECTION 4: DIAGNOSIS ──
    story.append(_section_divider(W))
    diag_style = (
        styles["diagnosis_positive"] if outcome == 1
        else styles["diagnosis_negative"]
    )
    story.append(KeepTogether([
        Paragraph("4.  DIAGNOSIS", styles["section_heading"]),
        Paragraph(f"Diabetes Status:  {interpret_outcome(outcome)}", diag_style),
    ]))

    # ── SECTION 5: CLINICAL JUSTIFICATION ──
    story.append(_section_divider(W))

    justification_text = build_ozempic_justification(indication, glucose, bmi)
    justification_table = Table(
        [[Paragraph(justification_text, styles["justification_box"])]],
        colWidths=[W],
    )
    justification_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#eef4fb")),
        ("BOX",           (0, 0), (-1, -1), 1, colors.HexColor("#4a7fb5")),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
    ]))

    story.append(KeepTogether([
        Paragraph(
            "5.  CLINICAL JUSTIFICATION FOR PRIOR AUTHORIZATION",
            styles["section_heading"],
        ),
        justification_table,
    ]))

    # ── FOOTER ──
    generated_on = datetime.now().strftime("%B %d, %Y")
    story.append(Spacer(1, 10))
    story.append(HRFlowable(
        width=W, thickness=0.5,
        color=colors.HexColor("#cccccc"),
        spaceBefore=0, spaceAfter=4,
    ))
    story.append(Paragraph(
        f"Generated: {generated_on}     |     Patient ID: {raw_patient_id}",
        styles["footer"],
    ))

    doc.build(story)


# ──────────────────────────────────────────────
# 6. BATCH PROCESSING
# ──────────────────────────────────────────────

def process_csv(
    csv_path: str,
    output_dir: str,
    merge: bool = False,
    limit: int = None,
):
    """
    Read the dataset CSV and generate one PDF per eligible patient.

    Skips patients who do not meet Ozempic eligibility criteria
    (Outcome=0 and BMI<30) silently — logged but no PDF created.

    Args:
        csv_path:   Path to the diabetes CSV file.
        output_dir: Directory to write output PDFs.
        merge:      If True, also produce a single merged PDF.
        limit:      Max rows to process (for testing).

    Returns:
        Tuple of (list of generated PDF paths, merged PDF path or None,
                  list of skipped patient IDs).
    """
    os.makedirs(output_dir, exist_ok=True)
    styles = build_styles()

    df = pd.read_csv(csv_path)

    # Case-insensitive column matching
    expected_cols = [
        "PatientID", "Insurance", "Pregnancies", "Glucose", "BloodPressure",
        "SkinThickness", "Insulin", "BMI", "DiabetesPedigreeFunction",
        "Age", "Outcome",
    ]
    col_map = {c.lower(): c for c in df.columns}
    rename = {}
    for expected in expected_cols:
        if expected not in df.columns and expected.lower() in col_map:
            rename[col_map[expected.lower()]] = expected
    if rename:
        df = df.rename(columns=rename)

    if limit:
        df = df.head(limit)

    generated = []
    skipped   = []
    total     = len(df)

    print(f"Processing {total} patient(s) from: {csv_path}")
    print(f"Output directory: {output_dir}\n")

    for idx, row_series in df.iterrows():
        row         = row_series.to_dict()
        patient_id  = idx + 1
        raw_pid     = str(row.get("PatientID", patient_id))
        outcome     = int(float(row.get("Outcome", -1)))
        bmi         = float(row.get("BMI", 0.0))

        eligible, indication = check_ozempic_eligibility(outcome, bmi)

        if not eligible:
            skipped.append(raw_pid)
            print(f"  [{patient_id:4d}/{total}] Skipped  (no Ozempic indication) — ID {raw_pid}")
            continue

        out_path = os.path.join(output_dir, f"patient_{raw_pid}.pdf")
        try:
            build_patient_pdf(patient_id, row, out_path, styles)
            generated.append(out_path)
            label = "diabetes" if indication == "diabetes" else "obesity "
            print(f"  [{patient_id:4d}/{total}] Created  ({label}) → {os.path.basename(out_path)}")
        except Exception as e:
            print(f"  [{patient_id:4d}/{total}] ERROR for patient {raw_pid}: {e}")

    print(f"\nGenerated : {len(generated)} PDF note(s)")
    print(f"Skipped   : {len(skipped)} patient(s) — no Ozempic indication")

    if merge and generated:
        merged_path = os.path.join(output_dir, "all_patients_merged.pdf")
        writer = PdfWriter()
        for pdf_path in generated:
            reader = PdfReader(pdf_path)
            for page in reader.pages:
                writer.add_page(page)
        with open(merged_path, "wb") as f:
            writer.write(f)
        print(f"Merged PDF : {merged_path}")
        return generated, merged_path, skipped

    return generated, None, skipped


def process_single_row(row_json: str, output_dir: str, patient_id: int = 1):
    """
    Generate a PDF for a single patient supplied as a JSON string.
    Returns None if patient is not eligible for Ozempic.

    Args:
        row_json:   JSON string of one patient's data.
        output_dir: Directory to write the PDF.
        patient_id: Row index (used as fallback if PatientID not in data).

    Returns:
        Path to the generated PDF, or None if ineligible.
    """
    os.makedirs(output_dir, exist_ok=True)
    styles  = build_styles()
    row     = json.loads(row_json)
    outcome = int(float(row.get("Outcome", -1)))
    bmi     = float(row.get("BMI", 0.0))

    eligible, indication = check_ozempic_eligibility(outcome, bmi)
    if not eligible:
        raw_pid = str(row.get("PatientID", patient_id))
        print(f"Patient {raw_pid} skipped — does not meet Ozempic criteria.")
        return None

    raw_pid  = str(row.get("PatientID", f"{patient_id:04d}"))
    out_path = os.path.join(output_dir, f"patient_{raw_pid}.pdf")
    build_patient_pdf(patient_id, row, out_path, styles)
    print(f"Created ({indication}): {out_path}")
    return out_path
