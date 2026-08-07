# Fichas individuales por coche — Prototipo visual (Fase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir un prototipo real (no simulado) de una ficha de coche individual con URL propia y del catálogo rediseñado, usando un coche real (CUPRA Formentor, `n=1`), para que Andrés lo revise visualmente en el navegador antes de generalizar el cambio a los 61 coches.

**Architecture:** Dos archivos estáticos nuevos (`coches/01-cupra-formentor.html`, `index-prototipo.html`) más una hoja de estilos compartida nueva (`assets/estilos.css`). La ficha del coche reutiliza el motor JS de la calculadora de financiación ya existente en `generar_web.py` (funciones `cv2*`, `initCalc`, lógica de `abrirModal`) **sin tocar su lógica de cálculo** — solo se extrae tal cual y se adapta el disparador (de "click abre modal" a "se auto-rellena al cargar la página") y se le quita el comportamiento de superposición (overlay) para que viva como una sección normal de la página. No se toca `generar_web.py`, `index.html` ni ningún archivo de producción en esta fase — todo son archivos nuevos y aislados.

**Tech Stack:** HTML/CSS/JS puro (sin frameworks), Python 3 solo para el script de extracción determinista.

---

## Contexto para quien ejecute este plan

- El generador real del catálogo es `generar_web.py` (2284 líneas) → produce `index.html`. Usa plantillas tipo `.format()`/f-string, así que las llaves literales en el código fuente están escapadas como `{{` y `}}` (equivalen a `{` y `}` reales en el HTML final).
- La ficha de coche hoy es un **modal** (pop-up) que vive dentro de `index.html`. El motor de la calculadora de financiación (`CV2`) ya está validado en producción — **no se reescribe su lógica**, solo se traslada.
- El coche de ejemplo para este prototipo es `n=1`, CUPRA Formentor, 36.900€, con 8 fotos ya descargadas en `fotos/01 - CUPRA Formentor - 36.900€/foto_01.jpg` … `foto_08.jpg` (copiadas también a `web_fotos/1/foto_01.jpg` … `foto_08.jpg`).
- Rangos de línea exactos ya verificados en `generar_web.py` (usa estos números, no los vuelvas a adivinar):
  - CSS calculadora + modal: líneas `583`–`920` (sin interpolaciones Python — verificado).
  - HTML del modal: líneas `1041`–`1264` (el `</div>` de la línea 1264 cierra `modal-backdrop`; la línea 1266 ya es `<footer>` — no la incluyas).
  - Helpers JS: `estadoLabel` en `1295`–`1297`, `fmtCuota` en `1298`–`1302`, `esReservado` en `1303`–`1306`.
  - Config + motor `CV2`: líneas `1451`–`2061` (desde `const CV2 = {{` hasta el final de `cv2RestoreTin`, justo antes de `initCalc`).
  - `initCalc(c)`: líneas `2062`–`2162`.
  - `abrirModal(n)`: líneas `2163`–`2220` — **NO se copia literal**, es solo referencia: usa `backdrop.classList.add('open')` y `backdrop.scrollTop`, que no existen en la ficha standalone. En el Task 3 se reescribe a mano como `cargarFicha(c)` sin esas dos líneas.
  - `goSlide`: líneas `2227`–`2233` únicamente.
  - Swipe táctil: líneas `2246`–`2251` únicamente.
  - **NO copiar las líneas `2235`–`2245`** (wiring de `prevBtn`/`nextBtn`/`closeBtn`/`backdrop`/teclado — `closeBtn` y `backdrop` no existen en la ficha standalone, y `prevBtn`/`nextBtn` ya se conectan a mano en el Task 3) **ni la línea `2253`** (`render();` — pertenece al catálogo, no a la ficha; si se pega, revienta el script entero con `ReferenceError: render is not defined` y nada de la página carga).

---

### Task 1: Crear la hoja de estilos compartida `assets/estilos.css`

**Files:**
- Create: `/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/assets/estilos.css`

- [ ] **Step 1: Crear la carpeta `assets/`**

Run: `mkdir -p "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/assets"`

