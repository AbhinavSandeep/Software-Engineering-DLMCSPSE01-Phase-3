#!/bin/sh
# Applies database migrations and loads the curated data set before the web
# server starts. Both steps are idempotent, so restarts are safe.
set -e

flask db upgrade
flask seed --if-empty

if [ -n "$ADMIN_EMAIL" ] && [ -n "$ADMIN_PASSWORD" ]; then
  # The password is read from the ADMIN_PASSWORD variable; an existing account is kept.
  flask create-admin "$ADMIN_EMAIL" || true
fi

exec "$@"
