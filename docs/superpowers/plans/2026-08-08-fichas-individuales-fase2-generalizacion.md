# Fichas individuales por coche — Fase 2: Generalización a los 61 coches Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extender `generar_web.py` para que, en cada ejecución, genere una página HTML real y compartible para cada uno de los ~61 coches del catálogo (no solo el CUPRA Formentor de prueba) y reemplace el `index.html` de producción (modal) por el catálogo rediseñado con tarjetas que enlazan a esas páginas reales — usando exactamente el diseño ya aprobado por Andrés en la Fase 1.

**Architecture:** El motor de la calculadora de financiación (ya validado, ya corregido con las condiciones de agosto 2026) se extrae UNA vez a `assets/calculadora.js`, compartido por las 61 páginas — evita repetir ~700 líneas de JS en cada archivo. `generar_web.py` gana dos funciones nuevas (`build_coche_html()` para una ficha, `build_index_html()` para el catálogo) que se derivan directamente de los archivos ya construidos y aprobados en la Fase 1 (`coches/01-cupra-formentor.html`, `index-prototipo.html`), parametrizados por coche. La función vieja `build_html()` (el modal de una sola página) se elimina al final, una vez todo lo nuevo esté verificado funcionando.

**Tech Stack:** Python 3 (generador), HTML/CSS/JS puro (salida), sin frameworks ni dependencias nuevas.

---

## Contexto para quien ejecute este plan

- **Fuentes de verdad ya validadas y aprobadas por Andrés** (no las rediseñes, solo parametrízalas):
  - `/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/coches/01-cupra-formentor.html` — ficha de coche completa y funcionando (galería, specs, equipamiento, calculadora con las condiciones de agosto 2026 ya corregidas, CTA final con enlace chico a Das WeltAuto).
  - `/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/index-prototipo.html` — catálogo con tarjetas (badges, pastillas, navegación de fotos, animación de entrada).
  - `/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/assets/estilos.css` — ya terminado, no se toca en este plan.
- **NO se toca la lógica de cálculo financiero.** El JS del motor `cv2*`/`initCalc`/`VR_TABLE`/`CV2_MANT` en `generar_web.py` (líneas `1442`–`2258`, ver rangos exactos abajo) ya está corregido con las condiciones VWFS de agosto 2026 — se extrae tal cual a `assets/calculadora.js`.
- `generar_web.py` sigue usando plantillas `.format()`/f-string con llaves dobles `{{`/`}}` en las secciones que hoy generan `index.html`. Las funciones NUEVAS que este plan agrega (`build_coche_html`, `build_index_html`) son funciones Python normales que devuelven HTML — **no** necesitan llaves dobles porque no reutilizan el mecanismo de f-string de `build_html()`; usan f-strings propias con llaves simples.
- Rangos de línea verificados en `generar_web.py` en este momento (ya reflejan las correcciones de financiación de hoy — si volviste a tocar el archivo antes de este plan, re-verifica con `grep -n` antes de asumir estos números):
  - `VR_TABLE`: `1442`–`1449`
  - `CV2` config: `1451`–`1467`
  - `CV2_ALL_PLAZOS`: `1468`
  - `CV2_MANT`: `1471`–`1477`
  - `cv2GetMantKey` … `cv2RestoreTin` (todas las funciones `cv2*`): `1478`–`2068`
  - `initCalc(c)`: `2069`–`2169`
  - `abrirModal(n)`: `2170`–`2228` — **NO se extrae**, es el patrón viejo (usa `backdrop`/`COCHES.find`), ya reemplazado por `cargarFicha()` en la Fase 1.
  - `goSlide(i)`: `2234`–`2240`
  - Swipe táctil (`let touchStartX` + `touchstart`/`touchend`): `2253`–`2258`
  - Helpers `estadoLabel`/`fmtCuota`/`esReservado`: `1295`–`1306`
- **CORRECCIÓN #1 (encontrada durante la Task 2):** `car["fotos"]` en `datos_coches.json` **NO** es una ruta web utilizable para la mayoría de los coches. Para los coches de Das WeltAuto (la gran mayoría), `car["fotos"]` contiene **rutas absolutas del disco local** (ej. `/Users/.../fotos/01 - CUPRA Formentor - 36.900€/foto_01.jpg`), puestas ahí por `actualizar_catalogo.py` solo para que `copiar_fotos()` sepa de dónde copiar — no son válidas para un `<img src>`. La ruta web correcta sale de `copiar_fotos(coches)` (función existente en `generar_web.py`, línea ~63). Para los coches de MotorFlash sí es correcto usar `car["fotos"]` directamente (ya vienen con ruta web relativa correcta).
- **CORRECCIÓN #2 (encontrada durante la Task 4 — reemplaza lo que decía antes sobre `idx`):** `copiar_fotos()` originalmente guardaba las fotos en `web_fotos/{idx:02d}/` con `idx` = posición 1-based del coche en la lista de coches activos (`enumerate(coches, start=1)`) — **no** `car["n"]`. Esto es un bug real: como `idx` depende de qué coches están activos ESE día, cuando un coche se retira, TODOS los coches que venían después de él en la lista se corren de número de carpeta — no solo el retirado, cualquier coche activo puede terminar con las fotos de otro. La corrección ya aplicada: `copiar_fotos()` ahora guarda y devuelve `rutas` con clave `car["n"]` (estable), no `idx` posicional — `web_fotos/{n:02d}/` significa siempre "fotos del coche actualmente numerado n", sin importar qué pasa con los demás coches. Patrón final correcto a usar en todo este plan:
  ```python
  rutas = copiar_fotos(coches)   # llamar UNA vez en main(), antes de generar fichas/índice
                                  # rutas: dict[int, list[str]], clave = car["n"] (NO posición/idx)
  for car in coches:
      n = car["n"]
      fotos_urls = car.get("fotos", []) if car.get("fuente") == "motorflash" else rutas.get(n, [])
      # pasar fotos_urls (no car["fotos"]) a build_coche_html() y a la tarjeta del índice
  ```
  Nunca reconstruyas la ruta a mano combinando `f"web_fotos/{n:02d}/..."` — usá siempre el resultado de esta resolución (`fotos_urls`), sea que venga de `rutas` (clave `n`) o de `car["fotos"]` (caso MotorFlash). No uses `idx`/`enumerate` para esto en ningún lado.
