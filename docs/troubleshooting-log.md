# Troubleshooting log

Real failures, in order, each with the symptom, exact error, diagnosis, root cause, and fix.

## 2026-11-01: `scripts/run-local.sh` would not run (Permission denied)

**Symptom:** The local test of PR 1's success path never started the app.

**Exact error:**

```text
timeout: failed to run command ‘scripts/run-local.sh’: Permission denied
```

**Diagnosis:** `git ls-files -s scripts deploy` showed `100644` for `scripts/run-local.sh` but `100755` for `deploy/deploy.sh`, so Git had recorded the script without its executable bit. `ls -l` on disk agreed.

**Root cause:** The script was made executable with `chmod +x`, but a later edit (a comment trim) rewrote the file and dropped the bit. The change was committed and merged in PR 1 without anyone running the script.

**Fix:** `chmod +x scripts/run-local.sh` and commit the mode change (`100644` to `100755`). Lesson: after editing a script, check its mode before committing, and run every script at least once before a PR claims it works. The PR 1 description had said the scripts were unverified, which is how this was found.

## 2026-11-01: Docker unavailable from WSL

**Symptom:** The DynamoDB Local checks for PR 1 could not run.

**Exact error:**

```text
The command 'docker' could not be found in this WSL 2 distro.
We recommend to activate the WSL integration in Docker Desktop settings.
```

From Windows, `docker version` also failed:

```text
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
```

**Diagnosis:** The WSL integration toggle for Ubuntu-24.04 was already on, but the Windows-side error showed the Docker engine itself was not running.

**Root cause:** Docker Desktop was not running.

**Fix:** Start Docker Desktop and wait for the engine to come up. `docker version` then reported a server, and `docker run` worked from Ubuntu.

## 2026-11-04: The live site returned 404 for the board page after the board PR merged

**Symptom:** About 25 minutes after the board page (PR 5) was squash-merged (00:11 UTC on 2026-11-05, 4:11 p.m. Pacific on 11-04), opening the public address in a browser showed a 404.

**Exact evidence** (plain requests to the public address at 00:36 UTC):

```text
/             404  text/html
/index.html   404  text/html
/board.js     404  text/html
/style.css    404  text/html
/health       200  application/json    {"database":"ok","status":"ok"}
/api/tasks    404  text/html; charset=utf-8
```

The 404 for `/` came from Nginx (`Server: nginx/1.28.3`, `Content-Length: 162`). The 404 for `/api/tasks` came from Flask, with its standard page: `<title>404 Not Found</title> ... The requested URL was not found on the server.`

**Diagnosis:** `/health` returned 200, so Nginx, Gunicorn, Flask and the DynamoDB path were all working. The `/api/tasks` 404 was in Flask's format, so Nginx did forward it and the running app had no such route. The static files returned Nginx's own 404, which is what it does when its `root` folder (`frontend/`) has nothing in it. Both matched the commit from the first deploy (`9cf0ab6`), which had `/health` only and no `frontend/` folder. GitHub confirmed PR 5 had merged and `frontend/` was on `main`. The deployed commit on the instance was not read directly; the cause was inferred from the response pattern and confirmed by the fix.

**Root cause:** Merging a PR does not change what is running. Deployment is manual by design (ADR-016): `deploy.sh` deploys only the commit it is given, and it had not been run since the first deploy, so PRs 3, 4 and 5 were on `main` but not on the server.

**Fix:** On the instance, fetch and deploy the new `main`: `sudo git -C /opt/jira-lite/app fetch -q origin`, then `sudo /opt/jira-lite/app/deploy/deploy.sh <commit of origin/main>`. A second set of requests at 00:37 UTC returned 200 for `/`, `/index.html`, `/board.js`, `/style.css`, `/health` and `/api/tasks`. Lesson: after merging a feature, deploy it and check the public address before calling it done. This gap between merging and deploying is the case for automated deployment, listed in the README under what I would change before real customers.