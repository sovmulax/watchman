#!/usr/bin/env bash
set -euo pipefail

# Secrets Docker (prod, §11.4) : un fichier monté sous /run/secrets écrase la
# variable d'env correspondante. Absent en dev (SQL_PASSWORD/DJANGO_SECRET_KEY
# viennent alors de .env comme d'habitude) — ce bloc est un no-op dans ce cas.
if [ -f /run/secrets/postgres_password ]; then
    export SQL_PASSWORD
    SQL_PASSWORD="$(cat /run/secrets/postgres_password)"
fi
if [ -f /run/secrets/django_secret_key ]; then
    export DJANGO_SECRET_KEY
    DJANGO_SECRET_KEY="$(cat /run/secrets/django_secret_key)"
fi

# Attendre la base de données (boucle pg_isready). Ignore l'attente si le
# moteur n'est pas Postgres (ex. SQLite local, pas de service à attendre).
python - <<'PYEOF'
import os
import sys
import time

engine = os.environ.get("SQL_ENGINE", "django.db.backends.sqlite3")
if "postgresql" not in engine:
    sys.exit(0)

import psycopg

for _ in range(30):
    try:
        with psycopg.connect(
            dbname=os.environ.get("SQL_DATABASE", "veille"),
            user=os.environ.get("SQL_USER", "veille"),
            password=os.environ.get("SQL_PASSWORD", ""),
            host=os.environ.get("SQL_HOST", "db"),
            port=os.environ.get("SQL_PORT", "5432"),
            connect_timeout=3,
        ):
            sys.exit(0)
    except Exception:
        time.sleep(1)
sys.exit("Database not reachable after 30s")
PYEOF

# Migrate/collectstatic uniquement sur le conteneur web (RUN_MIGRATIONS=1),
# pas sur worker/beat qui partagent la même image.
if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput
fi

exec "$@"
