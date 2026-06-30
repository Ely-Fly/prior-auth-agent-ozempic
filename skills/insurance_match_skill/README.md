# insurance_match_skill

ADK-compatible Python skill for Erick's part of the capstone: insurance matching,
simulated payer-criteria evaluation, missing-documentation detection, and denial-risk
scoring for synthetic Ozempic prior authorization notes.

## Tools exposed

- `extract_patient_case(note_text)` extracts patient ID, insurance plan, age,
  medication, glucose, BMI, diabetes status, prior therapy evidence, safety review
  evidence, and medical necessity rationale.
- `list_policies()` lists simulated Insurance A/B/C/D policies.
- `get_policy(policy_id)` returns one simulated policy.
- `evaluate_prior_authorization(note_text)` extracts the case, matches insurance,
  evaluates criteria, flags missing information, and returns denial risk.

## Design notes for writeup

The available diabetes datasets include glucose, BMI, diabetes outcome, age, and
insurance assignment, but not A1C. Therefore, this skill uses plasma glucose as the
primary objective lab variable and flags A1C as missing when required by a payer.

The policies are simulated and inspired by public clinical/policy references. They
are not real payer rules and must not be presented as real approval or denial logic.

## Example

```python
from skills.insurance_match_skill import evaluate_prior_authorization

result = evaluate_prior_authorization(note_text)
print(result["policy_id"])
print(result["denial_risk"])
```
