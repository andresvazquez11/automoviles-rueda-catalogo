# Sitio de prueba del rediseño — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publicar una versión navegable del rediseño aprobado (`docs/superpowers/specs/2026-09-21-rediseno-visual-catalogo-design.md`) en `automovilesruedaocasion.com/prueba/`, con datos y fotos reales de los ~50 coches activos, sin tocar `generar_web.py` ni ningún archivo de producción.

**Architecture:** Un script Python nuevo y aislado (`generar_prueba.py`) lee `datos_coches.json`, reutiliza las fotos ya publicadas en `web_fotos/` y los enlaces a las fichas ya publicadas en `coches/`, y escribe una sola página autocontenida en `prueba/index.html` (HTML + CSS + JS vainilla embebidos, sin frameworks). Las fichas de cada coche NO se duplican ni se tocan — la página de prueba enlaza directamente a las fichas reales que ya existen en producción (`/coches/NN-modelo.html`), así que "entrar a la ficha" ya funciona sin trabajo extra.

**Tech Stack:** Python 3 (stdlib: `json`, `pathlib`, `shutil`), HTML/CSS/JS vainilla (sin build step, coherente con el resto del sitio).

---

## Decisiones de alcance (de la spec, aplicadas acá)

- Comparador, modo oscuro, contador+hover de fotos, specs siempre visibles: igual que en el mockup, con TODOS los coches activos (no solo 4).
- Parallax: solo en el hero, con `background-attachment: fixed` (igual que el mockup).
- Foto del hero: se reutiliza la imagen generada con IA del mockup (`/tmp/mockup_assets/hero-ibiza.png`) como placeholder — la spec deja pendiente decidir la fuente final, esto es solo para navegar y probar.
- Fichas individuales: no se tocan. La página de prueba enlaza a las fichas reales ya publicadas.
- Nada de esto se commitea en `generar_web.py` — es un script y una carpeta de salida (`prueba/`) completamente aparte.

## Files

- Create: `generar_prueba.py` — script generador de la página de prueba.
- Create: `prueba/index.html` — salida generada (se genera con el script, no se escribe a mano).
- Create: `prueba/assets/hero.jpg` — foto de referencia del hero, copiada del mockup.

---

### Task 1: Extracción de datos reales de coches

**Files:**
- Create: `generar_prueba.py`

- [ ] **Step 1: Escribir la función que carga y filtra los coches**

Crear `generar_prueba.py` con este contenido inicial:

```python
#!/usr/bin/env python3
"""Genera una versión de PRUEBA del catálogo con el nuevo diseño (hero con
foto de estilo de vida + parallax, hover de fotos, specs siempre visibles,
comparador, modo oscuro), con datos y fotos REALES del catálogo actual.

No toca generar_web.py ni ningún archivo de producción — escribe todo en
prueba/, aparte. Las fichas de cada coche no se duplican: se enlaza
directamente a las fichas reales que ya existen en coches/.
"""
import json
import shutil
from pathlib import Path

BASE = Path(__file__).parent
JSON_PATH = BASE / "datos_coches.json"
COCHES_DIR = BASE / "coches"
WEB_FOTOS = BASE / "web_fotos"
OUT_DIR = BASE / "prueba"
HERO_SRC = Path("/tmp/mockup_assets/hero-ibiza.png")

ACCENT = "#c8102e"


def cargar_coches() -> list[dict]:
    """Carga datos_coches.json y arma la lista de coches para la página de
    prueba: solo los que tienen ficha real Y al menos una foto real."""
    coches = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    resultado = []
    for c in coches:
        if c.get("estado") == "Retirado":
            continue
        n = c["n"]
        fichas = sorted(COCHES_DIR.glob(f"{n:02d}-*.html"))
        if not fichas:
            continue
        fotos = sorted(WEB_FOTOS.glob(f"{n:02d}/foto_*.jpg"))
        if not fotos:
            continue
        resultado.append({
            "n": n,
            "modelo": c["modelo"],
            "version": c.get("version", ""),
            "precio": c.get("precio", ""),
            "km": c.get("km", ""),
            "cambio": c.get("cambio", ""),
            "combustible": c.get("combustible", ""),
            "estado": c.get("estado", ""),
            "ficha": f"/coches/{fichas[0].name}",
            "fotos": [f"/web_fotos/{n:02d}/{f.name}" for f in fotos[:3]],
            "total_fotos": len(fotos),
        })
    return resultado


if __name__ == "__main__":
    coches = cargar_coches()
    print(f"Coches cargados para la página de prueba: {len(coches)}")
```