- `datos_coches.json` es la fuente de datos. Un coche con `"estado": "Retirado"` ya no está publicado en Das WeltAuto (vendido) — según el diseño aprobado, su ficha **no se borra**: se genera igual, mostrando un aviso "Vendido" en vez del precio/CTA de reserva.
- **Dos fuentes de datos con campos distintos:** la mayoría de coches vienen de Das WeltAuto (`car.get("fuente")` ausente o `"dwa"`, con `car["url"]` = ruta relativa a `dasweltauto.es`). 2 coches actualmente vienen de MotorFlash (`car.get("fuente") == "motorflash"`, con `car["url_motorflash"]` = URL absoluta completa, y `car.get("url")` es `None`). El campo `"url"` final para el enlace "Ver ficha original" y para `og:url`/link externo debe resolverse así (igual que ya lo hacía el generador viejo — buscá `DASWELTAUTO + c["url"]` con `grep -n` para confirmarlo antes de escribir el nuevo código):
  ```python
  url_externa = car.get("url_motorflash") or (f"{DASWELTAUTO}{car['url']}" if car.get("url") else "")
  ```

---

### Task 1: Extraer el motor de la calculadora a `assets/calculadora.js` (archivo compartido)

**Files:**
- Create: `/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/assets/calculadora.js`

- [ ] **Step 1: Ejecutar el script de extracción**

Run:
```bash
cd "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda"
python3 << 'PYEOF'
lines = open("generar_web.py", encoding="utf-8").read().split("\n")

def bloque(a, b):
    return "\n".join(lines[a-1:b])

def unescape(s):
    return s.replace("{{", "{").replace("}}", "}")

partes = [
    unescape(bloque(1295, 1306)),   # helpers: estadoLabel, fmtCuota, esReservado, norm
    unescape(bloque(1442, 1467)),   # VR_TABLE + CV2 config
    unescape(bloque(1468, 1468)),   # CV2_ALL_PLAZOS
    unescape(bloque(1471, 2068)),   # CV2_MANT + todas las funciones cv2*
    unescape(bloque(2069, 2169)),   # initCalc(c)
    unescape(bloque(2234, 2240)),   # goSlide
    unescape(bloque(2253, 2258)),   # swipe táctil
]

salida = "\n\n".join(partes)

if "{{" in salida:
    raise SystemExit("ERROR: quedaron llaves dobles sin desescapar — revisar rangos")

open("/tmp/calculadora_extraida.js", "w", encoding="utf-8").write(salida)
print(f"OK — {len(salida.splitlines())} líneas extraídas a /tmp/calculadora_extraida.js")
PYEOF
```
Expected: `OK — <N> líneas extraídas a /tmp/calculadora_extraida.js` sin error.

- [ ] **Step 2: Verificar que no quedó ninguna interpolación Python de una sola llave**

Run: `grep -nE '\{[A-Z][A-Za-z_]*\}' /tmp/calculadora_extraida.js`
Expected: sin salida. Si aparece algo como `{COMERCIAL_NOMBRE}` o `{cars_js}`, DETENTE — significa que un rango capturó contenido fuera de scope; ajustá el rango antes de continuar (no lo "arregles" borrando la línea a mano).

- [ ] **Step 3: Escribir `assets/calculadora.js`**

Crear el archivo con este contenido: primero un comentario de cabecera, después el contenido completo de `/tmp/calculadora_extraida.js` (generado en el Step 1 — pegalo tal cual, sin modificarlo), y al final la función `cargarFicha` (nueva, generalizada a partir de la que ya funciona en `coches/01-cupra-formentor.html` — agrega el manejo del estado "vendido" que esa versión de prueba no necesitaba porque el coche de ejemplo estaba Disponible):

**IMPORTANTE — orden de declaraciones (bug ya detectado y corregido una vez, no reintroducirlo):** el contenido extraído en el Step 1 termina con la función `goSlide(i) {...}` seguida del bloque de swipe táctil (`let touchStartX = 0; slides.addEventListener('touchstart', ...); slides.addEventListener('touchend', ...);`), y ese bloque de swipe usa `slides`/`slideActual` por nombre. Los 6 `const`/`let` (`slides`, `dotsEl`, `prevBtn`, `nextBtn`, `fotosModal`, `slideActual`) **NO van inmediatamente después del marcador `PEGAR AQUÍ`** (eso los deja después del bloque de swipe en el archivo final, violando temporal-dead-zone: `slides.addEventListener(...)` se ejecutaría antes de que `const slides` exista, y el script entero lanza `ReferenceError` al cargar — ninguna ficha se pintaría). Van **pegados después del cierre de la función `goSlide(i) {...}` extraída, y ANTES del bloque `let touchStartX = 0; ...` del mismo contenido extraído** — es decir, hay que insertarlos DENTRO del bloque pegado tal cual, no antes de él. Ver más abajo dónde exactamente.

