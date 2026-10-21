"""
SuperDato - Script de demostración interactiva de extracción de tickets reales de Mercadona
"""
import glob
import re
import sys
from decimal import Decimal
import pypdf

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def parse_mercadona_ticket(pdf_path: str):
    print("\n" + "=" * 70)
    print(f"📄 PROCESANDO ARCHIVO: {pdf_path}")
    print("=" * 70)

    reader = pypdf.PdfReader(pdf_path)
    text = reader.pages[0].extract_text()

    # 1. Cabecera
    invoice_match = re.search(r"FACTURA SIMPLIFICADA:\s*([0-9\-]+)", text)
    date_match = re.search(r"(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})\s+OP:\s*(\d+)", text)
    total_match = re.search(r"TOTAL\s*\([€\?]\)\s*([\d,]+)", text)

    invoice_number = invoice_match.group(1) if invoice_match else "No encontrado"
    date_str = date_match.group(1) if date_match else "No encontrada"
    time_str = date_match.group(2) if date_match else "No encontrada"
    total_str = total_match.group(1).replace(",", ".") if total_match else "0.00"

    print(f"🏢 Establecimiento : MERCADONA, S.A. (A-46103834)")
    print(f"🧾 Factura Simplif.: {invoice_number}")
    print(f"📅 Fecha y Hora    : {date_str} a las {time_str}")
    print(f"💰 Importe Total   : {Decimal(total_str):.2f} €")
    print("-" * 70)

    # 2. Líneas de artículos
    lines_text = text.splitlines()
    in_items = False
    items = []
    
    i = 0
    while i < len(lines_text):
        line = lines_text[i].strip()
        
        if "Cnt. Descripción P. Unit Importe" in line or "Cnt. Descripci" in line:
            in_items = True
            i += 1
            continue
            
        if "TOTAL (" in line or "TOTAL 4" in line or "TOTAL 3" in line:
            in_items = False
            break

        if in_items and line:
            # Caso 1: Línea al peso (siguiente línea contiene 'kg')
            if i + 1 < len(lines_text) and "kg" in lines_text[i+1]:
                weight_line = lines_text[i+1].strip()
                # Ejemplo: 0,390 kg 3,00 €/kg 1,17
                w_match = re.search(r"([\d,]+)\s*kg\s+([\d,]+)\s*[€\?]/kg\s+([\d,]+)", weight_line)
                name_match = re.search(r"^\d+\s+(.+)$", line)
                item_name = name_match.group(1).strip() if name_match else line
                
                if w_match:
                    weight = Decimal(w_match.group(1).replace(",", "."))
                    price_kg = Decimal(w_match.group(2).replace(",", "."))
                    total = Decimal(w_match.group(3).replace(",", "."))
                    items.append({
                        "name": item_name,
                        "qty": f"{weight:.3f} kg",
                        "unit_price": f"{price_kg:.2f} €/kg",
                        "total": total,
                        "tipo": "AL PESO"
                    })
                i += 2
                continue
                
            # Caso 2: Parking / Especial
            if "PARKING" in line:
                items.append({
                    "name": "PARKING",
                    "qty": "1 ud",
                    "unit_price": "0.00 €",
                    "total": Decimal("0.00"),
                    "tipo": "SERVICIO"
                })
                i += 1
                if i < len(lines_text) and "ENTRADA" in lines_text[i]:
                    i += 1
                continue

            # Caso 3: Múltiples unidades estándar (Ej: 2 DEO ROLL-ON ALOE 0,90 1,80)
            multi_match = re.search(r"^(\d+)\s+(.+?)\s+([\d,]+)\s+([\d,]+)$", line)
            if multi_match:
                qty = int(multi_match.group(1))
                name = multi_match.group(2).strip()
                unit_p = Decimal(multi_match.group(3).replace(",", "."))
                total = Decimal(multi_match.group(4).replace(",", "."))
                items.append({
                    "name": name,
                    "qty": f"{qty} ud",
                    "unit_price": f"{unit_p:.2f} €",
                    "total": total,
                    "tipo": "ESTÁNDAR"
                })
                i += 1
                continue

            # Caso 4: Una sola unidad estándar (Ej: 1 PIPA GIGANTE AGUASAL 1,10)
            single_match = re.search(r"^1\s+(.+?)\s+([\d,]+)$", line)
            if single_match:
                name = single_match.group(1).strip()
                total = Decimal(single_match.group(2).replace(",", "."))
                items.append({
                    "name": name,
                    "qty": "1 ud",
                    "unit_price": f"{total:.2f} €",
                    "total": total,
                    "tipo": "ESTÁNDAR"
                })
                i += 1
                continue

        i += 1

    print(f"{'CANTIDAD':<12} | {'TIPO':<10} | {'ARTÍCULO':<28} | {'PRECIO':<12} | {'TOTAL'}")
    print("-" * 70)
    calculated_sum = Decimal("0.00")
    for item in items:
        calculated_sum += item['total']
        print(f"{item['qty']:<12} | {item['tipo']:<10} | {item['name']:<28} | {item['unit_price']:<12} | {item['total']:.2f} €")
    
    print("-" * 70)
    print(f"Suma calculada de líneas : {calculated_sum:.2f} €")
    print(f"Total oficial del ticket : {Decimal(total_str):.2f} €")
    diff = abs(calculated_sum - Decimal(total_str))
    if diff == Decimal("0.00"):
        print("✅ CONCILIACIÓN CONTABLE EXACTA (Diferencia = 0.00 €)")
    else:
        print(f"⚠️ DISCREPANCIA DETECTADA: {diff:.2f} €")

if __name__ == "__main__":
    for pdf in glob.glob("samples/*.pdf"):
        parse_mercadona_ticket(pdf)