- [ ] **Step 2: Verificar que carga una cantidad razonable de coches**

Run: `python3 generar_prueba.py`
Expected: una línea como `Coches cargados para la página de prueba: 48` (un número entre 35 y 55 — si da 0 o un número muy bajo, algo está mal en los globs de `coches/` o `web_fotos/` y hay que revisar antes de seguir).

- [ ] **Step 3: Commit**

```bash
git add generar_prueba.py
git commit -m "Add data loader for the design-preview page (prueba/)"
```

---

### Task 2: Plantilla HTML/CSS/JS de la página de prueba

**Files:**
- Modify: `generar_prueba.py`

- [ ] **Step 1: Agregar la función que arma el HTML completo**

Agregar a `generar_prueba.py`, antes del bloque `if __name__ == "__main__":`:

```python
def construir_html(coches: list[dict]) -> str:
    cars_json = json.dumps(coches, ensure_ascii=False)
    tarjetas_html = "\n".join(_tarjeta_html(c) for c in coches)

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>PRUEBA — Automóviles Rueda (rediseño)</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@500;600;700&family=Work+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
{_css()}
</style>
</head>
<body>

<div class="rd-banner-prueba">🧪 PÁGINA DE PRUEBA — rediseño en exploración, no es la versión en producción</div>

<div class="rd-header">
  <div class="rd-logo">Automóviles Rueda</div>
  <div class="rd-header-right">
    <span class="rd-header-sub">Vélez-Málaga · SEAT · CUPRA · Volkswagen</span>
    <button id="rd-dark-toggle" class="rd-toggle">
      <span id="rd-dark-label">🌙 Modo oscuro</span>
    </button>
  </div>
</div>

<div class="rd-hero">
  <div class="rd-hero-overlay"></div>
  <div class="rd-hero-copy">
    <div class="rd-hero-eyebrow">Seminuevos con garantía oficial</div>
    <h1>Encontrá tu<br>próximo coche</h1>
    <p>Seminuevos SEAT, CUPRA y Volkswagen en Vélez-Málaga, revisados, con garantía oficial y financiación a medida.</p>
  </div>
  <div class="rd-hero-bar">
    <div class="rd-hero-chips">
      <span class="rd-chip rd-chip-on">Todos</span>
      <span class="rd-chip">Disponible</span>
      <span class="rd-chip">Km 0</span>
    </div>
    <div class="rd-hero-count">{len(coches)} coches disponibles ahora</div>
    <a href="#catalogo" class="rd-cta">Ver catálogo completo</a>
  </div>
</div>

<div id="catalogo" class="rd-catalogo">
  <h2>Catálogo destacado</h2>
  <p class="rd-catalogo-sub">Pasá el mouse sobre la foto para ver más ángulos</p>
  <div class="rd-grid">
{tarjetas_html}
  </div>
</div>

<div id="rd-tray" class="rd-tray"></div>

<div id="rd-overlay" class="rd-overlay">
  <div class="rd-overlay-panel">
    <div class="rd-overlay-head">
      <div class="rd-overlay-title">Comparar coches</div>
      <button id="rd-overlay-close" class="rd-overlay-close">✕</button>
    </div>
    <div class="rd-cmp-wrap">
      <div class="rd-cmp-labels">
        <div class="rd-cmp-spacer"></div>
        <div class="rd-cmp-label-row">Modelo</div>
        <div class="rd-cmp-label-row">Versión</div>
        <div class="rd-cmp-label-row">Precio</div>
        <div class="rd-cmp-label-row">Km</div>
        <div class="rd-cmp-label-row">Combustible</div>
        <div class="rd-cmp-label-row">Cambio</div>
      </div>
      <div id="rd-cmp-cols" class="rd-cmp-cols"></div>
    </div>
  </div>
</div>

<script>
const CARS = {cars_json};
const ACCENT = "{ACCENT}";
{_js()}
</script>
</body>
</html>
"""


def _tarjeta_html(c: dict) -> str:
    return f"""    <div class="rd-card" data-n="{c['n']}">
      <div class="rd-card-photo">
        <img src="{c['fotos'][0]}" alt="{c['modelo']}">
        <div class="rd-counter">1/{c['total_fotos']}</div>
        <div class="rd-dots">{_dots_html(len(c['fotos']))}</div>
      </div>
      <a href="{c['ficha']}" class="rd-card-body">
        <div class="rd-card-modelo">{c['modelo']}</div>
        <div class="rd-card-version">{c['version']}</div>
        <div class="rd-card-precio">{c['precio']} €</div>
        <div class="rd-card-specs">
          <span>⛽ {c['combustible']}</span>
          <span>🛣️ {c['km']} km</span>
          <span>⚙️ {c['cambio']}</span>
        </div>
      </a>
      <button class="rd-compare-btn">+ Comparar</button>
    </div>"""


def _dots_html(n: int) -> str:
    return "".join(
        f'<div class="rd-dot{" rd-dot-on" if i == 0 else ""}"></div>'
        for i in range(n)
    )
```