- [ ] **Step 2: Escribir el nuevo lenguaje visual**

Crear el archivo con este contenido exacto:

```css
/* ══════════════════════════════════════════════════════════════════
   Automóviles Rueda — Sistema visual compartido (index + fichas)
   ══════════════════════════════════════════════════════════════════ */

:root {
  --rd-bg:        #f4f5f8;
  --rd-surface:   #ffffff;
  --rd-ink:       #0b0e14;
  --rd-ink-soft:  #4a5468;
  --rd-muted:     #8a93a6;
  --rd-border:    #e5e8ef;
  --rd-red:       #c8232b;
  --rd-red-dark:  #a01c23;
  --rd-green:     #1c9a5b;
  --rd-radius-lg: 20px;
  --rd-radius-md: 14px;
  --rd-radius-sm: 10px;
  --rd-shadow:    0 8px 24px rgba(11,14,20,0.08), 0 2px 6px rgba(11,14,20,0.05);
  --rd-shadow-lg: 0 20px 50px rgba(11,14,20,0.16), 0 6px 16px rgba(11,14,20,0.08);
  --rd-font: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: var(--rd-font);
  background: var(--rd-bg);
  color: var(--rd-ink);
  -webkit-font-smoothing: antialiased;
}
a { color: inherit; text-decoration: none; }
img { max-width: 100%; display: block; }

/* ── Header ── */
.rd-header {
  background: var(--rd-ink);
  color: #fff;
  padding: 14px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 3px solid var(--rd-red);
  position: sticky;
  top: 0;
  z-index: 40;
}
.rd-header-brand { display: flex; align-items: baseline; gap: 10px; }
.rd-header-brand strong { font-size: 18px; font-weight: 800; letter-spacing: -0.3px; }
.rd-header-brand span { font-size: 12px; color: #aab2c5; }

/* ── Volver / breadcrumb ── */
.rd-back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: var(--rd-ink-soft);
  padding: 10px 24px;
}
.rd-back:hover { color: var(--rd-red); }

/* ── Layout de ficha de coche ── */
.rd-coche-wrap {
  max-width: 1180px;
  margin: 0 auto;
  padding: 8px 24px 60px;
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 28px;
  align-items: start;
}
@media (max-width: 900px) {
  .rd-coche-wrap { grid-template-columns: 1fr; padding: 8px 16px 40px; }
}

/* ── Galería hero ── */
.rd-gallery-frame {
  background: var(--rd-surface);
  border-radius: var(--rd-radius-lg);
  overflow: hidden;
  box-shadow: var(--rd-shadow);
}

/* ── Franja de specs con icono ── */
.rd-spec-badges {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 10px;
  margin: 18px 0;
}
.rd-spec-badge {
  background: var(--rd-surface);
  border: 1px solid var(--rd-border);
  border-radius: var(--rd-radius-sm);
  padding: 12px 14px;
}
.rd-spec-badge .lbl { font-size: 11px; color: var(--rd-muted); text-transform: uppercase; letter-spacing: 0.4px; }
.rd-spec-badge .val { font-size: 15px; font-weight: 700; margin-top: 2px; }

/* ── Panel de precio fijo (sticky) ── */
.rd-price-panel {
  background: var(--rd-surface);
  border-radius: var(--rd-radius-lg);
  box-shadow: var(--rd-shadow-lg);
  padding: 24px;
  position: sticky;
  top: 84px;
}
.rd-price-panel .modelo   { font-size: 22px; font-weight: 800; letter-spacing: -0.4px; line-height: 1.15; }
.rd-price-panel .version  { font-size: 13px; color: var(--rd-muted); margin-top: 4px; }
.rd-price-panel .precio   { font-size: 34px; font-weight: 800; color: var(--rd-red); margin-top: 16px; letter-spacing: -0.6px; }
.rd-price-panel .estado   { display: inline-block; margin-top: 6px; font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 20px; }
.rd-price-panel .estado.disponible { background: #e7f8ef; color: var(--rd-green); }
.rd-price-panel .estado.reservado  { background: #fff2e0; color: #b3620a; }

.rd-btn {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  width: 100%; padding: 14px 18px; margin-top: 10px;
  border-radius: var(--rd-radius-sm); font-weight: 700; font-size: 15px;
  border: none; cursor: pointer;
}
.rd-btn-primary { background: var(--rd-red); color: #fff; }
.rd-btn-primary:hover { background: var(--rd-red-dark); }
.rd-btn-secondary { background: var(--rd-bg); color: var(--rd-ink); border: 1px solid var(--rd-border); }
.rd-btn-secondary:hover { background: #ebedf2; }

/* ── Grid de catálogo (index) ── */
.rd-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 20px;
  max-width: 1280px;
  margin: 0 auto;
  padding: 24px;
}
.rd-card {
  background: var(--rd-surface);
  border-radius: var(--rd-radius-md);
  overflow: hidden;
  box-shadow: var(--rd-shadow);
  transition: transform .15s ease, box-shadow .15s ease;
  display: block;
}
.rd-card:hover { transform: translateY(-4px); box-shadow: var(--rd-shadow-lg); }
.rd-card img { width: 100%; aspect-ratio: 4/3; object-fit: cover; background: var(--rd-bg); }
.rd-card-body { padding: 14px 16px 18px; }
.rd-card-modelo  { font-size: 16px; font-weight: 800; letter-spacing: -0.2px; }
.rd-card-version { font-size: 12px; color: var(--rd-muted); margin-top: 2px; height: 32px; overflow: hidden; }
.rd-card-precio  { font-size: 20px; font-weight: 800; color: var(--rd-red); margin-top: 8px; }
```

