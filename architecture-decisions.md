# Jira Lite — Architecture Decisions

**Project:** DevOps take-home assignment  
**Started:** 2026-10-30  
**Status:** Living document — update as decisions are made and verified

## Purpose

Record *why* we chose each major component, the alternatives considered, and the operational tradeoffs. This document complements the Software Requirements Specification (SRS): the SRS defines what Jira Lite must do; this file records architectural choices about how it will be built and deployed.

**Important:** A selected design is not the same as a deployed or tested system. The decisions below document our current plan, not completed implementation. A **proposed** decision has not been discussed with the developer yet and can still change.

## Current architecture (selected design)

- **Public entry point:** Nginx, running on a Linux-based Amazon EC2 instance.
- **Python application server:** Gunicorn, running on the same EC2 instance and receiving proxied application requests.
- **Backend framework:** Flask, running within Gunicorn-managed Python worker processes.
- **Database:** Amazon DynamoDB, a managed AWS service separate from EC2 (selected; see ADR-004).
- **AWS account and Region:** A dedicated Jira Lite AWS project on the Free plan, signed in through an MFA-protected AWS Builder ID, deployed in `us-east-2` (accepted and configured 2026-11-01; deployment capabilities still to be verified; ADR-014).
- **EC2 instance:** `t3.micro` (2 vCPUs, 1 GiB RAM) with Standard CPU credits (selected; not yet deployed). Actual charges on the new account still need checking (ADR-005).
- **Operating system:** Ubuntu Server 24.04 LTS (selected; not yet deployed).
- **Root disk:** 16 GiB Amazon EBS `gp3` general-purpose SSD (selected; not yet provisioned).
- **VPC:** Use the AWS **default VPC** for the deployment region (selected, conditional on one being present). Plan to place the EC2 host in a default public subnet; confirm internet routing and public IPv4 allocation during setup. The dedicated security-group design is selected; public IPv4 assignment and routing still need deployment verification.
- **Security group (design):** Dedicated group; inbound TCP 80 from the internet for Nginx; no inbound SSH/22 or Gunicorn/8000; outbound initially permitted; TCP 443 for inbound HTTPS only if the stretch goal is implemented.
- **Public URL:** An Elastic IP with no domain (proposed; not yet discussed; ADR-015).
- **Transport security:** Start with HTTP for the baseline; HTTPS/TLS is an SRS stretch goal, not a committed launch requirement.
- **Scope priority:** Deliver and test mandatory EC2 app, persistence, and `/health` plus required submission materials before stretch goals. CI, basic monitoring, rate limiting, automated deployment, and HTTPS are stretch goals, in that order (ADR-013).
- **Process management and deployment:** systemd runs Gunicorn, and the developer deploys with a short script through Session Manager (proposed; not yet discussed; ADR-016).
- **Deployment automation (stretch goal):** **GitHub Actions** is the selected design if time remains. Planned flow: push to `main` → run tests → use GitHub OIDC to assume a narrowly scoped AWS deployment IAM role → invoke AWS Systems Manager Run Command on the EC2 instance → deploy/restart Gunicorn → verify `/health`. Specific deployment packaging, IAM policy scopes, and workflow triggers require implementation and testing.
- **Server administration:** AWS Systems Manager **Session Manager** (selected). No inbound SSH/port 22 rule; access will be authorized through IAM rather than SSH keys.
- **IAM:** Use an EC2 instance profile/IAM role with permissions for SSM Agent, plus separately scoped DynamoDB application permissions (selected approach; policies listed in `docs/project-plan.md`; not yet created). The human operator needs their own identity permissions to start sessions. No hard-coded AWS access keys.
- **Database integration:** Python AWS SDK (Boto3) using temporary credentials from the EC2 instance role (drafted; not yet discussed; ADR-004).

**Planned request flow:** Browser → Nginx (EC2) → Gunicorn (EC2) → Flask application → DynamoDB (when data access is needed); responses return in reverse. Nginx can serve static frontend files directly (proposed in ADR-017).

## ADR-001 — Use Nginx as the public-facing web server and reverse proxy

**Status:** Selected; not yet deployed.

**Decision:** Use Nginx to accept incoming HTTP requests, serve static frontend assets, and forward application/API requests to Gunicorn. If HTTPS is implemented, Nginx can handle TLS termination.

**Rationale:** Assign the public HTTP entry point and reverse-proxy responsibilities to a focused component, independently configurable from the Python application server.

**Alternative considered:** Apache HTTP Server could fulfill the same reverse-proxy role. Apache with `mod_wsgi` could also host the Flask application without Gunicorn.

**Tradeoffs:** A dedicated reverse proxy gives clear responsibility boundaries and control of static assets and incoming traffic, but introduces a separate service and configuration to operate and troubleshoot. Apache is a viable alternative; it is not inherently inferior or necessarily more complicated.

## ADR-002 — Use Gunicorn to host the Flask application

**Status:** Selected; not yet deployed.

**Decision:** Run Flask using Gunicorn, a Python WSGI application server responsible for accepting proxied HTTP requests, managing Python worker processes, and invoking the Flask application.

**Rationale:** Keep application-worker and request-execution concerns separate from public-facing HTTP proxying. Python remains the runtime executing the application code; Gunicorn is not a replacement for the Python interpreter.

**Alternative considered:** Apache with `mod_wsgi` could combine public web serving and WSGI application hosting. Gunicorn could also serve the app directly without Nginx, although that would give up the chosen independent reverse-proxy layer.

**Tradeoffs:** An independent application server creates clear boundaries but means maintaining Gunicorn and Nginx as two processes/services rather than using a combined solution.

## ADR-003 — Use Flask for the backend

**Status:** Selected; not yet implemented.

**Decision:** Use Flask to define Jira Lite's HTTP routes and application logic.

**Rationale:** Flask is a lightweight Python framework suitable for the small API required by Jira Lite and works with Gunicorn through WSGI.

**Tradeoffs / alternatives:** More structured frameworks could offer additional features, but are not currently required. Specific framework alternatives have not yet been evaluated in detail.

## ADR-004 — Use Amazon DynamoDB for persistence

**Status:** DynamoDB is selected, and the developer's rationale is recorded below. The comparison with alternatives, table design (key `id`, `Scan` for listing), and capacity (5 read / 5 write, auto scaling off) were accepted on 2026-11-01. The owner reports the table `jira-lite-tasks` was created in `us-east-2` (ADR-014 audit); app integration is in PR 1 and not yet deployed or verified on EC2.

**Decision:** Use DynamoDB as Jira Lite's database.

**Rationale:** The developer chose DynamoDB because it runs separately from the EC2 instance and demonstrates breadth of AWS knowledge. DynamoDB is a fully managed, serverless service: Jira Lite will use a table, not a database instance. Both reasons also apply to Amazon RDS, so they do not by themselves explain choosing DynamoDB over RDS.

