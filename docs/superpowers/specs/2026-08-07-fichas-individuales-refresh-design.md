# Fichas individuales por coche + refresh estético del catálogo web

Fecha: 2026-08-07
Estado: Aprobado por Andrés (verbalmente en chat) — pendiente de revisión del spec escrito.

## Contexto

El catálogo web (`index.html`, generado por `generar_web.py`) muestra todos los coches en
una sola página. Al hacer clic en un coche se abre un modal (pop-up) con galería, specs y
la calculadora de financiación. Este modal no es enlazable: no existe una URL que apunte a
un coche concreto, así que Andrés no puede compartir "este coche" por WhatsApp con un
cliente — solo puede compartir el catálogo entero.

## Objetivo

1. Cada coche tiene su propia página HTML real, con URL propia, para poder compartir el
   link de un coche específico por WhatsApp — incluyendo vista previa con foto, modelo y
   precio (Open Graph tags), igual que al compartir un anuncio de Das WeltAuto o Wallapop.
2. Refresh estético de todo el sitio (catálogo + ficha de coche), inspirado en sitios
   modernos de coches (referencia principal: la propia ficha de detalle de Das WeltAuto).
   Paleta de color abierta a cambiar si mejora el resultado (no atada al azul/rojo actual).

## No-objetivos (fuera de alcance de este trabajo)

- No se monta servidor ni backend: el sitio sigue siendo 100% estático en GitHub Pages.
- No se cambia el origen de datos (`datos_coches.json`) ni el proceso de scraping.
- No se añade buscador de "coches similares" con lógica de recomendación (puede quedar
  como idea futura, no se implementa ahora).
- No se toca la calculadora de financiación en su lógica de cálculo — solo su ubicación
  visual (pasa de vivir en un modal a vivir en la sección de la ficha del coche).

## Arquitectura

### Archivos generados (por `generar_web.py`)

```
catalogo_automoviles_rueda/
├── index.html                    # catálogo (grid + buscador), rediseñado
├── assets/
│   ├── estilos.css               # CSS compartido entre index y todas las fichas
│   └── calculadora.js            # motor de la calculadora de financiación (compartido)
├── coches/
│   ├── 01-seat-leon.html
│   ├── 02-cupra-formentor.html
│   └── ...                       # un archivo real por coche
└── web_fotos/{n:02d}/foto_XX.jpg # sin cambios
```

Esto es un cambio de convención respecto a la decisión documentada en `CLAUDE.md`
("HTML 100% autocontenido, todo CSS/JS inline"). Con 61+ páginas, duplicar el CSS y el
motor de la calculadora en cada archivo infla el repositorio en cada actualización diaria
sin necesidad. La nueva convención: **sin dependencias externas al repo** (nada de CDNs),
pero sí archivos compartidos dentro del propio repo. `CLAUDE.md` se actualiza para reflejar
esto una vez implementado.

### URL / slug por coche

`coches/{n}-{slug-modelo}.html`, ej. `coches/12-seat-leon.html`.

- El slug se genera solo a partir de `n` (número interno estable) y `modelo` — **no** de
  `precio` ni `version`, que cambian con el tiempo. Así el link compartido hoy sigue
  apuntando al mismo archivo mañana aunque el precio cambie.
- `n` ya es estable entre actualizaciones salvo renumeración por integración de MotorFlash
  (caso ya manejado hoy en `actualizar_catalogo.py`, que renombra carpetas de fotos cuando
  cambia `n`). Al regenerar la web, `generar_web.py` debe borrar los archivos de
  `coches/` que ya no correspondan a ningún `n` actual antes de regenerar (igual que ya
  hace con `web_fotos/`), para no dejar páginas huérfanas con datos viejos.

### Coche vendido / retirado

Un link ya compartido no debe romperse. Cuando un coche pasa a `Retirado` (ya no aparece
en Das WeltAuto), su página en `coches/` **no se borra**: se sigue generando, pero con:
- Banner superior: "Este vehículo ya no está disponible."
- Precio y CTA de reserva ocultos (no tiene sentido reservar algo vendido).
- Un botón "Ver coches disponibles" que lleva al catálogo.