- [ ] **Step 3: Verificar que el archivo se creó y no está vacío**

Run: `wc -l "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/assets/estilos.css"`
Expected: un número mayor a 100 (líneas).

- [ ] **Step 4: Commit**

```bash
cd "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda"
git add assets/estilos.css
git commit -m "Prototipo: nuevo sistema visual compartido (assets/estilos.css)"
```

---

### Task 2: Extraer el motor de la calculadora (CSS + JS) de forma determinista

El objetivo de este task es sacar, **sin transcribir a mano**, los bloques ya validados de `generar_web.py` a un archivo de trabajo, para pegarlos en el Task 3 sin riesgo de errores de transcripción en la lógica financiera.

**Files:**
- Create: `/tmp/extracto_calculadora.txt` (archivo de trabajo temporal, no se commitea)

- [ ] **Step 1: Ejecutar el script de extracción**

Run:
```bash
python3 << 'PYEOF'
lines = open("/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/generar_web.py", encoding="utf-8").read().split("\n")

def bloque(a, b):
    # a, b son 1-indexados e inclusivos, como en el editor
    return "\n".join(lines[a-1:b])

css_calc  = bloque(583, 920)
html_modal = bloque(1041, 1264)
js_helpers = bloque(1295, 1306)   # estadoLabel, fmtCuota, esReservado
js_cv2     = bloque(1451, 2061)   # const CV2 ... cv2RestoreTin
js_initcalc = bloque(2062, 2162)  # initCalc(c)
js_goslide  = bloque(2227, 2233)  # function goSlide(i) { ... } — SOLO esto, no el wiring de alrededor
js_touch    = bloque(2246, 2251)  # let touchStartX ... touchstart/touchend listeners

def unescape(s):
    return s.replace("{{", "{").replace("}}", "}")

out = []
out.append("=== CSS (calculadora + modal) ===")
out.append(unescape(css_calc))
out.append("\n=== HTML (modal) ===")
out.append(unescape(html_modal))
out.append("\n=== JS helpers ===")
out.append(unescape(js_helpers))
out.append("\n=== JS CV2 engine ===")
out.append(unescape(js_cv2))
out.append("\n=== JS initCalc ===")
out.append(unescape(js_initcalc))
out.append("\n=== JS goSlide ===")
out.append(unescape(js_goslide))
out.append("\n=== JS touch swipe ===")
out.append(unescape(js_touch))

open("/tmp/extracto_calculadora.txt", "w", encoding="utf-8").write("\n".join(out))
print("OK —", sum(len(unescape(b).splitlines()) for b in [css_calc, html_modal, js_helpers, js_cv2, js_initcalc, js_goslide, js_touch]), "líneas extraídas")
PYEOF
```
Expected: imprime `OK — <número> líneas extraídas` sin errores.