```javascript
/* ══════════════════════════════════════════════════════════════════
   Automóviles Rueda — Motor de calculadora de financiación (compartido)
   Extraído de generar_web.py — condiciones VWFS Agosto 2026.
   NO modificar la lógica de cv2* / initCalc a mano: si cambian las
   condiciones, se actualiza generar_web.py y se re-ejecuta la
   extracción (Task 1 de docs/superpowers/plans/2026-08-08-fichas-individuales-fase2-generalizacion.md).
   ══════════════════════════════════════════════════════════════════ */

/* PEGAR AQUÍ: el contenido completo de /tmp/calculadora_extraida.js generado en el Step 1 */

/* ...contenido extraído... termina así (NO modificar la lógica, solo referencia para ubicar el punto de inserción):

function goSlide(i) {
  if (!fotosModal.length) return;
  slideActual = (i + fotosModal.length) % fotosModal.length;
  slides.style.transform = `translateX(${-slideActual * 100}%)`;
  dotsEl.querySelectorAll('.gallery-dot').forEach((d,idx) =>
    d.classList.toggle('active', idx === slideActual));
}

*/

// ── Aquí, justo después del cierre de goSlide() y ANTES de "let touchStartX" ──
const slides   = document.getElementById('gallery-slides');
const dotsEl   = document.getElementById('gallery-dots');
const prevBtn  = document.getElementById('gallery-prev');
const nextBtn  = document.getElementById('gallery-next');
let fotosModal = [];
let slideActual = 0;

/* ...y recién ahora sigue el resto del contenido extraído tal cual, el bloque de swipe táctil:

let touchStartX = 0;
slides.addEventListener('touchstart', e => { touchStartX = e.touches[0].clientX; }, {passive:true});
slides.addEventListener('touchend', e => {
  const dx = e.changedTouches[0].clientX - touchStartX;
  if (Math.abs(dx) > 50) goSlide(slideActual + (dx < 0 ? 1 : -1));
});

*/

// Rellena la ficha con los datos del único coche embebido en la página (COCHE).
// Si el coche está Retirado (vendido), oculta precio/CTA y muestra el aviso.
function cargarFicha(c) {
  fotosModal = c.fotos.length ? c.fotos : [];
  slideActual = 0;

  slides.innerHTML = fotosModal.length
    ? fotosModal.map((f,i) => `<div class="gallery-slide"><img src="${f}" alt="Foto ${i+1}" loading="lazy"></div>`).join('')
    : `<div class="gallery-slide" style="display:grid;place-items:center;color:var(--muted);width:100%;height:100%">Sin fotos</div>`;
  slides.style.transform = 'translateX(0)';

  dotsEl.innerHTML = fotosModal.length > 1
    ? fotosModal.map((_,i) => `<div class="gallery-dot ${i===0?'active':''}" data-i="${i}"></div>`).join('') : '';
  dotsEl.querySelectorAll('.gallery-dot').forEach(d =>
    d.addEventListener('click', () => goSlide(+d.dataset.i)));

  const showNav = fotosModal.length > 1;
  prevBtn.style.display = showNav ? '' : 'none';
  nextBtn.style.display = showNav ? '' : 'none';

  document.getElementById('m-modelo').textContent = c.modelo;
  document.getElementById('m-version').textContent = c.version;

  const specs = [
    ['Combustible', c.combustible], ['Kilómetros', c.km + ' km'],
    ['Matrícula', c.fecha], ['Cambio', c.cambio],
    ['Color', c.color], ['Ubicación', c.ubicacion],
  ].filter(([,v]) => v);
  document.getElementById('m-specs').innerHTML = specs.map(([l,v]) =>
    `<div class="rd-spec-badge"><div class="lbl">${l}</div><div class="val">${v}</div></div>`).join('');

  const equip = c.equipamiento || [];
  const equipSection = document.getElementById('equip-section');
  if (equip.length) {
    document.getElementById('m-equip').innerHTML = equip.map(e =>
      `<div class="equip-item"><span class="equip-check">✓</span><span>${e}</span></div>`).join('');
    equipSection.style.display = '';
  } else { equipSection.style.display = 'none'; }

  if (c.vendido) {
    document.getElementById('m-precio').textContent = '';
    document.getElementById('m-precio-sticky').textContent = '';
    const pill = document.getElementById('m-estado-pill');
    pill.textContent = '🚫 Vendido';
    pill.classList.add('reservado');
    document.getElementById('m-financiacion').style.display = 'none';
    document.getElementById('m-vendido-banner').style.display = '';
    document.getElementById('m-vendido-sticky').style.display = 'flex';
    document.getElementById('m-sticky-financiacion').style.display = 'none';
    return;
  }

  document.getElementById('m-precio').textContent = c.precio + ' €';
  document.getElementById('m-precio-sticky').textContent = c.precio + ' €';
  const pill = document.getElementById('m-estado-pill');
  const reservado = esReservado(c.estado);
  pill.textContent = reservado ? '🟠 Reservado' : '✅ Disponible';
  pill.classList.add(reservado ? 'reservado' : 'disponible');

  initCalc(c);

  const link = document.getElementById('m-link');
  if (c.url) { link.href = c.url; link.style.display = ''; } else { link.style.display = 'none'; }
}

prevBtn.addEventListener('click', () => goSlide(slideActual - 1));
nextBtn.addEventListener('click', () => goSlide(slideActual + 1));
```

- [ ] **Step 4: Verificar que el archivo no tiene el marcador sin reemplazar ni llaves dobles**

Run:
```bash
grep -c "PEGAR AQUÍ" "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/assets/calculadora.js"
grep -c '{{' "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/assets/calculadora.js"
```
Expected: ambos `0`.

- [ ] **Step 5: Commit**

```bash
cd "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda"
git add assets/calculadora.js
git commit -m "Fase 2: extraer motor de calculadora a assets/calculadora.js (compartido)"
```

---

### Task 2: Función generadora de fichas individuales (`build_coche_html`) en `generar_web.py`

**Files:**
- Modify: `/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/generar_web.py`

- [ ] **Step 1: Leer el archivo de referencia validado**

Leer completo `/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/coches/01-cupra-formentor.html`. Es la plantilla exacta a generalizar — cada elemento visual y cada `id` de este archivo debe existir igual en la función Python de abajo, solo que con los valores parametrizados en vez de hardcodeados a "CUPRA Formentor".

- [ ] **Step 2: Agregar `build_coche_html()` a `generar_web.py`**

Agregar esta función nueva antes de `def build_html(` (antes de la línea `174` actual — verificar con `grep -n "^def build_html" generar_web.py` que sigue siendo esa línea antes de insertar):

