# Software Requirements Specification (SRS)

**Project:** Jira Lite — Single-Page Kanban Task Board  
**Purpose:** DevOps Engineer Take-Home Assignment  
**Version:** 1.1 (scope and source updates)  
**Date:** October 30, 2026  
**Submission deadline:** November 6, 2026, 11:59 p.m. Pacific

## 1. Purpose and Scope

Jira Lite is a deliberately small, database-backed task-tracking web application. Its user interface consists of a **single-page Kanban board** with three columns: **To Do**, **In Progress**, and **Done**.

The application is thematically related to workplace collaboration software. Its primary purpose, however, is to demonstrate the ability to **deploy, secure, operate, troubleshoot, and explain** a web service running on AWS. Infrastructure quality takes priority over application complexity.

### Intended user

A visitor who opens the public application URL in a browser. No login or separate user roles are required for this demonstration.

### In scope

Creating, viewing, modifying, and deleting tasks; displaying tasks by status; persisting data; exposing an application/database health check; and deploying a publicly reachable service on Linux-based Amazon EC2.

### Out of scope

User accounts and authentication, team roles and permissions, multiple boards/projects, task assignments, deadlines, comments, notifications, activity history, and advanced Jira features. Drag-and-drop is **not required**; a simple status selector is sufficient.

## 2. Functional Requirements

| ID | Requirement |
| --- | --- |
| FR-01 | The system **shall** allow a visitor to create a task with a title, description, and status. |
| FR-02 | The system **shall** display all saved tasks on one Kanban board, grouped into **To Do**, **In Progress**, and **Done**. |
| FR-03 | The system **shall** allow a visitor to edit an existing task's title, description, and status. |
| FR-04 | The system **shall** allow a visitor to delete a task. |
| FR-05 | The system **shall** store task changes in a database and read them back when displaying the board. |
| FR-06 | The system **shall** expose a health endpoint (for example, `/health`) that checks both application availability and database connectivity. |

### Task data and validation

The only **user-facing task fields** are:

| Field | Rule |
| --- | --- |
| Title | Required; cannot be blank; at most 200 characters. |
| Description | Optional; may be blank; at most 2,000 characters. |
| Status | Required; exactly one of **To Do**, **In Progress**, or **Done**. |

The system may maintain an internal task identifier and creation time to distinguish and order records; these are not additional user-facing fields. Inputs that fail validation shall be rejected with a clear error rather than silently saved.

## 3. Nonfunctional Requirements

| ID | Requirement |
| --- | --- |
| NFR-01 — Persistence | Saved tasks **shall** remain available after an application restart and a restart of the same EC2 instance. |
| NFR-02 — Availability | The web page **shall** be reachable through a public URL while the assignment is under review, subject to ordinary service and AWS availability. |
| NFR-03 — Health | The health endpoint **shall** report success only when the application can access its database; database failure shall produce a failure response. |
| NFR-04 — Security | The deployment **shall** restrict administrative access and expose only the network ports required for the application. |
| NFR-05 — Secrets | Source code, the Git repository, and published documentation **shall not** contain passwords, private keys, or other secrets. |
| NFR-06 — Cost | The deployment **shall** use an AWS Free Tier-eligible configuration when the account permits; actual account eligibility and estimated charges must be checked, and a billing alert configured before any other AWS work. |
| NFR-07 — Operability | The deployment **shall** have documented steps for starting, stopping, restarting, checking status, and locating application/service logs. |
| NFR-08 — Simplicity | The implementation **shall** remain small enough to deploy, debug, and explain within the assignment's time constraints. |

**Security scope note:** Because there is no authentication, anyone who can reach the demo may modify its tasks. The service must use demonstration data only. Adding real employee data or treating this as a production-ready collaborative application is out of scope.

## 4. Deployment Constraints

These constraints come directly from the take-home assignment:

- The deployed application **must run on a Linux-based Amazon EC2 instance**.
- The web page **must be publicly accessible** through a browser URL.
- A database **must store and return** application data.
- A health-check endpoint **must verify** application and database operation.
- The solution should be designed to remain within applicable AWS Free Tier limits; costs must be monitored rather than assumed to be zero.
- The application must remain running until the reviewers indicate that their review is complete.

**Architecture decisions:** programming language, framework, Linux distribution, database engine, EC2 instance type, reverse proxy, process manager, and deployment approach are not predetermined requirements. The selected choices are recorded in [`architecture-decisions.md`](architecture-decisions.md).