- [ ] **Step 2: Verificar que no quedaron llaves dobles sin desescapar**

Run: `grep -c '{{' /tmp/extracto_calculadora.txt`
Expected: `0`

- [ ] **Step 3: Verificar que no quedó ninguna interpolación Python de una sola llave**

Run: `grep -nE '\{[A-Za-z_]' /tmp/extracto_calculadora.txt | grep -v 'class=\|id=\|c\.\|res\.\|rules\.\|mantInfo\.\|CV2\.\|CV2_MANT\|d\.dataset'`
Expected: sin salida (o solo coincidencias claramente de JS como `${{...}}` ya desescapado a `${...}` — si aparece algo con mayúscula tipo `{COMERCIAL_` o `{cars_js}`, DETENTE: significa que el rango de líneas capturó algo fuera de scope y hay que ajustar los números antes de continuar).

---

### Task 3: Construir la ficha del coche prototipo (`coches/01-cupra-formentor.html`)

**Files:**
- Create: `/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/coches/01-cupra-formentor.html`

- [ ] **Step 1: Crear la carpeta `coches/`**

Run: `mkdir -p "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/coches"`

- [ ] **Step 2: Copiar las 8 fotos del coche de ejemplo a una ruta relativa desde `coches/`**

La ficha vive en `coches/`, así que las fotos deben referenciarse como `../web_fotos/1/foto_01.jpg` (ya existen en esa ruta — verificar antes de continuar):

Run: `ls "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/web_fotos/1/"`
Expected: lista `foto_01.jpg` … `foto_08.jpg`. Si no existen, copiarlas primero: `cp "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/fotos/01 - CUPRA Formentor - 36.900€/foto_0"*.jpg "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/web_fotos/1/"`

- [ ] **Step 3: Escribir el archivo HTML completo**

Usa el contenido de `/tmp/extracto_calculadora.txt` generado en el Task 2 para rellenar las tres secciones marcadas `<!-- PEGAR: ... -->` / `/* PEGAR: ... */` / `// PEGAR: ...` de la plantilla de abajo — copia el texto **tal cual** aparece bajo cada encabezado `=== ... ===` de ese archivo, sin modificarlo. La única parte de la calculadora que se escribe a mano es la función `cargarFicha()` al final del `<script>` (sustituye a `abrirModal`, ver más abajo).

Estructura completa del archivo (con los datos reales del CUPRA Formentor `n=1`):