**Drafted comparison with alternatives (not yet discussed):** Jira Lite stores one simple record type with no relationships, so it gains little from a relational database. DynamoDB has no database server to size or patch. The EC2 instance role authorizes access, so there is no database password to store, and the application makes outbound HTTPS API calls, so no database port is opened.

- **Amazon RDS** suits relational data and SQL queries, but adds a database instance, credentials, and network rules that this data model does not need.
- **A database on the EC2 instance** (for example, PostgreSQL) needs no additional AWS service, but competes for the host's 1 GiB of RAM, makes backups and patching the developer's responsibility, and ties the data to the instance's EBS volume.

**Tradeoffs:** DynamoDB gives up joins and ad hoc queries, so access patterns must be known in advance. Listing every task requires a `Scan`, which reads the whole table; this is acceptable for one small board but would need redesign at scale. Reads are eventually consistent by default, so the board should request strongly consistent reads to avoid showing stale data after an edit or delete (AC-03, AC-04). Local development needs stubs or DynamoDB Local, and the design depends on an AWS-specific service. Relational data or complex queries would be a reason to revisit this choice before serving real customers.

**Implementation details (drafted; not yet discussed):** One table, `jira-lite-tasks`, in the DynamoDB Standard table class, with partition key `id` (a UUID string) and attributes `title`, `description`, `status`, and an internal `created_at` that keeps cards in a stable order. Flask accesses it via Boto3, and the EC2 IAM role allows only `GetItem`, `PutItem`, `UpdateItem`, `DeleteItem`, and `Scan` on this table, with no static access keys. The health check behavior is in ADR-018.

**Capacity (drafted; not yet discussed):** Use provisioned capacity of 5 read and 5 write units with auto scaling off. AWS ties DynamoDB's always-free allowance (25 GB of storage, 25 read units, 25 write units) to provisioned capacity on the Standard table class, and fixed capacity throttles requests under a flood instead of scaling with it. On-demand capacity needs no planning and absorbs traffic spikes, but it charges per request, and the AWS pages reviewed do not confirm that the free allowance covers it. The tradeoff is that a flood can slow or fail requests. Actual usage still needs checking after deployment.

