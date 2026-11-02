# Jira Lite — Project Plan

The steps from here to the November 6, 2026 submission. **None of these steps have been run yet**, so expect to correct some of them. AWS may label things differently than written here; if a screen doesn't match, stop and check before continuing.

We work through this one step at a time. Each phase starts only on your go-ahead, after the discussion listed for it. Anything in those discussions is a proposal until you've accepted it, and a step that depends on one can change.

When something really breaks, write it in `docs/troubleshooting-log.md` before fixing it: the symptom, the exact error, how you diagnosed it, the root cause, and the fix. The video needs one real example.

## Schedule

These are latest-by dates, so move work earlier around busy days. The rough total is 11–14 hours, including reviews and discussions. A slow review delays everything behind it, and there's no buffer left, so stretch goals are unlikely.

| Latest by | Done |
| --- | --- |
| Sun, Nov 1 | Phases 1–3: local setup, AWS account and safeguards, repository and standards |
| Mon, Nov 2 | PRs 1 and 2 reviewed and merged |
| Tue, Nov 3 | Stack live: `/health` responds publicly |
| Wed, Nov 4 | PRs 3–5 merged and deployed |
| Thu, Nov 5 | All checks pass; README and diagram merged |
| Fri, Nov 6 | Video recorded and submission sent by 11:59 p.m. Pacific |

## Discussion schedule

| Before | We discuss |
| --- | --- |
| Phase 1: Local setup | WSL and DynamoDB Local (ADR-019) |
| Phase 2: AWS account | Advanced sign-up, Free plan, and Region (ADR-014) |
| Phase 3: Repository | Commit standards, the merge method, who pushes branches and opens PRs, test and lint tools, repo visibility, `docs/reference/`, `.gitignore`, `.gitattributes` (ADR-020) |
| Phase 4: First working stack | boto3; `/health` design (ADR-018); systemd, the deploy script, the service user, and the server folders (ADR-016); table design, capacity, and the comparison with other databases (ADR-004); the AWS pieces: IAM policy, role, and instance profile, security group, default VPC, `t3.micro` and CPU credits, `gp3` storage, and Session Manager (ADR-005 to ADR-010) |
| Phase 5: Task features | Board page, API, and length limits (ADR-017) |
| Phase 6: Verify | Elastic IP (ADR-015) and the AC-06 failure test (ADR-018) |
| Phase 7: README and diagram | Diagram tool: Mermaid or draw.io |
| Phase 8: Stretch goals | Each one before it starts |
| Phase 9: Video | Each main choice and its alternative, in your own words (ADR-001, ADR-002, ADR-004 to ADR-006) |

## Pull requests

Everything on `main` is a feature you've reviewed and merged. Each PR delivers one feature, and work that depends on another PR waits for your review. When you review, ask about anything you couldn't explain on video.

| Step | Feature | Waits for | Tests |
| --- | --- | --- | --- |
| PR 1 | App skeleton and `/health` with a real DynamoDB check | Repository exists | Written first: success when the database responds, failure when it doesn't |
| PR 2 | Deployment files: Nginx config, systemd unit, deploy steps | PR 1 | None; checked by running them on EC2 |
| Deploy | You create the AWS resources and deploy; `/health` responds publicly | PR 2 | None; `/health` checked at the public link |
| PR 3 | Create and list tasks | Stack is live | Written first: rejects a blank title, a title over 200 characters, a description over 2,000 characters, and an invalid status. Also one success test each for create and list |
| PR 4 | Edit and delete tasks | PR 3 | One success test each, plus one rejected-input test for edit |
| PR 5 | Board page | PR 4 | None; checked in the browser by AC-01 to AC-04 |
| PR 6 | README and diagram | App deployed and verified | None |

## Phase 1: Local setup

1. In PowerShell, run `wsl --install -d Ubuntu-24.04` and create your Linux user.
2. In Ubuntu, run `sudo apt update && sudo apt install -y git python3-venv`.
3. Copy the project out of OneDrive:
   `cp -r "/mnt/c/Users/<you>/OneDrive/Desktop/Programming/Web/Jira-Lite" ~/jira-lite`
4. Copy the two original PDFs into `~/jira-lite/docs/reference/`.
5. In Docker Desktop, turn on WSL integration for Ubuntu-24.04. Check it with `docker run --rm hello-world`.
6. Run `code ~/jira-lite` to open the project through WSL, and use Claude Code from there. Its saved notes from the old folder won't carry over, but the project documents hold what's needed.

## Phase 2: AWS account and safeguards

Do this before anything else in AWS. Have a payment card and your phone ready.

*What actually happened (ADR-014):* the account is a dedicated project on AWS's project-based Free plan. You sign in with an MFA-protected AWS Builder ID and an AWS-managed administrator role. There is no root sign-in and no separate IAM console user, and the Region `us-east-2` was assigned by AWS. The original steps 1–4 (advanced sign-up, root MFA, IAM user) therefore didn't apply. We keep this account unless Phase 4 hits a blocker listed in ADR-014.