Cuando un coche pasa a `No disponible` (reservado), su página se genera con normalidad
pero con el mismo indicador "Reservado" que ya usa el catálogo hoy.

### Open Graph / vista previa de WhatsApp

Cada página de coche incluye en el `<head>`:
```html
<meta property="og:title" content="SEAT León FR 2021 · 18.500€ · Automóviles Rueda">
<meta property="og:description" content="Diésel · 45.000 km · Automático · Málaga">
<meta property="og:image" content="https://andresvazquez11.github.io/automoviles-rueda-catalogo/web_fotos/12/foto_01.jpg">
<meta property="og:url" content="https://andresvazquez11.github.io/automoviles-rueda-catalogo/coches/12-seat-leon.html">
<meta property="og:type" content="product">
```
La imagen debe ser una URL absoluta (no relativa) porque WhatsApp la descarga por su
cuenta al generar la vista previa — no ejecuta JavaScript ni resuelve rutas relativas
fuera del dominio.

## Diseño visual

### Ficha de coche (`coches/NN-slug.html`)

Inspirado en la estructura de la ficha de Das WeltAuto, adaptado a la marca:
- Galería grande arriba (ratio ancho, miniaturas o contador debajo), reutilizando las
  fotos ya existentes en `web_fotos/{n}/`.
- Franja de datos clave con iconos: combustible, km, año/matriculación, cambio.
- Panel de precio + botones "Reservar por WhatsApp" / "Llamar" — fijo (sticky) al hacer
  scroll en escritorio, como en Das WeltAuto.
- Sección de equipamiento (lista/chips, igual que hoy).
- Sección de calculadora de financiación (misma lógica, nueva ubicación — sección propia
  en vez de bloque dentro de un modal).
- Enlace "‹ Volver al catálogo" arriba.
- Botones para compartir (WhatsApp / copiar link) — nuevo, no existía en el modal porque
  no había nada que compartir.

### Catálogo (`index.html`)

- Mismo buscador y filtros que hoy.
- Tarjetas más grandes/modernas; cada tarjeta es un `<a href="coches/NN-slug.html">` real
  (funciona sin JavaScript, mejor para compartir/indexar), no un `onclick` que abre modal.
- El modal actual se elimina — ya no hace falta.

### Paleta y tipografía

Se define durante la construcción del prototipo (paso siguiente), no en este documento —
Andrés dijo estar abierto a cambiar la paleta actual si el resultado es mejor. El
prototipo es el punto de decisión real, no este texto.

## Plan de migración (evita generar 61 páginas antes de aprobar el diseño)

1. **Prototipo:** construir el nuevo `assets/estilos.css`, un ejemplo de ficha de coche
   completo (un coche real de `datos_coches.json`) y el `index.html` rediseñado con datos
   reales. Abrir ambos en el navegador para revisión visual de Andrés.
2. **Aprobación visual:** ajustar según feedback directo ("me pareció horrible" → se
   revisa desde la raíz, no se parchea, según indica `CLAUDE.md`).
3. **Generalizar:** una vez aprobado el prototipo, extender `generar_web.py` para generar
   las 61 fichas reales a partir de esa misma plantilla + limpiar huérfanas.
4. **Actualizar el `.command`:** `git add` debe incluir ahora `coches/` y `assets/` además
   de `index.html` y `web_fotos/`.
5. **Actualizar `CLAUDE.md`** con la nueva estructura de archivos y la convención de
   assets compartidos.

## Riesgos / decisiones explícitas

- **Tamaño del repo:** 61 archivos HTML nuevos + `assets/` es mucho menos que duplicar
  todo el CSS/JS en cada uno (motivo de elegir la Opción A sobre la B).
- **Fotos con ruta absoluta para OG:** requiere conocer el dominio final
  (`andresvazquez11.github.io/automoviles-rueda-catalogo`) hardcodeado en el generador —
  ya es así implícitamente hoy (el repo es específico de este dominio).
- **No se pierde nada de la calculadora de financiación** — se traslada su HTML/JS a un
  módulo compartido, mismo comportamiento y resultados.
