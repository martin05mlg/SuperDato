"""
Genera tickets de ejemplo 100% SINTÉTICOS (sin datos personales) en `backend/samples/`.

Imitan el formato de texto de un ticket digital de Mercadona para poder probar el
extractor y poblar la demo (`AUTO_SEED_SAMPLES`). No requiere dependencias externas.

Uso (desde la carpeta backend):
    python scripts/generate_sample_receipts.py
"""
from __future__ import annotations

import os
from decimal import ROUND_HALF_UP, Decimal
from typing import List, Optional, Tuple

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples")

# (cantidad, descripción, precio unitario, IVA %, kg si es pesado, precio €/kg)
Item = Tuple[int, str, str, int, Optional[str], Optional[str]]

TICKETS = [
    {
        "file": "20260105 Ticket sintetico A.pdf",
        "street": "AV DE LA MUESTRA 10",
        "city": "28001 MADRID",
        "phone": "900000001",
        "date": "05/01/2026",
        "time": "11:20",
        "op": "1000001",
        "invoice": "9999-001-100001",
        "card": "0000",
        "items": [
            (1, "LECHE ENTERA EJEMPLO", "0,89", 4, None, None),
            (2, "PAN DE BARRA EJEMPLO", "0,45", 4, None, None),
            (1, "PIZZA DEMO QUESOS", "3,50", 10, None, None),
            (1, "YOGUR NATURAL PACK", "1,65", 10, None, None),
            (1, "ARROZ REDONDO 1KG", "1,20", 10, None, None),
            (1, "DETERGENTE LIQUIDO", "5,90", 21, None, None),
            (1, "PAPEL HIGIENICO 12U", "3,25", 21, None, None),
            (1, "MANZANA GOLDEN", None, 4, "0,820", "2,10"),
            (1, "TOMATE RAMA", None, 4, "0,515", "2,95"),
        ],
    },
    {
        "file": "20260112 Ticket sintetico B.pdf",
        "street": "CL DEL EJEMPLO 25",
        "city": "50001 ZARAGOZA",
        "phone": "900000002",
        "date": "12/01/2026",
        "time": "18:05",
        "op": "1000002",
        "invoice": "9999-002-100002",
        "card": "0000",
        "items": [
            (1, "AGUA MINERAL 6X1,5L", "2,10", 10, None, None),
            (3, "HUEVOS DEMO DOCENA", "1,95", 4, None, None),
            (1, "POLLO ENTERO LIMPIO", None, 10, "1,350", "3,40"),
            (1, "PLATANO DEMO", None, 4, "0,640", "1,99"),
            (1, "QUESO TIERNO CUNA", "4,80", 10, None, None),
            (1, "CAFE MOLIDO NATURAL", "2,75", 10, None, None),
            (1, "GEL DE DUCHA SUAVE", "1,95", 21, None, None),
            (2, "PASTA ESPAGUETI", "0,85", 10, None, None),
            (1, "ZANAHORIA 1 KG", "1,05", 4, None, None),
        ],
    },
]


def _eur(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'), ROUND_HALF_UP)}".replace(".", ",")


def _dec(s: str) -> Decimal:
    return Decimal(s.replace(",", "."))


def build_lines(t: dict) -> List[str]:
    lines = [
        "MERCADONA, S.A.   A-46103834",
        t["street"],
        t["city"],
        f"TELÉFONO: {t['phone']}",
        f"{t['date']} {t['time']}  OP: {t['op']}",
        f"FACTURA SIMPLIFICADA: {t['invoice']}",
        "Cnt. Descripción P. Unit Importe",
    ]
    totals_by_rate = {}
    grand_total = Decimal("0.00")
    for qty, desc, unit, rate, kg, per_kg in t["items"]:
        if kg:
            line_total = (_dec(kg) * _dec(per_kg)).quantize(Decimal("0.01"), ROUND_HALF_UP)
            lines.append(f"1 {desc}")
            lines.append(f"{kg} kg {per_kg} €/kg {_eur(line_total)}")
        elif qty == 1:
            line_total = _dec(unit)
            lines.append(f"1 {desc} {_eur(line_total)}")
        else:
            line_total = (_dec(unit) * qty).quantize(Decimal("0.01"))
            lines.append(f"{qty} {desc} {unit} {_eur(line_total)}")
        totals_by_rate[rate] = totals_by_rate.get(rate, Decimal("0.00")) + line_total
        grand_total += line_total

    lines.append(f"TOTAL (€) {_eur(grand_total)}")
    lines.append(f"TARJETA BANCARIA {_eur(grand_total)}")
    lines.append("IVA BASE IMP. (€) CUOTA (€) TOTAL (€)")
    sum_base = sum_tax = Decimal("0.00")
    for rate in sorted(totals_by_rate):
        gross = totals_by_rate[rate]
        base = (gross / (Decimal(100 + rate) / 100)).quantize(Decimal("0.01"), ROUND_HALF_UP)
        tax = gross - base
        sum_base += base
        sum_tax += tax
        lines.append(f"{rate}% {_eur(base)} {_eur(tax)} {_eur(gross)}")
    lines.append(f"TOTAL {_eur(sum_base)} {_eur(sum_tax)} {_eur(grand_total)}")
    lines.append(f"TARJ. BANCARIA:  **** **** **** {t['card']}")
    lines.append("AUT: 000000 ARC: 00 AID: A0000000000000")
    lines.append("Verificado por dispositivo")
    lines.append(f"Importe: {_eur(grand_total)} € Visa")
    lines.append("TICKET SINTETICO DE EJEMPLO - SIN VALOR")
    return lines


def _escape(text: str) -> bytes:
    raw = text.encode("cp1252", errors="replace")
    return raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def render_pdf(lines: List[str]) -> bytes:
    """PDF mínimo de una página con fuente Courier (WinAnsi) sin dependencias."""
    content = [b"BT", b"/F1 9 Tf", b"11 TL", b"30 800 Td"]
    for line in lines:
        content.append(b"(" + _escape(line) + b") Tj T*")
    content.append(b"ET")
    stream = b"\n".join(content)

    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 842] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n".encode() + b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    for t in TICKETS:
        path = os.path.join(OUT_DIR, t["file"])
        with open(path, "wb") as f:
            f.write(render_pdf(build_lines(t)))
        print(f"Generado: {path}")


if __name__ == "__main__":
    main()

