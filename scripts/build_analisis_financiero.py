#!/usr/bin/env python3
"""
build_analisis_financiero.py
-----------------------------------------------------------------
Regenera analisis_financiero_datos.js mergeando los archivos
mensuales que viven en Archivos_Anal.Fiinan/YYYY-MM/.

Por cada mes, parsea los archivos que estén presentes:

  facturacion.xlsx        BS Gestion: comprobantes emitidos
  gastos_excel.xlsx       Excel propio del user (3 secciones)
  gastos_bs.xlsx          BS Gestion: gastos (comisiones reales)
  extracto_galicia.xlsx   Home banking Galicia
  resumen_santander.pdf   Resumen Santander del mes
  cobranzas.txt|png|jpg   Total cobrado del mes
  saldos.txt|png|jpg      Saldos al cierre del mes

Lo que ya estaba cargado en el JS (meses anteriores) se preserva
intacto. Solo se sobrescribe el mes para el cual hay archivos.

Uso:
  python3 scripts/build_analisis_financiero.py

Lo dispara la GitHub Action cuando alguien sube archivos a
Archivos_Anal.Fiinan/. El JS resultante se commitea automatico.
"""

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARCHIVOS_DIR = ROOT / "Archivos_Anal.Fiinan"
JS_OUT = ROOT / "analisis_financiero_datos.js"

# Configuracion de proveedores/vendedores conocidos
VENDEDOR_PAPA = "Gordillo, Victor"
TIPOS_NC = {"NCA", "NCB", "NCC", "NCM", "NC"}

# Palabras clave para detectar tarjetas en extractos bancarios
TARJETA_PATTERNS = {
    "Tarjeta Galicia - VISA":    [r"galicia.*visa", r"visa.*galicia"],
    "Tarjeta Galicia + MASTER":  [r"galicia.*master", r"master.*galicia"],
    "Tarjeta Galicia + VISA":    [r"galicia.*visa.*\+"],
    "Tarjeta Galicia - BUSINESS":[r"galicia.*business"],
    "Tarjeta ICBC":              [r"icbc"],
    "Tarjeta Santander Rio - VISA": [r"santander.*visa", r"santanderrio.*visa"],
    "Tarjeta Santander Rio - AMEX": [r"santander.*amex", r"santanderrio.*amex", r"amex"],
}


# =====================================================================
# Helpers
# =====================================================================

def log(*args):
    print("[build]", *args, file=sys.stderr)


def s(v):
    if v is None:
        return ""
    return str(v).strip()


def num(v):
    if v is None:
        return 0
    if isinstance(v, (int, float)):
        return float(v)
    txt = str(v).replace(",", ".").replace("$", "").strip()
    try:
        return float(txt)
    except ValueError:
        return 0


def parse_date(v):
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(v, fmt)
            except ValueError:
                pass
    return None


def load_existing_js():
    if not JS_OUT.exists():
        return {
            "meses": [],
            "facturacion_por_mes": {},
            "gastos_por_mes": {},
            "volumen_por_mes": {},
            "gastos_lista": [],
            "fact_lista": [],
            "top_conceptos": {},
            "cobranzas_2026": {"total_cobrado": 0, "total_cobranzas": 0,
                               "por_mes": {}, "cobrado_papa_2026": 0,
                               "por_vendedor": []},
            "saldos_bancarios": [],
            "prestamos": [],
            "tarjetas_pagos": {},
            "problemas_tumini": {"monto": 0, "facturado_2026": 0},
        }
    txt = JS_OUT.read_text(encoding="utf-8")
    txt = txt.replace("window.DATOS = ", "").rstrip().rstrip(";")
    return json.loads(txt)


def write_js(data):
    payload = "window.DATOS = " + json.dumps(data, ensure_ascii=False) + ";\n"
    JS_OUT.write_text(payload, encoding="utf-8")


def remove_month_from_lista(lista, ano_mes):
    return [x for x in lista if x.get("AnoMes") != ano_mes]


