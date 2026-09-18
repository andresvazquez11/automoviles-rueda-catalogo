# Traductor ES/EN Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A 🇪🇸/🇬🇧 flag toggle in the header that instantly switches the catalog and every car's detail page to English, with the translation itself precomputed and cached at generation time — no live translation service, no cost/latency for visitors.

**Architecture:** Fixed-vocabulary fields (fuel, gearbox, availability) get a plain Python dictionary. Free text (car version, equipment list, color) is translated once per car via the Gemini API (same `GOOGLE_API_KEY` already in `config.txt`, same `google-genai` package already used by `generar_imagenes_gemini.py`) and cached by content hash in `traducciones_cache.json`, so daily reruns only call the API for new/changed cars. Both languages are baked into the generated HTML — the catalog page (`index.html`) via `data-es`/`data-en` attributes swapped by a small shared script, and the car detail page (`coches/*.html`, which renders almost entirely from a JS-embedded JSON blob) via extra `_en` keys in that JSON, read by a now-language-aware `cargarFicha()` in `assets/calculadora.js`.

**Tech Stack:** Python 3 (`generar_web.py`), the `google-genai` package (already installed/used elsewhere in this project), vanilla JS/CSS (no new dependencies).

**Spec:** `docs/superpowers/specs/2026-09-18-traductor-es-en-design.md`

**Depends on:** none of this plan's tasks require the `coches-destacados` plan, and vice versa — the two can be implemented in either order. If both are implemented, Task 7 here and Task 7 of `2026-09-18-coches-destacados.md` both touch the same `git add` line in the daily `.command` script — read that line fresh each time rather than assuming its exact prior content.

---

## Reference

- Project root: `~/Desktop/catalogo_automoviles_rueda`
- This project has no automated test suite — verification is "regenerate the site, grep the output, open it in a browser and check it," matching the project's existing workflow.
- `config.txt` already has a line `GOOGLE_API_KEY=...` (used by `generar_imagenes_gemini.py`) — this plan reuses it, no new credential needed.
- `google-genai` is already installed (imported today as `from google import genai` in `generar_imagenes_gemini.py`).

---

### Task 1: Translation building blocks (no behavior change yet)

**Files:**
- Modify: `generar_web.py:8` (imports)
- Modify: `generar_web.py` — add new constants/functions after `dwa_foto_url` (around line 80)

- [ ] **Step 1: Add the `html` import**

Change:
```python
import hashlib, json, shutil, sys, urllib.parse
```
to:
```python
import hashlib, html, json, shutil, sys, urllib.parse
```

- [ ] **Step 2: Add the config/cache/i18n helpers**

Find this (the end of `dwa_foto_url`, right before the `_ICONO_INSTAGRAM` constant):
```python
    return f"{DASWELTAUTO}/esp/fotos_anuncios/{path}/x01.jpg"

_ICONO_INSTAGRAM = '''<svg width="22" height="22" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
```

Insert a new block between them, so it reads:
```python
    return f"{DASWELTAUTO}/esp/fotos_anuncios/{path}/x01.jpg"

# ── Traducción ES/EN — texto libre cacheado, vocabulario fijo por diccionario ─

CONFIG_PATH = BASE_DIR / "config.txt"
TRADUCCIONES_PATH = BASE_DIR / "traducciones_cache.json"

def _leer_google_api_key() -> "str | None":
    """Misma convención que generar_imagenes_gemini.py: GOOGLE_API_KEY=... en config.txt."""
    if not CONFIG_PATH.exists():
        return None
    for linea in CONFIG_PATH.read_text(encoding="utf-8").splitlines():
        if linea.strip().startswith("GOOGLE_API_KEY="):
            key = linea.split("=", 1)[1].strip()
            return key or None
    return None

def _cliente_gemini_o_none():
    """Cliente de Gemini para traducir texto libre, o None si no hay API key
    o falta el paquete — en ese caso el texto libre se queda en español (el
    toggle de idioma sigue funcionando para el resto de la página, solo no
    traduce ese texto ese día)."""
    key = _leer_google_api_key()
    if not key:
        print("  ⚠️  Sin GOOGLE_API_KEY en config.txt — el texto libre no se traduce hoy.")
        return None
    try:
        from google import genai
        return genai.Client(api_key=key)
    except ImportError:
        print("  ⚠️  Falta el paquete google-genai — el texto libre no se traduce hoy.")
        return None

def _cargar_cache_traducciones() -> dict:
    if TRADUCCIONES_PATH.exists():
        return json.loads(TRADUCCIONES_PATH.read_text(encoding="utf-8"))
    return {}

def _guardar_cache_traducciones(cache: dict) -> None:
    TRADUCCIONES_PATH.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )

def i18n_span(es: str, en: str, cls: str = "") -> str:
    """Envuelve un texto para el toggle de idioma del header: se ve el
    español por defecto, con el inglés guardado en data-en para cuando el
    visitante toca la bandera 🇬🇧 (ver assets/idioma.js, Task 5)."""
    es_attr = html.escape(es, quote=True)
    en_attr = html.escape(en, quote=True)
    extra = f" {cls}" if cls else ""
    return f'<span class="rd-i18n{extra}" data-es="{es_attr}" data-en="{en_attr}">{html.escape(es)}</span>'

COMBUSTIBLE_EN = {
    "Gasolina": "Petrol", "Diésel": "Diesel", "Diesel": "Diesel",
    "Híbrido": "Hybrid", "Hibrido": "Hybrid", "Eléctrico": "Electric", "Electrico": "Electric",
}
CAMBIO_EN = {"Manual": "Manual", "Automático": "Automatic", "Automatico": "Automatic"}
ESTADO_EN = {"Disponible": "Available", "Reservado": "Reserved"}

_ICONO_INSTAGRAM = '''<svg width="22" height="22" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
```

