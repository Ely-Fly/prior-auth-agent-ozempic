# Prior Authorization Assistant — Ozempic (Semaglutide)

An AI agent built with **Google ADK** and **Gemini 2.5 Flash** that automates
the generation of prior authorization clinical note PDFs for Ozempic
(semaglutide) prescriptions, based on patient diabetes and obesity data.

---

## Problem Statement

Prior authorization is one of the most time-consuming bottlenecks in modern
healthcare. Physicians must manually review patient records, determine clinical
eligibility, and produce structured documentation for insurance companies —
often for dozens of patients at a time. This repetitive, documentation-heavy
process is an ideal candidate for AI agent automation.

This project demonstrates how an AI agent can reason over structured patient
data, apply clinical eligibility logic, and generate patient-specific prior
authorization documents — reducing hours of manual work to a single
natural language request.

---

## Solution Overview

The **Prior Authorization Assistant** reads patient records from the PIMA
Indians Diabetes Dataset, determines whether each patient meets the clinical
criteria for Ozempic, and generates a formatted one-page PDF prior
authorization note for every eligible patient.

The agent supports three interaction modes:

- Generate a note for a **specific patient by ID**
- Generate notes for **all eligible patients** in the dataset at once
- Generate notes for a **subset of patients** for testing

Ineligible patients (no diabetes diagnosis and BMI below 30) are silently
skipped — mirroring how a real prior authorization workflow operates.

---

## Architecture

```
┌─────────────────────────────────────────────┐
│           User (adk web chat UI)            │
└────────────────────┬────────────────────────┘
                     │ natural language prompt
┌────────────────────▼────────────────────────┐
│           prior_auth_agent                  │
│     Google ADK + Gemini 2.5 Flash           │
│                                             │
│  Reads prompt → selects tool → calls skill  │
└────────────────────┬────────────────────────┘
                     │ tool call
┌────────────────────▼────────────────────────┐
│           clinic_note_skill                 │
│                                             │
│  generate_note_for_patient_id()             │
│  generate_note_from_row()                   │
│  generate_notes_from_csv()                  │
└────────────────────┬────────────────────────┘
                     │ writes
┌────────────────────▼────────────────────────┐
│           outputs/                          │
│                                             │
│  patient_93810.pdf                          │
│  patient_13278.pdf                          │
│  patient_42098.pdf  ...                     │
└─────────────────────────────────────────────┘
```

The agent uses the **docstrings and type hints** on each skill function to
reason about which tool to call and what parameters to pass. This is standard
ADK tool use — no custom routing logic is required.

---

## Project Structure

```
diabetes_agent/
│
├── README.md                        ← you are here
├── requirements.txt                 ← all dependencies
├── .env                             ← API key (not committed to git)
├── diabetes_updated.csv             ← patient dataset (768 patients)
├── run_skill.py                     ← CLI runner for testing without agent
│
├── prior_auth_agent/                ← ADK agent package
│   ├── __init__.py                  ← exposes root_agent
│   └── agent.py                     ← agent definition (model + tools)
│
└── skills/
    ├── __init__.py
    └── clinic_note_skill/           ← PDF generation skill
        ├── __init__.py              ← exposes three tool functions
        ├── skill.py                 ← ADK tool definitions
        ├── pdf_generator.py         ← ReportLab PDF rendering engine
        └── README.md                ← skill-level documentation
```

---

## Eligibility Logic

Before any PDF is generated, the skill checks whether the patient meets the
clinical criteria for Ozempic authorization:

| Case | Condition | Indication | Action |
|---|---|---|---|
| 1 | Outcome = 1 (Diabetic) | Glycemic control | Generate note |
| 2 | Outcome = 0 and BMI ≥ 30 (Obese) | Weight management | Generate note |
| 3 | Outcome = 0 and BMI < 30 | None | Skip silently |

Applied to the full dataset of 768 patients:
- **521 notes generated** (268 diabetes + 253 obesity)
- **247 patients skipped** — no Ozempic indication

---

## PDF Note Structure

Each generated PDF is a single-page clinical note with five sections:

