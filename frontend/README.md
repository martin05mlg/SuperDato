# SuperDato — Frontend SPA 🛒📊

Aplicación de interfaz de usuario (Single Page Application) de **SuperDato**, construida con **React 19**, **TypeScript**, **Vite** y **Tailwind CSS**.

---

## 🎨 Características Principales

- **Dashboard Contable & Analítica**:
  - Selector temporal flexible con presets (`Histórico`, `30 Días`, `Este Mes`, `Mes Anterior`, `Este Año`) y **selector interactivo por calendario** (`Desde` / `Hasta`).
  - Tarjetas de KPIs numéricos: Gasto acumulado, Variación MoM comparada con periodos equivalentes, Ticket medio, Mediana contable y Última Compra con fecha y hora exacta.
  - Gráficas interactivas con **Recharts**: Evolución temporal de gasto y distribución porcentual por categorías oficiales.
  - Tabla de Top 5 productos más comprados y listado de compras recientes.
- **Auditoría y Detalle de Tickets**:
  - Modal de detalle rápido con desglose completo de líneas unitarias y de peso.
  - Tabla fiscal de IVA conciliada (4%, 10%, 21%).
  - Edición en caliente de descripciones, unidades e importes con persistencia protegida (`is_manual_override`).
  - Subida manual de PDFs vía arrastrar y soltar (Drag & Drop).
- **Catálogo & Precios**:
  - Listado de productos clasificados por categorías oficiales de Mercadona con códigos cromáticos.
  - Histórico de precios inmutables por tienda y fecha con gráficos de tendencia.
- **Sincronización & Ajustes**:
  - Conexión OAuth 2.0 con Google Gmail para importación automática desatendida.
  - Monitor de trabajos de importación en segundo plano.
  - Gestión multi-hogar y selector de casa activa.

---

## 🛠️ Pila Tecnológica

| Biblioteca / Herramienta | Versión | Propósito |
| :--- | :--- | :--- |
| **React** | 19.x | Interfaz reactiva basada en componentes funcionales y hooks modernos. |
| **TypeScript** | 5.x | Tipado estricto extremo alineado con los esquemas Pydantic del backend. |
| **Vite** | 6.x | Servidor de desarrollo con Hot Module Replacement (HMR) y empaquetador de producción. |
| **Tailwind CSS** | 3.x | Sistema de diseño utilitario para layouts limpios y responsivos. |
| **TanStack Query** | 5.x | Gestión de estado asíncrono, caché, reintentos e invalidación de consultas. |
| **Recharts** | 3.x | Visualización declarativa e interactiva de gráficos estadísticos. |
| **Lucide Icons** | 1.x | Colección coherente de iconos vectoriales SVG. |

---

## 🚀 Comandos de Desarrollo

```bash
# Instalar dependencias
npm install

# Iniciar servidor de desarrollo en http://localhost:5173
npm run dev

# Verificación de tipos TypeScript y compilación de producción
npm run build

# Previsualizar build de producción
npm run preview
```

---

## 📂 Estructura de Directorios

```
frontend/
├── public/
│   ├── favicon.svg          # Logotipo oficial SuperDato en SVG
│   └── icons.svg
├── src/
│   ├── api/                 # Clientes Axios y endpoints del backend
│   │   ├── client.ts        # Instancia Axios con interceptores y base URL
│   │   └── receipts.api.ts  # Endpoints de tickets, catálogo y analítica
│   ├── components/          # Componentes reutilizables
│   │   ├── layout/          # Navbar, Sidebar y AppLayout
│   │   └── receipts/        # ReceiptDetailModal, ReceiptUploadModal
│   ├── context/             # React Contexts (AuthContext, HouseholdContext)
│   ├── pages/               # Páginas principales
│   │   ├── dashboard/       # DashboardPage.tsx
│   │   ├── receipts/        # ReceiptsListPage.tsx
│   │   ├── products/        # ProductsPage.tsx
│   │   ├── imports/         # ImportsPage.tsx
│   │   └── settings/        # SettingsPage.tsx
│   ├── types/               # Definiciones TypeScript de modelos y esquemas
│   ├── App.tsx              # Configuración de React Router y Providers
│   ├── index.css            # Configuración Tailwind CSS
│   └── main.tsx             # Punto de entrada de la aplicación
├── index.html               # Plantilla HTML con título e icono oficiales
├── package.json
├── tailwind.config.js
└── vite.config.ts
```