- [ ] **Step 3: Verify it imports cleanly**

```bash
cd ~/Desktop/catalogo_automoviles_rueda
python3 -c "
import generar_web as g
print(g.i18n_span('Hola', 'Hello'))
print(g.COMBUSTIBLE_EN['Gasolina'])
print(g._leer_google_api_key() is not None)
"
```
Expected: a `<span class="rd-i18n" data-es="Hola" data-en="Hello">Hola</span>` line, `Petrol`, and `True` (since `config.txt` already has the key).

- [ ] **Step 4: Commit**

```bash
git add generar_web.py
git commit -m "Add ES/EN translation building blocks (no behavior change yet)"
```

---

### Task 2: Batch-translate each car and cache the result

**Files:**
- Modify: `generar_web.py` — add `traducir_coche()` near the helpers from Task 1
- Modify: `generar_web.py` inside `main()` — compute and cache translations for every publishable car

Equipment lists can be long, and there are 50+ cars — translating line-by-line would mean hundreds of API calls. Instead, one call per car translates `version` + `equipamiento` + `color` together as JSON, and the whole result is cached by a hash of that car's combined translatable text, so unchanged cars cost nothing on the next run.

- [ ] **Step 1: Add `traducir_coche()`**

Add this after the block from Task 1 (right after `ESTADO_EN = {...}`):
```python
def _hash_coche_traducible(car: dict) -> str:
    contenido = (car.get("version", "") + "\n" +
                 "\n".join(car.get("equipamiento", [])) + "\n" +
                 car.get("color", ""))
    return hashlib.sha256(contenido.encode("utf-8")).hexdigest()[:16]

def traducir_coche(car: dict, cache: dict, client) -> dict:
    """Traduce version + equipamiento + color de un coche al inglés en una
    sola llamada a Gemini, cacheada por hash del contenido combinado — si
    nada de eso cambió desde la corrida anterior, no se vuelve a llamar a
    la API. Si falla la API (o no hay client), devuelve los mismos textos
    en español: el toggle de idioma sigue funcionando, solo no traduce ese
    texto libre ese día."""
    version = car.get("version", "")
    equipamiento = car.get("equipamiento", [])
    color = car.get("color", "")
    h = _hash_coche_traducible(car)
    if h in cache:
        return cache[h]
    fallback = {"version_en": version, "equipamiento_en": list(equipamiento), "color_en": color}
    if client is None:
        return fallback
    payload = {"version": version, "equipamiento": equipamiento, "color": color}
    prompt = (
        "Traduce al inglés este JSON de una ficha de coche usado (concesionario "
        "en España), tono comercial y natural para un comprador angloparlante. "
        "Devuelve SOLO un JSON con las mismas claves (version, equipamiento "
        "como lista en el mismo orden, color), sin explicaciones ni markdown:\n\n"
        + json.dumps(payload, ensure_ascii=False)
    )
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        texto = (response.text or "").strip()
        texto = texto.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        datos = json.loads(texto)
        resultado = {
            "version_en": datos.get("version") or version,
            "equipamiento_en": datos.get("equipamiento") or list(equipamiento),
            "color_en": datos.get("color") or color,
        }
        if len(resultado["equipamiento_en"]) != len(equipamiento):
            resultado["equipamiento_en"] = list(equipamiento)  # desalineado → mejor español que roto
        cache[h] = resultado
        return resultado
    except Exception as e:
        print(f"  ⚠️  Traducción falló para coche #{car.get('n')}: {e}")
        return fallback
```

- [ ] **Step 2: Wire it into `main()`**

Find this comment in `main()` (it marks the start of the shared photo-resolution step):
```python
    # ── Paso 1 (una sola vez, compartido entre perfiles): resolver las fotos
    # de cada coche, incluyendo el respaldo de fotos para "Retirado". ────────
    slugs_validos: set[str] = set()
```

Insert immediately before it:
```python
    print("🌐  Traduciendo texto libre al inglés (con caché)…")
    cache_trad = _cargar_cache_traducciones()
    tam_inicial = len(cache_trad)
    cliente_trad = _cliente_gemini_o_none()
    traducciones: dict[int, dict] = {}
    for car in todos_los_coches:
        if car["n"] in sin_foto:
            continue
        traducciones[car["n"]] = traducir_coche(car, cache_trad, cliente_trad)
    _guardar_cache_traducciones(cache_trad)
    print(f"    {len(cache_trad) - tam_inicial} coche(s) traducido(s) de nuevo, {tam_inicial} ya en caché")

    # ── Paso 1 (una sola vez, compartido entre perfiles): resolver las fotos
    # de cada coche, incluyendo el respaldo de fotos para "Retirado". ────────
    slugs_validos: set[str] = set()
```

