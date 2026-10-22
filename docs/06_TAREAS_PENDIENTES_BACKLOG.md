# SuperDato — 06. Tareas Pendientes y Backlog de Ejecución

Este documento desglosa todas las tareas técnicas del proyecto SuperDato por dominios y fases, manteniendo actualizada la trazabilidad del estado de ejecución.

---

## 1. Backlog de Tareas por Dominio Técnico

### Dominio 1: Base Técnica y Scaffolding (Fase 1)
- [x] **TSK-101 (P0)**: Inspeccionar el entorno existente, tickets reales de muestra en `samples/` y proyectos previos.
- [x] **TSK-102 (P0)**: Redactar la documentación técnica de arquitectura, modelo de datos, extractor, riesgos y plan de entregas.
- [x] **TSK-103 (P0)**: Configurar estructura de directorios del proyecto (`backend/`, `frontend/`, `docker/`).
- [x] **TSK-104 (P0)**: Crear `docker-compose.yml` para orquestar `api` (FastAPI), `worker` (Celery), `beat` (Celery Beat), `db` (PostgreSQL 16), `redis` (Redis 7) y `web` (React/Vite).
- [x] **TSK-105 (P0)**: Configurar `backend/pyproject.toml` y `requirements.txt` con FastAPI, SQLAlchemy 2.0, asyncpg, pydantic v2, pypdf, celery, redis, cryptography, argon2-cffi.
- [x] **TSK-106 (P0)**: Inicializar entorno de Alembic (`alembic/env.py`) para migraciones asíncronas.
- [x] **TSK-107 (P1)**: Configurar `frontend/` con Vite, React, TypeScript, Tailwind CSS y Lucide Icons.

---

### Dominio 2: Usuarios, Autenticación y Casas (Fase 2)
- [x] **TSK-201 (P0)**: Crear modelos SQLAlchemy: `User`, `Household`, `HouseholdMembership`, `HouseholdInvitation`.
- [x] **TSK-202 (P0)**: Implementar servicio de hashing de contraseñas (`argon2id`) y generador/validador de JWT (access + refresh tokens).
- [x] **TSK-203 (P0)**: Implementar endpoints de autenticación: `/api/v1/auth/register`, `/api/v1/auth/login`, `/api/v1/auth/refresh`, `/api/v1/auth/me`.
- [x] **TSK-204 (P0)**: Crear middleware de inyección de dependencias para verificar usuario autenticado y membresía en casa (`require_household_permission`).
- [x] **TSK-205 (P0)**: Implementar endpoints de gestión de casas: `/api/v1/households` (crear, listar, cambiar configuración, gestión de miembros).
- [x] **TSK-206 (P1)**: Implementar sistema de invitaciones por email y aceptación de invitaciones con token único y caducidad.
- [x] **TSK-207 (P0)**: Escribir pruebas unitarias e integración en `tests/domains/test_auth.py` y `tests/domains/test_households_rbac.py` verificando el aislamiento estricto entre casas y permisos.

---

### Dominio 3: Extractor de Tickets y Sincronización con Gmail (Fase 3)
- [x] **TSK-301 (P0)**: Desarrollar el módulo `PDFReceiptExtractor` en `backend/app/domains/receipts/extractor/` basado en `pypdf`.
  - Extracción de cabecera: CIF, número de factura (`TIENDA-CAJA-SEQ`), fecha y hora.
  - Extracción de líneas unitarias y de peso (`kg` con precio/kg).
  - Extracción de líneas especiales (parking, descuentos).
  - Extracción de tabla de IVA (4%, 10%, 21%).
- [x] **TSK-302 (P0)**: Desarrollar validador contable que concilie la suma de líneas con el total del ticket y la base de impuestos (0.00 € discrepancia verificada).
- [x] **TSK-303 (P0)**: Implementar cálculo de huella unívoca (`deduplication_hash`) con SHA-256 e inserción idempotente.
- [x] **TSK-304 (P1)**: Crear endpoint de subida manual de PDFs (`POST /api/v1/receipts/upload`) para procesar tickets sin requerir Gmail.
- [x] **TSK-305 (P0)**: Implementar cliente Google OAuth 2.0 y cifrado de tokens en reposo con Fernet/AES-256 (`GoogleAccountConnection`).
- [x] **TSK-306 (P1)**: Configurar tareas Celery (`sync_google_connection_task`) para escaneo de correos con filtro `from:mercadona.es` y descarga de adjuntos PDF.
- [x] **TSK-307 (P1)**: Crear modelo y endpoint de seguimiento de importaciones (`import_jobs`) con recuento de tickets nuevos, duplicados y con error.
- [x] **TSK-308 (P0)**: Escribir tests automatizados en `tests/domains/test_integrations.py` verificando cifrado, generación de URL y ejecución de jobs.

---

