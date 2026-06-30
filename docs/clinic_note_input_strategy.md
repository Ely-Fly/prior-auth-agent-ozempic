# Clinic Note Input Strategy

## Key correction

The CSV should be treated as a synthetic data source for creating examples, not as
the main workflow input.

In a realistic prior authorization workflow, clinic staff work from clinical notes,
progress notes, medication request notes, lab summaries, and insurance information.
Therefore, the agent should accept clinic-note text or generated clinical-note PDFs.

## Why this matters

Using only the CSV makes the prototype look like a dataset exercise. Using clinic
notes makes it look like a healthcare workflow:

`clinic note -> extraction -> insurance match -> criteria check -> denial risk`

## Supported note styles

The insurance match skill should support:

- Ella-format generated PDFs.
- Plain text copied from a clinical note.
- Notes using labels such as Insurance, Payer, Plan, Medication, Drug, A1C, HbA1c,
  Glucose, BMI, Type 2 Diabetes, T2DM, prior therapy, and safety review.

## CSV role

The CSV remains useful for:

- Generating synthetic patient examples.
- Creating reproducible demo notes.
- Testing edge cases.

It should not be described as the primary real-world input.
