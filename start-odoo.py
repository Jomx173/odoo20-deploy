#!/usr/bin/python3
import os
import re
import sys
from urllib.parse import unquote, urlsplit


def database_settings():
    uri = os.environ.get('DATABASE_URL', '')
    settings = {}
    if uri:
        try:
            url = urlsplit(uri)
            if url.scheme not in {'postgres', 'postgresql'} or not url.hostname:
                raise ValueError
            settings = {
                'DB_HOST': url.hostname,
                'DB_PORT': str(url.port or 5432),
                'DB_USER': unquote(url.username or ''),
                'DB_PASSWORD': unquote(url.password or ''),
                'DB_NAME': unquote(url.path.removeprefix('/')),
            }
        except ValueError:
            raise SystemExit('DATABASE_URL debe ser una URI válida de PostgreSQL') from None

    for key in ('DB_HOST', 'DB_PORT', 'DB_USER', 'DB_PASSWORD', 'DB_NAME'):
        settings[key] = os.environ.get(key) or settings.get(key)
        if not settings[key] and key != 'DB_NAME':
            raise SystemExit(f'Configura {key} o DATABASE_URL')

    settings['DB_NAME'] = settings['DB_NAME'] or 'defaultdb'
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', settings['DB_NAME']):
        raise SystemExit('DB_NAME contiene caracteres no admitidos')
    return settings


def main():
    settings = database_settings()
    env = os.environ.copy()
    env.pop('DATABASE_URL', None)
    env.pop('DB_PASSWORD', None)
    env['PGPASSWORD'] = settings['DB_PASSWORD']
    dbname = settings['DB_NAME']
    args = [
        'odoo', '--addons-path=/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons',
        f"--db_host={settings['DB_HOST']}", f"--db_port={settings['DB_PORT']}",
        f"--db_user={settings['DB_USER']}", '--db_sslmode=require',
        '-d', dbname, f'--db-filter=^{dbname}$', '--no-database-list',
        '--proxy-mode', '--http-interface=0.0.0.0',
        f"--http-port={env.get('PORT') or 8069}", '--workers=0', *sys.argv[1:],
    ]
    os.execvpe('odoo', args, env)


if __name__ == '__main__':
    main()