1. **Sign up:** done through the project-based experience on the Free plan (ADR-014). A Free plan can move to Paid later, but a Paid plan can't move back. If it later blocks a step below, record it and reassess before continuing.
2. **MFA:** enabled on the Builder ID.
3. **Daily sign-in:** the project's administrator role. No access keys exist.
5. **Create the billing alert** in AWS Budgets, using the monthly cost budget template:
   - **Amount:** $15. My rough estimate of normal usage is about $13 a month at on-demand rates (instance, 16 GiB of storage, and one public IP), drawn from credits. An alert should mean something unexpected is running. Replace this with real numbers after the first day.
   - **Alerts:** 80% of actual spend and 100% of forecasted spend, sent to your email. Verify the address if AWS asks.
   - **Cost option:** unblended costs, which show usage before credits. The "net" options apply credits, so they could stay at zero until the credits run out.
6. **Use `us-east-2`** (Ohio) and confirm a default VPC exists there (it does).
7. **Check the services this design needs:** open EC2, DynamoDB, and Systems Manager in the console and note any message saying your plan doesn't include them. AWS says the Free plan is limited to select services. Its Free Tier page lists EC2 and DynamoDB, but doesn't mention Systems Manager.

AWS lists setting up a cost budget and launching an EC2 instance as activities that earn more credits, so this plan should earn some along the way.

## Phase 3: Repository and standards

You create the repository; agents don't. After the commit standards discussion, I add the agreed standards to `AGENTS.md` and you review them, so they're part of the first commit. Then:

1. Set your Git identity, using the noreply address from your GitHub email settings so your personal email stays out of public history:
   `git config --global user.name "<your name>"`
   `git config --global user.email "<id>+Rileyhop1@users.noreply.github.com"`
2. In `~/jira-lite`, run `git init -b main`, then confirm `git status` doesn't list `docs/reference/` or `to-do-list.md`.
3. Make the first commit of the planning documents, which you've already reviewed.
4. When you're ready, run `sudo apt install -y gh && gh auth login`, then create the GitHub repository and push. PRs need it from here on.
5. If we agreed on branch protection, turn it on for `main` in the repository settings.
6. Delete the OneDrive copy, so there's only one copy.

## Phase 4: First working stack

This proves EC2, Nginx, Gunicorn, Flask, and DynamoDB work end to end before any task features exist.

First, PRs 1 and 2 get written and you review them. PR 1 also adds the exact test commands to `AGENTS.md`. Then, using your IAM user in the agreed Region:

*Status 2026-11-01:* steps 1–6 below were done early by the owner and reported working in the ADR-014 audit (not independently verified by an agent). The instance is named `jira-lite-server`, not `jira-lite`, and should stay **stopped** until the first deploy to save credits. Steps 7 and 8 are still open. PR 1 (app and `/health`) is written; PR 2 (deploy files) follows. The Region is `us-east-2`.

1. **DynamoDB table:** `jira-lite-tasks`, partition key `id` (String). Customize settings: Standard table class, provisioned capacity, auto scaling off, 5 read and 5 write units.
2. **IAM policy:** `jira-lite-dynamodb`, with your account ID filled in:

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "dynamodb:GetItem",
           "dynamodb:PutItem",
           "dynamodb:UpdateItem",
           "dynamodb:DeleteItem",
           "dynamodb:Scan"
         ],
         "Resource": "arn:aws:dynamodb:us-east-2:<account-id>:table/jira-lite-tasks"
       }
     ]
   }
   ```

3. **IAM role:** `jira-lite-ec2`, trusted by EC2, with `AmazonSSMManagedInstanceCore` and `jira-lite-dynamodb` attached.
4. **Security group:** `jira-lite-web` in the default VPC, with one inbound rule: HTTP (port 80) from `0.0.0.0/0`. Leave outbound as it is.
5. **EC2 instance:** `jira-lite`, Ubuntu Server 24.04 LTS (x86-64), `t3.micro`, no key pair, a default public subnet with a public IP, security group `jira-lite-web`, and 16 GiB of `gp3` storage. Under Advanced details, set the IAM instance profile to `jira-lite-ec2` and the credit specification to **Standard** (T3 defaults to Unlimited).
6. **Connect:** in the EC2 console, select the instance, then Connect, then Session Manager. It can take a few minutes to become available. Once connected, confirm the agent with `sudo snap services amazon-ssm-agent`.
7. **Install and deploy:** the repository must be public first (ADR-020), because the instance clones it without a stored credential. In the Session Manager shell:

   ```bash
   sudo apt update && sudo apt install -y nginx python3-venv git
   sudo git clone https://github.com/RileyHop1/jira-lite.git /opt/jira-lite/app
   COMMIT=$(sudo git -C /opt/jira-lite/app rev-parse HEAD)
   sudo /opt/jira-lite/app/deploy/deploy.sh "$COMMIT"
   ```

   Every later deploy is the last line with the commit you want. The script prints the previous commit, and rolling back is the same command with that commit. If it fails, it prints the last lines of the service log.
8. **Check from your browser:** `http://<public-ip>/health`.

