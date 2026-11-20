param(
  [Parameter(Mandatory = $true)]
  [string]$AivenUri
)

# Restaura el dump de Odoo en la base de datos PostgreSQL de Aiven.
# Uso: .\restore.ps1 "postgres://usuario:CLAVE@host:puerto/basedatos?sslmode=require"
# Nota: no ejecutar sin antes crear/configurar el servicio y la base en Aiven.
#       El parámetro $AivenUri contiene credenciales: no lo imprimas ni lo registres.

$ErrorActionPreference = "Stop"

$dump = Join-Path $PSScriptRoot "odoo.dump"
if (-not (Test-Path $dump)) {
  throw "No se encontró odoo.dump en $PSScriptRoot"
}

Write-Host "Restaurando odoo.dump hacia la base indicada en la URI de Aiven..."
Write-Host "(La URI se pasa de forma oculta al contenedor; no se mostrará aquí.)"

# Aiven requiere SSL; si la URI no lo incluye, se recomienda agregar ?sslmode=require
# (si ya tiene parámetros, usar &sslmode=require).
docker run --rm -v "${PWD}:/dump" postgres:18 pg_restore --no-owner --no-privileges -d "$AivenUri" /dump/odoo.dump

if ($LASTEXITCODE -ne 0) {
  throw "pg_restore terminó con código $LASTEXITCODE"
}

Write-Host "Restauración completada."