- [ ] **Step 2: Agregar el CSS (función `_css()`)**

Agregar a `generar_prueba.py`:

```python
def _css() -> str:
    return """
body { margin: 0; box-sizing: border-box; font-family: 'Work Sans', sans-serif; background: #ffffff; color: #141414; }
*, *::before, *::after { box-sizing: inherit; }

.rd-banner-prueba { background: #ffb020; color: #1a1400; text-align: center; font-size: 13px; font-weight: 700; padding: 8px 0; }

.rd-header { display: flex; align-items: center; justify-content: space-between; padding: 18px 48px; background: #0d0d0d; }
.rd-logo { font-family: 'Oswald', sans-serif; font-weight: 700; font-size: 22px; color: #fff; text-transform: uppercase; }
.rd-header-right { display: flex; align-items: center; gap: 28px; }
.rd-header-sub { color: #cfcfcf; font-size: 14px; }
.rd-toggle { cursor: pointer; border: none; background: #1c1c1c; color: #fff; padding: 9px 16px; border-radius: 999px; font-family: 'Work Sans', sans-serif; font-size: 13px; font-weight: 600; }

.rd-hero { position: relative; width: 100%; height: 640px; overflow: hidden;
  background-image: url(assets/hero.jpg); background-size: cover; background-position: center 40%;
  background-attachment: fixed; }
.rd-hero-overlay { position: absolute; inset: 0;
  background: linear-gradient(100deg, rgba(0,0,0,.72) 0%, rgba(0,0,0,.45) 38%, rgba(0,0,0,.05) 62%, rgba(0,0,0,0) 78%); }
.rd-hero-copy { position: relative; z-index: 2; max-width: 620px; padding: 96px 0 0 56px; }
.rd-hero-eyebrow { color: #c8102e; font-family: 'Oswald', sans-serif; font-weight: 600; font-size: 14px; letter-spacing: 3px; text-transform: uppercase; margin-bottom: 18px; }
.rd-hero h1 { margin: 0 0 20px 0; font-family: 'Oswald', sans-serif; font-weight: 700; font-size: 64px; line-height: .98; letter-spacing: -1px; text-transform: uppercase; color: #fff; }
.rd-hero p { margin: 0; font-size: 18px; line-height: 1.5; color: #e8e8e8; max-width: 460px; }
.rd-hero-bar { position: absolute; z-index: 3; bottom: 40px; right: 56px; width: 280px;
  background: rgba(13,13,13,.55); backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
  border: 1px solid rgba(255,255,255,.18); border-radius: 16px; padding: 18px 20px; }
.rd-hero-chips { display: flex; gap: 6px; margin-bottom: 12px; }
.rd-chip { padding: 6px 12px; border-radius: 999px; font-size: 12px; font-weight: 600; background: transparent; color: #fff; border: 1px solid rgba(255,255,255,.4); }
.rd-chip-on { background: #0d0d0d; border-color: #0d0d0d; }
.rd-hero-count { font-size: 12.5px; color: #d9d9d9; margin-bottom: 12px; }
.rd-cta { display: block; text-align: center; text-decoration: none; background: #c8102e; color: #fff; font-weight: 700; font-size: 14px; padding: 12px 0; border-radius: 10px; }

.rd-catalogo { padding: 72px 56px 140px 56px; }
.rd-catalogo h2 { margin: 0 0 8px 0; font-family: 'Oswald', sans-serif; font-weight: 700; font-size: 34px; text-transform: uppercase; letter-spacing: -.5px; }
.rd-catalogo-sub { margin: 0 0 40px 0; color: #6b6b6b; font-size: 15px; }
.rd-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 28px; }

.rd-card { background: #fff; border: 1px solid #e7e7e7; border-radius: 16px; overflow: hidden; transition: transform .2s, box-shadow .2s; display: flex; flex-direction: column; }
.rd-card:hover { transform: translateY(-4px); box-shadow: 0 18px 40px rgba(0,0,0,.16); }
.rd-card-photo { position: relative; width: 100%; aspect-ratio: 4/3; overflow: hidden; cursor: pointer; }
.rd-card-photo img { width: 100%; height: 100%; object-fit: cover; display: block; }
.rd-counter { position: absolute; top: 10px; left: 10px; background: rgba(13,13,13,.75); color: #fff; font-size: 12px; font-weight: 600; padding: 4px 9px; border-radius: 999px; }
.rd-dots { position: absolute; top: 10px; left: 0; right: 0; display: flex; gap: 4px; padding: 0 10px; }
.rd-dot { flex: 1; height: 3px; border-radius: 2px; background: rgba(255,255,255,.6); }
.rd-dot-on { background: #c8102e; }
.rd-card-body { display: block; padding: 18px 18px 0 18px; text-decoration: none; color: inherit; }
.rd-card-modelo { font-family: 'Oswald', sans-serif; font-weight: 700; font-size: 18px; text-transform: uppercase; }
.rd-card-version { font-size: 13px; color: #6b6b6b; margin: 2px 0 12px 0; }
.rd-card-precio { font-family: 'Oswald', sans-serif; font-weight: 700; font-size: 24px; color: #c8102e; margin-bottom: 12px; }
.rd-card-specs { display: flex; gap: 14px; flex-wrap: wrap; font-size: 12.5px; color: #6b6b6b; border-top: 1px solid #e7e7e7; padding-top: 12px; }
.rd-compare-btn { cursor: pointer; width: calc(100% - 36px); margin: 12px 18px 18px 18px; background: transparent; color: #141414; border: 1px solid #dcdcdc; border-radius: 10px; padding: 10px 0; font-family: 'Work Sans', sans-serif; font-size: 13px; font-weight: 600; }
.rd-compare-btn.activo { background: #c8102e; color: #fff; border-color: #c8102e; }

.rd-tray { display: none; position: fixed; z-index: 40; bottom: 24px; left: 50%; transform: translateX(-50%);
  background: #0d0d0d; border-radius: 999px; padding: 10px 10px 10px 20px; align-items: center; gap: 14px;
  box-shadow: 0 20px 50px rgba(0,0,0,.35); }
.rd-tray-label { color: #cfcfcf; font-size: 13px; white-space: nowrap; }
.rd-tray-chips { display: flex; gap: 6px; }
.rd-tray-chip { background: #1c1c1c; color: #fff; font-size: 12px; padding: 6px 10px; border-radius: 999px; display: flex; align-items: center; gap: 6px; white-space: nowrap; }
.rd-tray-x { cursor: pointer; opacity: .6; }
.rd-tray-btn { background: #c8102e; color: #fff; border: none; border-radius: 999px; padding: 10px 18px; font-family: 'Work Sans', sans-serif; font-size: 13px; font-weight: 700; cursor: pointer; white-space: nowrap; }

.rd-overlay { display: none; position: fixed; inset: 0; z-index: 50; background: rgba(0,0,0,.6); align-items: center; justify-content: center; padding: 40px; }
.rd-overlay-panel { background: #fff; border-radius: 20px; max-width: 840px; width: 100%; max-height: 86vh; overflow: auto; padding: 28px; }
.rd-overlay-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.rd-overlay-title { font-family: 'Oswald', sans-serif; font-weight: 700; font-size: 22px; text-transform: uppercase; }
.rd-overlay-close { background: none; border: none; font-size: 20px; cursor: pointer; }
.rd-cmp-wrap { display: flex; align-items: flex-start; overflow-x: auto; }
.rd-cmp-labels { width: 130px; flex-shrink: 0; }
.rd-cmp-spacer { height: 140px; }
.rd-cmp-label-row { height: 46px; display: flex; align-items: center; font-size: 12.5px; font-weight: 600; text-transform: uppercase; letter-spacing: .3px; }
.rd-cmp-cols { display: flex; }
.rd-cmp-col { width: 200px; flex-shrink: 0; border-left: 1px solid #e7e7e7; }
.rd-cmp-col img { width: 100%; height: 140px; object-fit: cover; display: block; }
.rd-cmp-row { height: 46px; display: flex; align-items: center; padding: 0 14px; font-size: 13px; }
.rd-cmp-strong { font-weight: 700; }
.rd-cmp-small { color: #6b6b6b; font-size: 12px; }
.rd-cmp-accent { color: #c8102e; font-weight: 700; }

body.dark { background: #0d0d0d; color: #f2f2f2; }
body.dark .rd-card { background: #171717; border-color: #2b2b2b; }
body.dark .rd-card-version, body.dark .rd-catalogo-sub, body.dark .rd-cmp-small { color: #a6a6a6; }
body.dark .rd-card-specs { border-top-color: #2b2b2b; }
body.dark .rd-compare-btn { color: #f2f2f2; border-color: #2b2b2b; }
body.dark .rd-overlay-panel { background: #171717; color: #f2f2f2; }
body.dark .rd-cmp-col { border-left-color: #2b2b2b; }
"""
```

