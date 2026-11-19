FROM odoo:20.0

USER root
COPY ./addons /mnt/extra-addons
RUN chown -R odoo:odoo /mnt/extra-addons

USER odoo

# Arranque para Render (plan Free, 512 MB) usando variables de entorno.
# PORT lo define Render; el resto se configuran como variables del servicio.
CMD ["sh", "-c", "odoo --addons-path=/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons --db_host=$DB_HOST --db_port=$DB_PORT --db_user=$DB_USER --db_password=$DB_PASSWORD --db_sslmode=require -d $DB_NAME --db-filter=^${DB_NAME}$ --no-database-list --http-port=${PORT:-8069} --workers=0 --limit-memory-soft=400000000 --limit-memory-hard=480000000"]