# =====================================================================
# Parsers de archivos
# =====================================================================

def parse_facturacion_xlsx(path, ano_mes):
    """Parsea facturacion.xlsx exportado de BS Gestion.
    Devuelve: (resumen_mes, fact_entries, volumen)
    """
    try:
        import openpyxl
    except ImportError:
        log(f"  facturacion: openpyxl no disponible")
        return None
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
    except Exception as e:
        log(f"  facturacion: error abriendo {path.name}: {e}")
        return None

    # Detectar headers (busca primera fila con columnas tipicas)
    rows = list(ws.iter_rows(values_only=True))
    header_row = None
    for i, r in enumerate(rows[:10]):
        cells = [s(c).lower() for c in r]
        if any("fecha" in c for c in cells) and any("total" in c or "importe" in c for c in cells):
            header_row = i
            break
    if header_row is None:
        log(f"  facturacion: no encuentro headers en {path.name}")
        return None

    headers = [s(c).lower() for c in rows[header_row]]

    def find_col(*keywords):
        for i, h in enumerate(headers):
            if all(k in h for k in keywords):
                return i
        return None

    col_fecha = find_col("fecha")
    col_cliente = find_col("cliente") or find_col("razon")
    col_vendedor = find_col("vendedor")
    col_tipo = find_col("tipo")
    col_nro = find_col("numero") or find_col("nro") or find_col("comprobante")
    col_total = find_col("total") or find_col("importe")
    col_items = find_col("items") or find_col("cantidad")

    if col_fecha is None or col_total is None:
        log(f"  facturacion: faltan columnas Fecha o Total en {path.name}")
        return None

    fact_entries = []
    total_bruto = 0
    ventas_papa = 0
    notas_credito = 0
    neto_maxi = 0
    clientes = set()
    items_total = 0
    pedidos = 0

    for r in rows[header_row + 1:]:
        f = parse_date(r[col_fecha]) if col_fecha < len(r) else None
        if not f:
            continue
        if f.strftime("%Y-%m") != ano_mes:
            continue
        cliente = s(r[col_cliente]) if col_cliente is not None and col_cliente < len(r) else ""
        vendedor = s(r[col_vendedor]) if col_vendedor is not None and col_vendedor < len(r) else ""
        tipo = s(r[col_tipo]).upper() if col_tipo is not None and col_tipo < len(r) else ""
        nro = s(r[col_nro]) if col_nro is not None and col_nro < len(r) else ""
        total = num(r[col_total]) if col_total < len(r) else 0
        items = int(num(r[col_items])) if col_items is not None and col_items < len(r) else 0

        es_nc = any(t in tipo for t in TIPOS_NC)
        es_papa = vendedor == VENDEDOR_PAPA

        if es_nc:
            notas_credito += -abs(total) if total > 0 else total
        else:
            total_bruto += total
            if es_papa:
                ventas_papa += total
            else:
                neto_maxi += total

        fact_entries.append({
            "Fecha": f.strftime("%Y-%m-%d"),
            "Cliente": cliente,
            "Vendedor": vendedor,
            "Tipo": tipo,
            "NroComp": nro,
            "AnoMes": ano_mes,
            "Total": total,
            "Items": items,
        })

        if not es_nc:
            pedidos += 1
            clientes.add(cliente)
            items_total += items

    resumen = {
        "total_bruto": round(total_bruto, 2),
        "ventas_papa": round(ventas_papa, 2),
        "notas_credito": round(notas_credito, 2),
        "neto_maxi": round(total_bruto - ventas_papa + notas_credito, 2),
    }
    volumen = {
        "pedidos": pedidos,
        "items": items_total,
        "clientes_unicos": len(clientes),
        "monto_promedio_pedido": round(total_bruto / pedidos, 2) if pedidos else 0,
    }
    return resumen, fact_entries, volumen


