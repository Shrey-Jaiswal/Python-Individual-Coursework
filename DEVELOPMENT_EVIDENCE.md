# Development Evidence

## Workflow summary
- Work happens on `shrey-branch` one ticket at a time.
- Each ticket is completed in 3-5 meaningful commits.
- After a ticket is complete, `issues.csv` is updated to reflect status.
- The project sync script is run to update the GitHub project board.
- The branch is merged to `main` after the ticket is verified.

## Evidence sources
- Ticket list and status: `issues.csv`
- Commit history: `git log --oneline --decorate --graph`
- CI verification: GitHub Actions workflow in `.github/workflows/ci.yml`

## Project board sync
The board is updated using the provided script after each ticket:

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

## Notes
- The evidence is intentionally lightweight and focuses on traceable progression.
- The `issues.csv` file is the single source of truth for ticket status.