- [ ] **Step 3: Regenerate and verify**

```bash
cd ~/Desktop/catalogo_automoviles_rueda && python3 generar_web.py
```
Expected: a new line like `🌐  Traduciendo texto libre al inglés (con caché)…` followed by `NN coche(s) traducido(s) de nuevo, 0 ya en caché` (all new, first run).

```bash
python3 -c "import json; d=json.load(open('traducciones_cache.json')); print(len(d)); print(list(d.values())[0])"
```
Expected: a count matching the number of publishable cars, and one entry showing `version_en`/`equipamiento_en`/`color_en`.

Run it again immediately:
```bash
python3 generar_web.py
```
Expected: this time the line reads `0 coche(s) traducido(s) de nuevo, NN ya en caché` — confirms the cache is actually being used.

- [ ] **Step 4: Commit**

```bash
git add generar_web.py traducciones_cache.json
git commit -m "Translate car version/equipment/color to English, cached by content hash"
```

---

### Task 3: Translate the catalog cards

**Files:**
- Modify: `generar_web.py` — `build_card_html` signature and body
- Modify: `generar_web.py` — `build_index_html`'s call to `build_card_html`, and its own signature
- Modify: `generar_web.py` — `main()`'s call to `build_index_html`

- [ ] **Step 1: Update `build_card_html`**

Change the signature:
```python
def build_card_html(car: dict, hist: dict, fotos: list[str]) -> str:
```
to:
```python
def build_card_html(car: dict, hist: dict, fotos: list[str], trad: dict) -> str:
```

Then replace the return statement:
```python
    return f'''<a class="rd-card" href="{href}" data-n="{n}" data-precio="{precio_num}" data-km="{km_num}" data-estado="{estado_lbl}" data-buscar="{buscar_txt}">
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
```
with:
```python
    return f'''<a class="rd-card" href="{href}" data-n="{n}" data-precio="{precio_num}" data-km="{km_num}" data-estado="{estado_lbl}" data-buscar="{buscar_txt}">
  <div class="rd-card-media">
    <div class="rd-card-photos">{fotos_html}</div>
    {nav_html}
    <div class="rd-card-dots">{dots_html}</div>
    <span class="rd-badge-estado {estado_cls}">{i18n_span(estado_lbl, ESTADO_EN[estado_lbl])}</span>
    {'<span class="rd-badge-oferta">' + i18n_span("OFERTA", "PRICE DROP") + '</span>' if p_ant else ''}
    <span class="rd-badge-dgt"><img src="{DGT_URLS[dgt_txt]}" alt="Etiqueta {dgt_txt}" loading="lazy"></span>
    {f'<span class="rd-badge-fotos">📷 {len(fotos)}</span>' if len(fotos) > 1 else ''}
  </div>
  <div class="rd-card-body">
    <div class="rd-card-modelo">{car["modelo"]}</div>
    <div class="rd-card-version">{i18n_span(car["version"], trad["version_en"])}</div>
    <div class="rd-card-pills">
      {f'<span class="rd-pill">⛽ {i18n_span(car["combustible"], COMBUSTIBLE_EN.get(car["combustible"], car["combustible"]))}</span>' if car.get("combustible") else ''}
      {f'<span class="rd-pill">🛣️ {car["km"]} km</span>' if car.get("km") else ''}
      {f'<span class="rd-pill">📅 {car["fecha"]}</span>' if car.get("fecha") else ''}
      {f'<span class="rd-pill">⚙️ {i18n_span(car["cambio"], CAMBIO_EN.get(car["cambio"], car["cambio"]))}</span>' if car.get("cambio") else ''}
    </div>
    <div class="rd-card-price-row">
      <div>{precio_row}</div>
      <div class="rd-card-cuota">{i18n_span("Desde", "From")} <strong>{cuota:.0f} €/mes</strong></div>
    </div>
  </div>
</a>'''
```

- [ ] **Step 2: Update `build_index_html`'s signature and its call to `build_card_html`**

Change:
```python
def build_index_html(cars: list[dict], rutas: dict[int, list[str]], perfil: dict) -> str:
```
to:
```python
def build_index_html(cars: list[dict], rutas: dict[int, list[str]], perfil: dict, traducciones: dict[int, dict]) -> str:
```

Change:
```python
    tarjetas = "\n".join(
        build_card_html(
            car, hist,
            [f"/{f.lstrip('/')}" for f in car.get("fotos", [])] if car.get("fuente") == "motorflash" else rutas.get(car["n"], [])
        )
        for car in cars
        if car.get("estado") != "Retirado"
    )
```
to:
```python
    tarjetas = "\n".join(
        build_card_html(
            car, hist,
            [f"/{f.lstrip('/')}" for f in car.get("fotos", [])] if car.get("fuente") == "motorflash" else rutas.get(car["n"], []),
            traducciones[car["n"]]
        )
        for car in cars
        if car.get("estado") != "Retirado"
    )
```

- [ ] **Step 3: Update `main()`'s call to `build_index_html`**

Change:
```python
        html_index = build_index_html(coches, rutas, perfil)
```
to:
```python
        html_index = build_index_html(coches, rutas, perfil, traducciones)
```