```html
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CUPRA Formentor 1.5 TSI e-Hybrid 204 CV · 36.900€ · Automóviles Rueda</title>
<meta name="description" content="CUPRA Formentor Híbrido, 60 km, matriculación 05/2026, cambio automático. Málaga.">

<!-- Open Graph — vista previa de WhatsApp -->
<meta property="og:type" content="product">
<meta property="og:title" content="CUPRA Formentor 1.5 TSI e-Hybrid 204 CV · 36.900€">
<meta property="og:description" content="Híbrido · 60 km · Matriculación 05/2026 · Automático · Málaga · Automóviles Rueda">
<meta property="og:image" content="https://andresvazquez11.github.io/automoviles-rueda-catalogo/web_fotos/1/foto_01.jpg">
<meta property="og:url" content="https://andresvazquez11.github.io/automoviles-rueda-catalogo/coches/01-cupra-formentor.html">

<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../assets/estilos.css">
<style>
/* PEGAR AQUÍ: contenido bajo "=== CSS (calculadora + modal) ===" de /tmp/extracto_calculadora.txt */
</style>
</head>
<body>

<header class="rd-header">
  <div class="rd-header-brand">
    <strong>Automóviles Rueda</strong>
    <span>Andrés Vázquez · 610 02 90 56</span>
  </div>
</header>
<a class="rd-back" href="../index-prototipo.html">&#8249; Volver al catálogo</a>

<div class="rd-coche-wrap">
  <div>
    <div class="rd-gallery-frame modal-gallery" id="modal-gallery">
      <div class="gallery-slides" id="gallery-slides"></div>
      <button class="gallery-btn prev" id="gallery-prev">&#8249;</button>
      <button class="gallery-btn next" id="gallery-next">&#8250;</button>
      <div class="gallery-dots" id="gallery-dots"></div>
    </div>
    <div class="rd-spec-badges" id="m-specs"></div>
    <div class="equip-section" id="equip-section">
      <h3>Equipamiento</h3>
      <div class="equip-grid" id="m-equip"></div>
    </div>
    <div class="modal-financiacion" id="m-financiacion">
      <!-- PEGAR AQUÍ: el contenido interior de "=== HTML (modal) ===" que corresponde
           al <div class="modal-financiacion" id="m-financiacion"> del extracto
           (desde su "Car info bar" hasta el cierre de ese mismo div) -->
    </div>
  </div>

  <div class="rd-price-panel">
    <div class="modelo" id="m-modelo"></div>
    <div class="version" id="m-version"></div>
    <div class="precio" id="m-precio"></div>
    <div class="estado" id="m-estado-pill"></div>
    <a class="rd-btn rd-btn-primary" href="https://wa.me/34610029056" target="_blank" rel="noopener">Reservar por WhatsApp</a>
    <a class="rd-btn rd-btn-secondary" href="tel:610029056">Llamar</a>
    <a class="rd-btn rd-btn-secondary" id="m-link" href="#" target="_blank" rel="noopener">Ver en Das WeltAuto</a>
  </div>
</div>

<script>
// PEGAR AQUÍ: contenido bajo "=== JS helpers ===" de /tmp/extracto_calculadora.txt
// PEGAR AQUÍ: contenido bajo "=== JS CV2 engine ===" de /tmp/extracto_calculadora.txt
// PEGAR AQUÍ: contenido bajo "=== JS initCalc ===" de /tmp/extracto_calculadora.txt
// PEGAR AQUÍ: contenido bajo "=== JS goSlide ===" de /tmp/extracto_calculadora.txt
// PEGAR AQUÍ: contenido bajo "=== JS touch swipe ===" de /tmp/extracto_calculadora.txt

const COCHE = {
  "n": 1, "modelo": "CUPRA Formentor",
  "version": "1.5 TSI e-Hybrid DSG 150 kW (204 CV)",
  "combustible": "Híbrido", "km": "60", "fecha": "05/2026",
  "cambio": "Automático", "color": "", "precio": "36.900",
  "ubicacion": "Málaga", "estado": "Disponible",
  "url": "https://www.dasweltauto.es/esp/concesionario-seat-automoviles-rueda/cupra-formentor-hibrido-electro-gasolina-204-cv-del-2026-en-malaga/176586541",
  "equipamiento": [
    "Faros Matrix LED con distribución variable de la luz",
    "Asientos de tela (material principal) y de cuero sintético (material secundario)",
    "Controles de climatización diferenciados para conductor/acompañante y asientos delanteros/traseros",
    "Aire acondicionado trizona con mandos traseros para el climatizador de automático",
    "Luces de freno, luces frontales antiniebla, luces de cruce, luces intermitentes laterales, Luces de día, Luces traseras y luces de carretera con tecnología LED",
    "Velocidad máxima: 210 km/h",
    "Edge Basis Pack",
    "Intelligent Drive Pack DSG",
    "Llantas delanteras y traseras en aluminio de 18 pulgadas de diámetro y 8,0 pulgadas de ancho 45,7 y 20,3",
    "Faros con lente elipsoidal, bombilla LED y luz larga con bombilla LED"
  ],
  "fotos": [
    "../web_fotos/1/foto_01.jpg", "../web_fotos/1/foto_02.jpg", "../web_fotos/1/foto_03.jpg",
    "../web_fotos/1/foto_04.jpg", "../web_fotos/1/foto_05.jpg", "../web_fotos/1/foto_06.jpg",
    "../web_fotos/1/foto_07.jpg", "../web_fotos/1/foto_08.jpg"
  ]
};

const slides   = document.getElementById('gallery-slides');
const dotsEl   = document.getElementById('gallery-dots');
const prevBtn  = document.getElementById('gallery-prev');
const nextBtn  = document.getElementById('gallery-next');
let fotosModal = [];
let slideActual = 0;

// Reemplaza a abrirModal(n): en vez de buscar el coche en un array COCHES por click,
// rellena la página directamente con el único coche embebido (COCHE), al cargar.
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
  document.getElementById('m-precio').textContent = c.precio + ' €';
  const pill = document.getElementById('m-estado-pill');
  const reservado = esReservado(c.estado);
  pill.textContent = reservado ? '🟠 Reservado' : '✅ Disponible';
  pill.classList.add(reservado ? 'reservado' : 'disponible');

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

  initCalc(c);

  const link = document.getElementById('m-link');
  if (c.url) { link.href = c.url; link.style.display = ''; } else { link.style.display = 'none'; }
}

prevBtn.addEventListener('click', () => goSlide(slideActual - 1));
nextBtn.addEventListener('click', () => goSlide(slideActual + 1));

cargarFicha(COCHE);
</script>
</body>
</html>
```