### Stretch goals (only after the baseline is verified and documented)

The baseline is everything needed to pass AC-01 through AC-11. Nothing in this section is required for acceptance. Start these only after the baseline works and the README and diagram are done, and work through them in this order. Each needs a discussion with the owner before it starts:

1. **CI:** GitHub Actions runs the tests on every push and pull request, with no AWS credentials.
2. **Basic monitoring:** A CloudWatch alarm emails the owner when the EC2 instance fails its status checks.
3. **Rate limiting:** Nginx limits requests per client to reduce abuse of the public write endpoint.
4. **Automated deployment:** A push to `main` deploys through GitHub OIDC and AWS Systems Manager Run Command (ADR-012).
5. **HTTPS/TLS:** Once the core application is deployed, publicly reachable over HTTP, persistent, and demonstrably healthy, configure HTTPS on Nginx if time and certificate provisioning permit. This requires a domain, which the baseline does not use. Prefer a free, trusted TLS certificate (such as Let's Encrypt), automate renewal where practical, and redirect HTTP (port 80) to HTTPS (port 443). Keep Gunicorn reachable only locally; Nginx terminates TLS and reverse-proxies requests to the Flask application. **HTTPS is not a baseline acceptance requirement.** If deferred, identify unencrypted HTTP traffic as a known limitation and require HTTPS before real-user production use.

Leave out any stretch goal that isn't finished and verified rather than submitting it half-working, and name it in the video as something to change before serving real customers. Docker, infrastructure as code, and Raspberry Pi development/testing are optional and not planned; the Raspberry Pi cannot replace EC2 as the submitted host.

## 5. Acceptance Criteria and Verification

Each item should be demonstrably true before submission.

| ID | Pass condition / verification |
| --- | --- |
| AC-01 | Open the public AWS URL from an external browser and load the single-page Kanban board. |
| AC-02 | Create a task with a title, description, and chosen status; verify it appears in the correct column. |
| AC-03 | Edit a task's title, description, and status; reload the page and verify the changes remain. |
| AC-04 | Delete a task; reload the page and verify it remains deleted. |
| AC-05 | Restart the application and then the same EC2 instance; verify previously saved tasks remain in the database. |
| AC-06 | Request `/health` with the database available and verify success; simulate database unavailability and verify a failure response. Restore the service afterward. |
| AC-07 | Confirm only necessary inbound ports are open, administrative access is restricted, and the repository contains no credentials or secrets. |
| AC-08 | Confirm actual AWS Free Tier eligibility, estimated charges, and billing alert; review ongoing usage before submission. |
| AC-09 | The README explains local setup, deployment, operation, and architectural tradeoffs; the diagram accurately follows a browser request through the deployed system and back. |
| AC-10 | Demonstrate a genuine failure encountered during development, the evidence used to diagnose its root cause, and the corrective action. |
| AC-11 | Provide a clear 2–5 minute video demonstrating the live app, architecture and alternatives considered, security/cost decisions, troubleshooting, and changes needed before serving real customers. If an optional enhancement was added, the submission explains why it was chosen. |

These checks operationalize the assignment's five evaluation categories: **It works; Architecture choices; Security and cost; Troubleshooting; Communication.**

## 6. Required Submission Deliverables

By **Friday, November 6, 2026, at 11:59 p.m. Pacific**, reply to the recruiter with:

1. **Live app URL** (leave it running until review is complete).
2. **Git repository URL**, including a README with run and deployment instructions.
3. **Architecture diagram** included in the README as an accessible image or file, showing AWS services and the request/response path.
4. **2–5 minute demo video** covering all topics in AC-11, including an alternative considered for each main architectural decision and why it was not selected.
5. **One-line confirmation** required by the instructions, **only if it is accurate**.

## 7. Design Principle

**Keep the app simple; make the deployment defensible.** A well-documented, reliable small application is the objective. Any feature or infrastructure enhancement must justify its additional complexity against the deadline and assessment criteria.

---

**Reference documents:** the take-home assignment, the job description, and the recruiter's invitation email, which is the source of the submission deadline. These are kept locally in `docs/reference/`, outside Git. This SRS also incorporates the project scope agreed during planning; requirements that go beyond the employer's mandatory minimum are project decisions rather than claims about the employer's rubric.