- [ ] **Step 4: Regenerate and verify**

```bash
cd ~/Desktop/catalogo_automoviles_rueda && python3 generar_web.py
grep -o 'class="rd-i18n" data-es="[^"]*" data-en="[^"]*"' index.html | head -5
```
Expected: several matches, including `data-es="Disponible" data-en="Available"` and at least one card's version text with an English translation in `data-en`.

- [ ] **Step 5: Commit**

```bash
git add generar_web.py index.html alejandro/index.html
git commit -m "Translate catalog card text (version, fuel, gearbox, status, badges)"
```

---

### Task 4: Translate the catalog's UI chrome (filters, search, sort, counter)

**Files:**
- Modify: `generar_web.py` inside `build_index_html` — the `.rd-controls` block and the `emptyMsg`/`aplicar()` JS

- [ ] **Step 1: Wrap the controls markup**

Change:
```python
<div class="rd-controls">
  <div class="rd-filter-tabs">
    <button class="rd-filter-btn activo" data-filter="todos">Todos ({total_disp + total_res})</button>
    <button class="rd-filter-btn" data-filter="Disponible">Disponible ({total_disp})</button>
    <button class="rd-filter-btn" data-filter="Reservado">Reservado ({total_res})</button>
  </div>
  <div class="rd-search-wrap">
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
    <input class="rd-search-input" id="rd-search" type="text" placeholder="Buscar modelo..." autocomplete="off">
  </div>
  <select class="rd-sort-select" id="rd-sort">
    <option value="default">Ordenar</option>
    <option value="precio-asc">Precio ↑ menor primero</option>
    <option value="precio-desc">Precio ↓ mayor primero</option>
    <option value="km-asc">Km ↑ menos km</option>
    <option value="km-desc">Km ↓ más km</option>
  </select>
  <div class="rd-counter">Mostrando <strong id="rd-cnt">{total_disp + total_res}</strong> vehículos</div>
</div>
```
to:
```python
<div class="rd-controls">
  <div class="rd-filter-tabs">
    <button class="rd-filter-btn activo" data-filter="todos">{i18n_span("Todos", "All")} ({total_disp + total_res})</button>
    <button class="rd-filter-btn" data-filter="Disponible">{i18n_span("Disponible", "Available")} ({total_disp})</button>
    <button class="rd-filter-btn" data-filter="Reservado">{i18n_span("Reservado", "Reserved")} ({total_res})</button>
  </div>
  <div class="rd-search-wrap">
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
    <input class="rd-search-input" id="rd-search" type="text" placeholder="Buscar modelo..." data-es-placeholder="Buscar modelo..." data-en-placeholder="Search model..." autocomplete="off">
  </div>
  <select class="rd-sort-select" id="rd-sort">
    <option value="default" class="rd-i18n" data-es="Ordenar" data-en="Sort by">Ordenar</option>
    <option value="precio-asc" class="rd-i18n" data-es="Precio ↑ menor primero" data-en="Price ↑ lowest first">Precio ↑ menor primero</option>
    <option value="precio-desc" class="rd-i18n" data-es="Precio ↓ mayor primero" data-en="Price ↓ highest first">Precio ↓ mayor primero</option>
    <option value="km-asc" class="rd-i18n" data-es="Km ↑ menos km" data-en="Mileage ↑ lowest first">Km ↑ menos km</option>
    <option value="km-desc" class="rd-i18n" data-es="Km ↓ más km" data-en="Mileage ↓ highest first">Km ↓ más km</option>
  </select>
  <div class="rd-counter">{i18n_span("Mostrando", "Showing")} <strong id="rd-cnt">{total_disp + total_res}</strong> {i18n_span("vehículos", "vehicles")}</div>
</div>
```

- [ ] **Step 2: Translate the "no results" message and keep it correct after re-render**

Change:
```python
  const emptyMsg = document.createElement('div');
  emptyMsg.className = 'rd-empty-state';
  emptyMsg.innerHTML = '<div>🔍</div><p>No se encontraron vehículos.</p>';
```
to:
```python
  const emptyMsg = document.createElement('div');
  emptyMsg.className = 'rd-empty-state';
  emptyMsg.innerHTML = '<div>🔍</div><p class="rd-i18n" data-es="No se encontraron vehículos." data-en="No vehicles found.">No se encontraron vehículos.</p>';
```

Change:
```python
    if (emptyMsg.parentNode) emptyMsg.remove();
    if (!visibles.length) grid.appendChild(emptyMsg);
```
to:
```python
    if (emptyMsg.parentNode) emptyMsg.remove();
    if (!visibles.length) {{
      grid.appendChild(emptyMsg);
      if (window.rdAplicarIdioma) window.rdAplicarIdioma(window.rdIdiomaActual());
    }}
```