```python
import re as _re_slug

def slug_coche(modelo: str) -> str:
    s = modelo.lower()
    for a, b in [('á','a'),('é','e'),('í','i'),('ó','o'),('ú','u'),('ñ','n')]:
        s = s.replace(a, b)
    s = _re_slug.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s

DOMINIO_WEB = "https://andresvazquez11.github.io/automoviles-rueda-catalogo"

def build_coche_html(car: dict) -> str:
    n = car["n"]
    slug = slug_coche(car["modelo"])
    vendido = car["estado"] == "Retirado"
    fotos_raw = car.get("fotos") or []
    fotos = [f"../{f}" for f in fotos_raw]   # la ficha vive en coches/, un nivel más abajo que el root
    foto_principal_root = fotos_raw[0] if fotos_raw else f"web_fotos/{n:02d}/foto_01.jpg"
    url_externa = car.get("url_motorflash") or (f"{DASWELTAUTO}{car['url']}" if car.get("url") else "")

    titulo = f'{car["modelo"]} {car["version"]} · {car["precio"]}€ · Automóviles Rueda' if not vendido \
        else f'{car["modelo"]} — Vendido · Automóviles Rueda'
    descripcion = f'{car.get("combustible","")} · {car.get("km","")} km · Matriculación {car.get("fecha","")} · {car.get("cambio","")} · {car.get("ubicacion","")} · Automóviles Rueda'

    coche_json = json.dumps({
        "n": n, "modelo": car["modelo"], "version": car["version"],
        "combustible": car.get("combustible",""), "km": car.get("km",""),
        "fecha": car.get("fecha",""), "fin_fecha_iso":
            (lambda f: f"{f.split('/')[1]}-{f.split('/')[0]}" if f and "/" in f and len(f.split("/"))==2 else "")(car.get("fecha","")),
        "cambio": car.get("cambio",""), "color": car.get("color",""),
        "precio": car["precio"], "estado": car["estado"], "vendido": vendido,
        "url": url_externa,
        "equipamiento": car.get("equipamiento", []),
        "fotos": fotos,
    }, ensure_ascii=False)

    vendido_banner = '' if not vendido else '''
  <div class="rd-vendido-banner" id="m-vendido-banner">
    Este vehículo ya no está disponible.
    <a href="../index.html">Ver coches disponibles →</a>
  </div>'''

    return f'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{titulo}</title>
<meta name="description" content="{descripcion}">

<meta property="og:type" content="product">
<meta property="og:title" content="{titulo}">
<meta property="og:description" content="{descripcion}">
<meta property="og:image" content="{DOMINIO_WEB}/{foto_principal_root}">
<meta property="og:url" content="{DOMINIO_WEB}/coches/{n:02d}-{slug}.html">

<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@500;600;700&family=Work+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../assets/estilos.css">
<style>
{CALCULADORA_CSS}
</style>
</head>
<body>

<header class="rd-header">
  <div class="rd-header-brand">
    <strong>Automóviles Rueda</strong>
    <span>{COMERCIAL_NOMBRE} · {COMERCIAL_TELEFONO}</span>
  </div>
</header>
<a class="rd-back" href="../index.html">&#8249; Volver al catálogo</a>
{vendido_banner}

<div class="rd-coche-wrap">
  <div class="rd-gallery-frame modal-gallery" id="modal-gallery">
    <div class="gallery-slides" id="gallery-slides"></div>
    <button class="gallery-btn prev" id="gallery-prev">&#8249;</button>
    <button class="gallery-btn next" id="gallery-next">&#8250;</button>
    <div class="gallery-dots" id="gallery-dots"></div>
  </div>

  <div class="rd-price-panel">
    <div>
      <div class="modelo" id="m-modelo"></div>
      <div class="version" id="m-version"></div>
      <div class="estado" id="m-estado-pill"></div>
    </div>
    <div class="precio-block">
      <div class="precio" id="m-precio"></div>
    </div>
  </div>

  <div class="rd-spec-badges" id="m-specs"></div>

  <div class="rd-section equip-section" id="equip-section">
    <h3>Equipamiento</h3>
    <div class="equip-grid" id="m-equip"></div>
  </div>

  <div class="modal-financiacion" id="m-financiacion">
{CALCULADORA_HTML_INTERIOR}
  </div>

  <div class="rd-footnote">
    <a id="m-link" href="#" target="_blank" rel="noopener">Ver ficha original en Das WeltAuto ↗</a>
  </div>
</div>

<div class="rd-sticky-mobile" id="m-vendido-sticky" style="display:none">
  <div>Vendido</div>
  <a class="rd-btn rd-btn-secondary" href="../index.html">Ver disponibles</a>
</div>
<div class="rd-sticky-mobile" id="m-sticky-financiacion">
  <div class="precio" id="m-precio-sticky"></div>
  <a class="rd-btn rd-btn-primary" href="#m-financiacion">Ver financiación</a>
</div>

<script src="../assets/calculadora.js"></script>
<script>
const COCHE = {coche_json};
cargarFicha(COCHE);
</script>
</body>
</html>
'''
```

**IMPORTANTE — dos placeholders en la plantilla de arriba que hay que resolver antes de que el código compile:**

1. `{CALCULADORA_CSS}` — no es una interpolación real todavía. Reemplazalo por el contenido real: es el mismo bloque CSS que ya está pegado dentro de `coches/01-cupra-formentor.html` entre `<style>` y `</style>` (búscalo con `grep -n "<style>" -A2 coches/01-cupra-formentor.html` para ubicar el inicio exacto). Cópialo tal cual a una variable Python `CALCULADORA_CSS = """..."""` definida antes de `build_coche_html`, y referenciala en el f-string de arriba como `{CALCULADORA_CSS}` (ya es una interpolación f-string válida una vez que existe esa variable — no hace falta escapar llaves porque este f-string es Python normal, no la plantilla `.format()` de `build_html()`).
2. `{CALCULADORA_HTML_INTERIOR}` — mismo criterio: el contenido interior de `<div class="modal-financiacion" id="m-financiacion">` en `coches/01-cupra-formentor.html` (desde el comentario `<!-- Car info bar -->` hasta el cierre de ese mismo div, sin incluir el div en sí). Cópialo a una variable Python `CALCULADORA_HTML_INTERIOR = """..."""` definida antes de `build_coche_html`, con **una sola edición**: agregar `id="m-vendido-banner"` ya está resuelto arriba (es otro elemento), así que acá no hay que cambiar nada más — pegalo literal.

- [ ] **Step 3: Agregar el CSS del aviso de "Vendido" a `assets/estilos.css`**

