# Mejoras Analíticas del Dashboard y Telemetría de Hábitos

Este documento describe la especificación de las mejoras aplicadas a la página principal ([Dashboard](file:///Z:/Martin/Proyectos/5.SuperDato-MercadonaTicketTracker/frontend/src/pages/dashboard/DashboardPage.tsx)) para aportar claridad contable, enriquecimiento interactivo y nuevas estadísticas de hábitos de compra.

---

## 1. Claridad en la Comparativa de Gasto Acumulado

### Problema anterior
Bajo la cifra de "Gasto Acumulado" se mostraba un porcentaje y una etiqueta genérica (`vs periodo anterior`), que cuando se visualizaba el histórico completo (ej. 993.70 €) comparaba erróneamente con el mes anterior sin contexto, generando confusión.

### Solución implementada
1. **En vista Histórica (ALL)**:
   - Se muestra la estimación de media mensual real:
     `Media estimada: 62.11 €/mes (16 meses activos)`
2. **En vista por Periodos (30D, Este Mes, Mes Anterior, Personalizado)**:
   - Se calcula el periodo equivalente previo exacto.
   - La etiqueta desglosa el rango y el importe anterior:
     `+15.2% vs. periodo anterior (01/09 - 30/09: 82.09 €)`
3. **Barra de datos clave destacados**:
   - **Ticket Récord**: 115.35 € | **Mínimo**: 2.12 €
   - **Frecuencia Media**: 1 compra cada ~24.7 días
   - **Día preferido**: Viernes
   - **IVA total aportado**: 87.97 €

---

## 2. Tooltip Interactivo en la Rueda de Distribución

### Problema anterior
Al posar el ratón sobre cualquier porción del gráfico circular de categorías (donut), Recharts únicamente mostraba `Gasto: 161.28 €`, sin indicar el nombre de la sección.

### Solución implementada
Se ha desarrollado el componente personalizado `CustomCategoryTooltip` que presenta en una tarjeta emergente elegante:
- **Punto de color y Nombre de la Categoría** (ej. 🔴 *Carnicería y Charcutería*)
- **Gasto monetario total en euros** (ej. *161.28 €*)
- **Cuota de la cesta en porcentaje** (ej. *16.2%*)
- **Total de artículos adquiridos** (ej. *50 ud*)

---

## 3. Ordenación Dual de Top Productos (Gasto vs Frecuencia)

### Problema anterior
El ranking de productos estaba fijado únicamente por importe total de gasto, impidiendo conocer qué productos básicos se compran más a menudo.

### Solución implementada
Selector de pestañas integrado en la cabecera del widget:
1. **Por Dinero (€)**:
   - Prioriza los productos de mayor desembolso acumulado (ej. *Reserva Lonchas, Pechuga de Pavo, Atún en Aceite de Oliva*).
2. **Por Nº Compras**:
   - Prioriza los productos indispensables de mayor recurrencia ticket a ticket (ej. *Bolsa de Plástico, Mozzarella Fresca, Parking, Plátanos, Barra de Pan*).
   - Muestra tanto el número de tickets en los que apareció como las unidades/kg totales.

---

## 4. Nuevo Bloque: Hábitos de Compra y Desglose Fiscal

Disponible en el endpoint `GET /api/v1/analytics/habits`, incluye 3 tarjetas analíticas:

1. **Días de la Semana con Más Compra**:
   - Barras de progreso de Lunes a Domingo con importes y porcentajes.
   - Detección automática del día estrella (en los datos actuales, el **Viernes concentra el 50.2%** del gasto con 498.53 €).
2. **Supermercados Mercadona Frecuentados**:
   - Ranking de tiendas por número de visitas y gasto total.
   - Normalización de direcciones y ciudades (Zaragoza, Maó, Irún, Alfaro, La Almunia).
3. **Desglose de IVA en la Cesta**:
   - IVA 4% Superreducido (Pan, huevos, frutas, verduras, leche): Base imponible e impuesto recaudado.
   - IVA 10% Reducido (Carnes, pescados, derivados lácteos).
   - IVA 21% General (Limpieza, cuidado personal, bolsas).
   - Total IVA aportado al Estado.

