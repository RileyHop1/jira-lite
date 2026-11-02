#!/usr/bin/env bash
# Deploy a commit of Jira Lite on the EC2 instance. Run as root:
#
#   sudo /opt/jira-lite/app/deploy/deploy.sh <commit>
#
# Safe to run repeatedly. Rolling back is the same command with the previous
# commit, which this script prints at the start. See ADR-016.
set -euo pipefail

APP_DIR=/opt/jira-lite/app
VENV_DIR=/opt/jira-lite/venv
SERVICE_USER=jira-lite
HEALTH_URL=http://127.0.0.1/health
HEALTH_TRIES=20

# Everything runs inside main(), called on the last line. `git checkout` can
# replace this file while bash is still reading it, and bash has already read
# the whole function by then, so the run finishes the version it started.
main() {
  # Stop early on a missing commit or a non-root run, before changing anything.
  if [[ $# -ne 1 || ! $1 =~ ^[0-9a-f]{7,40}$ ]]; then
    echo "Usage: $0 <commit>   (a hex commit hash of 7-40 characters)" >&2
    exit 2
  fi
  if [[ $EUID -ne 0 ]]; then
    echo "Run as root (use sudo)." >&2
    exit 2
  fi
  local commit=$1

  # Packages are installed here, so make files readable by Nginx and the
  # service user.
  umask 022

  # Print the current commit first: it is the rollback target if this fails.
  local previous
  previous=$(git -C "$APP_DIR" rev-parse HEAD)
  echo "Currently deployed: $previous"

  # Detached checkout of exactly the requested commit, so what runs is what
  # was reviewed and merged.
  git -C "$APP_DIR" fetch --quiet origin
  git -C "$APP_DIR" checkout --quiet --detach "$commit"

  # Dedicated no-login account for the app. Created once.
  if ! id "$SERVICE_USER" >/dev/null 2>&1; then
    useradd --system --no-create-home --shell /usr/sbin/nologin "$SERVICE_USER"
  fi

  # Virtual environment owned by root, so the app cannot change its own
  # packages. Created once, then kept in sync with the pinned requirements.
  if [[ ! -x $VENV_DIR/bin/python ]]; then
    python3 -m venv "$VENV_DIR"
  fi
  "$VENV_DIR/bin/pip" install --quiet --requirement "$APP_DIR/requirements.txt"

  # Install the Nginx site and drop Ubuntu's default site, which would
  # otherwise also claim port 80. `nginx -t` runs before the reload so a bad
  # config stops the deploy instead of taking Nginx down.
  cp "$APP_DIR/deploy/nginx-jira-lite.conf" /etc/nginx/sites-available/jira-lite
  ln -sfn /etc/nginx/sites-available/jira-lite /etc/nginx/sites-enabled/jira-lite
  rm -f /etc/nginx/sites-enabled/default
  nginx -t

  # Install the unit, enable it for boot, and restart so the new code runs.
  cp "$APP_DIR/deploy/jira-lite.service" /etc/systemd/system/jira-lite.service
  systemctl daemon-reload
  systemctl enable --quiet jira-lite
  systemctl restart jira-lite
  systemctl enable --quiet nginx
  systemctl reload-or-restart nginx

  # Success means /health answers through Nginx, which also proves Gunicorn
  # and DynamoDB. Retry briefly because Gunicorn needs a moment to start.
  local try
  for ((try = 1; try <= HEALTH_TRIES; try++)); do
    if curl --silent --fail --max-time 3 "$HEALTH_URL" >/dev/null; then
      echo "Deployed $commit. Previous (rollback target): $previous"
      return 0
    fi
    sleep 1
  done

  echo "Deploy of $commit failed: $HEALTH_URL did not return 200." >&2
  journalctl --unit jira-lite --lines 30 --no-pager >&2 || true
  echo "Roll back with: sudo $0 $previous" >&2
  return 1
}

main "$@"
exit $?
