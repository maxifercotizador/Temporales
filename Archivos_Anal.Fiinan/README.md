# Archivos del Análisis Financiero

Este sistema arranca **a partir de abril 2026**. Los meses anteriores ya están cargados en `analisis_financiero_datos.js` y no hace falta tocar nada.

## Cómo se usa cada mes

1. Abrís la carpeta del mes (ej. `2026-04/`).
2. Vas tirando los archivos a medida que los tenés. **Respetá los nombres de archivo** de la lista de abajo, así el sistema los reconoce.
3. Cuando termines de cargar todo el mes, push a `main`. El análisis se regenera con esos datos.

## Archivos que van en cada carpeta del mes

Estos son los **nombres exactos** que tienen que tener los archivos. Si los nombrás distinto, no se levantan.

| # | Archivo (nombre exacto) | Origen | Para qué sirve |
|---|---|---|---|
| 1 | `facturacion.xlsx` | BS Gestión → Comprobantes emitidos del 01/MM al fin de mes | Facturación del mes (FA, FB, NC), por vendedor, volumen |
| 2 | `gastos_excel.xlsx` | Tu `Gastos_2026.xlsx`, hoja del mes | Mercadería, fijos, varios, sueldos |
| 3 | `gastos_bs.xlsx` | BS Gestión, gastos del 01/MM al fin de mes | Comisiones reales del mes |
| 4 | `extracto_galicia.xlsx` | Home banking Galicia, movimientos del 01/MM al fin de mes | Pagos tarjetas Galicia, gastos bancarios |
| 5 | `resumen_santander.pdf` | PDF del resumen Santander del mes | Pagos tarjetas Santander |
| 6 | `cobranzas.png` (o `.jpg` o `.txt`) | Captura del dashboard de cobranzas, o 3 números en txt | Cobranzas del mes |
| 7 | `saldos.txt` (o `.png`) | Saldos al cierre, ver formato abajo | Saldos al cierre del mes |

### Si usás imagen para cobranzas/saldos
Tirás el screenshot tal cual (`cobranzas.png`, `saldos.png`). El pipeline lo lee con OCR.

### Si usás txt (más confiable, más rápido)

`cobranzas.txt`:
```
total_cobrado: 9100000
cantidad: 30
cobrado_papa: 1200000
```

`saldos.txt`:
```
galicia: 2529212
santander: 7613
usd: 44.62
```

## Datos que NO vienen de archivos

Estos se actualizan a mano en `analisis_financiero_datos.js`, solo cuando cambian:

- **Préstamos vigentes** (clave `prestamos`): cuando se agrega o termina uno.
- **Tumini** (clave `problemas_tumini`): monto adeudado y facturado.

## Nota sobre la automatización

Cuando subas los archivos por primera vez, te armo el pipeline (GitHub Actions) que parsea los Excel/PDF y regenera `analisis_financiero_datos.js` solo. Mientras tanto, podés cargar los archivos a la carpeta y avisarme — yo lo regenero al toque.

Si algún archivo te falta (ej. resumen Santander que cierra el 26 del mes siguiente), no pasa nada: subís lo que tengas y completás el resto cuando llegue.
