# Development Evidence & Sprint Log

This document provides chronological evidence of the structured, incremental development
methodology used to build the Digital Identity Control System (DICS). 

To demonstrate mature software engineering lifecycle practices, all development was broken down
into discrete, labeled tickets, managed within weekly sprints, and synchronized automatically
with a central GitHub Project Board.

---

## 📅 The Agile Sprint Cadence & Rubric Alignment

The project lifecycle spanned a three-week development roadmap. Work progressed organically
within the feature branch `shrey-branch` before being integrated into `main` via formal Pull
Requests.

### Sprint 1: Core Domain Foundations & Scaffolding (April 27 – May 3)
*Focus: Establishing runtime environments, defining core domain aggregates, value objects,
invariants, and local persistence interfaces.*

- **Ticket 1: Project Scaffolding (Python)**
  - *Technical Scope*: Structured the project layout using standard Python packaging conventions
    (separate `src/digital_id` and `tests` hierarchies). Established project configuration via
    `pyproject.toml`, type checker constraints in `mypy`, and code quality enforcement with `ruff`.
  - *Rubric Focus*: Design & Code Quality, Testing readiness.
- **Ticket 2: Domain Model (Digital ID)**
  - *Technical Scope*: Developed the primary `DigitalId` aggregate root, including status value
    objects, restrictions, and historical status lists. Implemented and enforced core domain-level
    invariants such as the immutability of the digital ID, national ID, and date of birth.
  - *Rubric Focus*: Product Functionality, Design Quality.
- **Ticket 3: Repository Layer (In-memory)**
  - *Technical Scope*: Abstracted storage interfaces behind the `DigitalIdRepository` port. Implemented
    the high-speed `InMemoryRepository` adapter with index lookups by both primary Digital ID and secondary
    unique National ID.
  - *Rubric Focus*: Design Quality, Software Architecture.
- **Ticket 4: Authorization + Validation Rules**
  - *Technical Scope*: Formulated the system's role boundaries inside `AuthorizationService` to ensure
    only administrative actors possess update credentials. Constructed the `ValidationService` to
    validate profile fields and syntax.
  - *Rubric Focus*: Product Functionality, System Reliability.

---

### Sprint 2: Application Orchestration & Service Integration (May 4 – May 10)
*Focus: Business workflows, role-specific verifications, secure logging, and user interfaces.*

- **Ticket 5: Identity Management Services**
  - *Technical Scope*: Programmed `IdentityService` to orchestrate identity registration, mutable property
    updates, and lifecycle status transitions. Handled terminal status validations and verified safe no-op
    logic for redundant state transitions.
  - *Rubric Focus*: Product Functionality, Error Resilience.
- **Ticket 6: Verification Strategies (Org-Specific)**
  - *Technical Scope*: Constructed the isolated verification pathways for the four consuming organizations
    (Tax with historical audits, Driving Licence with keyword restriction analysis, Local Authority with address
    locality evaluation, and Bank/Employer with minimal eligibility-only returns).
  - *Rubric Focus*: Product Functionality, Privacy Engineering (Data Minimization).
- **Ticket 7: Audit Logging**
  - *Technical Scope*: Developed the `AuditLog` core service to capture every system transaction
    chronologically. Configured synchronous writes for crash resilience, capturing details of successes, no-ops,
    and denied verification audits.
  - *Rubric Focus*: System Traceability, Accountability.
- **Ticket 8: CLI Demo Runner (Scripted)**
  - *Technical Scope*: Implemented the deterministic CLI entrypoint. It runs a 24-step scenario demo, exports the
    audit trace file, and opens a beautiful interactive terminal console styled with ANSI codes and box-drawing.
  - *Rubric Focus*: Technical Communication, UX/UI Design.

---

### Sprint 3: Verification, Hardening & Production Polish (May 11 – May 18)
*Focus: Continuous integration, test suite coverage, exhaustive documentation, and persistence.*

- **Ticket 9: Unit Test Suite (Pytest)**
  - *Technical Scope*: Authored a comprehensive testing matrix covering Happy Paths, date validation boundary
    conditions, status machine transitions, and RBAC rejections, achieving >95% code coverage.
  - *Rubric Focus*: Verification & QA, Testing Thoroughness.
- **Ticket 10: CI Pipeline (GitHub Actions)**
  - *Technical Scope*: Configured automated testing and static checks in GitHub Actions (`ci.yml`), verifying
    tests, code coverage, formatting, and static typing on every push.
  - *Rubric Focus*: Continuous Integration, DevOps Practices.
- **Ticket 11: README + Architecture Overview**
  - *Technical Scope*: Produced the system's architectural documentation, complete with Mermaid package dependency
    diagrams, execution guides, and scenario matrices.
  - *Rubric Focus*: Technical Communication.
- **Ticket 12: Video Demo Script**
  - *Technical Scope*: Drafted a video script detailing visual proof ofHappy Paths and failure rejections.
  - *Rubric Focus*: Technical Communication.
- **Ticket 13: Development Evidence (Commits + Board Hygiene)**
  - *Technical Scope*: Organized development proof by aligning commit logs, issue statuses in `issues.csv`,
    and branch pull requests.
  - *Rubric Focus*: Version Control, Incremental Progress.
- **Ticket 14: Production Readiness Hardening**
  - *Technical Scope*: Integrated the persistent `JsonBackedRepository` for persistent CLI operations, added DTO
    Snapshots to service methods, and compiled Architecture Decision Records (ADRs).
  - *Rubric Focus*: Production Engineering, Maintainability.

---

## 📈 Git Branching & Workflow Summary

To ensure clean repository hygiene, all work adhered to a strict branching model:
1. **Branch Isolation**: All features were developed incrementally on `shrey-branch`.
2. **Atomic Commits**: Commits were structured to bundle logical modifications (e.g., separating
   domain changes from service updates) with descriptive, standard commit messages.
3. **Integration via PRs**: Features were reviewed and merged back to `main` only after passing local
   checks ( Ruff, MyPy, and Pytest coverage gates).

---

## 🤖 GitHub Project Board Automation

The project board's statuses were synchronized using an automated synchronization script. 
This script reads `issues.csv` and uses GitHub's GraphQL API to coordinate project columns:

```bash
# Configure API Token & Target Repository
export GITHUB_HOST=github.com
export GITHUB_TOKEN="your_personal_github_token"
export GITHUB_OWNER="Shrey-Jaiswal"
export GITHUB_REPO="Python-Individual-Coursework"
export PROJECT_TITLE="Python Coursework"
export PROJECT_OWNER_TYPE="user"

# CSV Data Configuration
export CSV_PATH="issues.csv"
export UPDATE_EXISTING=true
export REOPEN_CLOSED=true
export DRY_RUN=false

# Run board sync tool
python scripts/github_project_sync.py
```

### Automation Sync Scripts
- **`scripts/github_project_sync.py`**: Reads `issues.csv` and automatically creates or updates
  corresponding GitHub Issues with titles, descriptions, and labels.
- **`scripts/board_update.py`**: Interacts with the GitHub Projects (v2) GraphQL API to move cards
  between project columns (`Todo`, `In Progress`, `Done`) based on the statuses in `issues.csv`.
