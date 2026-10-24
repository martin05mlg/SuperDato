/**
 * Export utilities for SuperDato
 * Supports Excel-compatible CSV (Spanish format: ';' delimiter, ',' decimal, UTF-8 BOM) and JSON.
 */
import type { Receipt } from '../types';

export function downloadFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function exportReceiptsSummaryCsv(receipts: Receipt[], householdName: string) {
  const BOM = '\uFEFF';
  const headers = [
    'Fecha',
    'Hora',
    'Nº Factura',
    'Tienda',
    'Ciudad',
    'Código Postal',
    'Método de Pago',
    'Nº Artículos',
    'Total (€)',
    'Descuentos (€)',
    'Estado',
  ];

  const rows = receipts.map((r) => [
    r.purchase_date,
    r.purchase_datetime ? r.purchase_datetime.substring(11, 16) : '',
    `"${r.invoice_number.replace(/"/g, '""')}"`,
    `"${(r.store_address || '').replace(/"/g, '""')}"`,
    `"${(r.store_city || '').replace(/"/g, '""')}"`,
    `"${(r.store_postal_code || '').replace(/"/g, '""')}"`,
    `"${(r.payment_method || '').replace(/"/g, '""')}"`,
    r.lines_count || (r.lines ? r.lines.length : 0),
    r.total_amount.toFixed(2).replace('.', ','),
    (0).toFixed(2).replace('.', ','),
    r.status,
  ]);

  const csvContent =
    BOM +
    headers.join(';') +
    '\n' +
    rows.map((row) => row.join(';')).join('\n');

  const cleanName = householdName.toLowerCase().replace(/[^a-z0-9]/g, '_');
  const dateStr = new Date().toISOString().split('T')[0];
  downloadFile(
    csvContent,
    `superdato_${cleanName}_tickets_resumen_${dateStr}.csv`,
    'text/csv;charset=utf-8;'
  );
}

export function exportFullReceiptLinesCsv(receipts: Receipt[], householdName: string) {
  const BOM = '\uFEFF';
  const headers = [
    'Fecha Compra',
    'Nº Factura',
    'Tienda',
    'Ciudad',
    'Nº Línea',
    'Producto',
    'Texto en Ticket',
    'Categoría',
    'Marca',
    'Cantidad',
    'Unidad',
    'Al Peso',
    'Precio Unitario (€)',
    'Descuento (€)',
    'Total Línea (€)',
  ];

  const rows: string[][] = [];

  receipts.forEach((r) => {
    const lines = r.lines || [];
    lines.forEach((l, idx) => {
      rows.push([
        r.purchase_date,
        `"${r.invoice_number.replace(/"/g, '""')}"`,
        `"${(r.store_address || '').replace(/"/g, '""')}"`,
        `"${(r.store_city || '').replace(/"/g, '""')}"`,
        String(l.line_order || idx + 1),
        `"${(l.product_name || l.enriched_name || l.raw_description).replace(/"/g, '""')}"`,
        `"${l.raw_description.replace(/"/g, '""')}"`,
        `"${(l.category_name || 'Otros').replace(/"/g, '""')}"`,
        `"${(l.brand || '').replace(/"/g, '""')}"`,
        String(l.quantity).replace('.', ','),
        l.unit_of_measure,
        l.is_weighed_item ? 'SÍ' : 'NO',
        l.unit_price.toFixed(2).replace('.', ','),
        (l.discount_amount || 0).toFixed(2).replace('.', ','),
        l.line_total.toFixed(2).replace('.', ','),
      ]);
    });
  });

  const csvContent =
    BOM +
    headers.join(';') +
    '\n' +
    rows.map((row) => row.join(';')).join('\n');

  const cleanName = householdName.toLowerCase().replace(/[^a-z0-9]/g, '_');
  const dateStr = new Date().toISOString().split('T')[0];
  downloadFile(
    csvContent,
    `superdato_${cleanName}_articulos_detalle_${dateStr}.csv`,
    'text/csv;charset=utf-8;'
  );
}

export function exportReceiptsJson(receipts: Receipt[], householdName: string) {
  const cleanName = householdName.toLowerCase().replace(/[^a-z0-9]/g, '_');
  const dateStr = new Date().toISOString().split('T')[0];
  const jsonContent = JSON.stringify(receipts, null, 2);
  downloadFile(
    jsonContent,
    `superdato_${cleanName}_backup_${dateStr}.json`,
    'application/json;charset=utf-8;'
  );
}

