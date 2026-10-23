# SuperDato — 10. Nuevas Funcionalidades Avanzadas

Este documento consolida la especificación técnica, arquitectura, modelos de datos y operativa de usuario de la nueva suite de características incorporadas a **SuperDato**:

1. **Entrada Manual de Tickets con Asistente Contable**.
2. **Exportación de Datos a Excel (CSV España) y Copia JSON**.
3. **Aplicación Web Progresiva (PWA Instalable)**.
4. **Presupuesto Mensual del Hogar con Proyección Financiera**.
5. **Detección de Inflación y Alertas de Subida de Precios en Tickets**.
6. **Métricas de Hábitos: Cuota de Marcas Propias (*Hacendado*) vs Fabricante**.
7. **Lista de la Compra Inteligente & Modo Supermercado Táctil**.

---

## 1. Entrada Manual de Tickets (Wizard Contable)

### Motivación y Casos de Uso
Permite registrar compras físicas cuando el usuario paga en efectivo, no facilitó el correo electrónico en caja, o conserva tickets de papel antiguos, preservando la trazabilidad de la cesta familiar y las observaciones de precios.

### Arquitectura Técnica
- **Endpoint**: `POST /api/v1/receipts/manual`
- **Contrato de Datos (`ManualReceiptCreate`)**:
  - `household_id`: Identificador del hogar propietario.
  - `purchase_datetime`: Fecha y hora de compra (ISO 8601).
  - `invoice_number`: Código manual opcional (generado automáticamente como `MANUAL-YYYYMMDD-XXXXXX` si se omite).
  - `store_address`, `store_city`, `store_postal_code`: Metadatos de la tienda.
  - `payment_method`: `TARJETA`, `EFECTIVO`, `BIZUM`.
  - `lines`: Lista de `ManualReceiptLineCreate` con `raw_description`, `product_id`, `quantity`, `unit_of_measure`, `unit_price`, `discount_amount`, `tax_rate_percent`, `is_weighed_item`.

### Lógica de Negocio y Persistencia
1. **Normalización y Enriquecimiento Automático**:
   Para cada artículo, `CatalogService.get_or_create_product_for_line` normaliza la descripción y reutiliza o crea el producto canónico global y sus alias verificados.
2. **Conciliación Contable de Impuestos**:
   Agrupa en tiempo real las líneas según su tipo impositivo en España:
   - **4% Superreducido**: Pan, leche, huevos, frutas y verduras.
   - **10% Reducido**: Carnes, pescados, aguas y derivados.
   - **21% General**: Limpieza, droguería, perfumería y bolsas.
   Calcula la base imponible y cuota tributaria (`ReceiptTaxLine`) asegurando que $\text{Base} + \text{Cuota} = \text{Total Línea}$.
3. **Inmutabilidad de Precios**:
   Registra una fila en `price_observations` vinculada al hogar y producto para alimentar el histórico de inflación y gráficos de evolución.

