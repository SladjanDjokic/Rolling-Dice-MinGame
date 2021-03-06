#!/usr/bin/env bash
echo "Command: $@"
set -e

/opt/bin/docker-setup.sh

if [[ -z "${VIRTUAL_ENV}" ]]; then
    source "$(pipenv --venv)/bin/activate"
fi

echo "Command: $@"
exec "$@"
