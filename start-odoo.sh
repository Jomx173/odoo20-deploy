#!/bin/sh
set -eu

: "${DB_HOST:?Configura DB_HOST}" "${DB_PORT:?Configura DB_PORT}"
: "${DB_USER:?Configura DB_USER}" "${DB_PASSWORD:?Configura DB_PASSWORD}"
DB_NAME=${DB_NAME:-defaultdb}
case "$DB_NAME" in
    *[!a-zA-Z0-9_-]*) echo 'DB_NAME contiene caracteres no admitidos' >&2; exit 1 ;;
esac

export PGPASSWORD="$DB_PASSWORD"
unset DB_PASSWORD

exec odoo --addons-path=/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons \
    --db_host="$DB_HOST" --db_port="$DB_PORT" --db_user="$DB_USER" \
    --db_sslmode=require -d "$DB_NAME" --db-filter="^${DB_NAME}$" \
    --no-database-list --proxy-mode --http-interface=0.0.0.0 \
    --http-port="${PORT:-8069}" --workers=0 "$@"
