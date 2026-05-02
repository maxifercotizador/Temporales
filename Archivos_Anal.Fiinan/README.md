# Archivos del Análisis Financiero

A partir de **abril 2026**. Los meses anteriores ya están cargados en `analisis_financiero_datos.js`.

## Estructura de cada mes

```
Archivos_Anal.Fiinan/2026-04/
├── Excels/                          ← 4 archivos
│   ├── facturacion.xlsx
│   ├── gastos_excel.xlsx
│   ├── gastos_bs.xlsx
│   └── extracto_galicia.xlsx        (3 cuentas Galicia, movimientos diarios)
│   └── extracto_santander.xlsx      (cuenta(s) Santander, movimientos diarios)
├── Galicia/                         ← PDFs de tarjeta (las que uses)
│   ├── resumen_visa.pdf             (VISA-2884)
│   ├── resumen_amex.pdf             (AMEX-0793)
│   ├── resumen_business.pdf         (VISA-9091)
│   ├── resumen_plus_visa.pdf        (VISA-3394)
│   └── resumen_plus_master.pdf      (MASTER-6770)
├── Santander/
│   ├── resumen_visa.pdf             (VISA-2857)
│   └── resumen_amex.pdf             (AMEX-62044)
├── ICBC/
│   └── resumen_visa.pdf             (VISA-7406)
├── cobranzas.txt
├── saldos.txt
└── LEEME.md
```

## Cómo cargar un mes

**Lo más fácil:** desde el dashboard `analisis_financiero.html` → tab **📤 Cargar mes** → te lleva directo a cada carpeta de GitHub.

## Formatos

### Excels (formato .xlsx)
| Archivo | De dónde |
|---|---|
| `facturacion.xlsx` | BS Gestión → Comprobantes emitidos del mes |
| `gastos_excel.xlsx` | Tu Excel personal `Gastos_2026.xlsx`, hoja del mes |
| `gastos_bs.xlsx` | BS Gestión → Gastos del mes (para comisiones reales) |
| `extracto_galicia.xlsx` | Home banking Galicia → 3 cuentas en uno |

### PDFs de tarjeta (formato .pdf)
- Bajás del home banking de cada banco.
- Si una tarjeta no la usaste un mes, **no subís ese PDF** (el script lo ignora).

### Texto plano (.txt)

`cobranzas.txt`:
```
total_cobrado: 9100000
cantidad: 30
cobrado_papa: 1200000
```

`saldos.txt` (saldos al cierre del mes):
```
galicia_principal: 2738.61
galicia_caja_ahorro: 2.14
galicia_plus: -309.69
galicia_caja_ahorro_plus: 0
santander: -411739.31
usd: 2.20
```

## Datos manuales en el JS

Estos NO vienen de archivos, se editan a mano en `analisis_financiero_datos.js`:
- **Préstamos vigentes** (clave `prestamos`)
- **Tumini** (clave `problemas_tumini`)

## Flujo automático

Cuando subís archivos a cualquier subcarpeta de un mes, GitHub Actions corre `scripts/build_analisis_financiero.py` que regenera `analisis_financiero_datos.js`. El dashboard refresca solo en 1-2 min.