### Dominio 4: Catálogo de Productos y Precios Históricos (Fase 4)
- [x] **TSK-401 (P0)**: Crear modelos de catálogo: `Category`, `Product`, `ProductAlias`, `PriceObservation`.
- [x] **TSK-402 (P1)**: Sembrar (seed) 13 categorías por defecto con slug, color e icono (Frutas, Carnicería, Pescadería, Lácteos, Panadería, Limpieza, etc.).
- [x] **TSK-403 (P0)**: Desarrollar normalizador de nombres de productos y asignación por alias automáticos y reglas deterministas.
- [x] **TSK-404 (P0)**: Registrar observaciones de precio inmutables (1:1) asociadas a cada línea de ticket procesada (`observed_at`, `unit_price`, `store_code`).
- [x] **TSK-405 (P1)**: Implementar endpoints de gestión y búsqueda de catálogo (`/api/v1/catalog/products`, `/api/v1/catalog/categories`, `/api/v1/catalog/products/{id}/price-history`).
- [x] **TSK-406 (P1)**: Implementar edición manual de líneas de ticket (`PATCH /api/v1/receipts/{id}/lines/{line_id}`) preservando la información original con `is_manual_override = True` y `validation_status = 'MANUALLY_EDITED'`.
- [x] **TSK-407 (P0)**: Escribir tests en `tests/domains/test_catalog.py` cubriendo normalización, alias, inmutabilidad de precios y llamadas a la API.
- [x] **TSK-408 (P0)**: Corregir carga de detalle de ticket (`GET /api/v1/receipts/{id}`) conectándolo directamente a la base de datos SQLAlchemy con `selectinload` de líneas y desglose fiscal (IVA), resolviendo referencias de clases en mappers y validación de esquemas Pydantic.

---

### Dominio 5: Dashboard y Analítica Avanzada (Fase 5)
- [x] **TSK-501 (P0)**: Desarrollar consultas agregadas de base de datos en `AnalyticsService`:
  - Gasto total del periodo y comparativa porcentual con el periodo anterior (MoM).
  - Ticket medio, mediana y número de visitas/compras.
  - Gasto agrupado por categoría (gráfico circular/donut con colores asignados).
  - Serie temporal de gasto agrupado por día, semana o mes.
  - Top productos ordenados por importe acumulado y por frecuencia de compra.
- [x] **TSK-502 (P0)**: Crear endpoints de analítica (`/api/v1/analytics/...`) con soporte de filtros dinámicos por rango de fechas (últimos 30 días, mes actual, año actual, rango personalizado).
- [x] **TSK-503 (P0)**: Implementar componentes visuales en React:
  - Tarjetas de KPIs numéricos (Gasto total, Variación MoM, Ticket medio, Total compras).
  - Gráfica interactiva de evolución de gasto temporal (Recharts AreaChart / BarChart).
  - Gráfica de distribución de gasto por categorías (Recharts PieChart con tooltip interactivo).
  - Tabla de Top productos y desglose de tickets recientes.
  - Selector global de rango de fechas sincronizado con TanStack Query en el Dashboard.

---

### Dominio 6: Frontend SPA y Experiencia de Usuario (Fases 1 a 5)
- [x] **TSK-601 (P0)**: Crear layout principal con barra lateral, navegación responsiva y selector desplegable de Hogar activo.
- [x] **TSK-602 (P0)**: Desarrollar vista de autenticación y perfil (`SettingsPage.tsx`).
- [x] **TSK-603 (P0)**: Desarrollar vista de Listado de Tickets con filtros, badges de estado y subida de archivos PDF.
- [x] **TSK-604 (P0)**: Desarrollar vista de Detalle y Edición de Ticket (`ReceiptDetailModal.tsx`) con corrección de líneas en caliente y desglose de IVA.
- [x] **TSK-605 (P1)**: Desarrollar vista de Gestión de Importaciones (`ImportsPage.tsx`) con estado de Google OAuth, botón de sincronización manual e historial de jobs.
- [x] **TSK-606 (P1)**: Desarrollar vista de Configuración del Hogar (gestión de miembros, roles, invitaciones).
- [x] **TSK-607 (P1)**: Desarrollar vista de Catálogo de Productos (`ProductsPage.tsx`) con filtro por categorías, gráfica Recharts de evolución de precios y vinculación de alias.

---

### Dominio 7: Pruebas, Seguridad y Despliegue (Fase 6)
- [x] **TSK-701 (P0)**: Crear suite completa de pruebas automáticas con `pytest` y `pytest-asyncio` (17 pruebas activas pasando en <3s).
- [ ] **TSK-702 (P0)**: Validar casos límite: tickets con productos vendidos al peso, tickets con devoluciones/descuentos, tickets duplicados, intentos de acceso no autorizado entre casas.
- [ ] **TSK-703 (P1)**: Documentar variables de entorno en `.env.example` y redactar `README.md` detallado para puesta en marcha con un solo comando (`docker compose up -d`).
- [ ] **TSK-704 (P1)**: Verificar la ausencia de fugas de credenciales en logs y validar políticas de seguridad.