```css
/* ── Aviso de coche vendido ── */
.rd-vendido-banner {
  max-width: 880px; margin: 0 auto; padding: 0 20px;
  background: #fdeaea; color: #a01c23; border: 1px solid #f3c6c6;
  border-radius: var(--rd-radius-sm); padding: 12px 16px; margin-top: 8px;
  font-size: 14px; font-weight: 600; text-align: center;
}
.rd-vendido-banner a { color: var(--rd-red); text-decoration: underline; margin-left: 8px; }
```
Agregalo al final de `/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/assets/estilos.css`.

- [ ] **Step 4: Verificar que el archivo Python sigue siendo válido**

Run: `cd "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda" && python3 -c "import ast; ast.parse(open('generar_web.py', encoding='utf-8').read())" && echo "OK sintaxis válida"`
Expected: `OK sintaxis válida`

- [ ] **Step 5: Probar `build_coche_html()` con un coche real, aislado**

Run:
```bash
cd "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda"
python3 -c "
import json, importlib.util
spec = importlib.util.spec_from_file_location('generar_web', 'generar_web.py')
# generar_web.py ejecuta main() al importarlo (ver 'main()' al final del archivo) —
# para probar solo build_coche_html sin correr todo el proceso de scraping/fotos,
# copiá la función build_coche_html (y sus variables CALCULADORA_CSS/CALCULADORA_HTML_INTERIOR/slug_coche/DOMINIO_WEB)
# a un archivo temporal de prueba en vez de importar generar_web.py directamente.
"
```
En vez de importar el módulo completo (que dispara todo `main()`), copiá manualmente `build_coche_html`, `slug_coche`, `DOMINIO_WEB`, `CALCULADORA_CSS`, `CALCULADORA_HTML_INTERIOR`, `DASWELTAUTO` (ya existe en el archivo, buscalo con `grep -n "^DASWELTAUTO"`) a un script suelto `/tmp/test_build_coche.py`, y al final agregá:
```python
data = json.loads(open("/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/datos_coches.json", encoding="utf-8").read())
car = next(c for c in data if c["n"] == 1)
html = build_coche_html(car)
open("/tmp/prueba_coche_1.html", "w", encoding="utf-8").write(html)
print("OK —", len(html.splitlines()), "líneas generadas")
```
Run: `python3 /tmp/test_build_coche.py`
Expected: `OK — <N> líneas generadas` sin traceback.

- [ ] **Step 6: Comparar la salida contra el archivo de referencia**

Run: `diff <(grep -o 'id="[a-z0-9-]*"' /tmp/prueba_coche_1.html | sort -u) <(grep -o 'id="[a-z0-9-]*"' "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/coches/01-cupra-formentor.html" | sort -u)`
Expected: sin diferencias relevantes (puede haber ids nuevos como `m-vendido-banner`/`m-vendido-sticky`/`m-sticky-financiacion` que no existían en la referencia porque ese coche no está vendido — está bien, son intencionales). Si falta algún id que SÍ está en la referencia (`m-modelo`, `m-precio`, `m-specs`, `m-equip`, `cv2-btn-wa`, etc.), DETENTE — la calculadora no va a poder poblarse.

- [ ] **Step 7: Commit**

```bash
cd "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda"
git add generar_web.py assets/estilos.css
git commit -m "Fase 2: agregar build_coche_html() — genera la ficha HTML de un coche"
```

---

### Task 3: Función generadora del catálogo (`build_index_html`) en `generar_web.py`

**Files:**
- Modify: `/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/generar_web.py`

- [ ] **Step 1: Leer el archivo de referencia validado**

Leer completo `/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/index-prototipo.html`. Contiene ya el diseño de tarjeta aprobado (badges, pastillas, navegación de fotos, animación) y el bloque `<script>` genérico que mueve las fotos de las tarjetas (no depende de datos de un coche específico — se puede copiar tal cual).

- [ ] **Step 2: Agregar `build_index_html()` a `generar_web.py`**

Agregar esta función después de `build_coche_html` (agregada en el Task 2):