(This message is created once in Spanish; if the visitor is already in English when it first appears, the `rdAplicarIdioma` call — defined in Task 5's `assets/idioma.js` — immediately corrects it. Doubled `{{`/`}}` again because this is inside the Python f-string.)

- [ ] **Step 3: Regenerate and verify**

```bash
cd ~/Desktop/catalogo_automoviles_rueda && python3 generar_web.py
grep -c 'rd-i18n' index.html
```
Expected: a count noticeably higher than before Task 3 (chrome strings added on top of card strings).

- [ ] **Step 4: Commit**

```bash
git add generar_web.py index.html alejandro/index.html
git commit -m "Translate catalog filter/search/sort/counter UI chrome"
```

---

### Task 5: The flag toggle button and the shared toggle script

**Files:**
- Modify: `generar_web.py` — add `lang_toggle_html()` near `header_social_html`
- Modify: `generar_web.py` — both header blocks (`build_index_html` and `build_coche_html`) and both `<head>` blocks
- Modify: `assets/estilos.css` — toggle button styling
- Create: `assets/idioma.js`

- [ ] **Step 1: Add `lang_toggle_html()`**

Add this right after the `header_social_html` function definition:
```python
def lang_toggle_html() -> str:
    """Botones de bandera para cambiar el idioma visible — comparten el
    mismo assets/idioma.js en index.html y en cada ficha de coche."""
    return '''<div class="rd-lang-toggle">
    <button type="button" class="rd-lang-btn activo" data-lang="es" aria-label="Ver en español">🇪🇸</button>
    <button type="button" class="rd-lang-btn" data-lang="en" aria-label="View in English">🇬🇧</button>
  </div>'''
```

- [ ] **Step 2: Add the button to both headers**

In `build_index_html`, change:
```python
<header class="rd-header">
  <div class="rd-header-brand">
    <strong>Automóviles Rueda</strong>
    <span class="rd-header-asesor"><em>Asesor comercial</em>{perfil["nombre"]} · <span class="rd-header-tel">{perfil["telefono"]}</span></span>
  </div>
  {header_social_html(perfil["redes"])}
</header>
```
to:
```python
<header class="rd-header">
  <div class="rd-header-brand">
    <strong>Automóviles Rueda</strong>
    <span class="rd-header-asesor"><em>Asesor comercial</em>{perfil["nombre"]} · <span class="rd-header-tel">{perfil["telefono"]}</span></span>
  </div>
  {header_social_html(perfil["redes"])}
  {lang_toggle_html()}
</header>
```

In `build_coche_html`, change:
```python
<header class="rd-header">
  <div class="rd-header-brand">
    <strong>Automóviles Rueda</strong>
    <span class="rd-header-asesor"><em>Asesor comercial</em>{nombre} · <span class="rd-header-tel">{telefono}</span></span>
  </div>
  {header_social_html(perfil["redes"])}
</header>
```
to:
```python
<header class="rd-header">
  <div class="rd-header-brand">
    <strong>Automóviles Rueda</strong>
    <span class="rd-header-asesor"><em>Asesor comercial</em>{nombre} · <span class="rd-header-tel">{telefono}</span></span>
  </div>
  {header_social_html(perfil["redes"])}
  {lang_toggle_html()}
</header>
```

- [ ] **Step 3: Load `idioma.js` on every page**

Using an editor with "replace all", change every occurrence of:
```python
<link rel="stylesheet" href="/assets/estilos.css">
```
to:
```python
<link rel="stylesheet" href="/assets/estilos.css">
<script src="/assets/idioma.js"></script>
```
(This line appears twice in `generar_web.py` — once in `build_coche_html`'s `<head>`, once in `build_index_html`'s `<head>`. Both need it, so a project-wide replace is correct here.)

- [ ] **Step 4: Create `assets/idioma.js`**

```javascript
(function() {
  var KEY = 'rd_idioma';

  function idiomaActual() {
    try { return localStorage.getItem(KEY) || 'es'; } catch (e) { return 'es'; }
  }

  function aplicar(idioma) {
    document.querySelectorAll('.rd-i18n').forEach(function(el) {
      var texto = el.getAttribute('data-' + idioma);
      if (texto !== null) el.textContent = texto;
    });
    document.querySelectorAll('[data-es-placeholder]').forEach(function(el) {
      var texto = el.getAttribute('data-' + idioma + '-placeholder');
      if (texto !== null) el.placeholder = texto;
    });
    document.querySelectorAll('.rd-lang-btn').forEach(function(btn) {
      btn.classList.toggle('activo', btn.dataset.lang === idioma);
    });
    document.documentElement.setAttribute('lang', idioma);
    if (typeof window.rdAlCambiarIdioma === 'function') window.rdAlCambiarIdioma(idioma);
  }

  function cambiar(idioma) {
    try { localStorage.setItem(KEY, idioma); } catch (e) {}
    aplicar(idioma);
  }

  // Expuesto para que otros scripts de la misma página (la franja de
  // destacados, la ficha de coche vía calculadora.js) puedan re-aplicar el
  // idioma actual a contenido que insertan después de la carga inicial.
  window.rdAplicarIdioma = aplicar;
  window.rdIdiomaActual = idiomaActual;
  window.rdCambiarIdioma = cambiar;

  document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.rd-lang-btn').forEach(function(btn) {
      btn.addEventListener('click', function() { cambiar(btn.dataset.lang); });
    });
    aplicar(idiomaActual());
  });
})();
```

- [ ] **Step 5: Add the toggle button CSS**

Append to `assets/estilos.css`, right after the existing `@media (max-width: 640px) { .rd-header ... }` block (the one ending with `.rd-header-social svg { width: 24px; height: 24px; }`):
```css
.rd-lang-toggle { display: flex; gap: 6px; flex-shrink: 0; }
.rd-lang-btn {
  background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.18);
  border-radius: 8px; padding: 6px 9px; font-size: 17px; line-height: 1;
  cursor: pointer; opacity: 0.55; transition: opacity .15s ease, border-color .15s ease;
}
.rd-lang-btn:hover { opacity: 0.85; }
.rd-lang-btn.activo { opacity: 1; border-color: var(--rd-red); background: rgba(200,35,43,0.18); }
@media (max-width: 640px) {
  .rd-lang-btn { padding: 5px 7px; font-size: 14px; }
}
```

- [ ] **Step 6: Regenerate and verify**

```bash
cd ~/Desktop/catalogo_automoviles_rueda && python3 generar_web.py
grep -c 'assets/idioma.js' index.html coches/01-*.html
grep -c 'rd-lang-toggle' index.html coches/01-*.html
```
Expected: `1` for each file/pattern combination (script tag once per page, toggle markup once per page).

- [ ] **Step 7: Manual check in browser**

```bash
open index.html
```
Click 🇬🇧 in the header. Expected: filter buttons, search placeholder, sort options, counter, card version text, and status/oferta badges all switch to English instantly, no page reload. Click 🇪🇸 — everything switches back. Open a car's detail page from the catalog while English is active — confirm the catalog is in English (the ficha itself won't be fully translated until Task 6, but the header toggle and its "active" state should already reflect English, since `idioma.js` is now on that page too).

