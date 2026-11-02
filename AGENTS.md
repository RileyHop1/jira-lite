# AGENTS.md — Jira Lite

These are repository-wide working rules for AI coding agents (Codex, Claude Code, Cursor, Copilot, and others) contributing to **Jira Lite**, a DevOps take-home project. They apply to code, tests, infrastructure, scripts, and documentation.

## 1. Read project documents before changing code

Read the assignment and the SRS at the beginning of a task. Read the other documents when a task touches them, and reread relevant sections when requirements are uncertain:

1. The take-home assignment, a transcribed local copy in `docs/reference/`. **Authoritative for external assignment requirements.**
2. [`SRS.md`](SRS.md) — Jira Lite functional requirements, acceptance criteria, scope, stretch goals, and deliverables.
3. [`architecture-decisions.md`](architecture-decisions.md) — selected architecture, rejected alternatives, tradeoffs, implementation status, and unresolved decisions. Read the ADRs relevant to the task.
4. [`docs/project-plan.md`](docs/project-plan.md) — milestones and the setup, AWS, and verification steps the owner follows.
5. The recruiter's invitation email, a local copy in `docs/reference/`. **Authoritative for the submission deadline and the required confirmation**, which appear in neither PDF.
6. The job description, a transcribed local copy in `docs/reference/`, providing role and evaluation context for demo and documentation work; **not an additional list of assignment requirements.**
7. [`to-do-list.md`](to-do-list.md) — the ordered checklist of every step, who does it, and what's done, plus tentative plans for agent work. It's gitignored and stays on the owner's machine. **Its plans aren't agreed decisions.**

`docs/reference/` is gitignored: employer documents stay on the owner's machine and are never published. If the folder is missing, rely on `SRS.md` and tell the owner.

If sources appear to conflict, **do not silently reinterpret or rewrite them**. Flag the conflict for the owner. The employer assignment and recruiter email take precedence for employer-mandated requirements; the SRS and ADRs capture the project's chosen scope and design. This file governs development conduct, not product requirements. Keep the two PDF transcriptions faithful to their originals; correct transcription errors only after checking the original PDFs, which the owner keeps in `docs/reference/`.

## 2. Scope and architecture discipline

- The full submission is due by **11:59 p.m. Pacific on Friday, November 6, 2026**. The owner's time is limited, so when options are otherwise equal, choose the smaller one.
- Prioritize the required public Linux EC2 application, database-backed CRUD/persistence, working application-plus-database `/health`, and submission artifacts. Start the stretch goals in SRS §4 only after the baseline is verified and documented; they must not jeopardize delivery.
- Honor the selected design: Flask + Gunicorn + Nginx on Ubuntu EC2, DynamoDB, AWS Systems Manager Session Manager, IAM roles, and dedicated security group. CI, monitoring, rate limiting, automated deployment, and HTTPS are stretch goals. **A design decision is not proof of deployment.**
- The first working version uses only the confirmed stack: EC2 with Nginx, Gunicorn, and DynamoDB, with Flask as the app.
- **Nothing new without a discussion at length.** The owner must be able to explain every choice, and accepting a default doesn't count as discussing it. To suggest something new, explain it and wait. ADRs marked "Proposed" are not agreed yet.
- Explain every library, tool, and AWS feature in plain terms before its first use, including details already written in an ADR. Every design decision is the owner's. Agents lay out the options and a recommendation, record what the owner decides, and check recorded decisions against the ADRs and documentation, flagging any conflict.
- Work one agreed step at a time. Each phase in `docs/project-plan.md` starts on the owner's go-ahead.
- Keep implementation understandable, small, and repeatable. The approved packages are `flask` and `gunicorn`. `pytest` (test runner) and `ruff` (linter, including missing-docstring checks) are approved for laptop use only and never run on the server. `boto3` gets discussed before Phase 4. Any other framework, service, package, dashboard, or architecture change needs the same discussion and the owner's approval.
- Do not expand the application's feature scope beyond the SRS to make it more like full Jira.
- Never store credentials or private keys in the repository. Use appropriate IAM roles and configuration; do not expose Gunicorn or enable SSH merely for convenience.

