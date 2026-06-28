"""
skills/
=======
Collection of ADK-compatible agent skills for the Diabetes AI Agent project.

Available skills:
    clinic_note_skill  — Generate PDF clinical notes from patient data rows
"""

from . import clinic_note_skill
__all__ = ["clinic_note_skill"]