def parse_gastos_excel_xlsx(path, ano_mes):
    """Parsea el Excel propio del user con las 3 secciones.
    Estructura conocida de 'Gastos Reales':
      cols 4-8:  Fecha | Concepto | Monto | Monto USD | Pague?  (Gastos Fijos)
      cols 10-13: Fecha | Proveedor | Facturado? | Importe       (Compras Mercadería)
      cols 15-18: Fecha | Concepto | Facturado? | Importe        (Otros Gastos)
    Devuelve: (resumen_categorias, gastos_lista, top_conceptos)
    """
    try:
        import openpyxl
    except ImportError:
        return None
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception as e:
        log(f"  gastos_excel: error abriendo: {e}")
        return None

    # Buscar la hoja: si solo tiene una hoja, usa esa; si tiene 'Gastos Reales' o similar, usa esa
    ws = None
    for name in wb.sheetnames:
        if "real" in name.lower() or "gasto" in name.lower():
            ws = wb[name]
            break
    if ws is None:
        ws = wb[wb.sheetnames[0]]

    fijos = mercaderia = varios = sueldos = 0
    lista = []
    conceptos_count = Counter()

    EXTRAS_GFIJOS_TAGS = {"prestamo", "préstamo", "alquiler", "tarjeta", "monotributo",
                          "autonomo", "autónomo", "iva", "iibb", "cargas sociales",
                          "seguro", "movistar", "personal flow", "contador"}

    for r in ws.iter_rows(min_row=3, values_only=True):
        if not r:
            continue

        # Sección 1: Gastos Fijos (cols 4-8)
        if len(r) > 6:
            f = parse_date(r[4])
            conc = s(r[5])
            monto = num(r[6])
            if f and f.strftime("%Y-%m") == ano_mes and conc and monto > 0:
                tipo = "Sueldos" if "sueldo" in conc.lower() else "GFijos"
                if tipo == "Sueldos":
                    sueldos += monto
                else:
                    fijos += monto
                lista.append({
                    "Fecha": f.strftime("%Y-%m-%d"),
                    "Concepto": conc, "Importe": monto,
                    "Tipo": tipo, "AnoMes": ano_mes,
                })
                conceptos_count[conc] += 1

        # Sección 2: Compras Mercadería (cols 10-13)
        if len(r) > 13:
            f = parse_date(r[10])
            prov = s(r[11])
            imp = num(r[13])
            if f and f.strftime("%Y-%m") == ano_mes and prov and imp > 0:
                mercaderia += imp
                lista.append({
                    "Fecha": f.strftime("%Y-%m-%d"),
                    "Concepto": prov, "Importe": imp,
                    "Tipo": "Mercaderia", "AnoMes": ano_mes,
                })

        # Sección 3: Otros Gastos (cols 15-18)
        if len(r) > 18:
            f = parse_date(r[15])
            conc = s(r[16])
            imp = num(r[18])
            if f and f.strftime("%Y-%m") == ano_mes and conc and imp > 0:
                varios += imp
                lista.append({
                    "Fecha": f.strftime("%Y-%m-%d"),
                    "Concepto": conc, "Importe": imp,
                    "Tipo": "GVarios", "AnoMes": ano_mes,
                })

    resumen = {
        "mercaderia": round(mercaderia, 2),
        "fijos": round(fijos, 2),
        "varios": round(varios, 2),
        "sueldos": round(sueldos, 2),
    }
    top = [{"concepto": c, "veces": n} for c, n in conceptos_count.most_common(10)]
    return resumen, lista, top


