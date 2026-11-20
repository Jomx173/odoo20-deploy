# Notas para informe/PDF - Despliegue Odoo 20 (Aiven + Render)

Fecha de preparación local: 2026-11-19  
Directorio de trabajo: `C:\Odoo20\deploy`

## 1. Inspección del entorno local

### Archivos revisados
- `C:\Odoo20\odoo\odoo.conf`
  - `db_user = odoo` (enmascarado en reporte: `odoo`)
  - `db_password = ****`
  - `db_name = odoo_dev`
  - `db_host = 127.0.0.1`, `db_port = 5432`
  - `addons_path = c:\odoo20\odoo\addons,c:\odoo20\odoo\odoo\addons,c:\odoo20\custom_addons,c:\odoo20\examen_final`
  - `admin_passwd = ****`
- `C:\Odoo20\docker-compose.yml`: **no encontrado** en el equipo (no se modificó nada; se trabajó solo en `C:\Odoo20\deploy`).
- `C:\Odoo20\custom_addons\ventas_unicah/__manifest__.py`: módulo propio `Ventas UNICAH` (depende de `sale_management`).

### Estado Docker observado
Comandos:
```powershell
docker --version
docker compose version
docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
```
Resultado:
- Docker `29.9.2`, Docker Compose `v5.6.1`
- Contenedor `odoo20-db-1` (`postgres:16`) **Up**
- Contenedor `odoo20-odoo-1` (`odoo:20.0`) **Exited (0)**

### Versiones y base de datos
```powershell
docker exec odoo20-db-1 psql -U odoo -d postgres -c "SELECT version();"
docker exec odoo20-db-1 psql -U odoo -d postgres -c "SELECT datname, pg_size_pretty(pg_database_size(datname)) AS size FROM pg_database ORDER BY pg_database_size(datname) DESC;"
docker exec odoo20-db-1 psql -U odoo -d odoo_dev -c "SELECT count(*) AS installed_modules FROM ir_module_module WHERE state='installed';"
docker exec odoo20-db-1 psql -U odoo -d DbJomx -c "SELECT count(*) AS installed_modules FROM ir_module_module WHERE state='installed';"
```
Resultado:
- PostgreSQL: **16.15** (Debian 16.15-1.pgdg13+2, x86_64)
- Bases: `DbJomx` (77 MB, 87 módulos instalados), `odoo_dev` (54 MB, 59 módulos instalados), `postgres`, `template0`, `template1`
- **Base seleccionada para despliegue:** `odoo_dev` (coincide con `db_name` en `odoo.conf` local).

Versión de Odoo (imagen):
```powershell
docker run --rm --entrypoint odoo odoo:20.0 --version
```
Resultado: `Odoo Server 20.0-20261015`

## 2. Generación y copia del dump

Se encendió/confirmó la BD (ya estaba activa) y se generó el dump **dentro** del contenedor, copiándolo sin redirección de PowerShell (para evitar corrupción de binario):
```powershell
docker exec odoo20-db-1 pg_dump -U odoo -Fc -f /tmp/odoo.dump odoo_dev
docker exec odoo20-db-1 ls -lh /tmp/odoo.dump
docker cp odoo20-db-1:/tmp/odoo.dump C:\Odoo20\deploy\odoo.dump
(Get-Item C:\Odoo20\deploy\odoo.dump).Length; "{0:N2} MB" -f ((Get-Item C:\Odoo20\deploy\odoo.dump).Length/1MB)
```
Resultado:
- `/tmp/odoo.dump`: 4.6M
- `C:\Odoo20\deploy\odoo.dump`: **4,754,199 bytes (4.53 MB)**, no vacío.

> Nota: se intentó primero `docker compose exec ...` desde `C:\Odoo20`, pero no hay `docker-compose.yml` en ese directorio; se usó `docker exec`/`docker cp` contra `odoo20-db-1`.

## 3. Preparación de archivos de despliegue (`C:\Odoo20\deploy`)

Copiado de addons propios (sin `__pycache__`):
```powershell
New-Item -ItemType Directory -Force -Path C:\Odoo20\deploy\addons | Out-Null
robocopy C:\Odoo20\custom_addons C:\Odoo20\deploy\addons /E /XD __pycache__ .git /NFL /NDL /NJH /NP
```
Archivos creados: `Dockerfile`, `.dockerignore`, `render.yaml`, `restore.ps1`, `README.md`, `NOTAS_PDF.md`.