Notas sobre el pegado (no ambiguo, pero sé preciso):
- El bloque `=== CSS (calculadora + modal) ===` va completo dentro del `<style>` del `<head>`.
- Del bloque `=== HTML (modal) ===`, solo se usa el fragmento interior del `<div class="modal-financiacion" id="m-financiacion">` (Car info bar, tabs, sliders, botón de WhatsApp de financiación) — el resto de ese bloque (galería, header, specs, equipo, CTA) ya está reemplazado por los elementos con las mismas ids en la plantilla de arriba, así que no se duplica.
- El `id="modal-gallery"` y clases `gallery-slides`/`gallery-dots`/`gallery-btn` deben coincidir exactamente con las que usa el JS de `=== JS goSlide ===` y `=== JS touch swipe ===` — no renombrar.
- `goSlide`, `esReservado`, `fmtCuota`, `estadoLabel`, `initCalc`, todas las `cv2*` se pegan **sin modificar ni una línea** — son las mismas que ya están validadas en producción.
- No pegar nada del bloque original `abrirModal` (backdrop/scrollTop) ni el wiring de `closeBtn`/`backdrop`/teclado/`render()` — esos elementos no existen en la ficha standalone y romperían el script. Ya están cubiertos por `cargarFicha(c)` (escrita a mano en la plantilla) y por los listeners de `prevBtn`/`nextBtn` ya incluidos en la plantilla.

- [ ] **Step 4: Verificar que el archivo no tiene llaves dobles ni placeholders sin pegar**

Run:
```bash
grep -c "PEGAR" "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/coches/01-cupra-formentor.html"
grep -c '{{' "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/coches/01-cupra-formentor.html"
```
Expected: ambos comandos devuelven `0`.

- [ ] **Step 5: Abrir el archivo en el navegador y verificar visualmente**

Run: `open "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/coches/01-cupra-formentor.html"`
Expected: se ve la galería con 8 fotos, el precio "36.900 €", los datos del coche, el equipamiento, y la calculadora de financiación funcionando (cambiar plazo/modalidad recalcula la cuota).

- [ ] **Step 6: Commit**

```bash
cd "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda"
git add coches/01-cupra-formentor.html
git commit -m "Prototipo: ficha individual del CUPRA Formentor (n=1)"
```

---

### Task 4: Construir el catálogo prototipo (`index-prototipo.html`)

**Files:**
- Create: `/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/index-prototipo.html`

- [ ] **Step 1: Generar las tarjetas reales a partir de `datos_coches.json`**