def parse_gastos_bs_xlsx(path, ano_mes):
    """BS Gestion gastos del mes -> comisiones_reales (sumadas)."""
    try:
        import openpyxl
    except ImportError:
        return 0
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
    except Exception as e:
        log(f"  gastos_bs: error abriendo: {e}")
        return 0

    rows = list(ws.iter_rows(values_only=True))
    header_row = None
    for i, r in enumerate(rows[:10]):
        cells = [s(c).lower() for c in r]
        if any("concepto" in c or "detalle" in c for c in cells) and \
           any("importe" in c or "total" in c for c in cells):
            header_row = i
            break
    if header_row is None:
        return 0

    headers = [s(c).lower() for c in rows[header_row]]
    col_fecha = next((i for i, h in enumerate(headers) if "fecha" in h), None)
    col_concepto = next((i for i, h in enumerate(headers)
                         if "concepto" in h or "detalle" in h or "descripcion" in h), None)
    col_importe = next((i for i, h in enumerate(headers)
                        if "importe" in h or "total" in h or "monto" in h), None)

    if col_fecha is None or col_concepto is None or col_importe is None:
        return 0

    total_comisiones = 0
    for r in rows[header_row + 1:]:
        f = parse_date(r[col_fecha]) if col_fecha < len(r) else None
        if not f or f.strftime("%Y-%m") != ano_mes:
            continue
        conc = s(r[col_concepto]).lower() if col_concepto < len(r) else ""
        if "comisión" in conc or "comision" in conc:
            total_comisiones += num(r[col_importe])

    return round(total_comisiones, 2)


def parse_extracto_galicia(path, ano_mes):
    """Detecta pagos de tarjetas en el extracto Galicia.
    Devuelve dict: {tarjeta_nombre: monto_total_mes}
    """
    try:
        import openpyxl
    except ImportError:
        return {}
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
    except Exception as e:
        log(f"  extracto_galicia: error: {e}")
        return {}

    rows = list(ws.iter_rows(values_only=True))
    header_row = None
    for i, r in enumerate(rows[:15]):
        cells = [s(c).lower() for c in r]
        if any("fecha" in c for c in cells):
            header_row = i
            break
    if header_row is None:
        return {}

    headers = [s(c).lower() for c in rows[header_row]]
    col_fecha = next((i for i, h in enumerate(headers) if "fecha" in h), None)
    col_concepto = next((i for i, h in enumerate(headers)
                         if "concepto" in h or "detalle" in h or "descripcion" in h), None)
    col_debe = next((i for i, h in enumerate(headers) if "debe" in h or "debito" in h), None)
    col_importe = next((i for i, h in enumerate(headers)
                        if "importe" in h or "monto" in h), None)

    if col_fecha is None or col_concepto is None:
        return {}

    pagos = defaultdict(float)
    for r in rows[header_row + 1:]:
        f = parse_date(r[col_fecha]) if col_fecha < len(r) else None
        if not f or f.strftime("%Y-%m") != ano_mes:
            continue
        conc = s(r[col_concepto]).lower() if col_concepto < len(r) else ""
        # importe: priorizar "debe" si existe, sino "importe"
        importe = 0
        if col_debe is not None and col_debe < len(r):
            importe = abs(num(r[col_debe]))
        if importe == 0 and col_importe is not None and col_importe < len(r):
            importe = abs(num(r[col_importe]))
        if importe <= 0:
            continue

        for tarjeta, patrones in TARJETA_PATTERNS.items():
            if "galicia" not in tarjeta.lower():
                continue
            for pat in patrones:
                if re.search(pat, conc, re.IGNORECASE):
                    pagos[tarjeta] += importe
                    break

    return {k: round(v, 2) for k, v in pagos.items()}


