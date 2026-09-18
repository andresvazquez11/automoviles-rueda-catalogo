# Coches Destacados — Diseño

Fecha: 2026-09-18

## Objetivo

Andrés (y, en su nombre, también las páginas de Alejandro) necesita poder marcar
hasta 3 coches del catálogo como "destacados" desde cualquier dispositivo
(móvil u ordenador) en cualquier momento del día, y que el cambio se vea en la
web pública en menos de un minuto — sin correr scripts Python ni hacer
`git push` a mano.

Un coche destacado debe:
- Aparecer en una franja separada, arriba de la grilla normal del catálogo.
- Mostrarse en una tarjeta más grande que las tarjetas normales.
- Llevar una tirita con un texto de oferta (elegido de una lista fija).

Solo Andrés gestiona los destacados de ambos perfiles (el suyo y el de
Alejandro); Alejandro no necesita acceso propio.

## Arquitectura

Sin servicios ni cuentas nuevas. Se aprovecha la infraestructura que ya existe
(GitHub + GitHub Pages) usando la API de GitHub directamente desde el
navegador, con un token de acceso personal que Andrés genera una vez y queda
guardado en el `localStorage` de cada dispositivo que use.

```
┌─────────────┐   fetch + PUT (API GitHub,     ┌──────────────────┐
│ /admin/      │   con token guardado)          │ Repo GitHub      │
│ index.html   │ ──────────────────────────────▶│ destacados.json  │
│ (móvil/PC)   │                                 └──────────────────┘
└─────────────┘                                          │
                                                   push → GitHub Pages
                                                    republica solo (~1 min)
                                                           │
                                                           ▼
                                          ┌───────────────────────────────┐
                                          │ index.html / alejandro/index  │
                                          │ fetch('/destacados.json')     │
                                          │ al cargar → pinta franja      │
                                          └───────────────────────────────┘
```

## Piezas nuevas

### 1. `destacados.json` (raíz del repo, público)

Fuente de verdad de la selección actual. Independiente de
`datos_coches.json` — el script diario de actualización del catálogo no lo
toca.

```json
{
  "andres":    [
    {"n": 12, "etiqueta": "Oferta del mes"},
    {"n": 7,  "etiqueta": "Últimas unidades"}
  ],
  "alejandro": [
    {"n": 3, "etiqueta": "Oferta especial"}
  ]
}
```

- Máximo 3 entradas por perfil.
- `etiqueta` es siempre una de las 5 frases fijas (ver abajo).
- Si el archivo no existe todavía (primer uso), se trata como `{}` — ningún
  coche destacado, sin errores.

### 2. `coches_lista.json` (raíz del repo, público, generado)

Generado por `generar_web.py` en cada corrida diaria, junto al resto de la
salida. Contiene solo lo necesario para pintar la lista de selección en
`/admin` — nunca se publica `datos_coches.json` completo (regla existente del
proyecto).

Por coche disponible: `n`, `modelo`, `version` corta, `precio`, y la URL de
una foto en miniatura (la misma CDN de Das WeltAuto que ya usa el resto del
sitio).

### 3. `/admin/index.html` (página estática nueva, escrita a mano)

No la genera `generar_web.py` — es una herramienta interna, se mantiene por
separado.

Flujo:
1. Al entrar, si no hay token guardado en `localStorage`, pide pegarlo
   (instrucciones en pantalla de cómo generarlo en GitHub, con permiso
   limitado a este repo).
2. Selector de perfil: Andrés / Alejandro.
3. Carga `coches_lista.json` y muestra cada coche disponible con foto en
   miniatura, modelo y precio, con una casilla para marcarlo.
4. Máximo 3 casillas marcadas a la vez (las demás se deshabilitan al llegar
   al límite).
5. Por cada coche marcado, un desplegable con las 5 frases fijas:
   - Oferta especial
   - Oferta del mes
   - Precio rebajado
   - Últimas unidades
   - Recomendado por el asesor
6. Botón "Guardar": lee el SHA actual de `destacados.json` vía la API de
   GitHub (`GET /repos/.../contents/destacados.json`), arma el nuevo
   contenido y hace `PUT` con ese SHA para crear un commit. Mensaje de commit
   automático (ej. `Actualizar destacados (andres) — 2026-09-18`).
7. Confirmación visual de que se guardó, y aviso de que puede tardar hasta un
   minuto en verse en la web pública.

Sin PIN adicional — el token es la única barrera para guardar cambios. La URL
no está enlazada desde el catálogo público, pero no se considera secreta: sin
el token, la página no puede escribir nada.

### 4. Cambios en `index.html` / `alejandro/index.html`

En `generar_web.py`, dentro del HTML/JS generado para cada perfil:

- Al cargar la página, `fetch('/destacados.json')` (ruta relativa a la raíz
  del dominio, funciona igual para ambos perfiles).
- Se toma la lista correspondiente al perfil actual (`andres` o `alejandro`).
- Por cada entrada, se busca la tarjeta (`.rd-card`) del coche `n`
  correspondiente ya renderizada en la grilla normal.
  - Si no existe (coche vendido/retirado/no encontrado), esa entrada se
    ignora silenciosamente — nunca se muestra un destacado que ya no está
    disponible.
  - Si existe, se clona esa tarjeta (no se mueve) dentro de una franja nueva
    "🌟 Destacados" que aparece arriba de los controles de filtro/búsqueda,
    con una clase CSS que la hace más grande y le agrega la tirita con la
    `etiqueta`. El clon es una tarjeta independiente (mismo enlace a la ficha
    del coche) — no comparte nodo con la de la grilla de abajo, así que no
    interfiere con el buscador/filtro/orden que operan sobre la grilla
    original.
- La grilla normal de abajo sigue mostrando todos los coches igual que hoy
  (incluidos los destacados, en su posición normal) — la franja de arriba es
  un adelanto, no un filtro ni un reemplazo.
- Si `destacados.json` no existe o falla el `fetch` (ej. sin conexión), la
  página no muestra la franja y sigue funcionando con normalidad — no es un
  punto de fallo para el catálogo.

## Qué NO cambia

- El flujo diario (`1️⃣ Actualizar Todo — Cambios + Fotos.command`) sigue
  igual. Solo se le suma la generación de `coches_lista.json`.
- `datos_coches.json` y el resto de scripts internos no se tocan.
- La calculadora de financiación, las fichas individuales de coche
  (`coches/*.html`) y el resto del sitio no cambian.

## Fuera de alcance

- Alejandro no tiene acceso propio al admin (lo gestiona Andrés).
- No hay edición de texto libre para la tirita — solo las 5 frases fijas.
- No se aplica "destacado" a las fichas individuales de coche, solo a la
  página de listado.
