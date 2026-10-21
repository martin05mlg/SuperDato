# SuperDato — 04. Riesgos Técnicos y Decisiones de Arquitectura

Este documento analiza en profundidad los 6 riesgos técnicos críticos identificados en la especificación, junto con sus estrategias de mitigación implementadas y las decisiones de diseño adoptadas para garantizar la fiabilidad del sistema.

---

## 1. Riesgo 1: Acceso y Permisos de Gmail API (Impacto: ALTO)

### Descripción del Riesgo
Para descargar los correos con tickets de Mercadona y sus adjuntos en PDF, se requiere el scope de Google `https://www.googleapis.com/auth/gmail.readonly`. Google cataloga este permiso como **Restricted Scope** (Ámbito Restringido).
Si una aplicación web se somete a verificación pública para usuarios generales en producción:
- Exige una auditoría anual externa de seguridad **CASA Tier 2** (Cloud Application Security Assessment), con un coste económico relevante y requisitos estrictos de infraestructura y cumplimiento.

### Mitigación y Decisión Técnica
1. **Modo de Proyecto "Testing" en Google Cloud Console para el MVP**:
   - Google permite registrar la app en estado `Testing` y autorizar hasta **100 usuarios de prueba específicos** mediante su dirección de correo.
   - En este modo no se requiere la verificación CASA de terceros, lo que permite operar el MVP con usuarios reales y hogares piloto de manera totalmente legal y segura.
2. **Consultas de Búsqueda de Alcance Mínimo**:
   - El sistema **nunca** lee el buzón completo ni correos personales ajenos. La API ejecuta exclusivamente consultas de filtrado por remitente oficial de tickets:
     ```
     from:(tickets@mercadona.es OR no-reply@mercadona.es OR factura@mercadona.es) has:attachment filename:pdf
     ```
3. **Mecanismo de Desconexión y Revocación Activa**:
   - Al desconectar una cuenta de Google desde la aplicación, el backend no solo borra el registro local, sino que realiza una llamada HTTP al endpoint de revocación de tokens de Google OAuth (`https://oauth2.googleapis.com/revoke`), invalidando inmediatamente el `refresh_token` en los servidores de Google.
4. **Vía Alternativa: Subida Manual de Tickets (Fallback Nativo)**:
   - Para usuarios que no deseen otorgar permisos de Gmail o mientras configuran su cuenta de Google, el sistema provee un endpoint y una zona de arrastrar y soltar (Drag & Drop) en el frontend para subir directamente los archivos PDF de los tickets, ejecutando exactamente el mismo pipeline de extracción y validación.

---

## 2. Riesgo 2: Variabilidad en el Formato de los Tickets (Impacto: ALTO)

### Descripción del Riesgo
Asumir un único formato rígido de ticket provocaría fallos silenciosos si Mercadona actualiza el diseño de sus facturas simplificadas, o si introduce conceptos inhabituales (productos vendidos al corte, promociones, cupones de descuento, devoluciones o tickets de varias páginas).

### Mitigación y Decisión Técnica
1. **Extracción Basada en Reglas Gramaticales Flexibles**:
   - Se utiliza una máquina de estados determinista probada contra casos reales que distingue explícitamente:
     - Líneas simples de 1 unidad (`1 DESCRIPCION TOTAL`).
     - Líneas con precio unitario explícito (`N DESCRIPCION P_UNIT TOTAL`).
     - Líneas de peso/granel en dos renglones (`1 DESCRIPCION` seguido de `PESO kg PRECIO_KG €/kg TOTAL`).
     - Líneas no facturables o servicios (`1 PARKING 0,00`).
     - Descuentos (`-X,XX €`).
2. **Validación Contable y Estados de Ticket**:
   - Cada ticket calcula la suma de sus líneas y la compara con el `TOTAL (€)` del ticket y con la suma de la tabla de IVA (`Base + Cuota`).
   - Si la suma no cuadra con un margen de tolerancia de $\pm 0.01$ €, el ticket **no se descarta**: se persiste con estado `REVISION_NEEDED` y se registran advertencias detalladas (`extraction_warnings`), permitiendo su corrección manual asistida desde la interfaz.
3. **Preservación del Texto Original (`raw_text`)**:
   - El texto extraído del PDF se almacena íntegramente en la columna `receipts.raw_text`. Esto permite re-ejecutar extractores mejorados en el futuro sin necesidad de volver a solicitar o descargar los archivos originales.

---

## 3. Riesgo 3: Permisos por Casa y Aislamiento de Datos Multi-Tenant (Impacto: ALTO)

### Descripción del Riesgo
Una fuga de información entre diferentes hogares (por ejemplo, que un usuario de la Casa A pueda ver compras o estadísticas de la Casa B mediante manipulación de parámetros de la API) comprometería la privacidad y seguridad del sistema.

