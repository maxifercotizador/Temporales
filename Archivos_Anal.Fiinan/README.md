# Archivos del Análisis Financiero

Acá guardás los archivos crudos que alimentan a `analisis_financiero.html`. Una subcarpeta por mes.

**Formato carpeta:** `AAAA-MM` (ej. `2026-04` para abril 2026).

## Qué va en cada carpeta del mes

Lista para alimentar **un solo mes** (ejemplo abril):

1. **Facturación del mes** — `facturacion.xlsx`
   - Exportar de **BS Gestión → Comprobantes emitidos** del 01/MM al fin de mes.

2. **Excel de gastos del mes** — `gastos_excel.xlsx`
   - Tu archivo `Gastos_2026.xlsx` recortado a la hoja del mes (o el mes correspondiente).

3. **Gastos BS Gestión del mes** — `gastos_bs.xlsx`
   - BS Gestión, gastos del 01/MM al fin de mes. Sirve para sacar **comisiones reales**.

4. **Extracto Galicia del mes** — `extracto_galicia.xlsx`
   - Home banking Galicia, movimientos del 01/MM al fin de mes.

5. **Resumen Santander del mes** — `resumen_santander.pdf`
   - PDF tal cual lo manda el banco (cierra ~26 del mes siguiente).

6. **Screenshot dashboard cobranzas** — `cobranzas.png` (o `.jpg`)
   - Captura del dashboard con totales actualizados al fin del mes.

7. **Saldos al cierre del mes** — `saldos.txt`
   - Tres números, uno por línea:
     ```
     galicia: 2529212
     santander: 7613
     usd: 44.62
     ```

> Si te falta alguno, dejalo sin subir. La que importa siempre es la facturación + gastos.

## Cómo se usa

1. Cada fin de mes (o cuando tengas todo), copiás los 7 archivos a la subcarpeta del mes.
2. Le pasás esa carpeta a Claude y le pedís que actualice `analisis_financiero_datos.js` con los datos del mes.
3. Push a `main`. GitHub Pages refresca y la app levanta los datos nuevos.

## Mapeo: archivo → qué sección actualiza en la app

| Archivo | Secciones que alimenta en el HTML |
|---|---|
| 1. Facturación BS Gestión | Resumen, Facturación, Vendedores, Volumen, Comparador, Fact vs Cobr |
| 2. Excel de gastos | Gastos (mercadería/fijos/varios/sueldos), Top conceptos |
| 3. Gastos BS Gestión | Comisiones reales del mes (parte de Gastos) |
| 4. Extracto Galicia | Pagos de tarjetas Galicia, gastos bancarios |
| 5. Resumen Santander | Pagos de tarjetas Santander |
| 6. Screenshot cobranzas | Tab Cobranzas (total cobrado, por mes, por vendedor) |
| 7. Saldos al cierre | Tab Flujo (snapshot de saldos bancarios) |

## Datos que NO vienen de archivos

- **Préstamos vigentes:** se cargan a mano en `analisis_financiero_datos.js` (clave `prestamos`). Solo se actualiza cuando hay un préstamo nuevo o termina uno.
- **Tumini:** monto adeudado y facturado. Manual (clave `problemas_tumini`).
