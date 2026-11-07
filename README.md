# Inka-Sec

Aplicación web de capacitación en ciberseguridad para empresas del Perú.

## Ejecutar el flujo de administrador en local

El frontend React está en `frontend/`, la API FastAPI en `mi-api-fastapi/` y la configuración recomendada para desarrollo usa PostgreSQL. La API crea sus tablas al arrancar. Necesitas Docker, Node.js y Python 3.11 o superior. Las pruebas automatizadas usan SQLite en una base separada.

1. En la raíz del repositorio, copia `.env.example` a `.env`. Sustituye `INKASEC_DB_PASSWORD` por una contraseña aleatoria alfanumérica. En `mi-api-fastapi/`, copia también `.env.example` a `.env` y coloca **la misma contraseña** en `DATABASE_URL`, en lugar de `replace-with-a-database-password`. Conserva el host `localhost` y el puerto `5433` cuando ejecutes la API en tu PC. No subas estos archivos `.env` al repositorio.

2. Desde la raíz, inicia PostgreSQL con `docker compose up -d db`. Los datos quedan en el volumen `inkasec_pg`, independiente del antiguo archivo SQLite `inkasec.db`.

3. En `mi-api-fastapi/`, crea un entorno virtual e instala las dependencias:

   ```bash
   python -m venv .venv
   # Activa el entorno: source .venv/bin/activate en bash.
   # En PowerShell: .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

4. En `mi-api-fastapi/.env`, sustituye también la clave JWT, el correo y la contraseña del administrador y el secreto TOTP. Puedes generar los dos secretos con Python:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   python -c "import base64, secrets; print(base64.b32encode(secrets.token_bytes(20)).decode().rstrip('='))"
   ```

   Guarda el secreto TOTP en tu aplicación de autenticación para obtener los códigos de seis dígitos.

5. Desde `mi-api-fastapi/`, crea el primer administrador en PostgreSQL y arranca la API:

   ```bash
   python -m app.bootstrap_admin
   python -m uvicorn app.main:app --reload --port 8000
   ```

6. En otra terminal, desde `frontend/`, instala y arranca React:

   ```bash
   npm ci
   npm run dev
   ```

   En Windows PowerShell, usa `npm.cmd ci` y `npm.cmd run dev` si PowerShell bloquea `npm.ps1`.

7. Abre `http://localhost:5173/`. Inicia sesión con el correo y contraseña configurados; luego escribe el código de tu aplicación de autenticación. Para cambiar el puerto de la API, configura `VITE_API_URL` en `frontend/.env`.

Si ejecutas también la API en Docker, usa `docker compose up -d --build db backend` desde la raíz, ejecuta `docker compose exec backend python -m app.bootstrap_admin` para crear el administrador y configura `VITE_API_URL=http://localhost:8001/api/v1` en `frontend/.env` antes de iniciar React. Docker Compose reemplaza la URL local de `mi-api-fastapi/.env` por la dirección interna `db:5432`.

**Cifrado en reposo:** Docker Compose guarda PostgreSQL en un volumen local, pero ese volumen no garantiza por sí mismo AES-256. Para cumplir el requisito del documento en producción, el servidor o proveedor de base de datos debe proporcionar almacenamiento cifrado AES-256 y se debe verificar esa configuración en el despliegue. El código de la aplicación no puede certificar el cifrado del disco.

El administrador dispone de URLs que se pueden abrir y recargar directamente: `/admin`, `/admin/usuarios`, `/admin/areas`, `/admin/auditoria` y `/admin/reportes`. Cada sección consulta su propio recurso de la API (`/api/v1/admin/dashboard`, `/users`, `/areas`, `/audit` y `/reports/summary`). En «Áreas y roles» se crean áreas por separado; los usuarios se crean en «Usuarios». La auditoría permite buscar y recorrer páginas de 20 eventos. El avance del reporte es el promedio de los módulos que ya tienen un registro de progreso, por lo que no equivale al cumplimiento de todas las asignaciones.

La ruta `http://localhost:5173/?preview=admin` muestra únicamente datos de ejemplo para revisar el diseño.

## Pipeline de GitHub Actions

Las pruebas del backend y Bandit se ejecutan en los pull requests hacia `main` y en cada push a `main`. Los despliegues en Render son opcionales: para activar el entorno de desarrollo, configura la variable del repositorio `RENDER_DEV_ENABLED=true`, el secreto `RENDER_DEV_HOOK` y la variable `RENDER_DEV_URL`. Para permitir el despliegue a producción después del chequeo de desarrollo, configura además `RENDER_PROD_ENABLED=true` y el secreto `RENDER_PROD_HOOK`. Sin estas variables de activación, los trabajos de despliegue se omiten y las pruebas siguen funcionando. Antes de activar producción, configura una aprobación obligatoria para el entorno en GitHub.