```python
def etiqueta_dgt_badge(combustible: str) -> tuple[str, str]:
    c = (combustible or "").lower()
    if "eléctrico" in c or "electrico" in c: return "CERO", "cero"
    if "mild" in c: return "ECO", "eco"
    if "híbrido" in c or "hibrido" in c: return "CERO", "cero"
    return "C", "c"

DGT_URLS = {
    "CERO": "https://commons.wikimedia.org/wiki/Special:FilePath/DistAmbDGT_CeroEmisiones.svg",
    "ECO":  "https://commons.wikimedia.org/wiki/Special:FilePath/DistAmbDGT_ECO.svg",
    "C":    "https://commons.wikimedia.org/wiki/Special:FilePath/DistAmbDGT_C.svg",
}

def build_card_html(car: dict, hist: dict, fotos: list[str]) -> str:
    n = car["n"]
    slug = slug_coche(car["modelo"])
    href = f"coches/{n:02d}-{slug}.html"
    # `fotos` la resuelve quien llama (ver Task 4): rutas.get(car["n"], []) para DWA,
    # car.get("fotos", []) para MotorFlash. NUNCA leer car["fotos"] acá directo
    # (para DWA es una ruta absoluta del disco local, no web) ni reconstruir desde n.

    reservado = car["estado"] == "No disponible"
    estado_cls = "reservado" if reservado else "disponible"
    estado_lbl = "Reservado" if reservado else "Disponible"
    dgt_txt, dgt_cls = etiqueta_dgt_badge(car.get("combustible", ""))
    cuota = _cuota_display(car)
    p_ant = precio_maximo_historico(car.get("url",""), int(str(car["precio"]).replace(".","").replace(",","").split()[0]), hist)

    fotos_html = "".join(
        f'<img src="{f}" alt="{car["modelo"]}" loading="lazy" class="{"activa" if i==0 else ""}">'
        for i, f in enumerate(fotos)
    )
    dots_html = "".join(f'<span class="rd-card-dot {"activa" if i==0 else ""}"></span>' for i in range(len(fotos))) if len(fotos) > 1 else ""
    nav_html = '<button class="rd-card-nav prev" aria-label="Foto anterior">&#8249;</button><button class="rd-card-nav next" aria-label="Foto siguiente">&#8250;</button>' if len(fotos) > 1 else ""
    precio_row = (
        f'<span class="rd-card-precio-old">{p_ant:,.0f} €</span><span class="rd-card-precio">{car["precio"]} €</span>'.replace(",", ".")
        if p_ant else f'<span class="rd-card-precio">{car["precio"]} €</span>'
    )

    return f'''<a class="rd-card" href="{href}">
  <div class="rd-card-media">
    <div class="rd-card-photos">{fotos_html}</div>
    {nav_html}
    <div class="rd-card-dots">{dots_html}</div>
    <span class="rd-badge-estado {estado_cls}">{estado_lbl}</span>
    {'<span class="rd-badge-oferta">OFERTA</span>' if p_ant else ''}
    <span class="rd-badge-dgt"><img src="{DGT_URLS[dgt_txt]}" alt="Etiqueta {dgt_txt}" loading="lazy"></span>
    {f'<span class="rd-badge-fotos">📷 {len(fotos)}</span>' if len(fotos) > 1 else ''}
  </div>
  <div class="rd-card-body">
    <div class="rd-card-modelo">{car["modelo"]}</div>
    <div class="rd-card-version">{car["version"]}</div>
    <div class="rd-card-pills">
      {f'<span class="rd-pill">⛽ {car["combustible"]}</span>' if car.get("combustible") else ''}
      {f'<span class="rd-pill">🛣️ {car["km"]} km</span>' if car.get("km") else ''}
      {f'<span class="rd-pill">📅 {car["fecha"]}</span>' if car.get("fecha") else ''}
      {f'<span class="rd-pill">⚙️ {car["cambio"]}</span>' if car.get("cambio") else ''}
    </div>
    <div class="rd-card-price-row">
      <div>{precio_row}</div>
      <div class="rd-card-cuota">Desde <strong>{cuota:.0f} €/mes</strong></div>
    </div>
  </div>
</a>'''

def build_index_html(cars: list[dict], rutas: dict[int, list[str]]) -> str:
    # NOTA (Corrección #2): `rutas` está keyed por car["n"] estable, no por
    # posición/idx — ver "CORRECCIÓN #2" en la sección de contexto arriba.
    hist = _cargar_historial_precios()
    visibles = [c for c in cars if c.get("estado") != "Retirado"]
    tarjetas = "\n".join(
        build_card_html(
            car, hist,
            car.get("fotos", []) if car.get("fuente") == "motorflash" else rutas.get(car["n"], [])
        )
        for car in cars
        if car.get("estado") != "Retirado"
    )

    return f'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Automóviles Rueda — Coches seminuevos SEAT · CUPRA · Volkswagen</title>
<meta name="description" content="Catálogo de vehículos seminuevos con garantía oficial Das WeltAuto. {len(visibles)} coches disponibles en Málaga.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@500;600;700&family=Work+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/estilos.css">
</head>
<body>
<header class="rd-header">
  <div class="rd-header-brand">
    <strong>Automóviles Rueda</strong>
    <span>{COMERCIAL_NOMBRE} · {COMERCIAL_TELEFONO}</span>
  </div>
</header>
<div class="rd-grid">
{tarjetas}
</div>
<script>
document.querySelectorAll('.rd-card-nav').forEach(btn => {{
  btn.addEventListener('click', e => {{
    e.preventDefault();
    e.stopPropagation();
    const media = btn.closest('.rd-card-media');
    const imgs  = [...media.querySelectorAll('.rd-card-photos img')];
    const dots  = [...media.querySelectorAll('.rd-card-dot')];
    let idx = imgs.findIndex(img => img.classList.contains('activa'));
    idx = btn.classList.contains('next')
      ? (idx + 1) % imgs.length
      : (idx - 1 + imgs.length) % imgs.length;
    imgs.forEach((img, i) => img.classList.toggle('activa', i === idx));
    dots.forEach((d, i) => d.classList.toggle('activa', i === idx));
  }});
}});
</script>
</body>
</html>
'''
```

Nota: esta función usa `{{`/`}}` SOLO dentro del bloque `<script>` porque ahí sí hace falta escapar (es un f-string de Python, y el JS usa `{` `}` reales que deben duplicarse para no ser interpretados como interpolación). Fuera de ese bloque `<script>`, las llaves simples (`{car["modelo"]}`, etc.) son interpolaciones Python válidas y NO se escapan.

- [ ] **Step 3: Verificar sintaxis**

Run: `cd "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda" && python3 -c "import ast; ast.parse(open('generar_web.py', encoding='utf-8').read())" && echo "OK sintaxis válida"`
Expected: `OK sintaxis válida`

- [ ] **Step 4: Commit**

```bash
cd "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda"
git add generar_web.py
git commit -m "Fase 2: agregar build_index_html() — genera el catálogo con tarjetas y enlaces reales"
```

---

### Task 4: Conectar todo en `main()` — generar las 61 fichas + el índice + limpiar huérfanas

**Files:**
- Modify: `/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/generar_web.py` (función `main()`, al final del archivo)

- [ ] **Step 1: Leer la función `main()` actual completa**

Run: `grep -n "^def main" "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/generar_web.py"` para ubicarla, y leela completa con la herramienta Read.

**IMPORTANTE:** en `main()`, la variable `coches` se carga con `json.loads(...)` y **enseguida se filtra** con `coches = [c for c in coches if c.get("estado") != "Retirado"]` (esto ya está en el código, no lo agregaste vos, no lo toques). O sea, `coches` NUNCA incluye los coches vendidos, y no incluye a los coches Retirado en absoluto. `copiar_fotos(coches)` se llama con esa lista filtrada y devuelve `rutas` **keyed por `car["n"]`** (ver "CORRECCIÓN #2" en el contexto de arriba — no por posición/idx).

Como esta Fase 2 sí necesita generar una ficha para los coches Retirado (con el aviso de "Vendido"), hace falta la lista COMPLETA sin filtrar además de la filtrada. Guardá ambas antes de tocar nada más — agregá esta línea INMEDIATAMENTE DESPUÉS de donde hoy se hace `coches = json.loads(JSON_PATH.read_text(...))` (antes del filtro que le sigue):

