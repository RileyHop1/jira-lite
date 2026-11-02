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