- [ ] **Step 8: Commit**

```bash
git add generar_web.py assets/estilos.css assets/idioma.js index.html alejandro/index.html coches/
git commit -m "Add ES/EN flag toggle button and shared idioma.js"
```

---

### Task 6: Translate the car detail page

**Files:**
- Modify: `generar_web.py` — `build_coche_html` signature, `coche_json`, and the static Spanish strings outside the financing calculator
- Modify: `generar_web.py` — `main()`'s call to `build_coche_html`
- Modify: `assets/calculadora.js` — `cargarFicha()`

The detail page renders almost everything via `cargarFicha()` in `assets/calculadora.js` from a `const COCHE = {...}` JSON blob embedded in the page — there's very little static server-rendered text to wrap with `i18n_span` here. The financing calculator itself (VWFS/BBVA tabs and their content) stays in Spanish per the design spec — none of its markup is touched.

- [ ] **Step 1: Update `build_coche_html`'s signature**

Change:
```python
def build_coche_html(car: dict, fotos_urls: list[str], perfil: dict) -> str:
```
to:
```python
def build_coche_html(car: dict, fotos_urls: list[str], perfil: dict, trad: dict) -> str:
```

- [ ] **Step 2: Add the English fields to `coche_json`**

Change:
```python
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
```
to:
```python
    coche_json = json.dumps({
        "n": n, "modelo": car["modelo"], "version": car["version"],
        "version_en": trad["version_en"],
        "combustible": car.get("combustible",""), "km": car.get("km",""),
        "fecha": car.get("fecha",""), "fin_fecha_iso":
            (lambda f: f"{f.split('/')[1]}-{f.split('/')[0]}" if f and "/" in f and len(f.split("/"))==2 else "")(car.get("fecha","")),
        "cambio": car.get("cambio",""), "color": car.get("color",""),
        "color_en": trad["color_en"],
        "precio": car["precio"], "estado": car["estado"], "vendido": vendido,
        "url": url_externa,
        "equipamiento": car.get("equipamiento", []),
        "equipamiento_en": trad["equipamiento_en"],
        "fotos": fotos,
    }, ensure_ascii=False)
```

- [ ] **Step 3: Translate the static Spanish text outside the calculator**

Change:
```python
    vendido_banner = '' if not vendido else '''
  <div class="rd-vendido-banner" id="m-vendido-banner">
    Este vehículo ya no está disponible.
    <a href="../index.html">Ver coches disponibles →</a>
  </div>'''
```
to:
```python
    vendido_banner = '' if not vendido else f'''
  <div class="rd-vendido-banner" id="m-vendido-banner">
    {i18n_span("Este vehículo ya no está disponible.", "This vehicle is no longer available.")}
    <a href="../index.html">{i18n_span("Ver coches disponibles →", "See available cars →")}</a>
  </div>'''
```

Change:
```python
<a class="rd-back" href="../index.html">&#8249; Volver al catálogo</a>
```
to:
```python
<a class="rd-back" href="../index.html">&#8249; {i18n_span("Volver al catálogo", "Back to catalog")}</a>
```

Change:
```python
  <div class="rd-section equip-section" id="equip-section">
    <h3>Equipamiento</h3>
    <div class="equip-grid" id="m-equip"></div>
  </div>
```
to:
```python
  <div class="rd-section equip-section" id="equip-section">
    <h3>{i18n_span("Equipamiento", "Equipment")}</h3>
    <div class="equip-grid" id="m-equip"></div>
  </div>
```