### Mitigación y Decisión Técnica
1. **Autorización en el Servidor en Cada Operación (Zero Trust en el Cliente)**:
   - Ocultar botones en la interfaz gráfica es puramente decorativo. Toda consulta de lectura, creación, modificación o eliminación en FastAPI inyecta una dependencia de autorización (`get_current_active_membership`):
     ```python
     @router.get("/receipts")
     async def list_receipts(
         household_id: UUID,
         membership: HouseholdMembership = Depends(require_permission(Permission.VIEW_RECEIPTS)),
         db: AsyncSession = Depends(get_db)
     ):
         # La consulta SQL fuerza estrictamente: WHERE household_id = :household_id
     ```
2. **Aislamiento a Nivel de Repositorio**:
   - Todas las consultas relacionales y agregaciones del Dashboard incluyen obligatoriamente el predicado `WHERE receipts.household_id = :current_household_id`.
3. **Separación de Roles**:
   - Solo `OWNER` y `ADMIN` pueden modificar miembros, invitaciones o eliminar tickets. Los miembros estándar (`MEMBER`) tienen permisos de lectura y subida.

---

## 4. Riesgo 4: Duplicados entre Cuentas y Re-sincronizaciones (Impacto: MEDIO-ALTO)

### Descripción del Riesgo
Dos usuarios de una misma casa pueden recibir en sus respectivos buzones de correo el mismo ticket digital de una compra conjunta. Además, al ejecutar sincronizaciones históricas periódicas, un mismo ticket se encontrará repetidamente.

### Mitigación y Decisión Técnica
1. **Huella Digital Criptográfica Unívoca (Fingerprint Hash)**:
   - Se genera un hash SHA-256 compuesto por:
     $$\text{Fingerprint} = \text{SHA256}(\text{company\_cif} + \text{"\_"} + \text{invoice\_number} + \text{"\_"} + \text{purchase\_datetime} + \text{"\_"} + \text{total\_amount})$$
   - La tabla `receipts` impone una restricción `UNIQUE (deduplication_hash)`.
2. **Manejo Idempotente en el Worker**:
   - Al encontrar un hash ya registrado en la base de datos, el worker de Celery incrementa el contador de `receipts_skipped` y no genera error ni aborta el lote.
3. **Detección de Colisiones entre Casas Distintas**:
   - Si dos usuarios de casas diferentes importan exactamente el mismo ticket (por ejemplo, personas que comparten un ticket para justificar gastos), el sistema permite vincular el ticket existente o registrar una advertencia de auditoría para resolver la ambigüedad.

---

## 5. Riesgo 5: Fiabilidad de las Estadísticas y Preservación de Correcciones (Impacto: MEDIO)

### Descripción del Riesgo
Si un usuario edita manualmente el nombre de un producto, su categoría o el precio de una línea que fue mal extraída, una sincronización posterior del correo podría sobrescribir y destruir sus correcciones manuales.
Asimismo, calcular precios por kilogramo cuando falta información de peso falsearía los gráficos de inflación.

### Mitigación y Decisión Técnica
1. **Regla de Inmunidad frente a Re-sincronizaciones (`is_manual_override`)**:
   - Tanto la cabecera del ticket (`receipts`) como cada una de sus líneas (`receipt_lines`) incorporan el flag booleano `is_manual_override`.
   - Si una tarea de Celery vuelve a procesar el origen del ticket, respeta y conserva todos los campos marcados con `is_manual_override = True`.
2. **Inmutabilidad de las Observaciones de Precios (`price_observations`)**:
   - Una compra nueva agrega una fila histórica con su marca de tiempo; jamás sobrescribe observaciones pasadas.
   - Si no se dispone del peso en kilogramos, `price_per_kg_or_l` se guarda como `NULL`, evitando inventar métricas unitarias erróneas.
3. **Tipos Numéricos Exactos (`NUMERIC`)**:
   - En ningún caso se utiliza `FLOAT` ni `REAL` para importes monetarios. Se utiliza estrictamente `NUMERIC(10, 2)` para euros y céntimos, y `NUMERIC(10, 3)` para pesos en kilogramos.

---

## 6. Riesgo 6: Seguridad de Secretos y Tokens OAuth (Impacto: ALTO)

### Descripción del Riesgo
El almacenamiento de `refresh_token` de cuentas de Google de usuarios en la base de datos representa un vector de alto riesgo si se guardase en texto plano.

### Mitigación y Decisión Técnica
1. **Cifrado Simétrico Autenticado en Reposo**:
   - Los tokens de Google se cifran mediante **AES-256-GCM** (usando `cryptography.fernet` o primitivas autenticadas) antes de almacenarse en la columna `google_account_connections.encrypted_tokens`.
   - La clave de cifrado maestro (`ENCRYPTION_MASTER_KEY`) se inyecta por variable de entorno y nunca se incluye en el repositorio.
2. **Zero-Log Policy para Datos Sensibles**:
   - Se configuran formateadores de logging en Python para suprimir cabeceras `Authorization`, payloads de tokens y datos personales de los logs de la aplicación y de Celery.
3. **Eliminación Conforme a RGPD**:
   - Si un usuario solicita la baja de su cuenta, se eliminan sus credenciales cifradas y sesiones, y se ofrece la anonimización de tickets históricos para no romper el balance contable de los otros miembros de su hogar.