- [ ] **Step 3: Agregar el JS vainilla (función `_js()`)**

Agregar a `generar_prueba.py`:

```python
def _js() -> str:
    return """
let compareIds = new Set();

function initCards() {
  document.querySelectorAll('.rd-card').forEach((card) => {
    const n = parseInt(card.dataset.n, 10);
    const car = CARS.find((c) => c.n === n);
    const zoneWrap = card.querySelector('.rd-card-photo');
    const img = zoneWrap.querySelector('img');
    const counter = card.querySelector('.rd-counter');
    const dots = card.querySelectorAll('.rd-dot');

    const setZone = (zone) => {
      img.src = car.fotos[zone];
      counter.textContent = (zone + 1) + '/' + car.total_fotos;
      dots.forEach((d, i) => d.classList.toggle('rd-dot-on', i === zone));
    };

    zoneWrap.addEventListener('mousemove', (e) => {
      const rect = zoneWrap.getBoundingClientRect();
      const ratio = (e.clientX - rect.left) / rect.width;
      const zone = Math.min(car.fotos.length - 1, Math.max(0, Math.floor(ratio * car.fotos.length)));
      setZone(zone);
    });
    zoneWrap.addEventListener('mouseleave', () => setZone(0));

    card.querySelector('.rd-compare-btn').addEventListener('click', () => toggleCompare(n));
  });
}

function toggleCompare(n) {
  const btn = document.querySelector('.rd-card[data-n="' + n + '"] .rd-compare-btn');
  if (compareIds.has(n)) {
    compareIds.delete(n);
    btn.textContent = '+ Comparar';
    btn.classList.remove('activo');
  } else {
    if (compareIds.size >= 3) { alert('Máximo 3 coches para comparar'); return; }
    compareIds.add(n);
    btn.textContent = '✓ Comparando';
    btn.classList.add('activo');
  }
  renderTray();
}

function renderTray() {
  const tray = document.getElementById('rd-tray');
  if (compareIds.size === 0) { tray.style.display = 'none'; tray.innerHTML = ''; return; }
  tray.style.display = 'flex';
  const chips = [...compareIds].map((n) => {
    const car = CARS.find((c) => c.n === n);
    return '<span class="rd-tray-chip">' + car.modelo + ' <span data-n="' + n + '" class="rd-tray-x">✕</span></span>';
  }).join('');
  tray.innerHTML =
    '<span class="rd-tray-label">Comparando ' + compareIds.size + '</span>' +
    '<div class="rd-tray-chips">' + chips + '</div>' +
    '<button id="rd-tray-btn" class="rd-tray-btn">Ver comparación</button>';
  tray.querySelectorAll('.rd-tray-x').forEach((x) => x.addEventListener('click', (e) => {
    e.preventDefault();
    const n = parseInt(e.target.dataset.n, 10);
    toggleCompare(n);
  }));
  document.getElementById('rd-tray-btn').addEventListener('click', openOverlay);
}

function openOverlay() {
  const cars = [...compareIds].map((n) => CARS.find((c) => c.n === n));
  document.getElementById('rd-cmp-cols').innerHTML = cars.map((c) => (
    '<div class="rd-cmp-col">' +
      '<img src="' + c.fotos[0] + '">' +
      '<div class="rd-cmp-row rd-cmp-strong">' + c.modelo + '</div>' +
      '<div class="rd-cmp-row rd-cmp-small">' + c.version + '</div>' +
      '<div class="rd-cmp-row rd-cmp-accent">' + c.precio + ' €</div>' +
      '<div class="rd-cmp-row">' + c.km + ' km</div>' +
      '<div class="rd-cmp-row">' + c.combustible + '</div>' +
      '<div class="rd-cmp-row">' + c.cambio + '</div>' +
    '</div>'
  )).join('');
  document.getElementById('rd-overlay').style.display = 'flex';
}

document.getElementById('rd-overlay-close').addEventListener('click', () => {
  document.getElementById('rd-overlay').style.display = 'none';
});

document.getElementById('rd-dark-toggle').addEventListener('click', () => {
  document.body.classList.toggle('dark');
  document.getElementById('rd-dark-label').textContent =
    document.body.classList.contains('dark') ? '☀️ Modo claro' : '🌙 Modo oscuro';
});

initCards();
"""
```