Done when `/health` responds publicly and its check really reaches DynamoDB. A reboot keeps this IP address, but a stop/start changes it until an Elastic IP is added.

## Phase 5: Task features

PRs 3, 4, and 5 get written and reviewed in that order. Deploy each one after you merge it, and check it at the public link.

Done when the tests pass and the board works at the public link.

## Phase 6: Verify

If we agree on an Elastic IP, allocate one and associate it with the instance first, since AC-05 stops and starts the instance.

Mark a check as passed only after you've seen it pass. Save screenshots or terminal output for the video.

| Check | How |
| --- | --- |
| AC-01 | Open the link on a phone with Wi-Fi off. |
| AC-02 to AC-04 | Create, edit, and delete a task, reloading the page after each. |
| AC-05 | Restart the Gunicorn service, reboot the instance, then stop and start it from the console. Tasks should remain and the link shouldn't change. |
| AC-06 | Confirm `/health` returns 200. Add the deny policy below to the `jira-lite-ec2` role, wait a minute, and confirm a 503. Remove it and confirm 200 again. |
| AC-07 | Confirm port 80 is the only inbound rule. On the instance, `sudo ss -tlnp` should show Gunicorn on `127.0.0.1` only. Search the repository and its history for keys and passwords. |
| AC-08 | In Billing, note the real charges, credit balance, and days remaining, and confirm the budget exists. Do this again just before submitting. |
| AC-09 to AC-11 | Covered by Phases 7 and 9; the genuine failure comes from the troubleshooting log. |

Deny policy for AC-06:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Deny",
      "Action": "dynamodb:*",
      "Resource": "arn:aws:dynamodb:us-east-2:<account-id>:table/jira-lite-tasks"
    }
  ]
}
```

## Phase 7: README and diagram

This is PR 6.

- **README:** what the app is, how to run it locally, how it was deployed, how to start, stop, restart, check status, and find logs (NFR-07), the main tradeoffs, and known limitations (HTTP only, no login, demo data only).
- **Diagram:** make it in Mermaid or draw.io, export it to `docs/architecture.png`, and add it to the README. Show the browser, public IP, security group, Nginx, Gunicorn, Flask, and DynamoDB, with the response path back. Put DynamoDB outside the VPC, and show Session Manager as the admin path.
- **Accuracy:** describe only what's actually deployed. Label anything unfinished as planned.

## Phase 8: Stretch goals (optional)

Only if you're ahead of schedule, in this order, and each after a discussion. Stop in time for the video to show the final system. Leave out anything unfinished, and be ready to say why you chose whatever you keep, since the assignment asks.

1. **CI:** a GitHub Actions workflow runs the tests on pushes and pull requests, with no AWS credentials. Say in the README that deployment is still manual.
2. **Basic monitoring:** a CloudWatch alarm on EC2 status checks emails you. Confirm the email arrives.
3. **Rate limiting:** add Nginx `limit_req` for `/api/`. Confirm normal use is unaffected and a burst gets rejected.
4. **Automated deployment:** build ADR-012 only if a large block of time remains.
5. **HTTPS:** needs a domain, so it's last (ADR-011).

## Phase 9: Video and submission

Record 2–5 minutes, clear enough for someone who isn't an AWS expert:

1. **The app working at its live link**, including `/health`.
2. **The diagram and main choices.** Name an alternative you actually considered for each: instance type and Linux distribution (ADR-005, ADR-006), database (ADR-004), and how traffic reaches the app (ADR-001, ADR-002).
3. **Security and free tier:** only port 80 open, no SSH, an IAM role with no stored keys or database password, your AWS plan, the budget alert, and your real numbers.
4. **One real failure** from the troubleshooting log, and how you found the cause.
5. **What you'd change before real customers:** HTTPS, login and permissions, a load balancer with multiple instances, automated deployment, monitoring, DynamoDB backups, infrastructure as code, and any stretch goal you didn't finish.

Reply to the recruiter's email with the live link, the repository link (README and diagram included), the video link, and the one-line confirmation, only if it is accurate. Open every link in a private browser window before sending.

Keep the app running until the reviewers say the review is finished.

## After the review

Once the reviewers confirm the review is finished: terminate the instance, **release the Elastic IP** if you added one (it keeps billing until you do), and delete the table, role, policy, and security group. Check Billing over the next few days to confirm nothing is still running.