## 3. Agent execution rules

- Inspect current code, tests, and documentation before editing. Make a short task plan for nontrivial changes; identify relevant SRS requirements and ADRs.
- Work in small, reviewable increments. Preserve existing behavior unless the change explicitly requires otherwise.
- Prefer established dependencies and repository conventions. Do not assume a package, command, service, or GitHub workflow exists until verified.
- Investigate errors using reproducible evidence (logs, error output, tests) and address root causes; do not mask failures or fabricate a troubleshooting story.
- Never claim tests, deployments, AWS settings, or endpoint behavior are verified unless actually checked. Report what ran, what passed, and what remains unverified.
- The employer allows AI tools **as long as the owner can explain everything deployed**. For any infrastructure, IAM, Nginx, systemd, or deployment change, state what it does, why it's needed, and what alternative was rejected, in plain terms the owner can repeat in the demo.
- Do not modify cloud resources, incur costs, merge PRs, or trigger a deployment without explicit authorization. The owner makes AWS changes; agents prepare the steps in `docs/project-plan.md`.
- At task completion, summarize changes, files affected, checks performed, and known risks/next steps.

## 4. Coding standards

- **Comments and structure:** Code is the project's main documentation. Every module and function gets a docstring with its purpose and any errors it raises. Inline comments explain why and anything non-obvious, not what the line already says. Every block in Nginx, systemd, and shell files gets a comment saying what it does and why. Keep modules small and focused, with clear names.
- **Python:** Follow PEP 8; use 4-space indentation, descriptive names, clear module boundaries, and type hints where they improve interfaces. Keep functions focused; prefer simple composition to clever abstractions.
- **Flask:** Keep HTTP routes thin, validate external inputs (including the SRS length limits), and place database operations in testable functions/modules. Return clear HTTP status codes and safe error messages.
- **Boto3/DynamoDB:** Centralize table access and configuration. Handle expected AWS errors explicitly; never swallow failures as success. Make health checks reflect real database reachability.
- **Frontend:** The approach isn't agreed yet (ADR-017). Anyone can write tasks, so task text must never be inserted as HTML.
- **Shell/scripts:** Prefer repeatable, idempotent steps. For Bash scripts use `set -euo pipefail` where appropriate; avoid destructive operations without safeguards and user approval.
- **Configuration/logging:** Keep secrets and machine-specific settings out of source. Use structured, actionable diagnostic messages without logging credentials, tokens, or sensitive request content.
- **General:** Avoid duplicated logic, dead code, undocumented magic values, unnecessary dependencies, and broad refactors mixed into feature patches.

## 5. Branches, commits, and pull requests

- The owner creates the repository and runs `git init`, the first commit, and the first push. The repository starts **private** and the owner makes it public before the first deploy (ADR-020). Once it exists, agents may push **feature branches** and open PRs through the owner's `gh` login. Agents never add remotes, change repository settings, or push to `main`.
- Everything on `main` is a feature the owner has reviewed and merged. Agents work on feature branches and never commit to or merge into `main`. Only the owner merges, using **squash merge**, so each PR becomes one commit on `main`. GitHub branch protection is not available on the owner's private repository (it needs a paid plan), so until the repository goes public (ADR-020) the rule is followed by discipline: **nobody pushes to `main` directly, including the owner; every change arrives through a squash-merged PR.** Once the repository is public, the owner turns on "Require a pull request before merging" with no required approvals and no bypass for admins, if the settings page allows it.
- Each PR delivers one feature. If work depends on an unmerged PR, do not start it until the owner has reviewed that PR.
- The branch and commit-message conventions below were agreed on 2026-11-01. PR titles follow the same Conventional Commits format, because the squash commit takes the PR title. Commits and PR descriptions carry the attribution lines the tooling specifies for the agent.
- Branch names use `feat/<topic>`, `fix/<topic>`, `docs/<topic>`, `test/<topic>`, `chore/<topic>`, or `ci/<topic>`. Use concise lowercase hyphenated topics.
- Use **Conventional Commits**, e.g. `feat: add task status update`, `fix: fail health check on DynamoDB error`, `test: cover invalid task inputs`, `docs: explain deployment`. One focused concern per commit; keep the history reviewable.
- Never commit `.env` secrets, AWS keys, local virtual environments, caches, build outputs, or debug data with sensitive content.
- Each PR should include **what changed and why**, referenced SRS requirement(s) / ADR(s), **tests and results**, risks or limitations, and deployment/rollback notes when applicable.
- Run applicable local checks before requesting review. Do not bypass failing tests, auto-merge, force-push shared branches, or claim code is ready without evidence.
- If implemented, GitHub Actions should run checks for PRs and deploy only from trusted `main` under the approved OIDC/SSM design; never grant deployment AWS credentials to untrusted PR code.

