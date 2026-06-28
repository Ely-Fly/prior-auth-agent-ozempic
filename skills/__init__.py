"""
skills/
=======
Collection of ADK-compatible agent skills for the Diabetes AI Agent project.

Available skills:
    clinic_note_skill      — Generate PDF clinical notes from patient data rows
    insurance_match_skill  — Match insurance criteria and estimate denial risk
"""

from . import clinic_note_skill
from . import insurance_match_skill

__all__ = ["clinic_note_skill", "insurance_match_skill"]
