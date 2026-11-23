# Inka-Sec

Bienvenidos a Inka-Sec, una aplicación web pensada para fortalecer el conocimiento básico de ciberseguridad en empresas del Perú.

InkaSec combina **módulos cortos en lenguaje sencillo**, **retos prácticos basados en situaciones reales del trabajo** y un **control de acceso por roles (RBAC)**, para que cada empresa capacite a su personal y mida su avance con indicadores concretos: porcentaje de módulos aprobados, desempeño en retos y temas con más errores.

> 📄 **¿Primera vez con el proyecto?** Sigue la guía paso a paso en [`docs/guia-instalacion.pdf`](docs/guia-instalacion.pdf): clonar, crear el entorno virtual, configurar, revisar y levantar los servicios.

---

## Contenido

- [Problema que resuelve](#problema-que-resuelve)
- [Roles y funcionalidades](#roles-y-funcionalidades)
- [Arquitectura](#arquitectura)
- [Tecnologías](#tecnologías)
- [Estructura del repositorio](#estructura-del-repositorio)
- [Inicio rápido](#inicio-rápido)
- [Cuentas de demostración](#cuentas-de-demostración)
- [Variables de entorno](#variables-de-entorno)
- [Pruebas y análisis de seguridad](#pruebas-y-análisis-de-seguridad)
- [Medidas de seguridad implementadas](#medidas-de-seguridad-implementadas)
- [CI/CD](#cicd)
- [API](#api)
- [Estado del proyecto](#estado-del-proyecto)
- [Cómo contribuir](#cómo-contribuir)

---

## Problema que resuelve

Muchos incidentes en empresas peruanas (fraudes por correo, robo de cuentas, pérdida de información) empiezan con una decisión cotidiana insegura de un trabajador. Las capacitaciones largas y teóricas no cambian ese hábito. InkaSec busca que el aprendizaje sea **breve, práctico y medible**, y que se refuerce en el tiempo (refuerzos a los 7, 30 y 90 días) siguiendo el modelo de cambio de conducta **COM-B** (Capacidad, Oportunidad, Motivación).

## Roles y funcionalidades

| Rol | Qué puede hacer hoy |
|---|---|
| **Trabajador** | Iniciar sesión, ver sus módulos y su avance, completar módulos (diagnóstico COM-B → microlección → preguntas → acción real), practicar retos de tres formatos tantas veces como quiera, ver sus temas débiles y obtener, renovar y descargar sus certificados por tema. |
| **Gestor de contenido** (código 2FA al correo) | Crea y edita módulos y retos en lenguaje sencillo, organízalos por tema (catálogo y búsqueda), asígnalos a la empresa, un área o una persona con fecha límite, y revisa quién terminó sus módulos, quién practicó sus retos y cuántos certificados hay por tema. Los aciertos de los retos solo se ven agregados (3 o más personas): el reto entrena, no sanciona. |
| **Administrador** (código 2FA al correo) | Crear, editar rol/estado, desactivar y eliminar usuarios; crear áreas; consultar la auditoría con búsqueda y paginación; ver indicadores por área y exportar el reporte en CSV. |

Cada empresa solo ve sus propios datos: todas las consultas se filtran por empresa (multiempresa).

## Arquitectura

Arquitectura cliente-servidor desacoplada en tres capas. El control de acceso se aplica **en la API en cada petición**; el frontend solo decide qué pantallas mostrar.

```mermaid
flowchart LR
    subgraph Cliente["Client Side · React + Vite"]
        H[Home Trabajador]
        C[Panel de Contenido]
        A[Panel Administrador]
    end
    subgraph API["Server Side · FastAPI"]
        G["Capa de entrada (middlewares)<br/>CORS · cabeceras · rate limit · CSRF"]
        AU["Autenticación<br/>Argon2 · JWT en cookie HttpOnly · código 2FA por correo"]
        R["RBAC por ruta<br/>/worker · /manager · /admin"]
        S[Servicios y repositorios]
    end
    DB[(PostgreSQL)]
    H & C & A -->|HTTPS + cookies| G --> AU --> R --> S --> DB
```

## Tecnologías

| Capa | Tecnología |
|---|---|
| Frontend | React 19, Vite 8, oxlint |
| Backend | Python 3.13, FastAPI, SQLAlchemy 2, Pydantic Settings |
| Seguridad | Argon2 (contraseñas), PyJWT (sesión), código 2FA de 6 dígitos enviado por correo (Brevo o SMTP) |
| Base de datos | PostgreSQL 18 (Docker / Render) · SQLite para desarrollo local rápido |
| Infraestructura | Docker Compose, GitHub Actions, Render |
| Calidad | pytest, Bandit (SAST), npm audit (SCA) |

## Estructura del repositorio

```
Inka-Sec/
├── docker-compose.yml          # db (PostgreSQL) + backend + frontend; perfil "test": backend-tests y frontend-tests
├── .env.example                # plantilla del .env de la raíz (credenciales de la BD local)
├── docs/guia-instalacion.pdf   # guía paso a paso para el equipo
├── .github/workflows/ci.yml    # pruebas, SAST, build, auditoría y despliegue
├── frontend/                   # React + Vite
│   └── src/
│       ├── App.jsx             # vistas por rol (trabajador, gestor, administrador)
│       ├── InkaSecLayout.jsx   # barra lateral, navegación y menú de usuario
│       ├── AuthContext.jsx     # estado de sesión
│       ├── challenges.jsx      # retos (rápido, por pasos, señales) y su editor
│       ├── certificates.jsx    # certificados, renovación y verificación pública
│       ├── ui.jsx              # piezas de interfaz compartidas
│       ├── api.js              # cliente HTTP (cookies + cabecera CSRF)
│       ├── __tests__/          # 67 pruebas de pantallas (Vitest + Testing Library)
│       └── test/               # preparación de las pruebas y datos de ejemplo
└── mi-api-fastapi/             # API FastAPI
    ├── .env.example            # plantilla de configuración de la API
    ├── requirements.txt        # dependencias de producción
    ├── requirements-dev.txt    # + pytest, pytest-cov, httpx, bandit
    ├── Dockerfile.test         # imagen solo para correr las pruebas con Docker
    ├── app/
    │   ├── main.py             # creación de la app y middlewares
    │   ├── core/               # configuración, seguridad, middlewares, dependencias RBAC
    │   ├── api/routes/         # auth, worker, manager, admin, health, certificates
    │   ├── services/           # lógica de negocio (auth, progreso, dashboards, auditoría)
    │   ├── repositories/       # consultas a la base de datos
    │   ├── models/             # tablas SQLAlchemy
    │   ├── schemas/            # validación de entradas (Pydantic)
    │   ├── data/               # 7 módulos COM-B de ejemplo
    │   ├── seed.py             # datos demo (solo desarrollo)
    │   ├── dev_seed_challenges.py  # crea los retos demo del trabajador (solo desarrollo)
    │   ├── bootstrap_admin.py  # crea el primer administrador real
    │   └── worker.py           # depura auditoría con más de AUDIT_RETENTION_DAYS
    └── tests/                  # 132 pruebas: funcionales y simulaciones de ataque
```

## Inicio rápido

Requisitos: **Git**, **Python 3.13**, **Node.js 22** y, para la opción con contenedores, **Docker Desktop**.

```bash
git clone https://github.com/XaXAlvaromO/Inka-Sec.git
cd Inka-Sec
cp .env.example .env
cp mi-api-fastapi/.env.example mi-api-fastapi/.env
# Edita mi-api-fastapi/.env: JWT_SECRET_KEY (mínimo 32 caracteres) y DEMO_PASSWORD.
python -c "import secrets; print(secrets.token_urlsafe(48))"   # genera el JWT_SECRET_KEY
```

**Opción A — Docker (todo junto):**

```bash
docker compose up --build
```

**Opción B — Sin Docker (SQLite):**

```bash
# Terminal 1: API
cd mi-api-fastapi
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8001

# Terminal 2: frontend
cd frontend
npm ci
npm run dev
```

| Servicio | URL |
|---|---|
| Aplicación web | http://localhost:5173 |
| API (salud) | http://localhost:8001/api/v1/health |
| Documentación interactiva de la API | http://localhost:8001/docs (deshabilitada en producción) |
| PostgreSQL (solo Docker) | `localhost:5433` |

## Cuentas de demostración

Con `SEED_DEMO_DATA=true` la API crea al arrancar la empresa demo, 7 módulos y estas cuentas. La contraseña de las tres es el valor de `DEMO_PASSWORD`.

| Rol | Correo | 2FA |
|---|---|---|
| Trabajador | `trabajador@inkasec.pe` | No |
| Gestor | `gestor@inkasec.pe` | Código por correo |
| Administrador | `admin@inkasec.pe` | Código por correo |

Gestores y administradores reciben un código de 6 dígitos al iniciar sesión. Con `EMAIL_BACKEND=console` (valor por defecto en local) el código aparece en la terminal de la API, así puedes probar sin enviar correos. Para recibirlo en un Gmail real, usa `EMAIL_BACKEND=smtp` (ver abajo).

Los 4 retos de ejemplo (dos rápidos, uno por pasos y uno de señales) se crean con el seed demo (`SEED_DEMO_DATA=true`); con esa opción activa, los que falten se agregan al reiniciar la API. Si ya tienes la base de datos, `python -m app.dev_seed_challenges` los agrega sin duplicar (o con `docker compose exec backend ...`).

## Retos y certificados

**Retos (entrenan, no califican).** Hay tres formatos:

- **Reto rápido:** un caso y una decisión.
- **Escenario por pasos:** de 2 a 5 decisiones seguidas; después de cada una se muestra qué pasaría.
- **Encuentra las señales:** un correo o mensaje dividido en partes; la persona marca las sospechosas y luego ve cuáles encontró, cuáles se le pasaron y cuáles marcó de más.

Se pueden repetir sin límite y fallar siempre muestra la explicación. El primer intento queda guardado solo para estadísticas agregadas por tema; la práctica posterior solo la ve el propio trabajador. El gestor ve quién practicó y cuántas veces, nunca si cada persona acertó, y los porcentajes de aciertos aparecen solo con 3 o más personas.

**Certificados por tema (RF-07).** Un trabajador obtiene el certificado de un tema cuando completa todos los módulos publicados de ese tema que tiene asignados, con al menos **80 %** en las preguntas de práctica de cada uno (se guarda su mejor intento). Completar un módulo exige pasar por el paso de acción real, así que también queda registrada.

- Vale **12 meses**, como la capacitación anual que exigen estándares como PCI DSS 12.6.
- Desde **30 días antes** de vencer, el trabajador puede renovarlo con un repaso corto de las preguntas del tema (80 % para aprobar, reintentos ilimitados). El certificado anterior queda como "reemplazado".
- Se descarga en PDF, en blanco y negro, sin puntaje: solo dice que la persona aprobó.
- Tiene un código único (por ejemplo `INKA-7KQ2-M9XP-4HTR`) que cualquiera puede comprobar en `/verificar/<código>`, sin iniciar sesión.

## Variables de entorno

Los archivos `.env` **nunca se suben a git**. Se crean a partir de las plantillas `.env.example`.

| Variable | Descripción | Valor local |
|---|---|---|
| `JWT_SECRET_KEY` | Clave que firma las sesiones. **Mínimo 32 caracteres** o la API no arranca. | generada |
| `APP_ENV` | `development` o `production`. En producción se exige HTTPS y se ocultan `/docs` y los scripts de desarrollo. | `development` |
| `DATABASE_URL` | Conexión a la BD. En Docker se reemplaza automáticamente por PostgreSQL. | `sqlite:///./inkasec.db` |
| `FRONTEND_ORIGIN` | Único origen autorizado por CORS. No puede ser `*`. | `http://localhost:5173` |
| `COOKIE_SECURE` / `COOKIE_SAMESITE` | Atributos de las cookies de sesión. `Secure=true` obligatorio en producción. | `false` / `lax` |
| `TRUSTED_PROXY_HOPS` | Proxies de confianza delante de la API (Render = 1). Con 0 se ignora `X-Forwarded-For`. | `0` |
| `SEED_DEMO_DATA` / `DEMO_PASSWORD` | Datos demo y su contraseña (mínimo 8 caracteres). Prohibido en producción. | `true` / tu clave |
| `AUDIT_RETENTION_DAYS` | Días que se conserva la auditoría. Mínimo 365 (RNF-06). | `365` |
| `EMAIL_BACKEND` | Cómo se envía el código 2FA: `console` (solo local, lo imprime en terminal), `smtp` (Gmail u otro servidor) o `brevo` (API HTTP, para Render gratuito). En producción no puede ser `console`. | `console` |
| `EMAIL_FROM` / `EMAIL_FROM_NAME` | Remitente del código. Con Brevo, el correo debe estar validado como remitente en la cuenta. | vacío / `InkaSec` |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD` | Servidor SMTP con STARTTLS. Gmail: `smtp.gmail.com`, puerto `587`, y una contraseña de aplicación de Google. | vacío / `587` |
| `BREVO_API_KEY` | Clave de la API de Brevo (`EMAIL_BACKEND=brevo`). | vacío |
| `BOOTSTRAP_ADMIN_*` | Primer administrador real (`python -m app.bootstrap_admin`). Correo al que tengas acceso y contraseña de ≥ 12 caracteres. | vacío |

## Pruebas y análisis de seguridad

**Con Docker (no necesitas instalar Python ni Node en tu PC):**

```bash
docker compose --profile test run --rm backend-tests    # pytest + cobertura (mínimo 85 %) + Bandit
docker compose --profile test run --rm frontend-tests   # oxlint + Vitest con cobertura + build
```

Agrega `--build` la primera vez y cada vez que cambien `requirements*.txt` o `package.json`. Los reportes de cobertura quedan en `mi-api-fastapi/htmlcov/index.html` y `frontend/coverage/index.html`.

**Sin Docker:** todo se instala desde los archivos de requisitos (`pip install -r requirements-dev.txt` y `npm ci`).

```bash
cd mi-api-fastapi
python -m pytest -q --cov=app --cov-report=term-missing   # 132 pruebas + cobertura
bandit -r app -ll -ii                                     # análisis estático (SAST)

cd ../frontend
npm run lint                   # oxlint
npm run test:coverage          # 67 pruebas de pantallas (Vitest + Testing Library) + cobertura
npm run build                  # compilación de producción
npm audit --omit=dev           # dependencias vulnerables (SCA)
```

| Herramienta | Qué revisa | Dónde se instala |
|---|---|---|
| pytest + pytest-cov | Que la API haga lo que debe, y qué porcentaje del código recorren las pruebas | `requirements-dev.txt` |
| Bandit | Patrones inseguros en el código Python (SAST) | `requirements-dev.txt` |
| Vitest + Testing Library + coverage-v8 | Las pantallas del frontend, como las usaría una persona, y su cobertura | `devDependencies` de `package.json` |
| oxlint | Errores comunes en JavaScript/React | `devDependencies` de `package.json` |
| npm audit | Librerías con vulnerabilidades conocidas (SCA) | Viene con npm |

Las pruebas usan una base SQLite en memoria y su propia configuración (`tests/conftest.py`), así que no tocan tu base de datos ni dependen de tu `.env`.

- `tests/test_progress.py`: reglas de progreso, retos y paneles por rol.
- `tests/test_certificates.py`: regla del 80 %, vigencia, renovación, PDF y verificación pública.
- `tests/test_challenge_formats.py`: retos por pasos y de señales, y columnas nuevas en bases existentes.
- `frontend/src/__tests__/`: pruebas de pantallas con datos reales de la API: inicio de sesión y 2FA, navegación del trabajador, los tres formatos de reto, certificados y verificación, panel del gestor, panel del administrador y el cliente de la API.
- `tests/test_security.py`: **simulaciones de ataque**. Incluyen:
  - fuerza bruta de contraseña y de 2FA;
  - IP falsificada en `X-Forwarded-For`;
  - tokens JWT alterados, sin firma (`alg none`) o expirados;
  - CSRF;
  - escalamiento de privilegios y acceso a datos de otra empresa;
  - inyección SQL y de fórmulas en el CSV;
  - configuración insegura.

## Medidas de seguridad implementadas

| Amenaza | Defensa | Prueba |
|---|---|---|
| Fuerza bruta de contraseña | Bloqueo de 15 min tras 3 fallos consecutivos (HTTP 423) y límite de 10 intentos/min por IP (HTTP 429) | `test_password_bruteforce_locks_the_account` |
| Fuerza bruta de 2FA | Los códigos fallidos suman al mismo contador; al bloquear, el desafío se invalida. El código se guarda como HMAC ligado al desafío | `test_2fa_bruteforce_locks_the_account_and_burns_the_challenge`, `test_email_code_is_stored_only_as_a_keyed_hash` |
| Robo de sesión por XSS | JWT en cookie `HttpOnly`; `Secure` obligatorio en producción; CSP en la API | `test_session_cookie_flags` |
| Falsificación de tokens | Firma HS256 obligatoria; se exigen `exp`, `iat` y `sub`; el rol se lee de la BD, no del token | `test_forged_tokens_are_rejected` |
| CSRF | Patrón *double submit cookie* en todo POST/PATCH/DELETE | `test_state_changes_require_matching_csrf_token` |
| Escalamiento de privilegios | RBAC verificado en cada ruta (HTTP 403) | `test_each_role_only_reaches_its_own_routes` |
| Acceso a otra empresa (IDOR) | Toda consulta filtra por `company_id` (HTTP 404) | `test_admin_cannot_touch_users_of_another_company` |
| Enumeración de usuarios | Misma respuesta y mismo costo de hash para correos inexistentes | `test_unknown_email_still_pays_the_hashing_cost` |
| Inyección SQL | Consultas parametrizadas con SQLAlchemy | `test_sql_injection_in_audit_search_is_inert` |
| Inyección de fórmulas en CSV | Celdas que empiezan con `= + - @` se exportan como texto | `test_csv_formula_injection_is_neutralized` |
| Claves débiles o expuestas | La API no arranca con un secreto corto; `.env` fuera de git | `test_insecure_configuration_refuses_to_start` |
| Trazabilidad | Auditoría con usuario, IP, fecha UTC y resultado; retención mínima de 12 meses | `test_admin_user_lifecycle` |

## CI/CD

Pipeline en GitHub Actions (`.github/workflows/ci.yml`), con permisos mínimos y los secretos pasados como variables de entorno:

1. **Backend**: pruebas con pytest y cobertura (falla por debajo de 85 %) y SAST con Bandit.
2. **Frontend**: lint, pruebas con Vitest y cobertura (falla por debajo de los mínimos de `vite.config.js`), build y `npm audit` de dependencias de producción (falla con severidad alta o crítica).
   Los reportes de cobertura de ambos quedan como artefactos del workflow (pestaña Actions → la ejecución → *Artifacts*).
3. **Deploy a Dev** en Render (solo en `push` a `main` y solo si los dos jobs anteriores pasan).
4. **Smoke test**: espera a que `/api/v1/health` responda 200 (verifica también la conexión a la BD).
5. **Deploy a Producción**: solo si la variable `RENDER_PROD_ENABLED` es `true`.

> En Render configura `APP_ENV=production`, `COOKIE_SECURE=true`, `TRUSTED_PROXY_HOPS=1`, `SEED_DEMO_DATA=false` y un `JWT_SECRET_KEY` propio de 32 caracteres o más.

## Despliegue en Render (paso a paso)

El archivo `render.yaml` describe tres servicios: la API (Docker), el frontend (sitio estático) y PostgreSQL.

1. En Render: **New → Blueprint**, elige este repositorio y la rama. Render te pedirá los valores marcados como `sync: false`:
   - `FRONTEND_ORIGIN`: la URL del sitio estático, por ejemplo `https://inkasec-web.onrender.com`.
   - `EMAIL_FROM`: el correo validado como remitente en Brevo (puede ser tu Gmail).
   - `BREVO_API_KEY`: clave de la API de Brevo (Settings → SMTP & API → API keys).
2. Si Render cambia el nombre de la API (si `inkasec-api` ya está ocupado), actualiza la regla `/api/*` del sitio estático en `render.yaml` con la URL real.
3. Crea el primer administrador desde la consola de la API (**Shell**), con un correo al que tengas acceso:
   ```bash
   BOOTSTRAP_ADMIN_EMAIL=tu.correo@gmail.com BOOTSTRAP_ADMIN_PASSWORD='una-clave-de-12-o-mas' python -m app.bootstrap_admin
   ```
   Luego inicia sesión en la web: el código 2FA llega a ese correo.

> **Importante:** el plan gratuito de Render bloquea el SMTP saliente (puertos 25, 465 y 587), por eso el correo se envía por la API HTTP de Brevo. Las bases de datos gratuitas caducan a los 30 días y los servicios gratuitos se duermen tras 15 minutos sin uso (la primera carga tarda unos segundos).

> **Retos y certificados:** las columnas nuevas de `challenges` y `challenge_attempts` se agregan solas al arrancar la API (`app/db/migrate.py`) y los certificados usan una tabla nueva (`topic_certificates`). Para esta actualización **no hace falta borrar la base de datos**.

> **Si ya desplegaste una versión anterior a la de asignaciones:** el código 2FA cambió de TOTP a correo y la tabla `auth_challenges` tiene una columna nueva. Como `AUTO_CREATE_TABLES` no modifica tablas existentes, borra la base de datos del servicio (o crea una nueva) antes de volver a desplegar. La tabla `assignments` también cambió (ahora puede apuntar a un reto y guarda quién la creó), así que aplica la misma regla.

## API

Prefijo: `/api/v1`. Autenticación por cookie; los métodos que modifican datos requieren la cabecera `X-CSRF-Token`.

| Método | Ruta | Rol |
|---|---|---|
| GET | `/health` | Público |
| POST | `/auth/login` · `/auth/2fa/verify` | Público |
| GET · POST | `/auth/me` · `/auth/logout` | Autenticado |
| GET | `/worker/dashboard` · `/worker/modules/{id}` | Trabajador |
| POST | `/worker/modules/{id}/comb` · `/worker/modules/{id}/capacity` · `/worker/modules/{id}/complete` · `/worker/challenges/{id}/answer` · `/worker/challenges/{id}/check` | Trabajador |
| GET · POST | `/worker/certificates` · `/worker/certificates/{id}/renewal` · `/worker/certificates/{id}/pdf` | Trabajador (solo los suyos) |
| GET | `/certificates/verify/{código}` | Público (30 consultas por minuto por IP) |
| GET | `/manager/dashboard` · `/manager/topics` · `/manager/stats` · `/manager/assignable` · `/manager/assignments` | Gestor |
| GET · POST · PUT | `/manager/modules/{id}` · `/manager/modules` · `/manager/challenges/{id}` · `/manager/challenges` | Gestor (solo lo que creó) |
| POST · DELETE | `/manager/assignments` · `/manager/assignments/{id}` | Gestor |
| GET · POST · PATCH · DELETE | `/admin/users` · `/admin/users/{id}` | Administrador |
| GET · POST | `/admin/areas` | Administrador |
| GET | `/admin/dashboard` · `/admin/audit` · `/admin/reports/summary` · `/admin/reports/export` | Administrador |

El detalle de cada ruta está en http://localhost:8001/docs mientras corre la API en desarrollo.

## Estado del proyecto

| Requerimiento | Estado |
|---|---|
| RF-01 Acceso con roles y 2FA por correo | ✅ Implementado |
| RF-02 Gestión de usuarios y áreas, auditoría | ✅ Implementado (edición limitada a rol y estado) |
| RF-03 Gestión de contenidos | ✅ Implementado: módulos y retos en lenguaje sencillo, temas del catálogo, búsqueda, borrador/publicado/archivado |
| RF-04 Asignaciones, plazos y notificaciones | 🟡 Parcial: asignación a empresa, área o persona con fecha límite; falta notificar por correo |
| RF-05 Evaluación con retos y retroalimentación | ✅ Implementado: tres formatos (rápido, por pasos, encuentra las señales), práctica sin límite, calificación en la API y explicación en cada intento |
| RF-06 Seguimiento, estadísticas y reportes | ✅ Implementado (errores agrupados por tema) |
| RF-07 Certificados | ✅ Implementado: uno por tema (80 % en cada módulo), vigencia de 12 meses, renovación con repaso, PDF y verificación pública |

## Cómo contribuir

1. Crea una rama desde `main`: `git switch -c feature/nombre-corto`.
2. Antes de subir cambios, ejecuta las pruebas, Bandit, el lint y el build (ver arriba).
3. Abre un Pull Request hacia `main`: el pipeline debe pasar para poder desplegar.
4. Nunca subas archivos `.env`, contraseñas ni secretos; usa los `.env.example` como referencia.