- [ ] **Step 4: Commit**

```bash
git add generar_prueba.py
git commit -m "Add HTML/CSS/JS template for the design-preview page"
```

---

### Task 3: Generar la salida y copiar la foto del hero

**Files:**
- Modify: `generar_prueba.py`
- Create: `prueba/index.html` (generado)
- Create: `prueba/assets/hero.jpg` (copiado)

- [ ] **Step 1: Reemplazar el bloque `if __name__ == "__main__":` para que escriba los archivos**

En `generar_prueba.py`, reemplazar el bloque final por:

```python
def main():
    coches = cargar_coches()
    print(f"Coches cargados para la página de prueba: {len(coches)}")

    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "assets").mkdir(exist_ok=True)

    if HERO_SRC.exists():
        shutil.copy(HERO_SRC, OUT_DIR / "assets" / "hero.jpg")
        print("Foto del hero copiada a prueba/assets/hero.jpg")
    else:
        print(f"⚠️  No se encontró {HERO_SRC} — prueba/assets/hero.jpg no se va a generar, el hero va a quedar sin foto de fondo.")

    html = construir_html(coches)
    (OUT_DIR / "index.html").write_text(html, encoding="utf-8")
    print(f"✅ prueba/index.html generado ({len(html)} caracteres, {len(coches)} coches)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Correr el generador**

Run: `python3 generar_prueba.py`
Expected:
```
Coches cargados para la página de prueba: <N entre 35 y 55>
Foto del hero copiada a prueba/assets/hero.jpg
✅ prueba/index.html generado (... caracteres, <N> coches)
```

- [ ] **Step 3: Verificación rápida del HTML generado (sin abrir navegador todavía)**

Run: `grep -c 'rd-card' prueba/index.html && grep -c 'href="/coches/' prueba/index.html`
Expected: dos números iguales a la cantidad de coches cargada en el Step 2 (cada tarjeta tiene una clase `rd-card` y un link `/coches/...`).

- [ ] **Step 4: Commit**

```bash
git add prueba/
git commit -m "Generate the design-preview page with real catalog data"
```

---

### Task 4: Verificación navegando la página de prueba

Esta tarea es manual — usar el navegador para confirmar que todo lo que pediste funciona antes de publicarla.

- [ ] **Step 1: Abrir `prueba/index.html` localmente y revisar el hero**

Abrir el archivo en el navegador (arrastrarlo o `open prueba/index.html` en Mac). Confirmar: se ve la foto de fondo del hero, el título grande, la barra flotante translúcida abajo a la derecha, y que al hacer scroll la foto del hero se queda "fija" (parallax).

- [ ] **Step 2: Probar el hover de fotos y el modo oscuro**

Pasar el mouse de izquierda a derecha sobre la foto de 2-3 tarjetas distintas — confirmar que la foto y el contador (`1/8`, `2/8`...) cambian. Tocar el botón de modo oscuro arriba a la derecha — confirmar que cambia todo el fondo.

- [ ] **Step 3: Probar el comparador**

Tocar "+ Comparar" en 2 o 3 tarjetas — confirmar que aparece la barra flotante abajo. Tocar "Ver comparación" — confirmar que se abre la tabla con fotos y datos reales de esos coches. Cerrarla con la ✕.

- [ ] **Step 4: Probar que se puede entrar a una ficha real**

Tocar el nombre o la foto de cualquier coche — confirmar que abre la ficha real de ese coche (la misma que ya existe hoy en producción) y que se puede scrollear con normalidad ahí.

- [ ] **Step 5: Si algo no se ve bien, anotar qué y volver al Task 2 a ajustar el CSS/JS correspondiente antes de seguir.**

---

### Task 5: Publicar en `automovilesruedaocasion.com/prueba/`

**Solo hacer este paso cuando el Task 4 salió bien.** Esto sube la carpeta `prueba/` al repositorio real — no toca `index.html` ni ningún archivo de producción, pero SÍ la deja visible públicamente (sin buscadores, gracias al `noindex` del HTML, pero cualquiera con el link puede entrar).

- [ ] **Step 1: Confirmar que no se modificó nada fuera de `prueba/` y `generar_prueba.py`**

Run: `git status --short`
Expected: solo `generar_prueba.py` y archivos dentro de `prueba/` (ya deberían estar commiteados de los pasos anteriores — este es un chequeo de que no quedó nada raro).

- [ ] **Step 2: Push**

```bash
git push origin main
```

- [ ] **Step 3: Esperar ~1 minuto (tiempo típico de GitHub Pages) y abrir**

`https://automovilesruedaocasion.com/prueba/`

Confirmar que carga igual que en local, y repetir la verificación del Task 4 ahí para confirmar que las rutas absolutas (`/web_fotos/...`, `/coches/...`, `/prueba/assets/hero.jpg`) funcionan también en producción.
