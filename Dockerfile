# syntax=docker/dockerfile:1
FROM odoo:20.0@sha256:c7352c766b245b3c0e5c7b7a57e7660dde3265872be9566870d44bdb974f44cf

USER root
COPY --chown=odoo:odoo ./addons /mnt/extra-addons
COPY --chmod=755 ./start-odoo.py /usr/local/bin/start-odoo

# Odoo redirects database-backed bundles to their own URL in this image.
RUN python3 - <<'PY'
from pathlib import Path

path = Path('/usr/lib/python3/dist-packages/odoo/addons/base/models/ir_attachment.py')
source = path.read_text(encoding='utf-8')
redirect = "            return Stream(type='url', url=self.url, **kw)"
old = '        elif self.url:\n' + redirect
new = "        elif self.url and not (self.type == 'binary' and self.db_datas):\n" + redirect
if source.count(old) != 1:
    raise SystemExit('Review the Odoo attachment stream fix for this image')
updated = source.replace(old, new, 1)
compile(updated, str(path), 'exec')
path.write_text(updated, encoding='utf-8')

# Old browsers may have cached the permanent redirect at the original URL.
path = path.with_name('ir_qweb.py')
source = path.read_text(encoding='utf-8')
old = "        ext = path.rsplit('.', maxsplit=1)[-1] if path else 'js'\n"
new = old + "        if path and path.startswith('/web/assets/'):\n            path += '?render_assets=1'\n"
if source.count(old) != 1:
    raise SystemExit('Review the Odoo asset URL cache fix for this image')
updated = source.replace(old, new, 1)
compile(updated, str(path), 'exec')
path.write_text(updated, encoding='utf-8')
PY

USER odoo

ENTRYPOINT ["/usr/local/bin/start-odoo"]
CMD []