```python
    todos_los_coches = json.loads(JSON_PATH.read_text(encoding="utf-8"))
```

Dejá el resto tal cual está (el `coches = [c for c in coches if ...]` que sigue, `copiar_fotos(coches)`, etc. no se tocan — solo agregás esa línea nueva antes, guardando una copia completa sin filtrar).

- [ ] **Step 2: Reemplazar la generación de `index.html` y agregar la generación de las fichas**

Dentro de `main()`, reemplazar la línea que hoy escribe `index.html` usando `build_html(...)` por esto:

```python
    coches_dir = OUTPUT_DIR / "coches"
    coches_dir.mkdir(exist_ok=True)

    slugs_validos = set()
    for car in todos_los_coches:
        n = car["n"]
        slug = slug_coche(car["modelo"])
        slugs_validos.add(f"{n:02d}-{slug}.html")

        if car.get("estado") == "Retirado":
            # Ya no se scrapea ni se copian fotos nuevas para estos — si la carpeta
            # de una corrida anterior todavía existe, se reusa tal cual; si no, sin fotos.
            # web_fotos/{n:02d}/ es estable (rutas keyed por n, no por idx — Corrección #2),
            # así que esta carpeta sigue siendo del MISMO coche aunque otros se retiren.
            carpeta_vieja = OUTPUT_DIR / "web_fotos" / f"{n:02d}"
            fotos_urls = sorted(
                f"web_fotos/{n:02d}/{p.name}" for p in carpeta_vieja.glob("foto_*.jpg")
            ) if carpeta_vieja.exists() else []
        elif car.get("fuente") == "motorflash":
            fotos_urls = car.get("fotos", [])
        else:
            fotos_urls = rutas.get(n, [])

        html_coche = build_coche_html(car, fotos_urls)
        (coches_dir / f"{n:02d}-{slug}.html").write_text(html_coche, encoding="utf-8")
    print(f"  {len(todos_los_coches)} fichas individuales generadas en coches/")

    archivadas = 0
    for f in coches_dir.glob("*.html"):
        if f.name not in slugs_validos:
            f.unlink()
            archivadas += 1
    if archivadas:
        print(f"  {archivadas} ficha(s) huérfana(s) eliminada(s) de coches/ (coche ya no existe)")

    html_index = build_index_html(coches, rutas)
    (OUTPUT_DIR / "index.html").write_text(html_index, encoding="utf-8")
    print(f"  index.html regenerado con el catálogo nuevo")
```

Confirmá con `grep -n "rutas = copiar_fotos"` que la variable con el resultado de `copiar_fotos(coches)` en el código actual se llama efectivamente `rutas` (si tiene otro nombre, usá ese nombre en el bloque de arriba en vez de `rutas`) — y confirmá que este bloque nuevo va DESPUÉS de esa llamada a `copiar_fotos()`, no antes (necesita que `rutas` ya exista).

- [ ] **Step 3: Verificar sintaxis**

Run: `cd "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda" && python3 -c "import ast; ast.parse(open('generar_web.py', encoding='utf-8').read())" && echo "OK sintaxis válida"`
Expected: `OK sintaxis válida`

- [ ] **Step 4: Ejecutar el generador completo**

Run: `cd "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda" && python3 generar_web.py`
Expected: sin traceback; en la salida deben verse las líneas `"N fichas individuales generadas en coches/"` y `"index.html regenerado con el catálogo nuevo"`, con N cercano a 61-62 (todos los coches, incluidos los "Retirado").

- [ ] **Step 5: Verificar la cantidad de archivos generados**

Run: `ls "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/coches/" | wc -l`
Expected: un número igual a la cantidad total de coches en `datos_coches.json` (incluye "Retirado"). Confirmalo con: `python3 -c "import json; print(len(json.load(open('datos_coches.json'))))"` — ambos números deben coincidir.

- [ ] **Step 6: Commit**

```bash
cd "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda"
git add generar_web.py coches/ index.html
git commit -m "Fase 2: generar las 61 fichas individuales reales + catálogo nuevo (index.html)"
```

---

### Task 5: Verificación visual real — varios coches, estados y móvil

**Files:** ninguno (solo verificación)

- [ ] **Step 1: Levantar un servidor local**

Run:
```bash
cd "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda"
nohup python3 -m http.server 8899 > /tmp/httpserver_fase2.log 2>&1 &
sleep 1
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8899/index.html
```
Expected: `200`

- [ ] **Step 2: Abrir el catálogo (`index.html`, no `index-prototipo.html`) en el navegador y verificar visualmente**

Navegar a `http://localhost:8899/index.html`, tomar screenshot. Verificar: se ve el mismo diseño aprobado en la Fase 1 (badges, pastillas, navegación de fotos), y AHORA TODAS las tarjetas son clickeables (no solo la del CUPRA Formentor). Hacer clic en 2-3 tarjetas de coches distintos (no solo n=1) y confirmar que cada una abre su propia ficha con datos correctos (modelo, precio, fotos, calculadora funcionando).

- [ ] **Step 3: Verificar un coche "Retirado" (vendido)**

Run: `python3 -c "
import json
data = json.loads(open('/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/datos_coches.json', encoding='utf-8').read())
c = next((x for x in data if x['estado']=='Retirado'), None)
print(c['n'], c['modelo']) if c else print('No hay ningún coche Retirado ahora mismo — saltar este paso')
"`
Si hay un coche Retirado, navegar directo a `http://localhost:8899/coches/{n:02d}-{slug}.html` con ese `n` (usar el slug real generado, listalo con `ls coches/ | grep -i <n con dos dígitos>`). Verificar: aparece el aviso "Este vehículo ya no está disponible", NO se ve precio ni la calculadora, y el enlace "Ver coches disponibles" vuelve al catálogo.

- [ ] **Step 4: Verificar en tamaño de celular**

