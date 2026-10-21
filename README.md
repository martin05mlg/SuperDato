# SuperDato 🛒📊

**SuperDato** es una plataforma web modular full-stack para importar, almacenar, auditar y analizar los tickets digitales de compra de **Mercadona** recibidos por correo electrónico.

Diseñada para hogares y usuarios particulares, permite conocer los hábitos de consumo reales, supervisar el gasto por categorías, seguir la evolución de precios históricos y conciliar el desglose de IVA con rigor contable.

---

## 🛠️ Pila Tecnológica

- **Backend**: Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (Async), Alembic, pypdf, Celery, Redis.
- **Base de Datos**: PostgreSQL 16 con tipos numéricos exactos (`NUMERIC`) y claves foráneas estrictas.
- **Frontend**: React 18/19, TypeScript, Vite, Tailwind CSS, Lucide Icons, Recharts, TanStack Query v5.
- **Contenedores**: Docker y Docker Compose (PostgreSQL, Redis, API, Celery Worker, Celery Beat, Nginx).

---

## 🚀 Puesta en Marcha Rápida (Local con Docker Compose)

1. **Clonar el repositorio y configurar variables de entorno**:
   ```bash
   cp .env.example .env
   ```

2. **Levantar todos los servicios**:
   ```bash
   docker compose up -d --build
   ```

3. **Acceder a las aplicaciones**:
   - 🌐 **Frontend**: [http://localhost:5173](http://localhost:5173)
   - 📑 **OpenAPI / Swagger Docs**: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
   - 🩺 **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 💻 Desarrollo Local (Sin Docker)

### Backend
1. **Activar el entorno virtual**:
   ```bash
   # Windows PowerShell
   .venv\Scripts\Activate.ps1
   # Linux / macOS
   source .venv/bin/activate
   ```

2. **Instalar dependencias**:
   ```bash
   pip install -r backend/requirements.txt
   ```

3. **Ejecutar pruebas automatizadas**:
   ```bash
   pytest backend/tests -v
   ```

4. **Arrancar el servidor de desarrollo**:
   ```bash
   cd backend
   uvicorn app.main:app --reload --port 8000
   ```

### Frontend
1. **Instalar dependencias**:
   ```bash
   cd frontend
   npm install
   ```

2. **Arrancar Vite**:
   ```bash
   npm run dev
   ```

---

## 📚 Documentación Técnica Detallada

- [`docs/01_ARQUITECTURA_Y_DISENO.md`](docs/01_ARQUITECTURA_Y_DISENO.md): Arquitectura del sistema, Clean Architecture y RBAC.
- [`docs/02_MODELO_DE_DATOS.md`](docs/02_MODELO_DE_DATOS.md): Esquema relacional PostgreSQL y tipos exactos.
- [`docs/03_EXTRACTOR_Y_GMAIL_INTEGRATION.md`](docs/03_EXTRACTOR_Y_GMAIL_INTEGRATION.md): Extractor determinista y OAuth 2.0.
- [`docs/04_RIESGOS_Y_DECISIONES_TECNICAS.md`](docs/04_RIESGOS_Y_DECISIONES_TECNICAS.md): Análisis de riesgos y mitigaciones de seguridad.
- [`docs/05_PLAN_DE_ENTREGAS_Y_PROGRESO.md`](docs/05_PLAN_DE_ENTREGAS_Y_PROGRESO.md): Seguimiento de fases y criterios de aceptación.
- [`docs/06_TAREAS_PENDIENTES_BACKLOG.md`](docs/06_TAREAS_PENDIENTES_BACKLOG.md): Backlog granular de tareas.

