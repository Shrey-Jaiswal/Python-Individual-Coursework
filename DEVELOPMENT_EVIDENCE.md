# Development log and sprint tracking

This document records the incremental development steps used to build the Digital Identity
Control System (DICS).

We organized development into discrete, labeled tickets across three weekly sprints. Progress
was managed in `issues.csv` and updated on a central GitHub Project Board using synchronization
scripts.

---

## Weekly sprints and ticket log

Work progressed on the feature branch `shrey-branch` before being merged into `main` via
pull requests.

### Sprint 1: Domain models and foundation (April 27 – May 3)
*Focus: Setting up the runtime environment, writing core domain entities, value objects,
invariants, and local persistence.*

- **Ticket 1: Project Scaffolding (Python)**
  - *Details*: Set up the Python project structure, grouping files into `src/digital_id` and
    `tests`. Added configuration files for `pyproject.toml`, `mypy`, and the `ruff` linter.
  - *Rubric focus*: Design, code quality, and test readiness.
- **Ticket 2: Domain Model (Digital ID)**
  - *Details*: Created the core `DigitalId` aggregate root, including status value objects,
    restrictions, and status history lists. Enforced domain level rules such as the immutability
    of the digital ID, national ID, and date of birth.
  - *Rubric focus*: Core functionality and design quality.
- **Ticket 3: Repository Layer (In-memory)**
  - *Details*: Wrote the `DigitalIdRepository` interface and the `InMemoryRepository` implementation,
    supporting quick lookups by both Digital ID and unique National ID.
  - *Rubric focus*: Design quality and database abstraction.
- **Ticket 4: Authorization + Validation Rules**
  - *Details*: Implemented the `AuthorizationService` to check user roles, and the `ValidationService`
    to validate field inputs and formats.
  - *Rubric focus*: Functionality and error handling.

---

### Sprint 2: Core workflows and command line interface (May 4 – May 10)
*Focus: Business workflows, organization-specific verification checks, logging, and the terminal UI.*

- **Ticket 5: Identity Management Services**
  - *Details*: Wrote the `IdentityService` to coordinate profile creation, mutable attribute
    updates, and status transitions. Handled terminal status validations and safe no-op transitions.
  - *Rubric focus*: Functionality and status lifecycle.
- **Ticket 6: Verification Strategies (Org-Specific)**
  - *Details*: Implemented custom verification rules for the four external organizations (Tax period
    audits, Driving Licence keyword filters, Local residency checks, and Bank eligibility checks).
  - *Rubric focus*: Functionality and data privacy.
- **Ticket 7: Audit Logging**
  - *Details*: Wrote the `AuditLog` service to record every transaction. Configured synchronous
    writes for crash safety, logging successes, no-ops, and denied attempts.
  - *Rubric focus*: Traceability and accountability.
- **Ticket 8: CLI Demo Runner (Scripted)**
  - *Details*: Created the command line runner. It runs a deterministic 24-step demo on startup,
    exports the audit log file, and opens an interactive console styled with ANSI colors and box-drawing.
  - *Rubric focus*: Presentation and UI design.

---

### Sprint 3: Testing, continuous integration, and hardening (May 11 – May 18)
*Focus: Test suite coverage, automated workflows, documentation, and persistent storage.*

- **Ticket 9: Unit Test Suite (Pytest)**
  - *Details*: Authored tests for happy paths, date boundary rules, status transitions, and role
    rejections, achieving over 95% code coverage.
  - *Rubric focus*: Verification, testing depth, and quality assurance.
- **Ticket 10: CI Pipeline (GitHub Actions)**
  - *Details*: Set up automated testing, linting, and type checking in GitHub Actions (`ci.yml`)
    on every push and pull request.
  - *Rubric focus*: Automated testing and continuous integration.
- **Ticket 11: README + Architecture Overview**
  - *Details*: Wrote the main repository documentation, explaining the layout, setup, and including
    a Mermaid architecture diagram.
  - *Rubric focus*: Technical communication.
- **Ticket 12: Video Demo Script**
  - *Details*: Created a script detailing the walkthrough to demonstrate happy paths and failure
    rejections.
  - *Rubric focus*: Technical communication.
- **Ticket 13: Development Evidence (Commits + Board Hygiene)**
  - *Details*: Structured development tracking by mapping git commits, issue statuses in `issues.csv`,
    and pull requests.
  - *Rubric focus*: Version control evidence.
- **Ticket 14: Production Readiness Hardening**
  - *Details*: Integrated the `JsonBackedRepository` for persistent CLI storage, updated service
    methods to return read-only DTO snapshots, and documented architecture decisions (ADRs).
  - *Rubric focus*: Robustness, maintainability, and code quality.

---

## Git workflow and branches

To maintain clean repository history:
1. All features were developed on `shrey-branch`.
2. Commits were kept small and descriptive.
3. Code was merged to `main` via pull requests after passing all local test, lint, and type gates.

---

## Project board automation

We synchronized the project board using automation scripts that read `issues.csv` and interact
with the GitHub API:

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

### Automation scripts
- `scripts/github_project_sync.py`: Reads `issues.csv` and automatically creates or updates GitHub Issues.
- `scripts/board_update.py`: Interacts with the GitHub Projects GraphQL API to move issues between
  `Todo`, `In Progress`, and `Done` columns based on the CSV data.
