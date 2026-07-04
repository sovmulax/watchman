#!/usr/bin/env bash
set -euo pipefail

# Attendre la base de données (boucle pg_isready).
python - <<'PYEOF'
import os
import sys
import time

import psycopg

url = os.environ["DATABASE_URL"]
for _ in range(30):
    try:
        with psycopg.connect(url, connect_timeout=3):
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
