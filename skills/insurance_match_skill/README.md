# insurance_match_skill

ADK-compatible skill for Erick's part of the prior authorization workflow.

It runs after `clinic_note_skill` generates a synthetic prior authorization PDF.
The skill reads the generated note, matches Insurance A/B/C/D, checks simulated
payer criteria, flags missing documentation, and estimates denial risk.

## Tools

- `extract_patient_case(note_text)`
- `extract_text_from_pdf(pdf_path)`
- `list_policies()`
- `get_policy(policy_id)`
- `evaluate_prior_authorization(note_text)`
- `evaluate_prior_authorization_pdf(pdf_path)`
- `evaluate_patient_from_csv(patient_id, csv_path="diabetes_updated.csv")`

## Compatibility workflow

```text
clinic_note_skill -> outputs/patient_<PatientID>.pdf -> insurance_match_skill -> denial risk
```

## Dataset note

The dataset has Glucose, BMI, Outcome, Age, and Insurance, but not A1C. The skill
uses Glucose as the primary objective lab variable and flags A1C as missing when
relevant.
