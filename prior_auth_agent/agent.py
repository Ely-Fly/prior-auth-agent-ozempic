from google.adk.agents import Agent

from skills.clinic_note_skill import (
    generate_notes_from_csv,
    generate_note_from_row,
    generate_note_for_patient_id,
)
from skills.insurance_match_skill import (
    evaluate_patient_from_csv,
    evaluate_prior_authorization,
    evaluate_prior_authorization_pdf,
    get_policy,
    list_policies,
)

root_agent = Agent(
    name="prior_auth_agent",
    model="gemini-2.5-flash-lite",
    description=(
        "Prior authorization assistant for Ozempic (semaglutide). Generates "
        "prior authorization clinical note PDFs for eligible patients and "
        "evaluates simulated insurance denial risk."
    ),
    tools=[
        generate_notes_from_csv,
        generate_note_from_row,
        generate_note_for_patient_id,
        evaluate_patient_from_csv,
        evaluate_prior_authorization,
        evaluate_prior_authorization_pdf,
        list_policies,
        get_policy,
    ],
)
