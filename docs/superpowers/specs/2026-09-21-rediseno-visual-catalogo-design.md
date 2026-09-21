# Rediseño visual del catálogo web — Diseño

Fecha: 2026-09-21

## Objetivo

Modernizar la estética de la página pública del catálogo (`index.html` y
equivalentes de Alejandro), inspirándose en sitios de venta de coches y
e-commerce de referencia (coches.net, Rivian, Nike, comparadores tipo
Edmunds), sin cambiar el pipeline de datos existente (sigue siendo un sitio
estático generado por `generar_web.py` a partir de `datos_coches.json`, sin
backend propio).

Se llegó a este diseño después de una ronda de investigación de referencias
y varias iteraciones sobre un mockup interactivo (Artifact de tipo "Design"),
aprobadas por Andrés en conversación. Este documento es el resumen de lo
aprobado, no una propuesta nueva.

## Qué se aprobó

1. **Hero con foto de estilo de vida + CTA flotante.** La portada deja de
   arrancar con la grilla de filtros pegada arriba; ahora hay una sección de
   pantalla completa con una foto grande (no un coche solo en showroom, sino
   una escena — ver "Fotografía del hero" abajo), un titular grande en
   Oswald mayúsculas, y una barra flotante compacta y semi-transparente
   ("vidrio esmerilado") abajo a la derecha con el conteo de coches
   disponibles y un botón que lleva al catálogo. **Descartado:** una tarjeta
   blanca opaca grande tapando el centro de la foto — se probó y no gustó,
   se reemplazó por la barra chica y translúcida.
2. **Efecto parallax en el hero.** Al hacer scroll, la foto de fondo del
   hero queda fija mientras el contenido se desliza por encima
   (`background-attachment: fixed`). Aprobado para escritorio; en mobile
   este truco de CSS no se comporta igual en todos los navegadores (Safari
   iOS en particular) — al implementarlo hay que decidir si se omite en
   mobile o se reemplaza por algo más simple ahí.
3. **Contador de fotos + avance por hover.** Cada tarjeta del catálogo
   muestra un contador tipo `1/8` sobre la miniatura. Al mover el mouse de
   izquierda a derecha sobre la foto, va cambiando de ángulo según en qué
   tercio de la imagen está el cursor (como en portales inmobiliarios/de
   coches). Es una mejora de escritorio — en mobile no hay hover, así que
   ahí simplemente se ve la primera foto fija, sin necesidad de ninguna
   adaptación especial.
4. **Specs siempre visibles.** Combustible, kilómetros y cambio se muestran
   siempre debajo del precio. **Descartado:** ocultarlos detrás de un hover
   — Andrés necesita ver el resumen del coche sin tener que interactuar
   primero, sobre todo pensando en mobile.
5. **Comparador de hasta 3 coches lado a lado.** Botón "+ Comparar" en cada
   tarjeta. Al elegir 2 o 3 coches aparece una barra flotante abajo con los
   elegidos y un botón "Ver comparación", que abre una tabla con foto,
   precio, km, combustible y cambio de cada uno en columnas.
6. **Modo oscuro.** Toggle en el header que cambia fondo/texto de toda la
   página.

## Qué queda fuera de este alcance (por ahora)

- **Versión mobile del hero/hover/parallax.** No se diseñó todavía una
  adaptación específica para pantalla chica. El comparador y el modo
  oscuro sí funcionan igual en mobile (son clic, no hover), así que no
  necesitan trabajo extra.
- **Buscador funcional en la barra flotante del hero.** En el mockup la
  barra es decorativa (chips de ejemplo + botón que hace scroll hacia
  abajo). La página real ya tiene su propio filtro/buscador más abajo en
  el catálogo — la barra del hero no lo reemplaza, es un CTA liviano que
  lleva hacia él. Si más adelante se quiere que la barra del hero filtre
  de verdad, es un alcance aparte.
- **Fotografía real del hero.** La foto usada en el mockup se generó con
  IA (Nano Banana Pro vía Freepik) como referencia de estilo/composición,
  no como foto final. Antes de implementar hay que decidir la fuente real:
  ¿una foto de stock con licencia, una sesión de fotos propia, o coches
  generados con IA igual que en el mockup pero producidos con más cuidado
  por coche/temporada?

## Veredicto pendiente

Andrés aclaró que la aprobación de este mockup es conceptual — el veredicto
final lo va a dar viendo los cambios funcionando en la página real, no en el
Artifact de exploración.

## Arquitectura de la implementación (a alto nivel)

Sin servicios nuevos. Todo vive en `generar_web.py` (HTML/CSS/JS inline que
ya genera hoy) y se sirve igual que ahora desde GitHub Pages:

```
generar_web.py
  ├─ nueva sección de hero (HTML/CSS, con la foto de fondo)
  ├─ JS de la tarjeta: hover-scrub de fotos (usa las fotos ya
  │  descargadas en web_fotos/NN/, no pide nada nuevo)
  ├─ JS del comparador: estado en memoria del navegador (no hace falta
  │  persistirlo ni mandarlo a ningún lado)
  └─ JS del modo oscuro: toggle de una clase en <body>,
     opcionalmente recordado en localStorage por dispositivo
```

No se toca `datos_coches.json`, `actualizar_catalogo.py` ni el workflow de
GitHub Actions — este cambio es puramente de presentación sobre los mismos
datos que ya se generan hoy.

## Próximo paso

Con este documento aprobado, el siguiente paso es escribir un plan de
implementación (`writing-plans`) que desglose el trabajo en pasos concretos
sobre `generar_web.py`, para ejecutarlo de a poco sin romper el sitio en
producción.