| Section | Content |
|---|---|
| 1. Patient Demographics | Patient ID, Age, Sex, Number of Pregnancies |
| 2. Insurance Information | Insurance plan code (A / B / C / D) |
| 3. Vital Signs & Labs | Glucose, Blood Pressure, Insulin, BMI with clinical interpretation |
| 4. Diagnosis | Color-coded POSITIVE (red) / NEGATIVE (green) |
| 5. Clinical Justification | Patient-specific Ozempic authorization paragraph referencing actual glucose and BMI values |

The justification paragraph in Section 5 is dynamically generated per patient —
it references the patient's actual clinical values and changes language
depending on whether the indication is diabetes or obesity.

---

## Clinical Interpretation Ranges

| Feature | Ranges |
|---|---|
| Glucose | <100 Normal / 100–125 Pre-diabetic / ≥126 Diabetic / 0 Not recorded |
| Blood Pressure | ≤80 Normal / 81–90 Stage 1 hypertension / ≥91 Stage 2 / 0 Not recorded |
| BMI | <18.5 Underweight / 18.5–24.9 Normal / 25–29.9 Overweight / ≥30 Obese / 0 Not recorded |
| Insulin | <16 Below normal / 16–166 Normal / >166 Elevated / 0 Not recorded |

---

## Dataset

**Source:** PIMA Indians Diabetes Database — National Institute of Diabetes
& Digestive & Kidney Diseases (1988), augmented with `PatientID` and
`Insurance` columns.

**Size:** 768 patients, 11 columns

| Column | Description |
|---|---|
| PatientID | Unique patient identifier |
| Insurance | Insurance plan code (A / B / C / D) |
| Pregnancies | Number of pregnancies |
| Glucose | Plasma glucose mg/dL (2-hr OGTT) |
| BloodPressure | Diastolic blood pressure mm Hg |
| SkinThickness | Triceps skinfold thickness mm (not used in note) |
| Insulin | 2-hr serum insulin µU/mL |
| BMI | Body mass index kg/m² |
| DiabetesPedigreeFunction | Genetic risk score (not used in note) |
| Age | Age in years |
| Outcome | 1 = diabetes diagnosed, 0 = not diagnosed |

---

## Setup

**Requirements:** Python 3.10+

1. Clone the repo:
   ```bash
   git clone <your-repo-url>
   cd diabetes_agent
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root:
   ```
   GOOGLE_API_KEY=your_key_here
   ```
   Get your API key at: https://aistudio.google.com/app/apikey

4. Launch the agent:
   ```bash
   adk web
   ```

5. Open the browser UI (usually at `http://localhost:8000`), select
   `prior_auth_agent` from the dropdown, and start chatting.

> The `outputs/` folder is created automatically on first run.
> No manual folder setup required.

---

## Example Prompts

Once `adk web` is running, try these in the chat UI:

| Prompt | What happens |
|---|---|
| "Generate a prior authorization note for patient 93810" | Looks up patient 93810, checks eligibility, generates one PDF |
| "Generate prior authorization notes for all patients in diabetes_updated.csv" | Batch-generates 521 PDFs, skips 247 ineligible patients |
| "Generate notes for the first 10 patients" | Processes first 10 rows for quick testing |
| "Generate a note for patient 46048" | Returns ineligible message — Outcome=0, BMI<30 |

---

## Key Concepts Demonstrated

This project applies the following concepts from the
Kaggle 5-Day AI Agents Intensive Course with Google:

| Key Concept | Where Demonstrated |
|---|---|
| Agent / Multi-agent system (ADK) | `prior_auth_agent/agent.py` — ADK Agent with Gemini 2.5 Flash |
| Agent Skills | `skills/clinic_note_skill/` — three registered ADK tool functions |
| Deployability | Launched via `adk web` — browser chat UI, zero extra infrastructure |

---

## Dependencies

```
google-adk
reportlab>=4.0
pandas>=1.5
pypdf>=3.0
```

Install all at once:
```bash
pip install -r requirements.txt
```

---

## Important Notes

- **Do not commit your `.env` file** — add it to `.gitignore`
- **API key:** Requires a Google AI Studio API key with billing enabled
- **Python version:** Python 3.10 or higher recommended
- **Model:** Uses `gemini-2.5-flash` — ensure your API key has access

---

## License

This project is intended for educational and research purposes only.
All generated clinical notes are based on research dataset values and
are not intended for real medical use.