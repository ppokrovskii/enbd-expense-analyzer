#!/bin/bash
set -e

echo "🔄 Waiting for postgres..."
while ! pg_isready -h postgres -U enbd_user -d enbd_db > /dev/null 2>&1; do
  sleep 1
done
echo "✅ Postgres is ready!"

echo "🔄 Running database migrations..."
alembic upgrade head
echo "✅ Migrations complete!"

echo "🚀 Starting application..."
exec "$@"