Usar `resize_window` a preset `mobile` (375x812) sobre la ficha de un coche disponible. Verificar: la calculadora se ve como tarjeta contenida (no gigante), la barra fija inferior muestra precio + "Ver financiación", y al tocarla hace scroll hasta la calculadora.

- [ ] **Step 5: Verificar que no hay errores de consola**

Run vía herramienta de navegador: `read_console_messages` con `onlyErrors: true` en al menos 2 fichas distintas y en el catálogo. Expected: sin errores.

- [ ] **Step 6: Detener el servidor**

Run: `pkill -f "http.server 8899"`

Este es un checkpoint humano además de automatizable: mostrale a Andrés el catálogo completo y 2-3 fichas reales (no solo la de prueba) antes de continuar a la Task 6 (que borra código viejo — mejor confirmarlo funcionando primero).

---

### Task 6: Eliminar el generador viejo (`build_html`, el modal) — limpieza final

**Files:**
- Modify: `/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/generar_web.py`

- [ ] **Step 1: Confirmar que `build_html()` ya no se llama desde ningún lado**

Run: `grep -n "build_html(" "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/generar_web.py"`
Expected: la ÚNICA aparición debe ser la línea `def build_html(...):` (su definición). Si aparece alguna llamada activa (`= build_html(...)`), DETENTE — significa que la Task 4 no reemplazó completamente el uso viejo; no borres la función todavía.

- [ ] **Step 2: Localizar el rango completo de `build_html()`**

Run: `grep -n "^def build_html\|^def main" "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/generar_web.py"`
Esto da la línea de inicio (`def build_html`) y la línea de inicio de la siguiente función top-level (`def main`) — todo lo que está entre ambas (sin incluir `def main`) es el cuerpo completo de `build_html()` a borrar.

- [ ] **Step 3: Borrar el cuerpo de `build_html()`**

Usando las líneas exactas obtenidas en el Step 2, borrar desde `def build_html(...)` hasta la línea inmediatamente anterior a `def main(...)`. (Usar la herramienta de edición para eliminar ese rango completo — es un bloque grande de una sola función, no hace falta preservar nada de su interior porque ya fue reemplazado por `build_coche_html` + `build_index_html`.)

- [ ] **Step 4: Verificar sintaxis**

Run: `cd "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda" && python3 -c "import ast; ast.parse(open('generar_web.py', encoding='utf-8').read())" && echo "OK sintaxis válida"`
Expected: `OK sintaxis válida`

- [ ] **Step 5: Re-ejecutar el generador completo para confirmar que nada se rompió**

Run: `cd "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda" && python3 generar_web.py`
Expected: mismo comportamiento que en la Task 4 Step 4 (sin traceback, N fichas generadas, index.html regenerado).

- [ ] **Step 6: Commit**

```bash
cd "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda"
git add generar_web.py
git commit -m "Fase 2: eliminar build_html() (modal viejo) — ya reemplazado por fichas reales"
```

---

### Task 7: Actualizar el `.command` y `CLAUDE.md`

**Files:**
- Modify: `/Users/hectorandresvazquezriquelme/Desktop/ejecutable redes/1️⃣ Actualizar Todo — Cambios + Fotos.command`
- Modify: `/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/CLAUDE.md`

- [ ] **Step 1: Actualizar el `git add` del `.command`**

En el archivo `/Users/hectorandresvazquezriquelme/Desktop/ejecutable redes/1️⃣ Actualizar Todo — Cambios + Fotos.command`, buscar la línea:
```bash
git add index.html web_fotos/
```
Reemplazarla por:
```bash
git add index.html web_fotos/ coches/ assets/
```

- [ ] **Step 2: Documentar la nueva estructura en `CLAUDE.md`**

En `/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/CLAUDE.md`, en la tabla "Archivos clave del catálogo web" (buscarla con `grep -n "Archivos clave del catálogo web" CLAUDE.md`), agregar estas filas:
```
| `coches/{n:02d}-{slug}.html` | Ficha individual de cada coche — URL propia, compartible, con vista previa de WhatsApp (Open Graph) |
| `assets/estilos.css` | Sistema visual compartido (index + fichas) |
| `assets/calculadora.js` | Motor de la calculadora de financiación, compartido por todas las fichas — se regenera desde `generar_web.py`, no editar a mano |
```
Y en la sección "Git / GitHub", donde dice `Solo se commitean index.html y web_fotos/ (no scripts ni JSON)`, actualizar a: `Se commitean index.html, web_fotos/, coches/ y assets/ (no scripts ni JSON — el PDF tampoco, pesa >100MB)`.

- [ ] **Step 3: Commit**

```bash
cd "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda"
git add CLAUDE.md
git commit -m "Fase 2: documentar coches/ y assets/ en CLAUDE.md, actualizar .command"
cd "/Users/hectorandresvazquezriquelme/Desktop/ejecutable redes"
git add "1️⃣ Actualizar Todo — Cambios + Fotos.command" 2>/dev/null || true
```

Nota: el `.command` vive fuera del repo de `catalogo_automoviles_rueda` (está en `~/Desktop/ejecutable redes/`), así que probablemente no esté versionado en el mismo git — si el `git add` de ese segundo bloque falla porque no es un repo git ahí, es esperable; el archivo ya quedó modificado en disco, que es lo que importa.

---

### Task 8: Checkpoint final con Andrés

**Files:** ninguno

- [ ] **Step 1: Resumen para mostrar**

No es un paso automatizable. Mostrarle a Andrés (por el panel del navegador, igual que en la Fase 1):
1. El catálogo completo (`index.html`) con las tarjetas de los ~61 coches.
2. 2-3 fichas de coches distintos, incluyendo si es posible una "Vendido".
3. Confirmar que puede compartir el link de una ficha (mencionar que la vista previa de WhatsApp ya tiene las etiquetas Open Graph correctas, igual que se verificó en la Fase 1).

**No hacer `git push` sin que Andrés lo pida explícitamente** — dejar todo commiteado localmente en `main` y esperar confirmación antes de subir a GitHub (el `.command` de Andrés hace su propio push cuando él lo corre; si nosotros ya pusheamos aparte, podría generar un commit duplicado o conflicto con su próxima corrida).