def parse_resumen_tarjeta_pdf(path, ano_mes, tarjeta_nombre):
    """Parsea un PDF de resumen de tarjeta. Extrae:
       - total: total a pagar del mes (busca lineas tipo "TOTAL"/"PAGO MINIMO"/"VENCIMIENTO")
       - transacciones: lista de {fecha, concepto, monto, cuotas}

    Es un parser GENERICO que se va a refinar cuando tengamos PDFs de muestra
    de cada banco (Galicia, Santander, ICBC tienen formatos distintos).
    """
    try:
        import pdfplumber
    except ImportError:
        log(f"  PDF: pdfplumber no disponible, skip {path.name}")
        return None
    try:
        with pdfplumber.open(path) as pdf:
            text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    except Exception as e:
        log(f"  PDF {path.name}: error abriendo: {e}")
        return None

    info = {"total": 0, "transacciones": []}

    # ===== Total a pagar (heurística genérica) =====
    # Busca el monto más alto que aparezca cerca de palabras clave de "total/vencimiento"
    candidatos = []
    for line in text.splitlines():
        up = line.upper()
        if ("TOTAL" in up or "PAGO MINIMO" in up or "VENCIMIENTO" in up or "SALDO ACTUAL" in up):
            for m in re.finditer(r"\$?\s*([\d.,]+)\s*$|\$\s*([\d.,]+)", line):
                txt = (m.group(1) or m.group(2) or "").replace(".", "").replace(",", ".")
                try:
                    v = float(txt)
                    if v > 100:
                        candidatos.append(v)
                except ValueError:
                    pass
    if candidatos:
        info["total"] = round(max(candidatos), 2)

    # ===== Transacciones (heurística genérica) =====
    # Busca líneas con patrón: fecha (dd/mm o dd-mm-yy) + descripción + monto al final
    yy_corto = ano_mes[2:4]
    mm = int(ano_mes.split("-")[1])
    for line in text.splitlines():
        # Patrón: dd/mm + concepto + monto
        m = re.match(r"\s*(\d{2})[/-](\d{2})(?:[/-](\d{2,4}))?\s+(.+?)\s+\$?\s*([\d.,]+)\s*$", line)
        if not m:
            continue
        d, mes, _, concepto, monto = m.groups()
        try:
            d = int(d); mes = int(mes)
            if mes < 1 or mes > 12 or d < 1 or d > 31:
                continue
            v = float(monto.replace(".", "").replace(",", "."))
            if v < 1 or v > 100_000_000:
                continue
        except ValueError:
            continue
        # Cuotas (texto tipo "C.01/12")
        cuotas = None
        m_cuotas = re.search(r"C\.?\s*(\d{1,2})\s*/\s*(\d{1,2})", concepto)
        if m_cuotas:
            cuotas = f"{m_cuotas.group(1)}/{m_cuotas.group(2)}"
        info["transacciones"].append({
            "fecha": f"{d:02d}/{mes:02d}",
            "concepto": concepto.strip()[:100],
            "monto": round(v, 2),
            "cuotas": cuotas,
        })

    return info


def parse_resumen_santander_pdf(path, ano_mes):
    # Compat: ahora redirigimos al parser genérico (Santander VISA único)
    info = parse_resumen_tarjeta_pdf(path, ano_mes, "Tarjeta Santander Rio - VISA")
    if info and info.get("total"):
        return {"Tarjeta Santander Rio - VISA": info["total"]}
    return {}


def parse_cobranzas_txt(path):
    """Parsea cobranzas.txt formato:
       total_cobrado: 9100000
       cantidad: 30
       cobrado_papa: 1200000
    """
    out = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k = k.strip().lower()
        out[k] = num(v)
    return out


def parse_saldos_txt(path):
    """Parsea saldos.txt formato:
       galicia: 2529212
       santander: 7613
       usd: 44.62
    """
    out = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        out[k.strip().lower()] = num(v)
    return out


# =====================================================================
# Procesar carpeta de un mes
# =====================================================================

