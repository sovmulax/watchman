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

# Migrate/collectstatic/seed_themes uniquement sur le conteneur web
# (RUN_MIGRATIONS=1), pas sur worker/beat qui partagent la même image.
# seed_themes est idempotent sur les métadonnées de thème mais réaffecte
# aussi theme.sources (M2M) depuis fixtures/seed_sources.json à chaque
# passage : sans lui, une base migrée sans jamais avoir tourné cette commande
# garde des thèmes sans sources rattachées, et le scraping en mode permanent
# ne ramène jamais rien quel que soit l'état du code.
# NB : seed_sources n'est PAS rejoué ici : il force is_active=False sur
# TOUTES les sources (chaque source doit être activée manuellement après
# vérification via l'action de test, cf. sa docstring) — le relancer à
# chaque redémarrage désactiverait silencieusement les sources déjà validées.
if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput
    python manage.py seed_themes
fi

exec "$@"
