# SuperDato 🛒📊

[![Docker Compose](https://img.shields.io/badge/Docker%20Compose-Ready-2496ED?logo=docker&logoColor=white)](docker-compose.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React 19](https://img.shields.io/badge/React-19.0-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16.0-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![PWA Ready](https://img.shields.io/badge/PWA-Ready-5A0FC8?logo=pwa&logoColor=white)](frontend/public/manifest.webmanifest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**SuperDato** es una plataforma web modular, autónoma y auto-alojable (*self-hosted*) para importar, organizar, auditar y analizar tus propios tickets de compra digitales y en papel.

Permite a familias, pisos compartidos y usuarios particulares monitorizar el gasto mensual del hogar, conciliar el desglose de IVA con precisión contable, comparar la evolución histórica de precios (IPC personal) y disponer de un asistente de lista de la compra inteligente mediante una aplicación web progresiva (PWA).

> [!IMPORTANT]
> **Aviso Legal y de Marca**: *SuperDato es un proyecto de software libre e independiente con fines educativos y de gestión doméstica personal. No está afiliado, patrocinado, autorizado ni respaldado en modo alguno por Mercadona, S.A. Todas las marcas comerciales mencionadas pertenecen a sus respectivos propietarios.*

---

## ✨ Características Principales

- 📥 **Sincronización Automática con Gmail**: Conexión nativa con Google OAuth 2.0 (`gmail.readonly`) que busca y descarga periódicamente tus tickets digitales.
- 🧾 **Motor Determinista de Tickets PDF y Manuales**: Extracción local de líneas de productos, pesos variables, tarifas de IVA (4%, 10%, 21%) y deduplicación criptográfica SHA-256.
- 🧮 **Conciliación Contable Estricta**: Verificación matemática entre líneas de artículos, base imponible, cuotas de IVA y total del ticket.
- 📈 **Control de Inflación Personal (IPC Personal)**: Seguimiento histórico de subidas y bajadas de precio por producto y categoría.
- 🛡️ **Aislamiento Multi-Hogar y Seguridad de Producción**: Control de acceso RBAC (*Owner*, *Admin*, *Member*, *Viewer*), cifrado en reposo **AES-256-GCM** para tokens OAuth, contraseñas **Argon2id**, cookies `HttpOnly` y limitación de tasa (*rate limiting*).
- 📱 **PWA Móvil**: Instalable en móvil y escritorio.
- ⚙️ **Panel de Superadministración (`/admin`)**: Gestión visual de invitaciones de un solo uso, usuarios, tickets de demostración y configuración dinámica de Google OAuth y URL pública del servidor sin editar archivos `.env`.

---

## 🚀 Despliegue Rápido con Docker (Zero-Config)

El proyecto está diseñado para arrancar con un solo comando sin necesidad de crear ni copiar archivos `.env`:

```bash
git clone https://github.com/martin05mlg/SuperDato.git
cd SuperDato
docker compose up -d
```

En el primer arranque, SuperDato:
1. Genera automáticamente claves criptográficas seguras (`SECRET_KEY` y `ENCRYPTION_MASTER_KEY`) y las persiste con permisos `0600` en el volumen `app_data` (`/app/data/.secrets.json`).
2. Ejecuta automáticamente las migraciones de base de datos con **Alembic** (`alembic upgrade head`).
3. Te espera en la web para configurar el Administrador mediante el **First-Run Web Setup Wizard**.

### 🔑 Configuración del Superadministrador (First-Run Web Setup)

Abre **[http://localhost:5173](http://localhost:5173)** en tu navegador. SuperDato detectará automáticamente el primer arranque y te recibirá con el asistente de configuración inicial:
- Configuras tu nombre, email y **la contraseña que tú elijas** directamente desde la web.
- **Sin necesidad de consultar logs de terminal ni copiar claves temporales.**
- Una vez creado, el asistente se desactiva permanentemente y los registros posteriores quedan cerrados por invitación.

> [!TIP]
> **Modo Desatendido (Opcional)**: Si despliegas con herramientas automáticas (Ansible, Portainer, Kubernetes) y prefieres preconfigurar el administrador sin pasar por la web, puedes definir `SUPERADMIN_PASSWORD` en tu `.env`.

Si en algún momento olvidas tu contraseña o la cuenta se bloquea por intentos fallidos, puedes restablecerla cómodamente por CLI:

```bash
docker compose exec api python scripts/reset_admin.py
```

---

## ⚙️ Configuración de Google OAuth desde la Web

Puedes configurar las credenciales de Google OAuth y la dirección pública de tu servidor directamente desde el navegador sin tocar variables de entorno:

1. Inicia sesión con la cuenta de superadministrador y abre el **Panel de Administración** (`/admin`).
2. Entra en la pestaña **"Google OAuth & Servidor"**.
3. Define la **URL Pública del Servidor** (ej. `http://localhost:5173` o `https://superdato.midominio.com`).
4. Copia la **URI de redireccionamiento autorizada** generada automáticamente (`<SERVER_PUBLIC_URL>/integrations/google/callback`) y regístrala en [Google Cloud Console](https://console.cloud.google.com/apis/credentials) con el scope `https://www.googleapis.com/auth/gmail.readonly`.
5. Pega el **Client ID** y el **Client Secret** en el panel y pulsa **Guardar Configuración**.

> [!TIP]
> También puedes eliminar en 1 clic los tickets sintéticos de muestra desde el Panel de Administración cuando empieces a subir tus propios tickets.

---

## 🌐 Despliegue en Producción con HTTPS y Backups

### Reverse Proxy (HTTPS)
Para exponer SuperDato fuera de `localhost`, colócalo detrás de un proxy inverso con TLS (por ejemplo **Caddy**):

```caddyfile
superdato.midominio.com {
    reverse_proxy localhost:5173
}
```

Después, actualiza la **URL Pública del Servidor** en `/admin` a `https://superdato.midominio.com`.

### Copias de Seguridad (Backups)
Para respaldar toda tu instancia necesitas conservar únicamente dos elementos:
1. **Base de datos PostgreSQL**:
   ```bash
   docker compose exec -T db pg_dump -U superdato superdato_db > backup_superdato.sql
   ```
2. **Archivo de claves criptográficas (`/app/data/.secrets.json`)** en el volumen `app_data`:
   ```bash
   docker compose cp api:/app/data/.secrets.json ./secrets_backup.json
   ```

---

## 💻 Desarrollo Local y Tests

```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

pip install -r backend/requirements-dev.txt
$env:PYTHONPATH="backend"; pytest -q
```

Para regenerar los tickets PDF sintéticos de prueba (nunca subas tickets reales al repositorio):

```bash
python backend/scripts/generate_sample_receipts.py
```

---

## 🔒 Privacidad, RGPD y Seguridad

- **Cifrado Autenticado**: Tokens OAuth cifrados en reposo mediante **AES-256-GCM** con clave derivada por HKDF-SHA256.
- **Derechos RGPD Integrados**: Exportación completa de datos en JSON (`GET /api/v1/auth/me/export`) y eliminación completa de cuenta (`POST /api/v1/auth/me/delete`). Consulta [PRIVACY.md](PRIVACY.md) y [SECURITY.md](SECURITY.md).

---

## 📄 Licencia

Distribuido bajo la licencia **MIT**. Consulta el archivo [LICENSE](LICENSE) para más información.