### Interfaz de Usuario
Componente modal [`ManualReceiptModal.tsx`](file:///z:/Martin/Proyectos/5.SuperDato-MercadonaTicketTracker/frontend/src/components/receipts/ManualReceiptModal.tsx) con buscador predictivo contra el catálogo de Mercadona, selector rápido de unidades/peso y panel contable con cálculo en directo.

---

## 2. Exportación de Datos a Excel y JSON

### Formatos Soportados
1. **Excel — Resumen de Tickets (`.csv`)**:
   - 1 fila por compra (Fecha, Hora, Nº Factura, Tienda, Ciudad, Método de Pago, Total en €, Descuentos).
2. **Excel — Detalle Completo de Artículos (`.csv`)**:
   - Desglose línea a línea de todos los productos (Fecha, Nº Factura, Tienda, Producto Canónico, Texto del Ticket, Categoría, Marca, Cantidad, Unidad, Al Peso, Precio Unitario, Descuento y Total).
3. **Copia de Seguridad JSON (`.json`)**:
   - Estructura anidada completa de tickets, líneas fiscales y artículos para almacenamiento o migración.

### Compatibilidad con Excel en España
Implementado en [`frontend/src/utils/export.ts`](file:///z:/Martin/Proyectos/5.SuperDato-MercadonaTicketTracker/frontend/src/utils/export.ts):
- Delimitador de campos por punto y coma (`;`).
- Separador decimal por coma (`,`).
- Prefijo Byte Order Mark UTF-8 (`\uFEFF`) para que Microsoft Excel lo abra directamente con tildes y caracteres especiales sin requerir el asistente de importación de texto.

---

## 3. PWA Instalable (Progressive Web App)

- **Manifiesto Web (`manifest.webmanifest`)**: Define nombre, descripción, colores de tema (`#059669`), modo `standalone` e iconos adaptables (*maskable*).
- **Service Worker (`public/sw.js`)**: Maneja el ciclo de vida de instalación y la caché del shell de la aplicación.
- **Soporte Móvil Nativo**: Metaetiquetas en `index.html` para iOS (*Apple Mobile Web App Capable*) y Android, permitiendo que la web se instale como una aplicación independiente sin barra de navegación del explorador.

---

## 4. Presupuesto Mensual Familiar y Proyección

### Modelo y Configuración
- Configurable por los roles `OWNER` y `ADMIN` desde [`SettingsPage.tsx`](file:///z:/Martin/Proyectos/5.SuperDato-MercadonaTicketTracker/frontend/src/pages/settings/SettingsPage.tsx).
- Persistido de forma no intrusiva en `households.settings["monthly_budget"]`.

### Algoritmo de Telemetría y Proyección
Calculado en `AnalyticsService.get_summary`:
1. **Gasto Acumulado del Mes en Curso**: Sumatorio de tickets asignados al hogar desde el primer día del mes actual hasta la fecha.
2. **Porcentaje de Consumo**: $\frac{\text{Gasto Acumulado}}{\text{Presupuesto}} \times 100$.
3. **Proyección Lineal a Fin de Mes**:
   $$\text{Proyección} = \frac{\text{Gasto Actual}}{\text{Día Actual del Mes}} \times \text{Días Totales del Mes}$$
4. **Saldo Restante y Presupuesto Diario**: Dinero disponible dividido entre los días que faltan para concluir el mes.

### Visualización en Dashboard
Widget interactivo con velocímetro / barra de progreso cromática (verde `<80%`, ámbar `80-100%`, roja en sobrecoste) y estimación comparativa.

---

## 5. Detección de Inflación y Alertas de Precios en Tickets

### Funcionamiento
Cada vez que se consulta el detalle de un ticket (`GET /api/v1/receipts/{id}`):
1. El backend busca la última `PriceObservation` previa para ese mismo producto en el historial del hogar (`observed_at < receipt.purchase_datetime`).
2. Si existe un precio anterior, calcula la variación porcentual:
   $$\Delta \% = \frac{\text{Precio Actual} - \text{Precio Anterior}}{\text{Precio Anterior}} \times 100$$
3. Si el precio difiere en $\ge 0.01$ €, inyecta `price_change_pct` y `previous_unit_price` en la línea del ticket.

### Interfaz en [`ReceiptDetailModal.tsx`](file:///z:/Martin/Proyectos/5.SuperDato-MercadonaTicketTracker/frontend/src/components/receipts/ReceiptDetailModal.tsx)
- 🔴 `↑ +12.5%`: Distintivo rojo de subida de precio con tooltip indicando el precio anterior registrado (ej: *Antes: 1.20 € (+0.15 €)*).
- 🟢 `↓ -6.2%`: Distintivo verde de bajada de precio.

---

## 6. Cuota de Marcas Propias (*Hacendado*) en Hábitos

### Clasificación Automática
En `AnalyticsService.get_habits`, los artículos se clasifican en:
- **Marcas Propias de Mercadona**: Detección de marcas registradas (*Hacendado, Bosque Verde, Deliplus, Compy, May*) mediante metadatos enriquecidos y análisis léxico.
- **Marcas de Fabricante**: Primeras marcas externas (Danone, Coca-Cola, Campofrío, etc.).

### Tarjeta en Dashboard
Nueva tarjeta analítica en el bloque de **Hábitos de Compra** que presenta el porcentaje de gasto en marca blanca frente a marcas líderes y el recuento total de artículos.

---

## 7. Lista de la Compra Inteligente & Modo Supermercado

### Nuevo Dominio Backend (`backend/app/domains/shopping/`)
- **Entidad `ShoppingListItem`**: Artículos de la lista con referencia opcional a `products.id`, cantidad, unidad, notas, estado de tachado (`is_checked`) y precio estimado.
- **Endpoints REST**:
  - `GET /api/v1/shopping/items`: Lista activa con subtotales estimados (€) en vivo.
  - `POST /api/v1/shopping/items`: Añadir artículo (resuelve automáticamente productos del catálogo).
  - `PATCH /api/v1/shopping/items/{id}`: Actualizar cantidad, notas o estado de tachado.
  - `DELETE /api/v1/shopping/items/{id}`: Eliminar artículo.
  - `POST /api/v1/shopping/clear-checked`: Limpieza en bloque de los artículos ya comprados.
  - `GET /api/v1/shopping/suggestions`: Motor de sugerencias predictivas.

### Algoritmo de Sugerencia de Reposición ("Toca Reponer")
1. Analiza el histórico de compras del hogar para productos adquiridos $\ge 2$ veces.
2. Calcula la frecuencia media entre compras:
   $$\text{Frecuencia Media (días)} = \frac{\text{Fecha Última Compra} - \text{Fecha Primera Compra}}{\text{Nº Compras} - 1}$$
3. Si los días transcurridos desde la última compra alcanzan el $\ge 85\%$ del ciclo medio habitual y el producto no está ya en la lista, se recomienda automáticamente con su motivo:
   *"Sueles comprarlo cada ~12 días (hace 14 días de tu última compra)"*.

### Pantalla [`ShoppingListPage.tsx`](file:///z:/Martin/Proyectos/5.SuperDato-MercadonaTicketTracker/frontend/src/pages/shopping/ShoppingListPage.tsx) y Modo Supermercado
- **Estimador de Carrito en Directo**: Desglose simultáneo de coste total, importe de lo que ya has metido al carro y lo que queda por coger.
- **Agrupación por Pasillos**: Ordenación automática de los artículos según su categoría en Mercadona (Frutas y Verduras, Lácteos, Carnicería, Limpieza).
- **Modo Supermercado Táctil**: Vista de pantalla completa optimizada para smartphones con botones grandes para ir tachando cómodamente con un solo toque mientras recorres los pasillos de la tienda.

---

## 8. Verificación y Calidad de Código

- **Pruebas Automatizadas**: 29 pruebas ejecutadas y aprobadas en `pytest` (`backend/tests/domains/test_manual_receipts.py` y `test_shopping_list.py`).
- **TypeScript y Empaquetado**: `tsc -b && vite build` compila con 0 errores y genera los assets estáticos de producción.
- **Aislamiento Multi-Tenant**: Todas las consultas de lista de la compra, presupuesto y tickets manuales están protegidas por `verify_household_access` con prevención estricta de vulnerabilidades IDOR.

