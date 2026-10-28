#!/usr/bin/env sh
set -e

echo "[entrypoint] Waiting for database connection..."
python << 'EOF'
import os
import sys
import time
import psycopg

db_name = os.environ.get("DB_NAME", "smart_survey_db")
db_user = os.environ.get("DB_USER", "postgres")
db_password = os.environ.get("DB_PASSWORD", "postgres")
db_host = os.environ.get("DB_HOST", "db")
db_port = os.environ.get("DB_PORT", "5432")

max_retries = 30
conninfo = f"dbname={db_name} user={db_user} password={db_password} host={db_host} port={db_port}"

for attempt in range(1, max_retries + 1):
    try:
        with psycopg.connect(conninfo, connect_timeout=3) as conn:
            print(f"[entrypoint] Database is ready (attempt {attempt})")
            sys.exit(0)
    except Exception as exc:
        print(f"[entrypoint] Database unavailable ({exc}), retrying {attempt}/{max_retries}...")
        time.sleep(1)

print("[entrypoint] Database connection failed after maximum retries.")
sys.exit(1)
EOF

if [ "$RUN_MIGRATIONS" != "false" ]; then
    echo "[entrypoint] Running database migrations..."
    python manage.py migrate --noinput
fi

if [ "$COLLECT_STATIC" != "false" ]; then
    echo "[entrypoint] Collecting static files..."
    python manage.py collectstatic --noinput || true
fi

echo "[entrypoint] Executing CMD: $@"
exec "$@"