Change:
```python
  <div class="rd-footnote">
    <a id="m-link" href="#" target="_blank" rel="noopener">Ver ficha original en Das WeltAuto ↗</a>
  </div>
```
to:
```python
  <div class="rd-footnote">
    <a id="m-link" href="#" target="_blank" rel="noopener">{i18n_span("Ver ficha original en Das WeltAuto ↗", "See original listing on Das WeltAuto ↗")}</a>
  </div>
```

Change:
```python
<div class="rd-sticky-mobile" id="m-vendido-sticky" style="display:none">
  <div>Vendido</div>
  <a class="rd-btn rd-btn-secondary" href="../index.html">Ver disponibles</a>
</div>
<div class="rd-sticky-mobile" id="m-sticky-financiacion">
  <div class="precio" id="m-precio-sticky"></div>
  <a class="rd-btn rd-btn-primary" href="#m-financiacion">Ver financiación</a>
</div>
```
to:
```python
<div class="rd-sticky-mobile" id="m-vendido-sticky" style="display:none">
  <div>{i18n_span("Vendido", "Sold")}</div>
  <a class="rd-btn rd-btn-secondary" href="../index.html">{i18n_span("Ver disponibles", "See available")}</a>
</div>
<div class="rd-sticky-mobile" id="m-sticky-financiacion">
  <div class="precio" id="m-precio-sticky"></div>
  <a class="rd-btn rd-btn-primary" href="#m-financiacion">{i18n_span("Ver financiación", "View financing")}</a>
</div>
```

- [ ] **Step 4: Update `main()`'s call to `build_coche_html`**

Change:
```python
            html_coche = build_coche_html(car, fotos_por_coche[n], perfil)
```
to:
```python
            html_coche = build_coche_html(car, fotos_por_coche[n], perfil, traducciones[n])
```

- [ ] **Step 5: Make `cargarFicha()` in `assets/calculadora.js` language-aware**

Change:
```javascript
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
```
to:
```javascript
  const idioma = (window.rdIdiomaActual ? window.rdIdiomaActual() : 'es');
  const en = idioma === 'en';

  document.getElementById('m-modelo').textContent = c.modelo;
  document.getElementById('m-version').textContent = (en && c.version_en) ? c.version_en : c.version;

  const specsLabelsEn = { 'Combustible': 'Fuel', 'Kilómetros': 'Mileage', 'Matrícula': 'Registered', 'Cambio': 'Gearbox', 'Color': 'Color', 'Ubicación': 'Location' };
  const combustibleEn = { 'Gasolina': 'Petrol', 'Diésel': 'Diesel', 'Híbrido': 'Hybrid', 'Eléctrico': 'Electric' };
  const cambioEn = { 'Manual': 'Manual', 'Automático': 'Automatic' };
  const specs = [
    ['Combustible', en ? (combustibleEn[c.combustible] || c.combustible) : c.combustible],
    ['Kilómetros', c.km + ' km'],
    ['Matrícula', c.fecha],
    ['Cambio', en ? (cambioEn[c.cambio] || c.cambio) : c.cambio],
    ['Color', (en && c.color_en) ? c.color_en : c.color],
    ['Ubicación', c.ubicacion],
  ].filter(([,v]) => v);
  document.getElementById('m-specs').innerHTML = specs.map(([l,v]) =>
    `<div class="rd-spec-badge"><div class="lbl">${en ? (specsLabelsEn[l] || l) : l}</div><div class="val">${v}</div></div>`).join('');

  const equip = (en && c.equipamiento_en && c.equipamiento_en.length === (c.equipamiento || []).length)
    ? c.equipamiento_en : (c.equipamiento || []);
  const equipSection = document.getElementById('equip-section');
  if (equip.length) {
    document.getElementById('m-equip').innerHTML = equip.map(e =>
      `<div class="equip-item"><span class="equip-check">✓</span><span>${e}</span></div>`).join('');
    equipSection.style.display = '';
  } else { equipSection.style.display = 'none'; }
```

Change:
```javascript
    const pill = document.getElementById('m-estado-pill');
    pill.textContent = '🚫 Vendido';
    pill.classList.add('reservado');
```
to:
```javascript
    const pill = document.getElementById('m-estado-pill');
    pill.textContent = en ? '🚫 Sold' : '🚫 Vendido';
    pill.classList.add('reservado');
```

Change:
```javascript
  const pill = document.getElementById('m-estado-pill');
  const reservado = esReservado(c.estado);
  pill.textContent = reservado ? '🟠 Reservado' : '✅ Disponible';
```
to:
```javascript
  const pill = document.getElementById('m-estado-pill');
  const reservado = esReservado(c.estado);
  pill.textContent = reservado ? (en ? '🟠 Reserved' : '🟠 Reservado') : (en ? '✅ Available' : '✅ Disponible');
```

- [ ] **Step 6: Register the re-render hook, right after the initial call**

