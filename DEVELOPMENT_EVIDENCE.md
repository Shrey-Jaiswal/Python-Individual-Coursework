# Development Evidence

## Development Timeline & Sprint Log

To demonstrate a structured and incremental development process, work was divided into weekly sprints and tracked via GitHub Issues and a Project Board. Below is the chronological progression of the 13 core tickets.

### Sprint 1: Core Domain & Infrastructure (April 27 - May 3)
*Focus: Project scaffolding, core domain logic, and basic persistence.*
- **Project scaffolding (Python)**: Setup Python project, pyproject.toml, ruff/mypy configs.
- **Domain model (Digital ID)**: Implemented `DigitalId` aggregate, value objects, and immutable constraints.
- **Repository layer (in-memory)**: Created the `InMemoryRepository` to enable deterministic testing.
- **Authorization + validation rules**: Established the `AuthorizationService` to ensure only the central authority can modify identities.

### Sprint 2: Application Services & Core Features (May 4 - May 10)
*Focus: Business workflows, role-specific verification, and traceability.*
- **Identity management services**: Built the `IdentityService` to handle creation, updates, and status transitions safely.
- **Verification strategies (org-specific)**: Implemented isolated validation rules for Tax, Driving Licence, Local Authority, and Banks.
- **Audit logging**: Built the `AuditLog` to record all successful and denied operations for strict traceability.
- **CLI demo runner (scripted)**: Implemented the deterministic CLI to run the automated scenario without user input.

### Sprint 3: Testing, CI, and Hardening (May 11 - May 18)
*Focus: Quality assurance, documentation, and production readiness.*
- **Unit test suite (pytest)**: Achieved >95% coverage across domain rules, services, and failure paths.
- **CI pipeline (GitHub Actions)**: Automated testing, type checking, and linting on push/PR to `main`.
- **README + architecture overview**: Documented the system, including Mermaid diagrams and setup instructions.
- **Video demo script**: Outlined the recording flow to demonstrate both happy paths and explicit failure rejections.
- **Production readiness hardening**: Introduced `IdentitySnapshot` DTOs, JSON persistence adapters, and comprehensive architecture decisions.

## Workflow Summary
- Work happened organically on `shrey-branch` one ticket at a time.
- Each ticket was completed in meaningful commits reflecting logical progression.
- After a ticket was complete, `issues.csv` was updated to reflect status.
- The project sync script was run to update the GitHub project board.
- The branch was merged to `main` via Pull Requests.

## Evidence Sources
- Ticket list and final status: `issues.csv`
- Commit history: `git log --oneline --decorate --graph`
- CI verification: GitHub Actions workflow in `.github/workflows/ci.yml`

## Project Board Sync Script
The board was iteratively updated using the provided script after each ticket:

```bash
export GITHUB_HOST=github.com
export GITHUB_TOKEN=REPLACE_WITH_TOKEN
export GITHUB_OWNER=Shrey-Jaiswal
export GITHUB_REPO=Python-Individual-Coursework
export PROJECT_TITLE="Python Coursework"
export PROJECT_OWNER_TYPE=user
export CSV_PATH=issues.csv
export UPDATE_EXISTING=true
export REOPEN_CLOSED=true
export DRY_RUN=false

python scripts/github_project_sync.py
```