Run:
```bash
cd "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda"
python3 << 'PYEOF'
import json, re

def slug(modelo):
    s = modelo.lower()
    s = (s.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u'))
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s

data = json.loads(open("datos_coches.json", encoding="utf-8").read())
cards = []
for c in data:
    if c["estado"] == "Retirado":
        continue
    n = c["n"]
    href = f'coches/{n}-{slug(c["modelo"])}.html' if n == 1 else '#'
    foto = f'web_fotos/{n}/foto_01.jpg'
    cards.append(f'''<a class="rd-card" href="{href}">
  <img src="{foto}" alt="{c["modelo"]}" loading="lazy">
  <div class="rd-card-body">
    <div class="rd-card-modelo">{c["modelo"]}</div>
    <div class="rd-card-version">{c["version"]}</div>
    <div class="rd-card-precio">{c["precio"]} €</div>
  </div>
</a>''')

html = "\n".join(cards)
open("/tmp/tarjetas_prototipo.html", "w", encoding="utf-8").write(html)
print(f"OK — {len(cards)} tarjetas generadas en /tmp/tarjetas_prototipo.html")
PYEOF
```
Expected: `OK — <N> tarjetas generadas en /tmp/tarjetas_prototipo.html` (N cercano a 60).

- [ ] **Step 2: Escribir `index-prototipo.html`**

Crea el archivo con este contenido, pegando el contenido completo de `/tmp/tarjetas_prototipo.html` donde dice `<!-- PEGAR: tarjetas -->`:

```html
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Prototipo — Catálogo Automóviles Rueda</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/estilos.css">
<style>
  .rd-aviso-prototipo {
    background: #fff3cd; color: #7a5c00; padding: 10px 24px;
    font-size: 13px; text-align: center; font-weight: 600;
  }
</style>
</head>
<body>
<div class="rd-aviso-prototipo">
  🚧 PROTOTIPO — solo la tarjeta de CUPRA Formentor abre una ficha real. Las demás son solo vista previa del diseño.
</div>
<header class="rd-header">
  <div class="rd-header-brand">
    <strong>Automóviles Rueda</strong>
    <span>Andrés Vázquez · 610 02 90 56</span>
  </div>
</header>
<div class="rd-grid">
<!-- PEGAR: tarjetas -->
</div>
</body>
</html>
```

- [ ] **Step 3: Verificar que no quedó el marcador sin reemplazar**

Run: `grep -c "PEGAR: tarjetas" "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/index-prototipo.html"`
Expected: `0`

- [ ] **Step 4: Abrir en el navegador y verificar visualmente**

Run: `open "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/index-prototipo.html"`
Expected: grid de tarjetas moderno con foto/modelo/precio de cada coche; al hacer clic en la tarjeta de CUPRA Formentor se abre la ficha real construida en el Task 3.

- [ ] **Step 5: Commit**

```bash
cd "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda"
git add index-prototipo.html
git commit -m "Prototipo: catálogo rediseñado (vista previa, no reemplaza index.html)"
```

---

### Task 5: Verificación final y checkpoint con Andrés

**Files:** ninguno (solo verificación)

- [ ] **Step 1: Confirmar que los archivos de producción no se tocaron**

Run: `cd "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda" && git diff --stat 6cc7b63 -- index.html generar_web.py`

(`6cc7b63` es el commit del spec, el punto de partida antes de este plan — ver `git log --oneline -- docs/superpowers/specs/2026-08-07-fichas-individuales-refresh-design.md` si necesitás confirmarlo.)

Expected: sin salida (ningún cambio en esos dos archivos).

- [ ] **Step 2: Verificar que las etiquetas Open Graph están presentes en la ficha**

Run: `grep -o 'og:[a-z]*' "/Users/hectorandresvazquezriquelme/Desktop/catalogo_automoviles_rueda/coches/01-cupra-formentor.html"`
Expected: `og:type`, `og:title`, `og:description`, `og:image`, `og:url`.

- [ ] **Step 3: Mostrar a Andrés y esperar aprobación**

Este es un checkpoint humano, no un paso automatizable. Abrir ambos archivos (`open coches/01-cupra-formentor.html` e `index-prototipo.html`) y pedirle a Andrés que los revise. **No continuar a la Fase 2 (generalizar a los 61 coches, actualizar `generar_web.py`, el `.command` y `CLAUDE.md`) sin su aprobación explícita.** La Fase 2 se planifica en un documento aparte una vez aprobado el diseño, porque el resultado visual de este prototipo puede cambiar decisiones (paleta, layout) que afectarían ese plan.
