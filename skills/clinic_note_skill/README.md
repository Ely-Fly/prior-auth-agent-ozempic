# clinic_note_skill

An ADK-compatible agent skill that converts rows from the PIMA Indians Diabetes
Dataset into formatted PDF clinical notes — one separate PDF per patient.

---

## Folder structure

```
clinic_note_skill/
├── __init__.py        ← exposes the two tool functions
├── skill.py           ← ADK tool definitions
├── pdf_generator.py   ← core PDF rendering engine (ReportLab)
├── outputs/           ← default output directory for generated PDFs
└── README.md
```

---

## Tools exposed

### `generate_note_from_row(patient_data, output_dir, patient_id)`

Generates a PDF for a single patient supplied as a dictionary.

**Input:**
```python
{
    "Pregnancies": 6,
    "Glucose": 148,
    "BloodPressure": 72,
    "Insulin": 0,
    "BMI": 33.6,
    "Age": 50,
    "Outcome": 1
}
```

**Output:**
```python
{
    "success": True,
    "pdf_path": "/absolute/path/to/patient_0001.pdf",
    "patient_id": 1,
    "error": None
}
```

---

### `generate_notes_from_csv(csv_path, output_dir, merge, limit)`

Batch-generates one PDF per patient row from a PIMA diabetes CSV file.

**Output:**
```python
{
    "success": True,
    "total_processed": 768,
    "pdf_paths": ["/path/patient_0001.pdf", ...],
    "merged_pdf": "/path/all_patients_merged.pdf",  # if merge=True
    "errors": [],
    "error": None
}
```

---

## Usage inside an ADK agent

```python
from skills.clinic_note_skill import generate_note_from_row, generate_notes_from_csv

# Single patient
result = generate_note_from_row(
    patient_data={"Pregnancies": 6, "Glucose": 148, ...},
    output_dir="./outputs",
    patient_id=1,
)

# Full dataset — one PDF per patient
result = generate_notes_from_csv(
    csv_path="diabetes.csv",
    output_dir="./outputs",
)
```

## CLI usage (for testing)

```bash
# From the diabetes_agent/ root:

python run_skill.py --csv diabetes.csv
python run_skill.py --csv diabetes.csv --merge
python run_skill.py --csv diabetes.csv --limit 5
python run_skill.py --row '{"Pregnancies":6,"Glucose":148,"BloodPressure":72,"Insulin":0,"BMI":33.6,"Age":50,"Outcome":1}'
```

---

## PDF note sections

| Section | Content |
|---|---|
| Title | "Clinical Diagnostic Note" |
| 1. Patient Demographics | Patient ID, Age, Pregnancies, Sex |
| 2. Vital Signs & Labs | Glucose, Blood Pressure, Insulin, BMI with clinical interpretation |
| 3. Diagnosis | Color-coded POSITIVE (red) / NEGATIVE (green) + WHO criteria note |
| Footer | Date generated, Patient ID |

---

## Clinical interpretation ranges

| Feature | Ranges |
|---|---|
| Glucose | <100 Normal / 100–125 Pre-diabetic / ≥126 Diabetic / 0 Not recorded |
| Blood Pressure | ≤80 Normal / 81–90 Stage 1 hypertension / ≥91 Stage 2 / 0 Not recorded |
| BMI | <18.5 Underweight / 18.5–24.9 Normal / 25–29.9 Overweight / ≥30 Obese / 0 Not recorded |
| Insulin | <16 Below normal / 16–166 Normal / >166 Elevated / 0 Not recorded |

---

## Dependencies

```
reportlab>=4.0
pandas>=1.5
pypdf>=3.0
```

```bash
pip install reportlab pandas pypdf
```