### Verificación de flags de Odoo 20
```powershell
docker run --rm --entrypoint bash odoo:20.0 -c "odoo server --help 2>&1 | grep -nE 'db_host|db_port|db_user|db_password|db_sslmode|db-filter|db_filter|database|no-database-list|list.db|http-port|http_port|workers|limit-memory'"
```
Flags confirmados en Odoo 20.0-20261015: `--db-filter`, `--http-port`/`-p`, `--log-db`, `--database`/`-d`, `--db_user`/`-r`, `--db_password`/`-w`, `--db_host`, `--db_port`, `--db_sslmode`, `--no-database-list`, `--workers`, `--limit-memory-soft`, `--limit-memory-hard` (entre otros).  
**Ajuste aplicado:** se invoca `odoo` (comando por defecto `server`) con `--addons-path` explícito para incluir `/mnt/extra-addons`; flags usados tal como se solicitaron, con `-d $DB_NAME` y `--db-filter=^${DB_NAME}$`.

## 4. Prueba de build del Dockerfile
```powershell
cd C:\Odoo20\deploy
docker build -t odoo-deploy .
```
Resultado: **compilación exitosa** (imagen `odoo-deploy:latest`).
- Base: `odoo:20.0`
- Copia de `./addons` a `/mnt/extra-addons` y `chown` a `odoo:odoo`
- Imagen final exportada correctamente.

No se conectó a Aiven durante la prueba.

## 5. Repositorio Git (local, sin push)
```powershell
git init
git add .dockerignore Dockerfile README.md render.yaml restore.ps1 addons NOTAS_PDF.md
git commit -m "Preparacion despliegue Odoo 20 (Aiven + Render)"
```
Resultado:
- Repo inicializado en `C:\Odoo20\deploy\.git`
- `.gitignore` ignora `odoo.dump` y artefactos temporales.
- Commit inicial creado: `be0fa35` — 9 archivos, 375 inserciones. **Sin push.**

## 6. Errores/advertencias y resoluciones

| Situación | Detalle | Resolución |
|---|---|---|
| No existe `docker-compose.yml` en `C:\Odoo20` | `docker compose exec/cp` falló con “no configuration file provided: not found” desde la raíz | Se usaron contenedores por nombre: `docker exec odoo20-db-1 ...` y `docker cp odoo20-db-1:/tmp/odoo.dump ...` (BD ya estaba activa) |
| `odoo --help`/`--version` con entrypoint por defecto intentó conectar a host `db` | Mensaje “Database connection failure: could not translate host name \`db\`…” al ejecutar `docker run --rm odoo:20.0 odoo ...` | Se consultó versión/ayuda con `--entrypoint odoo` / `--entrypoint bash` (`odoo --version`, `odoo server --help`) y se confirmaron los flags |
| `psql -U odoo -c ...` sin `-d` | FATAL: database "odoo" does not exist | Se ejecutaron consultas contra `-d postgres`, `-d odoo_dev` y `-d DbJomx` según correspondía |
| WSL1 en entorno | Docker/`docker build` mostró aviso de WSL1 (lentitud potencial) | Build completó correctamente; no requirió acción adicional |
| `pg_dump: error: ... connection ... failed` no observado | Dump generado correctamente (formato `-Fc`) | Verificado tamaño 4.53 MB (> 0 KB) |

## 7. Pendientes (a realizar por mí en la nube)

1. **Aiven (PostgreSQL, plan Free):** crear servicio PostgreSQL y base de datos; obtener URI/host, puerto, usuario, contraseña y nombre de BD (SSL requerido). Proporcionar la **URI** para ejecutar `restore.ps1` (sin compartirla en canales inseguros).
2. **Restaurar:** `.\restore.ps1 "<URI_AIVEN_con_sslmode=require>"` en `C:\Odoo20\deploy` (no ejecutado).
3. **Render (Web Service, Docker, plan Free, 512 MB):** crear servicio desde el repo/`render.yaml`, configurar `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` (valores de Aiven). Render define `PORT`.
4. **Verificación:** abrir URL en producción, validar módulo `ventas_unicah`, crear usuario administrador de Odoo para revisión y capturar evidencias (Aiven/Render/config BD/errores). Documentar credenciales de Odoo (no de Aiven/Render) en la entrega.
## 8. Restauracion en Aiven y cierre del despliegue (2026-11-19)

- Cliente usado para el restore: `postgres:18` (actualizado desde `postgres:17` en `restore.ps1`).
- Antes del restore, `defaultdb` tenia 337 tablas en `public` y 0 modulos instalados (restore anterior incompleto).
- Se detuvo un `pg_restore` antiguo colgado y se relanzo con:
  `docker run --rm -v C:\Odoo20\deploy:/dump postgres:18 pg_restore --clean --if-exists --no-owner --no-privileges -d <URI> /dump/odoo.dump`
- Salida redirigida a `restore.log` (ignorado por git). Credenciales nunca escritas en el repo.
- Remote git: https://github.com/Jomx173/odoo20-deploy.git (rama `master`).
- Build verificado: `docker build -t odoo-deploy C:\Odoo20\deploy` -> OK (imagen `odoo-deploy:latest`).