def process_month(month_dir, data):
    name = month_dir.name  # "2026-04"
    if not re.match(r"\d{4}-\d{2}$", name):
        return False
    ano_mes = name

    # Recolectar todos los archivos: raíz del mes + subcarpetas (Excels, Galicia, Santander, ICBC)
    files = {}
    for f in month_dir.rglob("*"):
        if not f.is_file():
            continue
        if f.name.lower() in ("leeme.md", ".gitkeep"):
            continue
        # Key: tuple (subcarpeta_lower, filename_lower)
        rel_parent = f.parent.name.lower() if f.parent != month_dir else ""
        files[(rel_parent, f.name.lower())] = f

    if not files:
        return False

    def find(folder, name_lower):
        return files.get((folder.lower(), name_lower.lower()))

    log(f"Procesando {ano_mes} ({len(files)} archivos en {len(set(k[0] for k in files))} carpetas)...")
    cambios = []

    # 1. facturacion.xlsx (en Excels/)
    fpath = find("Excels", "facturacion.xlsx") or find("", "facturacion.xlsx")
    if fpath:
        r = parse_facturacion_xlsx(fpath, ano_mes)
        if r:
            resumen, entries, vol = r
            data["facturacion_por_mes"][ano_mes] = resumen
            data["volumen_por_mes"][ano_mes] = vol
            data["fact_lista"] = remove_month_from_lista(data.get("fact_lista", []), ano_mes) + entries
            cambios.append(f"facturacion ({len(entries)} comprobantes)")

    # 2. gastos_excel.xlsx (en Excels/)
    fpath = find("Excels", "gastos_excel.xlsx") or find("", "gastos_excel.xlsx")
    if fpath:
        r = parse_gastos_excel_xlsx(fpath, ano_mes)
        if r:
            resumen, lista, top = r
            existing = data["gastos_por_mes"].get(ano_mes, {})
            existing.update(resumen)
            existing["total"] = round(sum(resumen.values()), 2) + existing.get("comisiones_reales", 0)
            data["gastos_por_mes"][ano_mes] = existing
            data["gastos_lista"] = remove_month_from_lista(data.get("gastos_lista", []), ano_mes) + lista
            data["top_conceptos"][ano_mes] = top
            cambios.append(f"gastos_excel ({len(lista)} items)")

    # 3. gastos_bs.xlsx (en Excels/)
    fpath = find("Excels", "gastos_bs.xlsx") or find("", "gastos_bs.xlsx")
    if fpath:
        comisiones = parse_gastos_bs_xlsx(fpath, ano_mes)
        if comisiones:
            existing = data["gastos_por_mes"].get(ano_mes, {})
            existing["comisiones_reales"] = comisiones
            existing["total"] = round(
                existing.get("mercaderia", 0) + existing.get("fijos", 0) +
                existing.get("varios", 0) + existing.get("sueldos", 0) + comisiones, 2)
            data["gastos_por_mes"][ano_mes] = existing
            cambios.append(f"comisiones_reales ${comisiones:,.0f}")

    # 4. extracto_galicia.xlsx (en Excels/) — todas las cuentas Galicia consolidadas
    fpath = find("Excels", "extracto_galicia.xlsx") or find("", "extracto_galicia.xlsx")
    if fpath:
        pagos = parse_extracto_galicia(fpath, ano_mes)
        if pagos:
            for tarjeta, monto in pagos.items():
                data["tarjetas_pagos"].setdefault(tarjeta, {})[ano_mes] = monto
            cambios.append(f"galicia tarjetas ({len(pagos)})")

    # 5. PDFs de tarjetas (Galicia/, Santander/, ICBC/)
    pdf_specs = [
        ("Galicia",   "resumen_visa.pdf",         "Tarjeta Galicia - VISA"),
        ("Galicia",   "resumen_amex.pdf",         "Tarjeta Galicia - AMEX"),
        ("Galicia",   "resumen_business.pdf",     "Tarjeta Galicia - BUSINESS"),
        ("Galicia",   "resumen_plus_visa.pdf",    "Tarjeta Galicia + VISA"),
        ("Galicia",   "resumen_plus_master.pdf",  "Tarjeta Galicia + MASTER"),
        ("Santander", "resumen_visa.pdf",         "Tarjeta Santander Rio - VISA"),
        ("Santander", "resumen_amex.pdf",         "Tarjeta Santander Rio - AMEX"),
        ("ICBC",      "resumen_visa.pdf",         "Tarjeta ICBC"),
    ]
    pdfs_procesados = 0
    for folder, fname, tarjeta_nombre in pdf_specs:
        fpath = find(folder, fname)
        if not fpath:
            continue
        info = parse_resumen_tarjeta_pdf(fpath, ano_mes, tarjeta_nombre)
        if info and info.get("total"):
            data["tarjetas_pagos"].setdefault(tarjeta_nombre, {})[ano_mes] = info["total"]
            # Detalle de transacciones para análisis
            if info.get("transacciones"):
                data.setdefault("tarjetas_detalle", {}) \
                    .setdefault(tarjeta_nombre, {})[ano_mes] = info["transacciones"]
            pdfs_procesados += 1
    if pdfs_procesados:
        cambios.append(f"PDFs tarjeta ({pdfs_procesados})")

    # 6. cobranzas.txt (en raíz del mes)
    fpath = find("", "cobranzas.txt")
    if fpath:
        c = parse_cobranzas_txt(fpath)
        if c.get("total_cobrado"):
            cob = data.get("cobranzas_2026", {})
            por_mes = cob.setdefault("por_mes", {})
            por_mes[ano_mes] = {
                "monto": int(c.get("total_cobrado", 0)),
                "cantidad": int(c.get("cantidad", 0)),
            }
            cob["total_cobrado"] = sum(v["monto"] for v in por_mes.values())
            cob["total_cobranzas"] = sum(v["cantidad"] for v in por_mes.values())
            data["cobranzas_2026"] = cob
            cambios.append(f"cobranzas ${c['total_cobrado']:,.0f}")

    # 7. saldos.txt (en raíz del mes)
    fpath = find("", "saldos.txt")
    if fpath:
        sal = parse_saldos_txt(fpath)
        if sal:
            yr, mo = map(int, ano_mes.split("-"))
            from calendar import monthrange
            last_day = monthrange(yr, mo)[1]
            fecha = f"{ano_mes}-{last_day:02d}"
            # Soporta tanto formato viejo (galicia/santander/usd) como nuevo (galicia_principal/galicia_caja_ahorro/galicia_plus/santander/usd)
            galicia_total = (
                sal.get("galicia_principal", 0) +
                sal.get("galicia_caja_ahorro", 0) +
                sal.get("galicia_plus", 0) +
                sal.get("galicia", 0)  # backwards compat
            )
            entry = {
                "fecha": fecha,
                "galicia": int(galicia_total),
                "santander": int(sal.get("santander", 0)),
                "usd": sal.get("usd", 0),
            }
            entry["total"] = entry["galicia"] + entry["santander"]
            # Detalle de cuentas (si vino con el nuevo formato)
            if any(k in sal for k in ("galicia_principal", "galicia_caja_ahorro", "galicia_plus")):
                entry["detalle"] = {
                    "galicia_principal": sal.get("galicia_principal", 0),
                    "galicia_caja_ahorro": sal.get("galicia_caja_ahorro", 0),
                    "galicia_plus": sal.get("galicia_plus", 0),
                }
            sb = data.get("saldos_bancarios", [])
            sb = [e for e in sb if e.get("fecha") != fecha]
            sb.append(entry)
            sb.sort(key=lambda e: e.get("fecha", ""))
            data["saldos_bancarios"] = sb
            cambios.append(f"saldos al {fecha}")

    if cambios and ano_mes not in data.get("meses", []):
        data.setdefault("meses", []).append(ano_mes)
        data["meses"].sort()

    if cambios:
        log(f"  {ano_mes}: " + ", ".join(cambios))
        return True
    return False


# =====================================================================
# Main
# =====================================================================

def main():
    if not ARCHIVOS_DIR.exists():
        log("No existe", ARCHIVOS_DIR)
        return 0

    data = load_existing_js()
    cambios_total = 0
    for month_dir in sorted(ARCHIVOS_DIR.iterdir()):
        if not month_dir.is_dir():
            continue
        if process_month(month_dir, data):
            cambios_total += 1

    if cambios_total:
        write_js(data)
        log(f"OK: {cambios_total} mes(es) actualizados → {JS_OUT.name}")
    else:
        log("Sin cambios — ningún mes tenía archivos para procesar")
    return 0


if __name__ == "__main__":
    sys.exit(main())
