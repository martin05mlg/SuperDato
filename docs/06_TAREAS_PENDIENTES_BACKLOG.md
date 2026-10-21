# SuperDato — 06. Tareas Pendientes y Backlog de Ejecución

Este documento desglosa todas las tareas técnicas necesarias para llevar el MVP de SuperDato desde la fase actual de diseño hasta su despliegue y validación final de extremo a extremo.

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
- [ ] **TSK-301 (P0)**: Desarrollar el módulo `PDFReceiptExtractor` en `backend/app/domains/receipts/extractor/` basado en `pypdf`.
  - Extracción de cabecera: CIF, número de factura (`TIENDA-CAJA-SEQ`), fecha y hora.
  - Extracción de líneas unitarias y de peso (`kg` con precio/kg).
  - Extracción de líneas especiales (parking, descuentos).
  - Extracción de tabla de IVA (4%, 10%, 21%).
- [ ] **TSK-302 (P0)**: Desarrollar validador contable que concilie la suma de líneas con el total del ticket y la base de impuestos.
- [ ] **TSK-303 (P0)**: Implementar cálculo de huella unívoca (`deduplication_hash`) con SHA-256 e inserción idempotente.
- [ ] **TSK-304 (P1)**: Crear endpoint de subida manual de PDFs (`POST /api/v1/households/{id}/receipts/upload`) para procesar tickets sin requerir Gmail.
- [ ] **TSK-305 (P0)**: Implementar cliente Google OAuth 2.0 y cifrado de tokens en reposo (`GoogleAccountConnection`).
- [ ] **TSK-306 (P1)**: Configurar tareas Celery para escaneo periódico de correos con filtro `from:mercadona.es` y descarga de adjuntos PDF.
- [ ] **TSK-307 (P1)**: Crear modelo y endpoint de seguimiento de importaciones (`import_jobs`) con recuento de tickets nuevos, duplicados y con error.
- [ ] **TSK-308 (P0)**: Escribir tests con los PDFs reales de `samples/` verificando que los totales e importes coinciden al 100%.

---

### Dominio 4: Catálogo de Productos y Precios Históricos (Fase 4)
- [ ] **TSK-401 (P0)**: Crear modelos de catálogo: `Category`, `Product`, `ProductAlias`, `PriceObservation`.
- [ ] **TSK-402 (P1)**: Sembrar (seed) categorías por defecto de la cesta de la compra (Frutas, Lácteos, Carnicería, Panadería, Limpieza, etc.).
- [ ] **TSK-403 (P0)**: Desarrollar normalizador de nombres de productos y asignación por alias automáticos y reglas deterministas.
- [ ] **TSK-404 (P0)**: Registrar observaciones de precio inmutables asociadas a cada línea de ticket procesada.
- [ ] **TSK-405 (P1)**: Implementar endpoints de gestión y búsqueda de catálogo (`/api/v1/catalog/products`, `/api/v1/catalog/categories`).
- [ ] **TSK-406 (P1)**: Implementar edición manual de líneas de ticket preservando la información original con `is_manual_override = True`.

---

### Dominio 5: Dashboard y Analítica (Fase 5)
- [ ] **TSK-501 (P0)**: Desarrollar consultas agregadas de base de datos en `AnalyticsService`:
  - Gasto total del periodo y comparativa porcentual con el periodo anterior.
  - Ticket medio y número de visitas/compras.
  - Gasto agrupado por categoría (gráfico circular/donut).
  - Serie temporal de gasto por día/semana/mes.
  - Top 10 productos por importe acumulado y por frecuencia de compra.
- [ ] **TSK-502 (P0)**: Crear endpoints de analítica (`/api/v1/households/{id}/analytics/...`) con soporte de filtros por rango de fechas.
- [ ] **TSK-503 (P0)**: Implementar componentes visuales en React:
  - Tarjetas de KPIs numéricos (Gasto total, Variación, Ticket medio, Total compras).
  - Gráfica interactiva de evolución de gasto temporal (Recharts).
  - Gráfica de distribución de gasto por categorías (Recharts PieChart).
  - Tabla de Top productos y compras recientes.
  - Selector global de rango de fechas sincronizado con TanStack Query.

---

### Dominio 6: Frontend SPA y Experiencia de Usuario (Fase 5 / 6)
- [ ] **TSK-601 (P0)**: Crear layout principal con barra lateral, navegación responsiva y selector desplegable de Hogar activo.
- [ ] **TSK-602 (P0)**: Desarrollar vistas de autenticación (Login, Registro).
- [ ] **TSK-603 (P0)**: Desarrollar vista de Listado de Tickets con paginación, filtros por fecha y badges de estado (`PROCESSED`, `REVISION_NEEDED`, `ERROR`).
- [ ] **TSK-604 (P0)**: Desarrollar vista de Detalle y Edición de Ticket (visualización de líneas originales, productos asignados y tabla fiscal de IVA).
- [ ] **TSK-605 (P1)**: Desarrollar modal/zona de subida de tickets PDF con barra de progreso y reporte instantáneo.
- [ ] **TSK-606 (P1)**: Desarrollar vista de Configuración del Hogar (gestión de miembros, roles, invitaciones y conexión con Gmail).
- [ ] **TSK-607 (P1)**: Desarrollar vista de Explorador de Productos con histórico de precios por producto.

---

### Dominio 7: Pruebas, Seguridad y Despliegue (Fase 6)
- [ ] **TSK-701 (P0)**: Crear suite completa de pruebas unitarias y de integración con `pytest` y `pytest-asyncio`.
- [ ] **TSK-702 (P0)**: Validar casos límite: tickets con productos vendidos al peso, tickets con devoluciones/descuentos, tickets duplicados, intentos de acceso no autorizado entre casas.
- [ ] **TSK-703 (P1)**: Documentar variables de entorno en `.env.example` y redactar `README.md` detallado para puesta en marcha con un solo comando (`docker compose up -d`).
- [ ] **TSK-704 (P1)**: Verificar la ausencia de fugas de credenciales en logs y validar políticas de seguridad.