Find the bottom of `build_coche_html`'s template:
```python
<script>
const COCHE = {coche_json};
cargarFicha(COCHE);
</script>
```
Change it to:
```python
<script>
const COCHE = {coche_json};
cargarFicha(COCHE);
window.rdAlCambiarIdioma = function() {{ cargarFicha(COCHE); }};
</script>
```
(This makes the flag toggle re-render the ficha immediately when clicked while already on that page — see `assets/idioma.js`'s `aplicar()` from Task 5, which calls `window.rdAlCambiarIdioma` after every language switch.)

- [ ] **Step 7: Regenerate and verify**

```bash
cd ~/Desktop/catalogo_automoviles_rueda && python3 generar_web.py
grep -o '"version_en":"[^"]*"' coches/01-*.html | head -1
grep -o '"equipamiento_en":\[[^]]\{1,80\}' coches/01-*.html | head -1
```
Expected: both greps print a non-empty match — `version_en` with an English string, and the start of an `equipamiento_en` array.

- [ ] **Step 8: Manual check in browser**

```bash
open coches/01-*.html
```
Toggle 🇬🇧 in the header — confirm version, spec labels/values, and every equipment line switch to English, and the price/estado pill updates. Toggle back to 🇪🇸 — confirm it reverts. Confirm the financing calculator (tabs, cuota, campaign text) stays in Spanish throughout, as intended.

- [ ] **Step 9: Commit**

```bash
git add generar_web.py assets/calculadora.js coches/
git commit -m "Translate car detail page (version, specs, equipment, status pill)"
```

---

### Task 7: Wire `traducciones_cache.json` into the daily update script

**Files:**
- Modify: `~/Desktop/ejecutable redes/1️⃣ Actualizar Todo — Cambios + Fotos.command` (outside the git repo)

Without this, translations keep regenerating locally every day but the cache never reaches GitHub — so every server this repo is cloned onto (or a fresh clone) re-translates everything from scratch instead of reusing the cache, defeating the point of caching.

- [ ] **Step 1: Read the current `git add` line and append `traducciones_cache.json`**

```bash
grep "git add" ~/Desktop/"ejecutable redes"/"1️⃣ Actualizar Todo — Cambios + Fotos.command"
```
Read the output, then edit that exact line in the `.command` file so it ends with `... traducciones_cache.json` (in addition to whatever files are already listed there — if the `coches-destacados` plan's Task 7 already ran, `coches_lista.json` will already be on that line too; keep it and just add `traducciones_cache.json`).

- [ ] **Step 2: Verify by inspection**

```bash
grep "git add" ~/Desktop/"ejecutable redes"/"1️⃣ Actualizar Todo — Cambios + Fotos.command"
```
Expected: the line includes `traducciones_cache.json`.

(No commit needed — this file lives outside the git repo.)

---

### Task 8: Full end-to-end verification

**Files:** none (verification only)

- [ ] **Step 1: Full regeneration from a clean cache-hit state**

```bash
cd ~/Desktop/catalogo_automoviles_rueda && python3 generar_web.py
```
Expected: no Python errors, and the translation line reports mostly/all cache hits (`0 coche(s) traducido(s) de nuevo, NN ya en caché`, assuming no car data changed since Task 2/6's runs).

- [ ] **Step 2: Browser walkthrough — catalog**

```bash
open index.html
```
- Toggle 🇬🇧: header stays put, filter/search/sort/counter switch to English, every visible card's version and pills switch to English, "PRICE DROP"/"Available"/"Reserved" badges show correctly.
- Type in the search box — placeholder should already read "Search model..." while in English.
- Toggle back to 🇪🇸 — everything reverts.
- Open dev tools console — no red errors during either toggle.

- [ ] **Step 3: Browser walkthrough — car detail page**

Click into any car from the catalog while in English. Expected: it opens already in English (the choice persisted via `localStorage`), version/specs/equipment all translated, calculator still in Spanish. Toggle 🇪🇸/🇬🇧 a few times on this page directly — content should update instantly without a reload.

- [ ] **Step 4: Check Alejandro's page too**

```bash
open alejandro/index.html
```
Expected: same toggle behavior, same translations — since `assets/idioma.js` and `assets/estilos.css` are shared, no separate work was needed for this profile.

- [ ] **Step 5: Push when satisfied**

```bash
cd ~/Desktop/catalogo_automoviles_rueda
git push origin main
```

---

## Self-Review Notes

- **Spec coverage:** fixed-vocabulary dictionary translation, no IA (Task 1) · free-text translation via Gemini with content-hash caching (Task 2) · both languages baked into generated HTML, page stays self-contained for visitors (Tasks 3, 4, 6 — nothing fetches a translation service at view time) · flag toggle in header, instant, no reload, remembered via `localStorage`, shared across index + ficha (Task 5) · calculator excluded from translation (Task 6, its markup is never touched) · works identically for both profiles since header/CSS/JS are shared (Task 8, Step 4) — all covered.
- **Placeholder scan:** none found — every step has literal code.
- **Type consistency:** `trad`/`traducciones[n]` always has exactly the keys `version_en`, `equipamiento_en`, `color_en` everywhere it's produced (Task 2's `traducir_coche` and its `fallback`) and everywhere it's consumed (Task 3's `build_card_html`, Task 6's `coche_json`) — checked call sites agree on this shape. `window.rdAplicarIdioma` / `rdIdiomaActual` / `rdCambiarIdioma` / `rdAlCambiarIdioma` names match exactly between `assets/idioma.js` (Task 5, defines the first three) and `assets/calculadora.js` (Task 6, reads `rdIdiomaActual` and defines `rdAlCambiarIdioma`) and the destacados script from the other plan (reads `rdAplicarIdioma`/`rdIdiomaActual`, if that plan is implemented too).