**Sources:** [Amazon DynamoDB pricing](https://aws.amazon.com/dynamodb/pricing/) · [What is Amazon DynamoDB?](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Introduction.html).

## ADR-005 — Prefer EC2 `t3.micro` for the application host

**Status:** Selected; not deployed. AWS documents `t3.micro` as Free Tier eligible for both older accounts and accounts on its current credit-based program. Confirm regional availability and actual charges on the new account.

**Decision:** Plan for a Linux EC2 `t3.micro` to host Nginx, Gunicorn and Flask. The instance provides **2 vCPUs and 1 GiB RAM**. DynamoDB remains a separate managed database service.

**Rationale:** Jira Lite is expected to have very low traffic and intermittent short CPU-intensive periods. The **T3 burstable** family has a baseline CPU allowance, lets an instance accumulate CPU credits while below baseline, and allows short periods of higher CPU utilization by spending those credits. On `t3.micro`, the baseline is **10% per vCPU**, with **12 credits earned per hour** at baseline and a maximum accrued credit balance of **288**. Bursting is *additional access to CPU processing time*, **not** a change in clock speed or vCPU count.

**Alternative considered:** A non-burstable M-family instance offers more consistent sustained processing capacity but would be oversized for this small app. Other burstable families exist, such as T2 and T4g; T4g uses ARM architecture, while T3 is x86-64. These alternatives were discussed at the family level, not benchmarked for this app.

**Tradeoffs and operational constraints:** A small burstable instance is economical for occasional activity, but **1 GiB of RAM is a tight limit** for Linux, Nginx, and Gunicorn together. CPU credits have a cap, so sustained above-baseline demand is not free. **Standard** CPU credit mode throttles back toward baseline when credits run out; **Unlimited** can incur surplus CPU charges when sustained utilization exceeds baseline. Standard mode is selected for cost predictability. T3 instances launch in Unlimited mode by default, so Standard must be chosen under Advanced details when launching the instance. EC2 billing is primarily based on provisioned runtime and related resources, **not actual CPU utilization**, though Unlimited surcharges can apply. Charges for the instance, storage, and public IPv4 usage are expected to draw on the new account's credits, but are not yet confirmed.

**Sources:** [AWS T3 instance specifications](https://aws.amazon.com/ec2/instance-types/t3/) · [AWS burstable credit concepts](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-credits-baseline-concepts.html) · [Free Tier usage for Amazon EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-free-tier-usage.html) · [T3 launch credit settings](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-performance-instances-how-to.html).

## ADR-006 — Use Ubuntu Server 24.04 LTS on EC2

**Status:** Selected; not yet deployed.

**Decision:** Run the application host on **Ubuntu Server 24.04 LTS**.

**Rationale:** The developer has daily-driven Ubuntu and has practical experience administering Debian-based Linux distributions. Familiarity with APT, system administration, and troubleshooting reduces initial setup time, the learning curve, and the likelihood of avoidable configuration mistakes. Ubuntu is well documented, has an LTS maintenance lifecycle, and fully supports the planned Nginx → Gunicorn → Flask stack. This is a **lower operational risk and shorter ramp-up time for this project**, not a claim that Ubuntu inherently provides better server uptime or availability.

**Alternative considered:** **Amazon Linux 2023**, an AWS-maintained distribution designed for AWS workloads. It uses DNF rather than APT and offers EC2-oriented defaults, package-versioning/reproducibility features, and AWS support and integration. It was not selected because the application has no Amazon-Linux-specific requirement, while learning unfamiliar administration conventions would add work without a demonstrated benefit for this assignment.

**Tradeoffs:** Ubuntu does not have some Amazon Linux-specific tooling and packaging conventions, but works with standard AWS IAM roles, monitoring integrations, and EC2 infrastructure. Prior familiarity is a valid operational advantage for a small, time-limited assignment; it does not replace ongoing updates, service supervision, monitoring, or security configuration.

**Interview-ready rationale:** “I chose Ubuntu Server 24.04 LTS because I've used Ubuntu regularly and have experience with Debian-based distributions. Both Ubuntu and Amazon Linux can run the stack, but using a familiar OS reduces setup time and makes troubleshooting more predictable. Amazon Linux is a reasonable alternative for deeper AWS-specific operational alignment; our application doesn't require its particular features.”

**Sources:** [Ubuntu 24.04 LTS release notes](https://documentation.ubuntu.com/release-notes/24.04/) · [Amazon Linux 2023 user guide](https://docs.aws.amazon.com/linux/al2023/ug/what-is-amazon-linux.html).

## ADR-007 — Use 16 GiB of EBS gp3 root storage

**Status:** Selected; not yet provisioned. AWS account-specific costs and Free Tier coverage remain to be verified.

**Decision:** Attach a **16 GiB Amazon Elastic Block Store (EBS) gp3** general-purpose SSD root volume to the Ubuntu EC2 instance. This stores Ubuntu, Nginx, Gunicorn, Flask, application files, configuration, and system logs. Jira Lite's task and board records remain in **DynamoDB**, not on the EC2 disk.

**Rationale:** gp3 is a general-purpose SSD with predictable baseline I/O performance independent of the provisioned storage size. For the small prototype, 16 GiB is a modest allocation that leaves room for OS updates and logs without reserving a large volume. EBS is the storage service; gp3 is one volume type offered by that service. “Elastic” means capacity can be explicitly expanded, not that disk usage automatically increases its allocated capacity.

**Alternative considered:** **gp2** EBS general-purpose SSD, which ties baseline I/O performance more closely to volume size and uses burst credits for small volumes. gp3 avoids this dependency and normally offers lower per-GB storage pricing. An 8 GiB gp3 volume was also considered, but would provide less headroom for OS packages and logs.

**Tradeoffs:** EBS is billed based primarily on **provisioned** storage and performance parameters, not only used file space. Root EBS volumes persist through a normal EC2 stop/start, but can be deleted on instance termination according to the *Delete on Termination* setting. 16 GiB is a starting estimate, not a tested minimum; check free space and actual billing after deployment.

**Reference:** [AWS EBS general-purpose SSD volumes](https://docs.aws.amazon.com/ebs/latest/userguide/general-purpose.html).

## ADR-008 — Use the default AWS VPC for Jira Lite

**Status:** Selected design; not yet configured. Confirm that a default VPC exists in the target AWS region.

**Decision:** Run the single Jira Lite EC2 instance inside the AWS-managed **default Virtual Private Cloud (VPC)** rather than creating a custom VPC. The planned network path uses a **public default subnet**, an Internet Gateway route, and a public IPv4 address so browsers can reach Nginx. An Elastic IP is proposed for the public address (ADR-015), and the exact subnet will be chosen during deployment; the security-group design is recorded in ADR-010.

**Rationale:** A VPC provides the private, logically isolated network in which our EC2 instance resides. The default VPC normally comes with subnets, a main route table, an Internet Gateway, and established internet routing, avoiding unnecessary setup for a single, low-traffic EC2 application. It lets us focus on safe access rules, deployment, and observability rather than custom network topology.

**Alternative considered:** Build a **custom VPC**, with explicitly chosen CIDR ranges, subnets, routes, and potentially a private EC2 subnet fronted by a public Application Load Balancer. A custom VPC allows more deliberate segmentation and isolation, but would introduce additional configuration, complexity, and potentially costs without a demonstrated need for Jira Lite.

**Tradeoffs and security:** Default VPC does **not** mean security is automatically correctly configured. A route to an Internet Gateway plus a public IPv4 address can make an EC2 instance reachable, but the **security group** governs which inbound connections are permitted. We still need to define least-privilege web and administrative access, avoid publicly exposing Gunicorn, and review IPv4 charges. Default-VPC presence is region/account-specific; if missing, choose a minimally configured VPC instead. **A least-privilege security-group design has since been selected (ADR-010), but public IP assignment and actual AWS configuration are not yet verified.**

**Reference:** [AWS default VPC and default subnets](https://docs.aws.amazon.com/vpc/latest/userguide/default-vpc.html).

## ADR-009 — Administer EC2 through AWS Session Manager with IAM roles

**Status:** Accepted on 2026-11-01; not yet configured or tested. Selected for Phase 4 deployment.

**Decision:** Use **AWS Systems Manager Session Manager** to administer the Jira Lite Ubuntu EC2 instance through browser-based shell sessions. **Do not expose inbound SSH port 22.**

Use the existing MFA-protected AWS Builder ID and its project administrator role for human administration.

Attach a dedicated **IAM role through an EC2 instance profile** to provide temporary AWS credentials for the SSM Agent and Flask application's Boto3 calls. Use `AmazonSSMManagedInstanceCore` for SSM connectivity and a separately scoped DynamoDB policy granting only the required operations on Jira Lite's table.

Before deployment, verify how the new AWS project account's default application permissions interact with the intended instance role.

**Rationale:** Session Manager provides secure administrative access without opening an SSH port, configuring SSH keys, or storing long-lived AWS credentials.

This reduces the publicly exposed network surface while providing experience with core AWS operational practices, including IAM roles, instance profiles, temporary credentials, and Systems Manager.

The existing AWS project administrator role eliminates the need to create a separate IAM console user. AWS Builder ID provides human authentication, while the EC2 instance role provides programmatic access for applications and services.

The architecture also keeps administrative access separate from public application traffic.

**Alternatives considered:**

- **SSH with key-based authentication:** Simpler and independent of Systems Manager, but requires SSH key management and inbound TCP port 22, restricted to the developer's public IP. Rejected in favor of Session Manager.
- **Systems Manager Default Host Management Configuration:** Automatically manages compatible EC2 instances without individual instance profiles. AWS recommends it for supported environments. However, a dedicated instance profile gives this small deployment a clearer boundary for application-specific permissions. Retained as a fallback if the intended instance-role setup is unavailable.
- **AWS access keys stored on EC2:** Would allow Boto3 calls but introduces long-lived credentials that require storage, rotation, and protection. Rejected.

**Implementation requirements / security boundaries:**

- **Region and account:** All infrastructure is located within the dedicated Jira Lite AWS project in `us-east-2` (Ohio), as established in ADR-014.
- **SSM Agent:** Use an Ubuntu Server 24.04 LTS AMI with SSM Agent preinstalled. Verify its status using `sudo snap services amazon-ssm-agent`. If necessary, start it using `sudo snap start amazon-ssm-agent`.
- **Instance permissions:** Create an EC2 IAM role with a trust policy allowing `ec2.amazonaws.com` to assume it. Attach `AmazonSSMManagedInstanceCore` and a separate least-privilege DynamoDB policy. Associate the role with the instance through its instance profile.
- **Application permissions:** Restrict DynamoDB access to the Jira Lite table and required operations, such as `GetItem`, `PutItem`, `UpdateItem`, `DeleteItem`, and `Scan`. Confirm actual permissions after deployment, including the effect of AWS project-managed defaults.
- **Human permissions:** Use the existing project administrator role. Confirm that it permits `ssm:StartSession` and related session-management actions. Do not create a separate IAM console administrator.
- **Authentication:** MFA is enabled on the AWS Builder ID. No AWS access keys are required on the developer's computer or stored in the application configuration.
- **Network connectivity:** The EC2 instance must reach Systems Manager endpoints through outbound HTTPS/TCP 443. Use the default VPC and its public-subnet internet route. Do not provision NAT gateways or paid VPC endpoints for this demonstration.
- **Inbound security:** Allow HTTP port 80 to Nginx. Keep TCP port 22 closed. Gunicorn listens only on `127.0.0.1:8000`, not on a public interface. HTTPS port 443 is reserved for the optional stretch goal (ADR-010).
- **Session security:** Review `ssm-user` privileges. Session history is available through Systems Manager; full shell transcript logging requires separate configuration and is not assumed to be enabled. Administrative shell sessions may provide elevated operating-system privileges.

**Verification requirements:**

1. Confirm the intended EC2 IAM role and instance profile can be created and attached within the project's managed security environment.
2. Confirm the launched instance appears as a managed node in Systems Manager.
3. Start an interactive shell from the EC2 console using Session Manager.
4. Verify SSM Agent is running.
5. Confirm the application can reach DynamoDB using temporary instance credentials without access keys.
6. Confirm the application's effective DynamoDB permissions are consistent with the intended least-privilege policy.
7. Confirm port 22 is not open and Gunicorn listens only on localhost.

The earlier successful `aws ssm describe-instance-information` command proves read access to the Systems Manager API, but not that Session Manager connections work. That must be tested after EC2 launches.

**Tradeoffs:** Session Manager depends on a working SSM Agent, AWS permissions, outbound connectivity, and Systems Manager service availability. Misconfiguration can prevent administrative access even when the instance itself is healthy.

AWS project accounts provide managed security defaults and broad same-project resource access. Those defaults simplify initial setup but complicate verification of application-level least privilege. The intended permissions must be tested rather than assumed.

Creating a dedicated instance profile introduces additional IAM configuration compared with Default Host Management Configuration, but provides an explicit security model suitable for explaining during the DevOps assessment.

Optional CloudWatch or S3 session logging may introduce costs. It is not required for the baseline deployment and must be reviewed separately before enabling.

**Sources:**

- [AWS Session Manager setup](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-getting-started.html)
- [Instance IAM permissions](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-getting-started-instance-profile.html)
- [Default Host Management Configuration](https://docs.aws.amazon.com/systems-manager/latest/userguide/fleet-manager-default-host-management-configuration.html)
- [AWS project sign-up and permissions](https://docs.aws.amazon.com/accounts/latest/reference/sign-up-for-aws.html)
- [AWS project security policies](https://docs.aws.amazon.com/accounts/latest/reference/scps-and-rcps-for-projects.html)
- [Operator access policies](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-getting-started-restrict-access.html)
- [Install SSM Agent on Ubuntu with Snap](https://docs.aws.amazon.com/systems-manager/latest/userguide/agent-install-ubuntu-64-snap.html)
- [Session Manager logging](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-logging.html)

## ADR-010 — Use a dedicated, least-privilege EC2 security group

**Status:** Selected design; not yet created or tested in AWS.

**Decision:** Create a **dedicated security group for Jira Lite**, rather than using the default VPC security group. For the initial HTTP-based baseline:

- **Inbound TCP 80**: allow from the internet (`0.0.0.0/0`) to Nginx. Add an IPv6 `::/0` rule only if IPv6 is actually enabled for the instance and public access is intended.
- **Inbound TCP 22 (SSH)**: no rule, because administration uses Session Manager (ADR-009).
- **Inbound TCP 8000/5000 (Gunicorn/Flask)**: no rule. Bind Gunicorn to `127.0.0.1` or a Unix domain socket so only local Nginx can reach the application server. A security group alone is not a substitute for a local bind.
- **Inbound TCP 443**: **not yet enabled**; add it if HTTPS is implemented as a stretch goal (ADR-011).
- **All other unsolicited inbound traffic**: deny by omission (security groups permit only explicitly allowed inbound rules).
- **Outbound**: initially allow all outbound destinations/protocols to support OS package updates, outbound HTTPS to Session Manager, and DynamoDB AWS API calls. Review opportunities to narrow egress after the baseline is working.

**Rationale:** The required public application must accept browser traffic, but its administrative path and internal app server do not need to be internet-facing. A dedicated group is easier to audit, explain, and change without affecting unrelated infrastructure. This follows the least-privilege principle for inbound network exposure.

**Alternatives considered:** Reuse the default security group, which may include unwanted rules such as access from other members of that group; open SSH port 22 to a narrowly scoped source IP; expose Gunicorn directly without Nginx; restrict every outbound destination from day one. All are viable in some circumstances, but none improves this small take-home's chosen threat model or setup effort enough to justify the tradeoff.

**Tradeoffs / qualifications:** HTTP on port 80 is **unencrypted** and should not carry secrets; the TLS decision is separately deferred. Wide-open outbound access is less restrictive than a hardened production egress policy but avoids unnecessary dependency troubleshooting during the initial deployment. These rules only apply to the instance's network interface; the instance also needs a public IPv4 address, correct internet route, and a listening Nginx process. Security groups are **stateful**: response traffic to allowed connections is automatically permitted. No security group exists yet; these are configuration targets.

**Reference:** [AWS VPC security groups](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html).

## ADR-011 — Deliver HTTP first and defer HTTPS to an SRS stretch goal

**Status:** Selected scope/priority decision; HTTPS not yet implemented.

**Decision:** Make a publicly reachable **HTTP** version of Jira Lite the baseline. Record **HTTPS/TLS as an optional stretch goal in `SRS.md`** to pursue after deployment, persistence, and `/health` work. If implemented, it needs a domain, which the baseline does not use (ADR-015); Nginx terminates TLS with a trusted certificate (potentially Let's Encrypt), incoming port 443 is enabled, port 80 redirects to HTTPS, and certificate renewal is automated. Do not claim these future features are deployed.

**Rationale:** The assignment lists HTTPS as a nice-to-have, while the required demonstration emphasizes a working public Linux EC2 application, persistent data, a database-aware health check, clear architectural explanations, and security and cost tradeoffs. Completing and verifying those first reduces delivery risk.

**Alternative considered:** Configure HTTPS immediately, potentially requiring DNS/domain ownership, certificate issuance and renewal, and additional troubleshooting; an AWS load balancer plus AWS Certificate Manager would increase architecture and potentially cost.

**Tradeoffs and security:** HTTP exposes content and requests to interception or modification in transit. The baseline is intended for **non-sensitive demo data only** and must not handle login credentials or other secrets over HTTP. HTTPS would be mandatory before serving real users in production. Revisit the HTTPS stretch goal after core functionality and deployment are working.

**Source:** Project `SRS.md`, “Optional enhancements” (HTTPS/TLS stretch goal); take-home assignment, optional features section.

## ADR-012 — Use GitHub Actions for CI/CD, deployed through AWS Systems Manager

**Status:** Selected design, now a stretch goal (ADR-013); pipeline not yet implemented or verified. The baseline's deployment approach is proposed in ADR-016.

**Decision:** If time remains after the baseline is verified and documented, use **GitHub Actions** to automate the Jira Lite test-and-deploy workflow. Running the tests in GitHub Actions comes first as its own stretch goal, because it needs no AWS credentials. The intended deployment process is:

1. A push to the `main` branch starts the GitHub Actions workflow.
2. The workflow installs necessary test dependencies and runs application tests; **only passing tests** can lead to deployment.
3. The workflow authenticates to AWS using **GitHub OIDC federation** and a dedicated, least-privilege IAM deployment role rather than storing long-lived AWS access keys in repository secrets.
4. The workflow requests deployment via **AWS Systems Manager Run Command** to the designated EC2 instance; this is distinct from **Session Manager**, which remains our interactive administration method. This avoids opening inbound SSH/port 22.
5. A repeatable deployment script on EC2 updates the deployed application version, installs/refreshes Python dependencies as necessary, restarts the **Gunicorn** system service (when configured), and checks the `/health` endpoint. The exact artifact delivery and failure/rollback behavior remain implementation details to design and test.

**Rationale:** GitHub Actions provides visible, repeatable test and deployment history and hands-on CI/CD experience directly relevant to the DevOps role. It integrates with our Git repository and existing AWS/SSM/IAM choices without increasing the EC2 inbound attack surface. Using OIDC reduces the risk and maintenance burden of static AWS credentials. Performing a manual/scripted deployment first limits troubleshooting complexity by separating app/host configuration issues from pipeline issues.

**Alternatives considered:** A **manual deployment script executed through Session Manager** would be simpler, but would not automatically test and deploy commits. AWS CodePipeline/CodeDeploy would provide AWS-native CI/CD but introduce additional services and configuration for a one-instance take-home. A GitHub Actions workflow using **SSH** would be familiar but conflicts with the chosen no-inbound-SSH design. Long-lived IAM access keys in GitHub Secrets are also unnecessary when OIDC can be configured.

**Tradeoffs / safeguards:** OIDC trust-policy subject restrictions, IAM rights for triggering Run Command on **only the intended instance** and required documents, and instance-side SSM permissions need careful configuration. Restrict deployment to a trusted branch and ensure untrusted pull-request code cannot obtain deployment credentials. The instance must be able to acquire the intended application revision securely; fetching it from a public Git repository is proposed in ADR-020. Health checks should fail the workflow when deployment is unsuccessful. This adds complexity, so **the working public app and required features take priority** if implementation encounters delays. Free Tier and any service-related costs must be checked during deployment.

**References:** [GitHub Actions OIDC with AWS](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws) · [AWS Systems Manager Run Command](https://docs.aws.amazon.com/systems-manager/latest/userguide/run-command.html).

## ADR-013 — Prioritize mandatory deliverables; keep monitoring lightweight and optional

**Status:** Selected project-priority decision, revised 2026-10-30; no stretch goal is implemented.

**Decision:** First deliver and verify the **three mandatory technical requirements** in the take-home: (1) a publicly accessible web application running on Linux EC2, (2) persistent database writes and reads, and (3) a `/health` endpoint checking both application and database connectivity. Complete the required live URL, repository/README, architecture diagram, and 2–5 minute walkthrough with cost/security rationale and a genuine troubleshooting example. Do **not** treat optional enhancements as prerequisites for a successful submission.

The developer has limited time before the deadline, so the baseline is only what the acceptance criteria require. Everything else is a stretch goal, started only after the baseline is verified and the README and diagram are done, in this order (SRS §4): **CI** with no AWS credentials, **one CloudWatch alarm** on EC2 status checks, **Nginx rate limiting**, **automated deployment** (ADR-012), and **HTTPS** (ADR-011). The order puts cheap, low-risk items first. Each stretch goal needs a discussion with the developer before it starts. A stretch goal that isn't finished and verified is left out and named in the video as something to change before serving real customers. For baseline diagnosis, use the required `/health` endpoint and server/application logs.

**Rationale:** The assignment explicitly says a simple application deployed well is better than a complex one that barely works. CI/CD, basic monitoring, HTTPS, Docker, and infrastructure as code are listed as optional; choosing a small number deliberately keeps development, verification, and the demo manageable. The DevOps role values troubleshooting and operations, but reliable execution and a defensible explanation matter more than maximizing service count.

**Alternatives considered:** Keeping automated deployment in the baseline would show the most DevOps skill, but it carries the most setup and failure risk for the time available. Also rejected: building extensive monitoring and alerting before getting the app working, adding a dashboard stack such as Grafana, or completing every optional enhancement. These increase setup, costs, and potential failure modes without satisfying additional mandatory assignment criteria. Doing no diagnostics whatsoever would also weaken the required troubleshooting explanation; preserve useful logs and verify `/health` even without monitoring automation.

**Tradeoffs:** The HTTP-first baseline does not encrypt public web traffic, so demo data must be non-sensitive; HTTPS is necessary before production use. Minimal monitoring may not detect outages automatically, but the app's health can still be checked manually and logs examined. Deployments stay manual unless the automated deployment stretch goal is finished.

**Source:** Take-home assignment, pp. 1–2, mandatory app functionality, optional enhancements, and submission/evaluation criteria; DevOps Engineer job description, monitoring and CI/CD responsibilities.

## ADR-014 — Use a dedicated AWS project on the Free plan in `us-east-2`

**Status:** Accepted and configured on 2026-11-01 (Phase 2). Deployment capabilities still require verification.

**Decision:** Use a dedicated **Jira Lite AWS project**, created through AWS's new project-based experience, on the **Free plan** in **`us-east-2` (Ohio)**. Authenticate through an MFA-protected AWS Builder ID and use the project's existing administrator role for console access. Configure a Zero Spend Budget for cost monitoring. Do not activate advanced AWS features or upgrade to Paid unless a required capability is unavailable.

**Rationale:** A dedicated project separates Jira Lite's infrastructure and costs from another existing AWS project. AWS's project-based experience provides administrator access without requiring a traditional root account or manually created IAM administrator.

Although the original proposal favored advanced sign-up and `us-west-2`, the new project was successfully created in `us-east-2`. AWS automatically assigns this Region to U.S. project accounts. The shorter distance to the reviewers offered by Oregon does not justify changing account configurations for this demonstration application.

The Free plan prevents out-of-pocket usage charges while active, which supports the assignment's cost-safety requirements. AWS credits are still consumed by eligible usage. The Zero Spend Budget provides additional monitoring without requiring a Paid plan.

**Verified configuration:**

| Component | Actual configuration |
|---|---|
| Account type | Dedicated AWS project: Jira Lite |
| Sign-up experience | New project-based AWS experience |
| Plan | Free |
| Region | `us-east-2` (Ohio) |
| Authentication | AWS Builder ID with MFA enabled |
| Console administration | Existing assumed administrator role |
| Budget | Zero Spend Budget created |
| Default VPC | Present (ID omitted) |
| VPC status | Available |
| EC2 | Read-only API request succeeded |
| DynamoDB | Read-only API request succeeded |
| Systems Manager | Read-only API request succeeded |

The three service requests returned empty resource lists, as expected before deployment. They establish API accessibility but do not yet prove resource-creation permissions or successful service integration.

**Alternatives considered:**

- **Advanced AWS sign-up:** Offers greater control over Regions, account governance, and security configuration. Rejected because the existing project supports the planned services and avoids unnecessary account complexity.
- **Reuse another existing project:** Would avoid creating another project but mix unrelated infrastructure and cost tracking. Rejected in favor of isolation.
- **Paid plan:** Provides additional services and features, but introduces potential out-of-pocket charges. Not currently necessary.
- **`us-west-2` (Oregon):** Geographically closer to the reviewers but unavailable as the project's assigned Region without activating advanced capabilities.

**Tradeoffs and remaining risks:**

AWS project accounts do not provide root-user sign-in, even after activating advanced features. Human console access uses AWS-managed project roles; separately created IAM roles and users are intended for programmatic access.

The new project experience also uses managed security defaults that may differ from our original least-privilege IAM design. Before deployment, verify that we can configure the intended EC2 instance role, restrict DynamoDB permissions, and use Systems Manager Session Manager.

The Free plan includes service restrictions and expires after six months or when credits are exhausted, whichever occurs first. A Zero Spend Budget provides alerts but does not stop resource usage or credit consumption.

Activating advanced features would require upgrading first, changing cost and account-management assumptions. Any such change requires a separate decision rather than an automatic upgrade.

**Limitations of the project-based Free plan (detail):**

| Area | Limitation | Effect on Jira Lite |
|---|---|---|
| Human authentication | You sign in with an MFA-protected AWS Builder ID and assume an AWS-managed project administrator role. Custom IAM users and roles cannot be used for normal console sign-in. | The plan's "create an IAM console user" step is not possible and not needed. |
| IAM permissions | AWS manages some project-level permissions automatically, so least-privilege configurations may behave differently than in a traditional account. | We cannot assume a policy we write is the only thing deciding access. Verify each one. |
| EC2 instance access | Custom IAM roles can still be created and attached to EC2 instances through an instance profile. | The `jira-lite-ec2` role (Session Manager plus DynamoDB) should still work. This is what we verify first at deployment. |
| Root user | No root sign-in, even after activating advanced features. | Account-level tasks use the project role or the console's account pages. |
| Service coverage | The Free plan is limited to select services, and it expires after six months or when credits run out, whichever comes first. | Any step the plan blocks is recorded in the troubleshooting log. |

**Decision (2026-11-01, owner):** Keep the existing Free project for now. During the Phase 4 deployment, verify that the custom EC2 instance permissions work as intended. Reconsider the account configuration only if a restriction prevents us from meeting an assignment requirement.

**Budget and credits (owner, 2026-11-01):** Both budgets exist: the Zero Spend Budget and the planned $15 cost budget. The owner has about $120 of AWS credits to work with. The $120 is a ceiling on credit usage, not a target, and the real figure gets recorded after the first day (AC-08).

**Velocity rule (owner, 2026-11-01):** Speed matters more than perfection at this stage. Read-only calls to EC2, DynamoDB, and Systems Manager have succeeded, but creating resources and attaching the instance role (the part that depends on how the project's federated sign-in handles IAM) is unproven. We try it as is. If one of the blockers below shows up and a fix isn't found within about 30 minutes, we stop and hold a pivot discussion instead of working around it.

**What counts as a blocker (reconsider the account only if one of these happens):**

1. The EC2 instance role or instance profile cannot be created or attached.
2. Session Manager cannot connect, even after waiting a few minutes and checking the role. Fallback order: Default Host Management Configuration (ADR-009), then the options below.
3. The instance role cannot reach DynamoDB, or the AC-06 deny-policy test cannot be performed.
4. The DynamoDB table, security group, or EC2 instance cannot be created.

**Options if a blocker occurs (each needs its own discussion and the owner's approval first):**

- **Activate advanced features:** requires upgrading to the Paid plan first, which adds possible out-of-pocket charges and cannot be undone.
- **Create a traditional AWS account:** gives root and IAM users and a choice of Region, but needs a new sign-up, payment card, phone verification, and a rebuilt budget, and costs setup time.

**Verification checklist at deployment (record results in this ADR and the troubleshooting log):**

Items 1–3 were reported done in the owner's audit of 2026-11-01 (the audit says the instance profile was also checked with the AWS CLI). Agent has no AWS access and has not independently verified them. No project-level restriction blocked any of them, so the pivot discussion is not triggered.

- [x] Create the `jira-lite-dynamodb` policy and the `jira-lite-ec2` role, and attach them to the instance profile.
- [x] Launch the instance, and confirm it appears as a managed node in Systems Manager.
- [x] Open a Session Manager session from the console.
- [ ] Confirm `/health` returns 200, which proves the role reaches DynamoDB.
- [ ] Confirm the human role's permissions can create each resource without workarounds.

**Consequences for the project plan:**

- Replace `us-west-2` with `us-east-2` in regional settings, IAM policy ARNs, deployment files, and documentation.
- Remove the steps for creating a root account and a separate IAM console administrator.
- Retain verification of the EC2 instance role and its database permissions.
- Replace the planned $15 initial budget with the configured Zero Spend Budget.
- Record actual resource costs and remaining credits after deployment.
- Keep all demonstration infrastructure within the Jira Lite project.

**Sources:**

- [Compare AWS sign-up options](https://docs.aws.amazon.com/accounts/latest/reference/sign-up-for-aws.html)
- [Create an AWS project](https://docs.aws.amazon.com/accounts/latest/reference/create-project.html)
- [AWS Regions for projects](https://docs.aws.amazon.com/accounts/latest/reference/project-regions.html)
- [Supported services for the new AWS experience](https://docs.aws.amazon.com/accounts/latest/reference/supported-services-sign-up-new.html)
- [AWS Free Tier plans](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html)
- [Track Free Tier usage](https://docs.aws.amazon.com/accounts/latest/reference/bcm-lite-free-tier-track.html)
- [Activate advanced AWS features](https://docs.aws.amazon.com/accounts/latest/reference/activate-advanced-features.html)

## ADR-015 — Use an Elastic IP and no domain for the public URL

**Status:** Proposed; to be decided by the owner before verification (Phase 6). An auto-assigned public IP is used until then.

**Decision:** Attach an **Elastic IP** to the instance and submit `http://<elastic-ip>/` as the live link. The baseline uses no domain or DNS.

**Rationale:** The live link has to keep working until the review is finished. An auto-assigned public IPv4 address is released when an instance stops and changes when it starts again, while an Elastic IP stays the same, so a stop/start cannot break the submitted link.

**Alternatives considered:** An **auto-assigned public IP** costs the same per hour, but any stop/start changes the link. A **domain with Route 53** gives a better URL and makes HTTPS practical, but adds cost and DNS to the baseline.

**Tradeoffs:** A bare IP address over HTTP looks less polished, and browsers mark it as not secure. AWS charges for all public IPv4 addresses ($0.005 per hour in its 2024 announcement); confirm the current rate and that credits cover it. An Elastic IP keeps billing while it stays allocated, even with no instance attached, so it must be released at teardown.

**Sources:** [Elastic IP addresses](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/elastic-ip-addresses-eip.html) · [Public IPv4 address charge](https://aws.amazon.com/blogs/aws/new-aws-public-ipv4-address-charge-public-ip-insights/) · [Identify and optimize public IPv4 usage](https://aws.amazon.com/blogs/networking-and-content-delivery/identify-and-optimize-public-ipv4-address-usage-on-aws/).

## ADR-016 — Run Gunicorn under systemd and deploy manually with a short script

**Status:** Accepted on 2026-11-01 (dedicated `jira-lite` service user, systemd unit, Gunicorn on `127.0.0.1:8000`, a `deploy.sh <commit>` script). Implemented in the repository (PR 2, merged) and exercised in an Ubuntu container with `systemctl` stubbed; real systemd behavior is not yet verified, and nothing is deployed.

**Decision:** Run Gunicorn as a **systemd** service with 2 workers on `127.0.0.1:8000`, starting on boot and restarting on failure. Gunicorn logs go to journald and Nginx logs to `/var/log/nginx/`. The developer creates AWS resources by hand in the console, following `docs/project-plan.md`, and deploys by running a short script in a Session Manager session. The script fetches a specific commit, updates Python packages in a virtual environment, restarts the service, and checks `/health`.

**Rationale:** systemd is already part of Ubuntu and covers restart after failure and reboot (NFR-01) and the start, stop, status, and log commands NFR-07 requires. Two workers should leave room in 1 GiB of RAM. A localhost TCP port can be tested directly with `curl` during troubleshooting. Creating the AWS resources personally keeps the developer able to explain everything deployed, which is the assignment's condition for using AI tools.

**Alternatives considered:** **Docker** would package the app consistently but adds a layer to run and explain on a 1 GiB host. **`nohup` or `screen`** would not survive a reboot. A **Unix socket** avoids a TCP port but adds file-permission setup and is harder to test by hand. **Terraform or CloudFormation** would make provisioning repeatable and is a listed nice-to-have, but takes time the required items need.

**Tradeoffs:** Console setup isn't reproducible from code; the written steps are the substitute. There is no automated rollback: to go back, rerun the script with the previous commit. The worker count and memory fit are untested.

## ADR-017 — Serve a plain frontend from Nginx with a small JSON API

**Status:** Accepted on 2026-11-01 as a plain static page from Nginx plus a small JSON API. The SRS length limits are still to be discussed before the task features (Phase 5). Not yet implemented.

**Decision:** The board is one static page of plain **HTML, CSS, and JavaScript**, with no framework or build step, served by Nginx. JavaScript calls a small Flask JSON API: `GET` and `POST /api/tasks`, and `PUT` and `DELETE /api/tasks/<id>`. Nginx proxies `/api/` and `/health` to Gunicorn. Flask enforces the SRS length limits (title 200 characters, description 2,000), and the page renders task text with `textContent`, never `innerHTML`.

**Rationale:** This is the smallest frontend that meets the SRS, with nothing to compile, and it gives Nginx and Gunicorn clearly separate jobs on the diagram (ADR-001). The app has no login, so anyone can write text that every visitor's browser renders; `textContent` prevents stored cross-site scripting, and length limits bound what each request can store.

**Alternatives considered:** **React or Vue** adds a toolchain and build step this one page doesn't need. **Server-rendered Jinja templates** need little JavaScript, but reload the page on every action and leave Nginx no static files to serve.

**Tradeoffs:** Hand-written DOM code would not scale to a larger UI. If development runs locally without Nginx (proposed in ADR-019), Flask also serves the page, which means two paths to the same files. Without the rate-limiting stretch goal, clients can send as many requests as the server accepts; the fixed DynamoDB capacity proposed in ADR-004 would limit the effect on cost.

## ADR-018 — Make `/health` perform a real DynamoDB read

**Status:** Design accepted on 2026-11-01 (owner; also covers the boto3 `Table` interface, lazy per-worker table handle, and environment-based configuration). Implemented in the repository (PR 1, merged) and tested against DynamoDB Local; not yet deployed or checked on EC2. The failure test (AC-06) is still to be discussed before Phase 6.

**Clarifications from the 2026-11-01 review:**

- `GetItem` proves the app can reach the table and has **read** permission. It does not prove write or delete permission. That is deliberate: the check must not change data.
- "No keys stored" means no **long-term** access keys. The instance role supplies temporary credentials through the instance metadata service, and AWS refreshes them automatically.
- The 2-second connect and read timeouts are separate limits, not a total request deadline. `total_max_attempts=1` is set explicitly because the default retry count depends on the retry mode and SDK version; an earlier draft's "five attempts" figure was imprecise and the design doesn't rely on it. The effective defaults for DynamoDB are unverified.
- The 503 is a status code. The generic JSON body, with the real error only in the log, is what keeps internal details out of the response.

**Decision:** `GET /health` runs a DynamoDB `GetItem` for a key that doesn't exist, with timeouts of about 2 seconds and no retries. It returns **200** when the call succeeds and **503** when it fails, with a short JSON body; error details go to the logs, not the response. To test failure (AC-06), temporarily attach an explicit deny on the table to the instance role, confirm the 503, and then remove it.

**Rationale:** This uses the same credentials, table, and permission path as the app, so a 200 means the app can actually read its database (NFR-03). Short timeouts matter because a database problem could otherwise hang the request until Gunicorn kills the worker, showing a generic Nginx error rather than a clear 503. An explicit deny is a real AWS failure, needs no code or configuration change, and is easy to undo.

**Alternatives considered:** **`DescribeTable`** is a management call that needs a permission the app otherwise doesn't use, and it doesn't prove data access. A **bad table name in configuration** tests a misconfiguration and requires changing the deployment. **Blocking outbound traffic** would also cut off Session Manager.

**Tradeoffs:** Every public `/health` request uses a small amount of read capacity. IAM changes take a short time to apply, so the failure test may need a brief wait.

## ADR-019 — Develop locally in WSL Ubuntu with DynamoDB Local

**Status:** Accepted on 2026-11-01 (owner). In use: WSL Ubuntu 24.04 and DynamoDB Local in Docker, through `scripts/run-local.sh`.

**Decision:** Develop in **Ubuntu 24.04 under WSL**, with the project at `~/jira-lite`. A local run uses Flask's development server and **DynamoDB Local** in Docker, with `AWS_ENDPOINT_URL_DYNAMODB` pointing Boto3 at the container. Tests use `pytest`, Flask's test client, and stubbed or mocked DynamoDB access, with no AWS calls.

**Rationale:** The local OS and default Python version match the EC2 host, Bash scripts behave as they will on EC2, and Gunicorn can be tried locally (it doesn't run on native Windows). It also moves the project out of OneDrive, where syncing a `.git` folder is a known cause of conflicts and corruption, and avoids Windows line endings. The developer already knows Ubuntu (ADR-006).

**Alternatives considered:** **Native Windows** needs no new distribution but loses Gunicorn and Bash parity. A **real DynamoDB table for development** is the most faithful, but would require AWS access keys on the laptop, which this design otherwise avoids. **`moto` in server mode** needs no Docker but adds a package that imitates the service.

**Tradeoffs:** WSL and Docker integration add a setup step. DynamoDB Local doesn't enforce IAM permissions, so those can only be verified on EC2.

## ADR-020 — Publish a public repository and keep employer documents local

**Status:** Accepted on 2026-11-01 (owner), with a staged rollout: **private first, public before the first deploy**. Not yet created.

**Decision:** Publish the code, SRS, ADRs, and README in a GitHub repository (planned as `Rileyhop1/jira-lite`). Create it **private**. The owner makes it **public before the first deploy to EC2**, because the instance clones it without a stored credential. The employer PDFs, the recruiter email, and the transcriptions stay in the gitignored `docs/reference/` folder.

**Branch protection:** GitHub offers it on private repositories only on paid plans, so it can't be enabled while the repo is private. Until the flip, the "PR only, squash merge, nobody pushes to `main`" rule is kept by discipline (AGENTS.md §5). It gets turned on right after the repo goes public, if the settings page allows it for the owner's plan.

**Why staged:** The owner prefers to keep work unpublished until there is something running. Private history becomes public when the repo is flipped, so before flipping we re-run the secrets and personal-details scan across the full history (`git log -p --all`), and the commit email must already be the noreply address.

**Rationale:** Reviewers can open a public link with no invitation, and EC2 can fetch code without a stored credential. Reviewers don't need their own documents back, and the email includes a recruiter's contact details.

**Alternatives considered:** A **private repository** would need each reviewer's GitHub username and a credential on EC2. **Committing the employer documents** would help agents on a fresh clone, but would republish them with no benefit to reviewers.

**Tradeoffs:** Everything pushed is public, including Git history, so a leaked secret must be rotated, not just deleted. Commit email addresses become public, so use GitHub's noreply address. Anyone can open pull requests, which makes the ADR-012 restriction on deployment credentials essential if that stretch goal is built.

## Open items

These remain open; the steps and discussion schedule are in `docs/project-plan.md`:

1. Discuss ADR-014 to ADR-020 and the drafted parts of ADR-004, each before the phase that needs it. Explain details in the older ADRs, such as Boto3, when the work reaches them.
2. Verify that the agreed sign-up path and plan allow this design (Region choice, IAM role, public IP). Confirm actual charges and the credit balance after launch.
3. Verify the network design: default VPC and public subnet, public IP, internet routing, and dedicated security group.
4. Verify Session Manager, the instance role, and the operator's IAM identity.
5. Test the Gunicorn, Nginx, and deployment configuration on the instance.
6. Finalize stretch-goal details only if they are started: workflow triggers, OIDC trust and permissions, alarm settings, rate limits, and domain and certificate strategy.
7. Final architecture diagram and README summary once the deployment is real.

## Decision log

| Date | Decision | Status |
| --- | --- | --- |
| 2026-10-30 | Nginx as reverse proxy and static-file server | Selected |
| 2026-10-30 | Gunicorn as independent Flask application server | Selected |
| 2026-10-30 | Flask for backend application | Selected |
| Before 2026-10-30 | DynamoDB as database (from SRS discussion) | Selected; rationale recorded 2026-10-30; comparison with alternatives not yet discussed |
| 2026-10-30 | `t3.micro` EC2 (2 vCPUs, 1 GiB RAM) with Standard CPU credits | Selected; not yet deployed |
| 2026-10-30 | Ubuntu Server 24.04 LTS over Amazon Linux 2023, primarily for familiarity and reduced setup/troubleshooting time | Selected; not yet deployed |
| 2026-10-30 | 16 GiB EBS `gp3` root volume over `gp2` (and a smaller 8 GiB volume) | Selected; not yet provisioned |
| 2026-10-30 | AWS default VPC rather than custom VPC for the single EC2 host | Selected; security group and public IP details pending |
| 2026-10-30 | AWS Systems Manager Session Manager for EC2 administration instead of SSH; IAM instance role and operator permissions | Selected; exact IAM policies and setup pending |
| 2026-10-30 | Dedicated security group: inbound HTTP/80, no SSH/22 or Gunicorn inbound, outbound initially allowed | Selected design; deployment pending |
| 2026-10-30 | Defer HTTPS to an SRS stretch goal; HTTP-first baseline | Selected priority; optional enhancement pending |
| 2026-10-30 | GitHub Actions for CI/CD with intended AWS OIDC + Systems Manager Run Command; manual/scripted deployment first | Selected design; stretch goal; not yet implemented |
| 2026-10-30 | Prioritize required EC2 app, database, `/health`, and submission deliverables; everything else is a stretch goal | Selected project priority; revised 2026-10-30 |
| 2026-11-01 | Dedicated AWS project on the Free plan, Builder ID sign-in, `us-east-2`; keep it unless a deployment blocker appears (replaces the 2026-10-30 advanced sign-up / `us-west-2` proposal) | Accepted and configured; deployment capabilities pending |
| 2026-10-30 | Elastic IP and no domain for the public URL | Proposed; not yet discussed |
| 2026-10-30 | systemd for Gunicorn; manual deployment script; developer provisions AWS by hand | Proposed; not yet discussed |
| 2026-10-30 | Plain static frontend from Nginx with a small JSON API | Proposed; not yet discussed |
| 2026-10-30 | `/health` performs a real DynamoDB read with short timeouts | Proposed; not yet discussed |
| 2026-10-30 | Local development in WSL Ubuntu with DynamoDB Local | Proposed; not yet discussed |
| 2026-10-30 | Public GitHub repository; employer documents kept local | Proposed; not yet discussed |

## Assignment alignment

The take-home requires a public web page served from Linux EC2, a database storing and retrieving data, and a health endpoint that checks the application and database. It also asks for a clear architecture diagram and an explanation of major choices, alternatives, and tradeoffs. Optional improvements include HTTPS, CI/CD, containerization, infrastructure as code, and monitoring; these should be adopted deliberately rather than treated as requirements.

_Source: the user-provided take-home assignment PDF, pp. 1–2._