## 6. Testing and quality gates

- This project doesn't use full test-driven development. The assignment reviews the running deployment, so tests stay small and the live checks in `docs/project-plan.md` Phase 6 prove the system works.
- Write the test before the code where the SRS states the expected result: `/health` with the database available **and unavailable** (a Flask-only success response is not sufficient), and the task validation rules.
- Give each task route one success test, plus one rejected-input test for editing. Use the Flask test client and a stand-in for DynamoDB access, with no AWS calls.
- A bug in application code gets a test that reproduces it before the fix, when the test client can reproduce it.
- Adding tests beyond these needs the owner's approval.
- Verify persistence after application and EC2 restarts in the deployed environment when that environment exists; do not substitute an in-memory mock for this acceptance check.
- For deployment and CI changes, validate script behavior, least-privilege assumptions, failure handling, and health-based success. Do not mark untested operational behavior as complete.
- **Commands**, run from the repository root with the virtual environment active (`python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt`): `pytest` runs the tests, `ruff check` lints (including docstrings), and `ruff format --check` checks formatting. `scripts/run-local.sh` runs the app against DynamoDB Local and needs Docker.
- Run formatters, linters, and tests **configured in the repository**. If tooling is not configured yet, recommend a minimal setup rather than inventing passing checks or introducing heavyweight infrastructure.
- The expected bar is **correct, readable, and tested**, not an arbitrary coverage percentage. Report skipped and blocked checks explicitly.

## 7. Documentation and handoff

- Do not add a documentation file per feature; docstrings and comments carry that detail. The document set is `README.md`, `SRS.md`, `architecture-decisions.md`, `AGENTS.md`, `docs/project-plan.md`, `docs/troubleshooting-log.md`, and the architecture diagram, plus the local `docs/reference/` folder and `to-do-list.md`. Any other document needs the owner's approval.
- `to-do-list.md` tracks the order of the work, who does each step, and what's done, and holds tentative plans for agent work; `docs/project-plan.md` holds the exact settings and commands. Tick a step only once it's really done, and when a step changes, update both files.
- Keep `README.md` accurate on local setup, deployment, operations, current capabilities, and limitations. Update instructions in the same PR as any relevant change.
- Update `SRS.md` when scope or acceptance criteria change **only with owner approval**; update ADRs when an architectural decision is selected or revised, including alternatives and tradeoffs. Distinguish **selected**, **implemented**, and **verified**.
- Maintain an accurate architecture diagram and operations instructions as the deployment becomes real. Do not imply the design is live when it is only planned.
- Keep original employer documents in `docs/reference/` as reference copies outside Git. Never alter their substance to match the implementation.
- On any real failure, before moving on, append the symptom, exact error, diagnosis, root cause, and fix to `docs/troubleshooting-log.md`. This is evidence for the final demo; do not manufacture incidents, resolutions, test results, URLs, or cost figures.

## 8. Definition of done

A change is ready for review when it is scoped to the SRS/ADRs, code is readable, tests/checks have been run or honestly identified as blocked, documentation matches behavior, credentials are absent from the diff, and the PR clearly states risks. Merging, provisioning, and deployment remain owner-controlled actions.
