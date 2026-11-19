# Despliegue Odoo 20 (Render + Aiven PostgreSQL, plan Free)

Contenido preparado en esta carpeta (sin Docker en la nube más allá de la imagen que usa Render para construir el servicio web; **no** incluye `docker-compose`).

## Archivos
- `addons/ventas_unicah/`: módulo propio a desplegar.
- `Dockerfile`: imagen basada en `odoo:20.0`, copia `addons/` a `/mnt/extra-addons` y arranca Odoo con parámetros por variables de entorno (compatible con Render).
- `.dockerignore`: excluye `odoo.dump` y archivos pesados del contexto de build.
- `render.yaml`: definición del servicio web en Render (runtime Docker, plan free) con variables `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` (`sync: false`).
- `restore.ps1`: script para restaurar `odoo.dump` en la base de Aiven usando `pg_restore` (no ejecutado aquí).
- `odoo.dump`: volcado de la base `odoo_dev` (formato custom `-Fc`). **Ignorado por git**.
- `NOTAS_PDF.md`: comandos ejecutados, errores y resoluciones (para informe).

## Orden de pasos
1. **Aiven (PostgreSQL, plan Free):** crear el servicio PostgreSQL y la base de datos destino. Anotar host, puerto, nombre de BD, usuario y contraseña/URI (con SSL). No compartir credenciales del servicio.
2. **Restaurar datos:** ejecutar `.\restore.ps1 "<URI_AIVEN_con_sslmode=require>"` desde esta carpeta (requiere Docker local y la URI de Aiven). Verificar que la restauración finalice sin errores críticos.
3. **Repositorio Git:** esta carpeta ya tiene git inicializado y el primer commit (sin push). Crear un repositorio remoto y hacer `git push` (asegurarse de no subir `odoo.dump`).
4. **Render (Web Service, plan Free, Docker, 512 MB):** crear el servicio desde el repo (o usando `render.yaml`) y configurar las variables de entorno `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` con los valores de Aiven. Render inyecta `PORT` automáticamente.
5. **Verificar:** abrir la URL pública del servicio en Render, comprobar que Odoo carga y que el módulo `ventas_unicah` está disponible/instalado. Crear/verificar un usuario administrador de Odoo para revisión (entregar URL y credenciales de Odoo, no las de Aiven/Render).
6. **Informe/PDF:** usar `NOTAS_PDF.md` y las capturas del proceso en la nube (creación de BD en Aiven, configuración de Render, URL en producción, configuración de BD, problemas y soluciones).

## Notas
- La base de origen local es `odoo_dev` (PostgreSQL 16, usuario `odoo`). Se usa `--db-filter` para fijar la base y `--no-database-list` para deshabilitar el selector/gestor de BD en producción.
- `--workers=0` y límites de memoria reducidos están ajustados al plan Free de Render (512 MB).
- Aiven requiere SSL (`--db_sslmode=require`). Verificar que la URI/conexión use `sslmode=require`.