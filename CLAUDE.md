# Seguimiento_Prospectos.html — App CRM móvil MAXIFER

## Contexto

App standalone que vive dentro del repo `Temporales` (cuenta `maxifercotizador`), junto a otras apps HTML como `VIAJE_SUR.html` y `postventa_maxifer.html`.

Es un CRM mobile-first para Maxi (dueño de MAXIFER). Lee y escribe sobre el board de Monday "Seguimiento Prospectos" vía API. Diseñada para usar desde el celular.

URL de producción: `https://maxifercotizador.github.io/Temporales/Seguimiento_Prospectos.html`

## Stack

- HTML/CSS/JS puro, single-file (`Seguimiento_Prospectos.html`).
- Sin frameworks, sin build, sin npm.
- API: Monday.com v2024-10 vía fetch.
- Storage: `localStorage` para token y caché de contactos.

## Workflow Maxi (regla del repo)

- **Push directo a `main`**, sin PRs ni branches.
- **Español Argentina** en todo (UI, comentarios, commits).
- Commits descriptivos y cortos (ej: "agrega filtro por provincia").
- No uses emojis en commits.

## Datos clave (NO TOCAR sin avisar)

```
BOARD_ID = 18410539555
SUBBOARD_ID = 18410539771

GRUPOS:
- Clientes:       group_mm2vjn2q
- Interesados:    group_mm2vmmzx
- Proveedores:    group_mm2vxen7
- Archivados:     group_mm2w32m6

COLUMNAS PRINCIPALES (ítem):
- phone:          phone_mm2vbfbn
- link:           link_mm2vy9df
- etiqueta:       text_mm2vfm4e
- dia_visita:     dropdown_mm2veg95
- zona:           dropdown_mm2v7rbr
- provincia:      dropdown_mm2vemmm
- tipo_contacto:  color_mm2v26hx
- estado:         color_mm2vhgm9
- tipo_negocio:   dropdown_mm2vtmn8
- interes:        dropdown_mm2vrwpz
- fecha_primer:   date_mm2v9a5a
- fecha_ultimo:   date_mm2v6dkw
- proximo_seg:    date_mm2vqy63
- resumen:        long_text_mm2vq649
- comentario:     long_text_mm2vce4h

COLUMNAS SUBELEMENTOS:
- fecha:          date_mm2vk132
- tipo:           color_mm2v9qf5
- resumen:        long_text_mm2vacff
- productos:      dropdown_mm2vd9mq
- accion:         text_mm2vmqtg
```

## Estructura de la app

### 3 pestañas
1. **🔥 Hoy** — contactos con `proximo_seg` ≤ hoy (atrasados + hoy).
2. **🟡 Leads** — todos los del grupo Interesados.
3. **🟢 Clientes** — todos los del grupo Clientes.

### Tarjeta de contacto
- Nombre + tag (Cliente/Lead/Proveedor).
- Meta: estado, tipo negocio, zona, provincia, día de visita.
- Resumen (truncado a 2 líneas, click expande).
- Banner de seguimiento con días.
- 4 botones: WhatsApp, marcar contactado, posponer, detalle.

### Modales
- **WhatsApp:** templates contextuales generados según estado del contacto + custom.
- **Posponer:** botones rápidos (+2/+4/+7/+15/+30 días hábiles) o fecha custom.
- **Detalle:** info completa + historial de subelementos.
- **Settings:** cambiar token, refrescar, limpiar caché, logout.

## Lógica de mensajes WhatsApp

Los templates se generan en `generateTemplates(contact)` según `contact.estado`:
- `Presupuesto enviado` → seguimiento + crear urgencia
- `Quedó en escribir` / `Sin respuesta` → reactivación suave
- `Sin plata aún` → check de timing
- `Reactivar` → lead caliente
- Cliente (cualquier estado) → saludo + aviso novedad
- Genéricos siempre disponibles

Si querés agregar más templates, modificá esa función.

## Lógica anti-baneo WhatsApp

La app NO automatiza envíos. Solo construye `wa.me/{numero}?text={msg}` y abre WhatsApp. El usuario tiene que tocar enviar manualmente.

## TODOs / mejoras pendientes

- [ ] Service Worker para modo offline + banner al abrir con resumen del día.
- [ ] Métricas/dashboard (conversiones, tasa respuesta) — pendiente de armar.
- [ ] Crear subelemento desde la app después de marcar contactado (hoy solo limpia próximo_seg).
- [ ] Filtros adicionales: por estado, por día de visita.
- [ ] Búsqueda por nombre/teléfono.

## Cuando Maxi pida cambios

Maxi prefiere:
- Cambios pequeños, push directo a main.
- Probarlos enseguida desde el celu.
- Revertirlos fácil si no funcan.

Si vas a tocar la lógica de Monday API o el parseo, **probá primero con un contacto de prueba**, no con todo el board.

## Seguridad

- Token de Monday vive solo en `localStorage` del navegador del usuario.
- **Nunca commitear tokens**, ni siquiera de prueba.
- El repo puede ser público sin riesgo: el HTML no contiene secretos.

## Convivencia con otras apps del repo

Este archivo convive en el repo `Temporales` con:
- `postventa_maxifer.html`
- `VIAJE_SUR.html`
- (otros que Maxi pueda agregar)

Cada uno es independiente, no hay archivos compartidos. No tocar los otros archivos.
