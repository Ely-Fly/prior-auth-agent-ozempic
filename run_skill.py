"""
run_skill.py
------------
Command-line runner for the clinic_note_skill.
Calls the same tool functions an ADK agent would use.

Usage:
    # Batch — all patients in CSV
    python run_skill.py --csv diabetes.csv

    # Batch + merge into one PDF
    python run_skill.py --csv diabetes.csv --merge

    # Test on first 5 rows only
    python run_skill.py --csv diabetes.csv --limit 5

    # Single patient as JSON
    python run_skill.py --row '{"Pregnancies":6,"Glucose":148,"BloodPressure":72,
        "Insulin":0,"BMI":33.6,"Age":50,"Outcome":1}'
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from skills.clinic_note_skill import generate_note_from_row, generate_notes_from_csv


def main():
    parser = argparse.ArgumentParser(
        description="CLI runner for the clinic_note_skill ADK tool."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--csv", help="Path to the PIMA diabetes CSV file.")
    group.add_argument("--row", help="Single patient as a JSON string.")

    parser.add_argument(
        "--output", default="./skills/clinic_note_skill/outputs",
        help="Output directory for generated PDFs.",
    )
    parser.add_argument(
        "--merge", action="store_true",
        help="Also produce a merged single PDF (batch mode only).",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Process only the first N rows (batch mode only).",
    )
    parser.add_argument(
        "--patient-id", type=int, default=1,
        help="Patient ID for single-row mode (default: 1).",
    )

    args = parser.parse_args()

    if args.csv:
        result = generate_notes_from_csv(
            csv_path=args.csv,
            output_dir=args.output,
            merge=args.merge,
            limit=args.limit,
        )
        if result["success"]:
            print(f"\nSuccess! Generated {result['total_processed']} PDF note(s).")
            print(f"Output directory: {args.output}")
            if result["merged_pdf"]:
                print(f"Merged PDF: {result['merged_pdf']}")
        else:
            print(f"\nERROR: {result['error']}")
            sys.exit(1)

    else:
        try:
            patient_data = json.loads(args.row)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON for --row: {e}")
            sys.exit(1)

        result = generate_note_from_row(
            patient_data=patient_data,
            output_dir=args.output,
            patient_id=args.patient_id,
        )
        if result["success"]:
            print(f"\nSuccess! PDF created: {result['pdf_path']}")
        else:
            print(f"\nERROR: {result['error']}")
            sys.exit(1)


if __name__ == "__main__":
    main()
