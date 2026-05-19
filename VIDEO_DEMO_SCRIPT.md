# Video Demo Script (<=10 minutes)

## Goal
Show the system behavior and justify design decisions clearly, aligned to the rubric:
- Functionality (lifecycle + verification + audit)
- Design/Quality (clean layering and rules)
- Testing/CI (pytest, lint, mypy, CI workflow)
- Version control evidence (tickets + commits)
- Communication (clear narrative)

## Timing + Voiceover + On-screen Actions

### 0:00 - 0:30 Intro (context and requirements)
**Voiceover:**
"This is my IOT452U individual coursework. I built a console-based backend for Digital ID lifecycle management. The central authority creates and updates identities and is the only role allowed to change status. Other organisations only verify identities with role-specific rules. I will show the architecture, key rules, a scripted demo, and the automated tests and CI."

**On screen:**
- Open README and briefly scroll to the overview section.

---

### 0:30 - 1:45 Architecture overview
**Voiceover:**
"The system is structured into clean layers: domain models hold rules and invariants, services implement application workflows, and persistence handles storage. The CLI and demo runner are thin orchestration layers. This separation keeps business rules deterministic and testable."

**On screen:**
- Scroll to the Mermaid diagram in README.
- Point out key modules: `digital_id.domain`, `digital_id.services`, `digital_id.persistence`, `digital_id.demo`.

---

### 1:45 - 5:30 Scripted demo (core functionality)
**Voiceover:**
"I will run the scripted demo to show representative success and failure paths in a deterministic sequence. The demo creates an identity, treats a repeated active status as a no-op, updates mutable fields, rejects duplicate creation, rejects unauthorized status and restriction changes, then demonstrates organisation-specific verification flows. It also shows missing identity handling, revoked-state protections, and audit export."

**On screen (terminal):**
```bash
python -m digital_id --scripted-only --audit-path audit_log.json
```

**Voiceover cues while output appears:**
- "Create identity and update passes."
- "Repeating the current status is handled as an explicit no-op."
- "Duplicate creation is rejected as expected."
- "A non-central role attempting a status change is rejected."
- "A bank role attempting tax verification is rejected (org-level authorisation)."
- "Tax verification fails while suspended, and then still fails for a period where the status history shows a suspension."
- "Restrictions are added and cleared only through the central authority service."
- "Driving verification fails with an active restriction, then passes when cleared."
- "Local authority check shows locality mismatch then match."
- "Bank/employer receives a validity-only response."
- "Missing identity lookup and update-after-revoked are rejected in defined ways."
- "Successful, failed, and denied audit entries are recorded and exported to JSON."

**On screen:**
- Open `audit_log.json` and show a few entries (creation, update, status change, verification).

---

### 5:30 - 7:00 Rules and determinism
**Voiceover:**
"Key rules are deterministic: identity attributes like digital ID, national ID, and date of birth are immutable; status transitions allow active and suspended to move, while revoked is terminal; repeated status changes are no-ops; and updates or restriction changes on revoked identities are rejected. Verification receives only a digital ID and returns a limited result, so consuming organisations do not handle the full identity record."

**On screen:**
- Briefly open the status and domain files to show the rule definitions (no deep dive).

---

### 7:00 - 8:30 Testing and CI
**Voiceover:**
"Testing uses pytest with focused unit tests for domain rules, identity services, organisation-specific verification, audit denial paths, JSON persistence, and CLI flows. Continuous integration runs linting, type checks, and tests with a 95% coverage gate on every push and pull request."

**On screen:**
```bash
python -m pytest
python -m ruff check src tests
python -m mypy src --config-file pyproject.toml
```
- Show the CI workflow file and/or the GitHub Actions page.

---

### 8:30 - 9:30 Version control evidence
**Voiceover:**
"Development is tracked by tickets in issues.csv with incremental commits. This shows organized progress and ties work to the rubric categories."

**On screen:**
- Open `issues.csv` and show the ticket list with statuses.
- Optional: `git log --oneline` to show incremental commits.

---

### 9:30 - 10:00 Wrap-up
**Voiceover:**
"That concludes the demonstration. The system implements the required lifecycle management, role-specific verification, and audit logging, with clear architecture and automated verification through tests and CI."

**On screen:**
- Return to README top.
