# Multi-asesor + dominio propio — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `generar_web.py` generate the catalog once per advisor profile (Andrés at the site root, Alejandro at `/alejandro/`), sharing the same daily-updated car data, photos, CSS and JS — with each profile's own name/phone/email in header, footer, WhatsApp buttons and financing widgets — and switch the site's canonical domain to `automovilesruedaocasion.com`.

**Architecture:** Introduce a `PERFILES` list of advisor dicts (`nombre`, `telefono`, `email`, `carpeta`). Split `main()` into a shared photo-resolution pass (unchanged output location: `web_fotos/`) and a per-profile HTML-generation pass that writes `index.html` + `coches/*.html` into each profile's own output directory. Switch every asset/photo reference from folder-relative (`web_fotos/...`, `../assets/...`) to domain-root-absolute (`/web_fotos/...`, `/assets/...`) so both profiles reference the exact same image/CSS/JS files without duplication. Add a small `ASESOR` JS object per ficha page so the shared `assets/calculadora.js` shows the right advisor in its WhatsApp CTAs.

**Tech Stack:** Python 3 (stdlib only: `json`, `pathlib`, `urllib.parse`), static HTML/CSS/vanilla JS, GitHub Pages, no test framework in this repo (verification is done by regenerating and grepping/inspecting the output — see Task 9).

**No test framework exists in this repo.** Every task's "test" step is a `python3 generar_web.py` regeneration followed by a `grep`/`python3 -c` check against the generated files — this matches how the codebase is already verified (see `CLAUDE.md`, no `pytest`/`unittest` anywhere in the project).

---

## Task 1: Replace advisor constants with a `PERFILES` list

**Files:**
- Modify: `generar_web.py:1-30` (imports + constants block)

- [ ] **Step 1: Add `urllib.parse` import and replace the advisor/domain constants**

In `generar_web.py`, the current top of the file reads:

```python
import hashlib, json, shutil, sys
from datetime import datetime
from pathlib import Path
import requests

BASE_DIR   = Path(__file__).parent
JSON_PATH  = BASE_DIR / "datos_coches.json"
FOTOS_DIR  = BASE_DIR / "fotos"
WEB_FOTOS  = BASE_DIR / "web_fotos"
HTML_PATH  = BASE_DIR / "index.html"

DASWELTAUTO = "https://www.dasweltauto.es"

# Datos del comercial
COMERCIAL_NOMBRE   = "Andrés Vázquez"
COMERCIAL_TELEFONO = "610 02 90 56"
COMERCIAL_EMAIL    = "andres.vazquez@automovilesrueda.com"

# Redes sociales
INSTAGRAM_URL = "https://www.instagram.com/seat_cupra_velezmalaga_ar/"
FACEBOOK_URL  = "https://www.facebook.com/profile.php?id=61560676831246"
TIKTOK_URL    = "https://www.tiktok.com/@automoviles.rueda"
```

Replace it with:

```python
import hashlib, json, shutil, sys, urllib.parse
from datetime import datetime
from pathlib import Path
import requests

BASE_DIR   = Path(__file__).parent
JSON_PATH  = BASE_DIR / "datos_coches.json"
FOTOS_DIR  = BASE_DIR / "fotos"
WEB_FOTOS  = BASE_DIR / "web_fotos"
HTML_PATH  = BASE_DIR / "index.html"

DASWELTAUTO = "https://www.dasweltauto.es"

# Perfiles de asesor — cada uno genera su propia copia del sitio (mismos
# coches y fotos, compartidos) en su propia carpeta de salida.
# "carpeta": "" => se genera en la raíz del repo (BASE_DIR).
PERFILES = [
    {
        "carpeta": "",
        "nombre": "Andrés Vázquez",
        "telefono": "610 02 90 56",
        "email": "andres.vazquez@automovilesrueda.com",
    },
    {
        "carpeta": "alejandro",
        "nombre": "Alejandro Morales Pájaro",
        "telefono": "685 90 77 41",
        "email": "alejandro.morales@automovilesrueda.com",
    },
]

def datos_perfil(perfil: dict) -> dict:
    """Deriva los valores calculados (nombre corto, teléfono en formatos
    wa.me/tel:, carpeta de salida, dominio de la página) a partir de un
    perfil de PERFILES. Centraliza el cálculo para no repetirlo en cada
    función que necesita estos datos."""
    telefono_digits = perfil["telefono"].replace(" ", "")
    telefono_wa = "34" + telefono_digits
    out_dir = BASE_DIR / perfil["carpeta"] if perfil["carpeta"] else BASE_DIR
    dominio_pagina = f"{DOMINIO_BASE}/{perfil['carpeta']}" if perfil["carpeta"] else DOMINIO_BASE
    return {
        "nombre": perfil["nombre"],
        "nombre_corto": perfil["nombre"].split()[0],
        "telefono": perfil["telefono"],
        "telefono_wa": telefono_wa,
        "telefono_tel_href": "+" + telefono_wa,
        "email": perfil["email"],
        "out_dir": out_dir,
        "dominio_pagina": dominio_pagina,
    }

# Redes sociales (compartidas por todos los perfiles — son del concesionario)
INSTAGRAM_URL = "https://www.instagram.com/seat_cupra_velezmalaga_ar/"
FACEBOOK_URL  = "https://www.facebook.com/profile.php?id=61560676831246"
TIKTOK_URL    = "https://www.tiktok.com/@automoviles.rueda"
```

Note: `DOMINIO_BASE` is referenced here but defined later in the file (Task 3 renames `DOMINIO_WEB` to `DOMINIO_BASE`) — Python resolves it at call time (`datos_perfil` runs inside `main()`, well after module load), so this forward reference is fine as long as Task 3 is completed before running the script.

- [ ] **Step 2: Verify no other code still references the removed constants**

Run:

```bash
cd ~/Desktop/catalogo_automoviles_rueda && grep -n "COMERCIAL_NOMBRE\|COMERCIAL_TELEFONO\|COMERCIAL_EMAIL" generar_web.py
```

Expected: no output (all removed) — if any lines print, note them; they get fixed in Tasks 2, 4 and 6 below.

- [ ] **Step 3: Commit**

```bash
cd ~/Desktop/catalogo_automoviles_rueda
git add generar_web.py
git commit -m "$(cat <<'EOF'
Replace single advisor constants with a PERFILES list

Prepares generar_web.py to generate one site per advisor profile,
sharing the same car data and photos.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Parameterize `footer_whatsapp_html` and fix the hardcoded WhatsApp number bug

**Files:**
- Modify: `generar_web.py:84-107` (function `footer_whatsapp_html`)

- [ ] **Step 1: Replace the function**

Current code:

```python
def footer_whatsapp_html(link_dwa: str = "https://www.dasweltauto.es/esp/concesionario-seat-automoviles-rueda") -> str:
    """Pie de página (contacto + enlace DWA + última actualización) y botón
    flotante de WhatsApp — compartidos entre index.html y las fichas de coche."""
    ahora = datetime.now().strftime('%d/%m/%Y — %H:%M')
    return f'''
<footer class="rd-footer">
  <p>
    <strong>Automóviles Rueda</strong> · {COMERCIAL_NOMBRE} ·
    <a href="tel:{COMERCIAL_TELEFONO.replace(' ', '')}">{COMERCIAL_TELEFONO}</a> ·
    <a href="mailto:{COMERCIAL_EMAIL}">{COMERCIAL_EMAIL}</a>
  </p>
  <p class="rd-footer-dwa">
    <a href="{link_dwa}" target="_blank" rel="noopener">Ver todos los coches en Das WeltAuto ↗</a>
  </p>
  <p class="rd-footer-updated">🔄 Última actualización: {ahora} h</p>
</footer>

<a class="rd-whatsapp-float"
   href="https://wa.me/34610029056?text=Hola%20Andr%C3%A9s%2C%20te%20escribo%20desde%20el%20cat%C3%A1logo%20de%20coches.%20Me%20interesa%20uno%20de%20los%20veh%C3%ADculos."
   target="_blank" rel="noopener" aria-label="Enviar WhatsApp a {COMERCIAL_NOMBRE}">
  <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
  <span class="rd-wa-label">WhatsApp</span>
</a>
'''
```

New code:

```python
def footer_whatsapp_html(perfil: dict, link_dwa: str = "https://www.dasweltauto.es/esp/concesionario-seat-automoviles-rueda") -> str:
    """Pie de página (contacto + enlace DWA + última actualización) y botón
    flotante de WhatsApp — compartidos entre index.html y las fichas de coche.
    `perfil` trae los datos de contacto del asesor de PERFILES."""
    ahora = datetime.now().strftime('%d/%m/%Y — %H:%M')
    nombre = perfil["nombre"]
    telefono = perfil["telefono"]
    email = perfil["email"]
    telefono_wa = "34" + telefono.replace(" ", "")
    mensaje_wa = urllib.parse.quote(
        f"Hola {nombre.split()[0]}, te escribo desde el catálogo de coches. Me interesa uno de los vehículos."
    )
    return f'''
<footer class="rd-footer">
  <p>
    <strong>Automóviles Rueda</strong> · {nombre} ·
    <a href="tel:{telefono.replace(' ', '')}">{telefono}</a> ·
    <a href="mailto:{email}">{email}</a>
  </p>
  <p class="rd-footer-dwa">
    <a href="{link_dwa}" target="_blank" rel="noopener">Ver todos los coches en Das WeltAuto ↗</a>
  </p>
  <p class="rd-footer-updated">🔄 Última actualización: {ahora} h</p>
</footer>

<a class="rd-whatsapp-float"
   href="https://wa.me/{telefono_wa}?text={mensaje_wa}"
   target="_blank" rel="noopener" aria-label="Enviar WhatsApp a {nombre}">
  <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
  <span class="rd-wa-label">WhatsApp</span>
</a>
'''
```

(Only the function signature, the `nombre`/`telefono`/`email`/`telefono_wa`/`mensaje_wa` lines, and the two `<footer>`/`<a class="rd-whatsapp-float">` blocks changed — the SVG path is byte-for-byte identical, copy it as-is.)

- [ ] **Step 2: Verify with a quick Python check**

Run:

```bash
cd ~/Desktop/catalogo_automoviles_rueda && python3 -c "
import generar_web as g
perfil = {'carpeta': 'alejandro', 'nombre': 'Alejandro Morales Pájaro', 'telefono': '685 90 77 41', 'email': 'alejandro.morales@automovilesrueda.com'}
html = g.footer_whatsapp_html(perfil)
assert 'wa.me/34685907741' in html, 'número de WhatsApp incorrecto'
assert 'Alejandro Morales Pájaro' in html
assert 'alejandro.morales@automovilesrueda.com' in html
assert 'Hola%20Alejandro' in html
print('OK footer_whatsapp_html')
"
```

Expected output: `OK footer_whatsapp_html` (this will currently fail with a `NameError: DOMINIO_BASE`-free import error only if Task 3 hasn't run yet and something else in the module references an undefined name at import time — `generar_web.py` has no other top-level code that runs at import besides constant assignments, so this should pass once Task 1 is done, even before Task 3, since `datos_perfil()` is a function and isn't called by this test).

- [ ] **Step 3: Commit**

```bash
cd ~/Desktop/catalogo_automoviles_rueda
git add generar_web.py
git commit -m "$(cat <<'EOF'
Parameterize footer_whatsapp_html by advisor profile

Also fixes a bug where the WhatsApp float button's phone number was
hardcoded to 34610029056 regardless of the advisor constant.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Make photo paths absolute from the domain root, rename `DOMINIO_WEB`

**Files:**
- Modify: `generar_web.py:160-217` (function `copiar_fotos`)
- Modify: `generar_web.py:321` (constant, was `DOMINIO_WEB`)

- [ ] **Step 1: Make `copiar_fotos` emit absolute paths**

In `copiar_fotos`, find:

```python
        if fotos_src:
            # Carpeta local verificada (coincide con DWA, o no hay URL para
            # verificar pero es el mejor dato disponible) — usar la galería completa.
            for i, foto in enumerate(fotos_src[:8], start=1):
                dst = dest / f"foto_{i:02d}.jpg"
                shutil.copy2(foto, dst)
                urls.append(f"web_fotos/{n:02d}/foto_{i:02d}.jpg")
        elif portada_dwa:
            # Sin carpeta local válida, pero DWA sigue publicando la foto de
            # portada del anuncio (identidad segura: por URL, no por "n") —
            # coches reservados incluidos, mientras el anuncio siga activo.
            (dest / "foto_01.jpg").write_bytes(portada_dwa)
            urls = [f"web_fotos/{n:02d}/foto_01.jpg"]
```

Replace the two `urls...` lines so paths are absolute from the domain root (so both advisor profiles, at different folder depths, resolve to the same shared files):

```python
        if fotos_src:
            # Carpeta local verificada (coincide con DWA, o no hay URL para
            # verificar pero es el mejor dato disponible) — usar la galería completa.
            for i, foto in enumerate(fotos_src[:8], start=1):
                dst = dest / f"foto_{i:02d}.jpg"
                shutil.copy2(foto, dst)
                urls.append(f"/web_fotos/{n:02d}/foto_{i:02d}.jpg")
        elif portada_dwa:
            # Sin carpeta local válida, pero DWA sigue publicando la foto de
            # portada del anuncio (identidad segura: por URL, no por "n") —
            # coches reservados incluidos, mientras el anuncio siga activo.
            (dest / "foto_01.jpg").write_bytes(portada_dwa)
            urls = [f"/web_fotos/{n:02d}/foto_01.jpg"]
```

(Only the two `urls.append(...)` / `urls = [...]` lines gain a leading `/` — nothing else in this function changes. The existence-check logic elsewhere in the file that does `(BASE_DIR / f)` on paths coming from `datos_coches.json`'s `fotos` field for MotorFlash cars is untouched, since those raw JSON values stay relative — Task 7 normalizes them only when building the HTML-facing list.)

- [ ] **Step 2: Rename `DOMINIO_WEB` to `DOMINIO_BASE` and drop the repo-name path segment**

Find:

```python
DOMINIO_WEB = "https://andresvazquez11.github.io/automoviles-rueda-catalogo"
```

Replace with:

```python
DOMINIO_BASE = "https://automovilesruedaocasion.com"
```

- [ ] **Step 3: Verify no remaining references to the old name**

Run:

```bash
cd ~/Desktop/catalogo_automoviles_rueda && grep -n "DOMINIO_WEB" generar_web.py
```

Expected: no output. (Task 4 below updates the two call sites that used `DOMINIO_WEB` to use the new per-profile `dominio_pagina` value instead.)

- [ ] **Step 4: Commit**

```bash
cd ~/Desktop/catalogo_automoviles_rueda
git add generar_web.py
git commit -m "$(cat <<'EOF'
Make photo paths absolute and switch domain to automovilesruedaocasion.com

Absolute /web_fotos/... paths let both advisor profiles (root and
/alejandro/) share the same photo files without duplication, since
they now resolve correctly regardless of the page's folder depth.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Parameterize `build_coche_html` by profile, fix shared asset paths, add the `ASESOR` JS object

**Files:**
- Modify: `generar_web.py:997-1131` (function `build_coche_html`)
- Modify: `generar_web.py:925-927` (inside `CALCULADORA_HTML_INTERIOR` constant)
- Modify: `generar_web.py:990-992` (inside `BBVA_HTML_INTERIOR` constant)

- [ ] **Step 1: Replace the hardcoded phone/name inside `CALCULADORA_HTML_INTERIOR` with placeholder tokens**

Find (inside the `CALCULADORA_HTML_INTERIOR = '''...'''` constant):

```python
        <a class="btn-phone" href="tel:+34610029056">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.07 10.8a19.79 19.79 0 01-3.07-8.68A2 2 0 012 0h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L6.91 7.91a16 16 0 006.72 6.72l1.28-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"/></svg>
          610 02 90 56 · Andrés
        </a>
```

Replace with:

```python
        <a class="btn-phone" href="tel:__TEL_HREF__">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.07 10.8a19.79 19.79 0 01-3.07-8.68A2 2 0 012 0h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L6.91 7.91a16 16 0 006.72 6.72l1.28-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"/></svg>
          __TEL_DISPLAY__ · __NOMBRE_CORTO__
        </a>
```

- [ ] **Step 2: Same replacement inside `BBVA_HTML_INTERIOR`**

Find (inside the `BBVA_HTML_INTERIOR = '''...'''` constant — note this block is IDENTICAL in structure to Step 1's but is a separate occurrence further down the file, inside `BBVA_HTML_INTERIOR` not `CALCULADORA_HTML_INTERIOR`):

```python
      <a class="btn-phone" href="tel:+34610029056">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.07 10.8a19.79 19.79 0 01-3.07-8.68A2 2 0 012 0h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L6.91 7.91a16 16 0 006.72 6.72l1.28-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"/></svg>
        610 02 90 56 · Andrés
      </a>
```

Replace with:

```python
      <a class="btn-phone" href="tel:__TEL_HREF__">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.07 10.8a19.79 19.79 0 01-3.07-8.68A2 2 0 012 0h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L6.91 7.91a16 16 0 006.72 6.72l1.28-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"/></svg>
        __TEL_DISPLAY__ · __NOMBRE_CORTO__
      </a>
```

(These two blocks have slightly different indentation — 8 spaces in Step 1, 6 spaces in Step 2 — match the original file's indentation exactly; don't normalize it.)

- [ ] **Step 3: Replace `build_coche_html`**

Current code:

```python
def build_coche_html(car: dict, fotos_urls: list[str]) -> str:
    n = car["n"]
    slug = slug_coche(car["modelo"])
    vendido = car["estado"] == "Retirado"
    fotos = [f"../{f}" for f in fotos_urls]   # la ficha vive en coches/, un nivel más abajo que el root
    # OJO: no adivinar f"web_fotos/{n:02d}/foto_01.jpg" cuando no hay fotos_urls —
    # "n" no es estable entre corridas y esa carpeta puede pertenecer a OTRO coche.
    foto_principal_root = fotos_urls[0] if fotos_urls else ""
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

    og_image_tag = (f'<meta property="og:image" content="{DOMINIO_WEB}/{foto_principal_root}">'
                     if foto_principal_root else '')

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
{og_image_tag}
<meta property="og:url" content="{DOMINIO_WEB}/coches/{n:02d}-{slug}.html">

<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@500;600;700&family=Work+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../assets/estilos.css">
<style>
{CALCULADORA_CSS}
</style>
</head>
<body class="rd-has-sticky">

<header class="rd-header">
  <div class="rd-header-brand">
    <strong>Automóviles Rueda</strong>
    <span>{COMERCIAL_NOMBRE} · {COMERCIAL_TELEFONO}</span>
  </div>
  {header_social_html()}
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

  <div class="financiera-tabs" id="financiera-tabs">
    <button class="financiera-tab active" id="fin-vwfs" onclick="setFinanciera('VWFS', this)">
      VWFS <span class="fin-sub">Volkswagen Finance</span>
    </button>
    <button class="financiera-tab" id="fin-bbva" onclick="setFinanciera('BBVA', this)">
      BBVA <span class="fin-sub">Préstamo Vehículo</span>
    </button>
  </div>

  <div class="modal-financiacion" id="m-financiacion">
{CALCULADORA_HTML_INTERIOR}
  </div>

  <div class="bbva-panel" id="bbva-financiacion" style="display:none">
{BBVA_HTML_INTERIOR}
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
{footer_whatsapp_html()}
{goatcounter_script_html()}
</body>
</html>
'''
```

Replace with:

```python
def build_coche_html(car: dict, fotos_urls: list[str], perfil: dict) -> str:
    n = car["n"]
    slug = slug_coche(car["modelo"])
    vendido = car["estado"] == "Retirado"
    fotos = fotos_urls   # ya son rutas absolutas desde la raíz del dominio (ver Task 3/7)
    foto_principal_root = fotos_urls[0] if fotos_urls else ""
    url_externa = car.get("url_motorflash") or (f"{DASWELTAUTO}{car['url']}" if car.get("url") else "")

    datos = datos_perfil(perfil)
    nombre = datos["nombre"]
    telefono = datos["telefono"]

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

    asesor_json = json.dumps({
        "nombreCorto": datos["nombre_corto"],
        "telefonoDisplay": telefono,
        "telefonoWa": datos["telefono_wa"],
    }, ensure_ascii=False)

    vendido_banner = '' if not vendido else '''
  <div class="rd-vendido-banner" id="m-vendido-banner">
    Este vehículo ya no está disponible.
    <a href="../index.html">Ver coches disponibles →</a>
  </div>'''

    og_image_tag = (f'<meta property="og:image" content="{datos["dominio_pagina"]}{foto_principal_root}">'
                     if foto_principal_root else '')

    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{titulo}</title>
<meta name="description" content="{descripcion}">

<meta property="og:type" content="product">
<meta property="og:title" content="{titulo}">
<meta property="og:description" content="{descripcion}">
{og_image_tag}
<meta property="og:url" content="{datos["dominio_pagina"]}/coches/{n:02d}-{slug}.html">

<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@500;600;700&family=Work+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/estilos.css">
<style>
{CALCULADORA_CSS}
</style>
</head>
<body class="rd-has-sticky">

<header class="rd-header">
  <div class="rd-header-brand">
    <strong>Automóviles Rueda</strong>
    <span>{nombre} · {telefono}</span>
  </div>
  {header_social_html()}
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

  <div class="financiera-tabs" id="financiera-tabs">
    <button class="financiera-tab active" id="fin-vwfs" onclick="setFinanciera('VWFS', this)">
      VWFS <span class="fin-sub">Volkswagen Finance</span>
    </button>
    <button class="financiera-tab" id="fin-bbva" onclick="setFinanciera('BBVA', this)">
      BBVA <span class="fin-sub">Préstamo Vehículo</span>
    </button>
  </div>

  <div class="modal-financiacion" id="m-financiacion">
{CALCULADORA_HTML_INTERIOR}
  </div>

  <div class="bbva-panel" id="bbva-financiacion" style="display:none">
{BBVA_HTML_INTERIOR}
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

<script>
const ASESOR = {asesor_json};
</script>
<script src="/assets/calculadora.js"></script>
<script>
const COCHE = {coche_json};
cargarFicha(COCHE);
</script>
{footer_whatsapp_html(perfil)}
{goatcounter_script_html()}
</body>
</html>
'''
    return (html
            .replace("__TEL_HREF__", datos["telefono_tel_href"])
            .replace("__TEL_DISPLAY__", telefono)
            .replace("__NOMBRE_CORTO__", datos["nombre_corto"]))
```

What changed and why:
- Signature gained `perfil: dict`.
- `fotos = fotos_urls` (no more `"../" + f` prefix — Task 3 already made these absolute).
- `og_image_tag` / `og:url` use `datos["dominio_pagina"]` instead of the removed `DOMINIO_WEB` (note: no `/` between `{datos["dominio_pagina"]}` and `{foto_principal_root}` in the image tag, since `foto_principal_root` already starts with `/`).
- `<link rel="stylesheet" href="/assets/estilos.css">` — was `"../assets/estilos.css"` (relative paths break for the `/alejandro/coches/*.html` fichas, which don't have their own `assets/` folder).
- Header now uses `{nombre} · {telefono}` from `datos_perfil(perfil)`.
- Added a `const ASESOR = {asesor_json};` script tag BEFORE `<script src="/assets/calculadora.js">` (was `"../assets/calculadora.js"`, same relative-path problem as the CSS) so the shared JS (Task 5) knows which advisor to put in its own WhatsApp links.
- `{footer_whatsapp_html()}` → `{footer_whatsapp_html(perfil)}`.
- The whole `html` string now runs through `.replace()` to fill in the `__TEL_HREF__` / `__TEL_DISPLAY__` / `__NOMBRE_CORTO__` tokens planted in `CALCULADORA_HTML_INTERIOR`/`BBVA_HTML_INTERIOR` (Steps 1-2 above) — this avoids rewriting those two large constants into f-strings (which contain literal `{`/`}` JS/CSS characters that would need escaping).
- The "`Volver al catálogo`" / "`../index.html`" links are UNCHANGED (still relative) — a ficha always lives exactly one folder below its own profile's `index.html`, for both profiles, so the relative link already resolves correctly without any change.

- [ ] **Step 4: Verify with a quick Python check**

Run:

```bash
cd ~/Desktop/catalogo_automoviles_rueda && python3 -c "
import generar_web as g
perfil_alejandro = {'carpeta': 'alejandro', 'nombre': 'Alejandro Morales Pájaro', 'telefono': '685 90 77 41', 'email': 'alejandro.morales@automovilesrueda.com'}
car = {'n': 1, 'modelo': 'SEAT Ibiza', 'version': 'Style', 'precio': '15.000', 'estado': 'Disponible', 'combustible': 'Gasolina', 'km': '10.000', 'fecha': '01/2024', 'cambio': 'Manual', 'ubicacion': 'Málaga', 'url': '/esp/12345', 'equipamiento': []}
html = g.build_coche_html(car, ['/web_fotos/01/foto_01.jpg'], perfil_alejandro)
assert '__TEL_HREF__' not in html and '__TEL_DISPLAY__' not in html and '__NOMBRE_CORTO__' not in html, 'quedó un token sin reemplazar'
assert 'tel:+34685907741' in html
assert '685 90 77 41 · Alejandro' in html
assert '/assets/estilos.css' in html and '../assets/estilos.css' not in html
assert '/assets/calculadora.js' in html and '../assets/calculadora.js' not in html
assert 'const ASESOR = {\"nombreCorto\": \"Alejandro\"' in html
assert 'automovilesruedaocasion.com/alejandro/coches/01-seat-ibiza.html' in html
print('OK build_coche_html')
"
```

Expected output: `OK build_coche_html`

- [ ] **Step 5: Commit**

```bash
cd ~/Desktop/catalogo_automoviles_rueda
git add generar_web.py
git commit -m "$(cat <<'EOF'
Parameterize build_coche_html by advisor profile

Fixes /assets/ and photo links to be domain-root-absolute so ficha
pages work at any folder depth, and injects a per-page ASESOR JS
object so the shared financing calculator shows the right advisor.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Make `assets/calculadora.js` read the advisor from `ASESOR` instead of hardcoding Andrés

**Files:**
- Modify: `assets/calculadora.js:459` (inside `cv2UpdateResults`-family function)
- Modify: `assets/calculadora.js:478`
- Modify: `assets/calculadora.js:514-515` (inside `cv2BuildWaLink`)
- Modify: `assets/calculadora.js:923-924` (inside the BBVA render function)
- Modify: `assets/calculadora.js:930`

- [ ] **Step 1: Fix the credit-minimum warning (line 459)**

Find:

```javascript
      warnEl.textContent = '⚠ Importe financiado (' + cv2Fmt(importeFinanciado) + ' €) inferior al mínimo de la campaña ' + rules.campanaLabel + ' (' + cv2Fmt(rules.creditoMinimo) + ' €). Consulta condiciones con Andrés.';
```

Replace with:

```javascript
      warnEl.textContent = '⚠ Importe financiado (' + cv2Fmt(importeFinanciado) + ' €) inferior al mínimo de la campaña ' + rules.campanaLabel + ' (' + cv2Fmt(rules.creditoMinimo) + ' €). Consulta condiciones con ' + ASESOR.nombreCorto + '.';
```

- [ ] **Step 2: Fix the VWFS legal text (line 478)**

Find:

```javascript
  legalTxt += `Condiciones exactas con Andrés · 610 02 90 56.`;
```

Replace with:

```javascript
  legalTxt += `Condiciones exactas con ${ASESOR.nombreCorto} · ${ASESOR.telefonoDisplay}.`;
```

- [ ] **Step 3: Fix the VWFS WhatsApp message + link (lines 514-515)**

Find:

```javascript
  msg += `_Cálculo orientativo. Condiciones exactas con Andrés · 610 02 90 56_`;
  const waEl = document.getElementById('cv2-btn-wa');
  if (waEl) waEl.href = `https://wa.me/34610029056?text=${encodeURIComponent(msg)}`;
```

Replace with:

```javascript
  msg += `_Cálculo orientativo. Condiciones exactas con ${ASESOR.nombreCorto} · ${ASESOR.telefonoDisplay}_`;
  const waEl = document.getElementById('cv2-btn-wa');
  if (waEl) waEl.href = `https://wa.me/${ASESOR.telefonoWa}?text=${encodeURIComponent(msg)}`;
```

- [ ] **Step 4: Fix the BBVA WhatsApp message + link (lines 923-924)**

Find:

```javascript
    const msg = `Hola Andrés, te escribo desde la calculadora de financiación. Me interesa ${modelo} de ${bbvaFmt(precio)} € financiado con BBVA a ${BBVA.meses} meses (TIN 5,50%). Cuota estimada: ${bbvaFmt2(cuota)} €/mes.`;
    waBtn.href = 'https://wa.me/34610029056?text=' + encodeURIComponent(msg);
```

Replace with:

```javascript
    const msg = `Hola ${ASESOR.nombreCorto}, te escribo desde la calculadora de financiación. Me interesa ${modelo} de ${bbvaFmt(precio)} € financiado con BBVA a ${BBVA.meses} meses (TIN 5,50%). Cuota estimada: ${bbvaFmt2(cuota)} €/mes.`;
    waBtn.href = 'https://wa.me/' + ASESOR.telefonoWa + '?text=' + encodeURIComponent(msg);
```

- [ ] **Step 5: Fix the BBVA legal text (line 930)**

Find:

```javascript
      `Ejemplo de cuota a ${BBVA.meses} meses: ${bbvaFmt2(cuota)} €. TIN 5,50% fijo. Entrada inicial: ${bbvaFmt(BBVA.entrada)} €. Importe financiado: ${bbvaFmt(importe)} €. Comisión de apertura financiada en la cuota. Precio total a plazos: ${bbvaFmt2(total)} €. Condiciones sujetas a modificación por parte de BBVA. Condiciones exactas con Andrés · 610 02 90 56.`;
```

Replace with:

```javascript
      `Ejemplo de cuota a ${BBVA.meses} meses: ${bbvaFmt2(cuota)} €. TIN 5,50% fijo. Entrada inicial: ${bbvaFmt(BBVA.entrada)} €. Importe financiado: ${bbvaFmt(importe)} €. Comisión de apertura financiada en la cuota. Precio total a plazos: ${bbvaFmt2(total)} €. Condiciones sujetas a modificación por parte de BBVA. Condiciones exactas con ${ASESOR.nombreCorto} · ${ASESOR.telefonoDisplay}.`;
```

- [ ] **Step 6: Verify no hardcoded advisor data remains in the shared JS**

Run:

```bash
cd ~/Desktop/catalogo_automoviles_rueda && grep -n "Andrés\|34610029056\|610 02 90 56" assets/calculadora.js
```

Expected: no output.

- [ ] **Step 7: Commit**

```bash
cd ~/Desktop/catalogo_automoviles_rueda
git add assets/calculadora.js
git commit -m "$(cat <<'EOF'
Read advisor name/phone from ASESOR global in calculadora.js

The financing calculator's WhatsApp CTAs had Andrés's name and phone
hardcoded in 6 places. They now read window ASESOR, set per-page by
build_coche_html, so Alejandro's ficha pages show his own contact.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Parameterize `build_index_html` by profile and fix its asset path

**Files:**
- Modify: `generar_web.py:1203-1334` (function `build_index_html`)

- [ ] **Step 1: Update the function signature, header, asset link and footer call**

Find:

```python
def build_index_html(cars: list[dict], rutas: dict[int, list[str]]) -> str:
```

Replace with:

```python
def build_index_html(cars: list[dict], rutas: dict[int, list[str]], perfil: dict) -> str:
```

Find:

```python
<link rel="stylesheet" href="assets/estilos.css">
</head>
<body>
<header class="rd-header">
  <div class="rd-header-brand">
    <strong>Automóviles Rueda</strong>
    <span>{COMERCIAL_NOMBRE} · {COMERCIAL_TELEFONO}</span>
  </div>
  {header_social_html()}
</header>
```

Replace with:

```python
<link rel="stylesheet" href="/assets/estilos.css">
</head>
<body>
<header class="rd-header">
  <div class="rd-header-brand">
    <strong>Automóviles Rueda</strong>
    <span>{perfil["nombre"]} · {perfil["telefono"]}</span>
  </div>
  {header_social_html()}
</header>
```

Find:

```python
{footer_whatsapp_html()}
{goatcounter_script_html()}
</body>
</html>
'''
```

(this is the occurrence inside `build_index_html` — `build_coche_html` no longer has a bare `{footer_whatsapp_html()}` after Task 4, so this match is now unique in the file)

Replace with:

```python
{footer_whatsapp_html(perfil)}
{goatcounter_script_html()}
</body>
</html>
'''
```

- [ ] **Step 2: Verify with a quick Python check**

Run:

```bash
cd ~/Desktop/catalogo_automoviles_rueda && python3 -c "
import generar_web as g
perfil_alejandro = {'carpeta': 'alejandro', 'nombre': 'Alejandro Morales Pájaro', 'telefono': '685 90 77 41', 'email': 'alejandro.morales@automovilesrueda.com'}
html = g.build_index_html([], {}, perfil_alejandro)
assert 'Alejandro Morales Pájaro · 685 90 77 41' in html
assert '/assets/estilos.css' in html and 'href=\"assets/estilos.css\"' not in html
assert 'wa.me/34685907741' in html
print('OK build_index_html')
"
```

Expected output: `OK build_index_html`

- [ ] **Step 3: Commit**

```bash
cd ~/Desktop/catalogo_automoviles_rueda
git add generar_web.py
git commit -m "$(cat <<'EOF'
Parameterize build_index_html by advisor profile

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Refactor `main()` to generate once per profile

**Files:**
- Modify: `generar_web.py:1339-1424` (function `main`)

- [ ] **Step 1: Replace `main()`**

Current code (the whole function):

```python
def main():
    if not JSON_PATH.exists():
        print(f"❌  No se encontró {JSON_PATH}")
        sys.exit(1)

    coches = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    todos_los_coches = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    # Los coches "Retirado" ya no están publicados en Das WeltAuto → no se publican
    coches = [c for c in coches if c.get("estado") != "Retirado"]
    print(f"✅  {len(coches)} coches cargados de datos_coches.json")

    print("📸  Copiando fotos a web_fotos/ …")
    rutas = copiar_fotos(coches)
    total_fotos = sum(len(v) for v in rutas.values())
    print(f"    {total_fotos} fotos copiadas")

    coches_dir = BASE_DIR / "coches"
    coches_dir.mkdir(exist_ok=True)

    # Sin foto verificada = no se publica (ni en el índice ni con ficha propia).
    # Los "Retirado" se tratan aparte más abajo (ya estaban excluidos del índice).
    sin_foto = set()
    for c in coches:
        if c.get("fuente") == "motorflash":
            tiene_foto = [f for f in c.get("fotos", []) if (BASE_DIR / f).exists()]
        else:
            tiene_foto = rutas.get(c["n"])
        if not tiene_foto:
            sin_foto.add(c["n"])
    if sin_foto:
        coches = [c for c in coches if c["n"] not in sin_foto]
        print(f"  ⛔ {len(sin_foto)} coche(s) sin foto verificada, no publicado(s) en la web")

    slugs_validos = set()
    for car in todos_los_coches:
        n = car["n"]
        if n in sin_foto:
            continue  # sin foto verificada → sin ficha individual tampoco
        slug = slug_coche(car["modelo"])
        slugs_validos.add(f"{n:02d}-{slug}.html")

        if car.get("estado") == "Retirado":
            # Ya no se scrapea ni se copian fotos nuevas para estos. Buscar su
            # carpeta VERIFICADA en fotos/ (por número+modelo+precio, igual que
            # copiar_fotos) en vez de asumir que web_fotos/{n:02d}/ es suya — "n"
            # no es estable y esa carpeta puede ser de otro coche que la ocupó
            # en una corrida anterior.
            carpeta_vieja = find_car_folder(n, car["modelo"], car.get("precio", ""))
            fotos_src = sorted(carpeta_vieja.glob("foto_*.jpg")) if carpeta_vieja else []
            dest_retirado = WEB_FOTOS / f"{n:02d}"
            dest_retirado.mkdir(exist_ok=True)
            if fotos_src:
                fotos_urls = []
                for i, foto in enumerate(fotos_src[:8], start=1):
                    dst = dest_retirado / f"foto_{i:02d}.jpg"
                    shutil.copy2(foto, dst)
                    fotos_urls.append(f"web_fotos/{n:02d}/{dst.name}")
            else:
                for _viejo in dest_retirado.glob("foto_*.jpg"):
                    _viejo.unlink()
                fotos_urls = []
        elif car.get("fuente") == "motorflash":
            fotos_urls = [f for f in car.get("fotos", []) if (BASE_DIR / f).exists()]
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
    HTML_PATH.write_text(html_index, encoding="utf-8")
    print(f"  index.html regenerado con el catálogo nuevo")
    print()
    print("  Listo. Sube index.html, coches/ y web_fotos/ a GitHub Pages para compartirlo.")
```

Replace with:

```python
def main():
    if not JSON_PATH.exists():
        print(f"❌  No se encontró {JSON_PATH}")
        sys.exit(1)

    coches = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    todos_los_coches = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    # Los coches "Retirado" ya no están publicados en Das WeltAuto → no se publican
    coches = [c for c in coches if c.get("estado") != "Retirado"]
    print(f"✅  {len(coches)} coches cargados de datos_coches.json")

    print("📸  Copiando fotos a web_fotos/ …")
    rutas = copiar_fotos(coches)
    total_fotos = sum(len(v) for v in rutas.values())
    print(f"    {total_fotos} fotos copiadas")

    # Sin foto verificada = no se publica (ni en el índice ni con ficha propia).
    # Los "Retirado" se tratan aparte más abajo (ya estaban excluidos del índice).
    sin_foto = set()
    for c in coches:
        if c.get("fuente") == "motorflash":
            tiene_foto = [f for f in c.get("fotos", []) if (BASE_DIR / f).exists()]
        else:
            tiene_foto = rutas.get(c["n"])
        if not tiene_foto:
            sin_foto.add(c["n"])
    if sin_foto:
        coches = [c for c in coches if c["n"] not in sin_foto]
        print(f"  ⛔ {len(sin_foto)} coche(s) sin foto verificada, no publicado(s) en la web")

    # ── Paso 1 (una sola vez, compartido entre perfiles): resolver las fotos
    # de cada coche, incluyendo el respaldo de fotos para "Retirado". ────────
    slugs_validos: set[str] = set()
    fotos_por_coche: dict[int, list[str]] = {}
    for car in todos_los_coches:
        n = car["n"]
        if n in sin_foto:
            continue  # sin foto verificada → sin ficha individual tampoco
        slug = slug_coche(car["modelo"])
        slugs_validos.add(f"{n:02d}-{slug}.html")

        if car.get("estado") == "Retirado":
            # Ya no se scrapea ni se copian fotos nuevas para estos. Buscar su
            # carpeta VERIFICADA en fotos/ (por número+modelo+precio, igual que
            # copiar_fotos) en vez de asumir que web_fotos/{n:02d}/ es suya — "n"
            # no es estable y esa carpeta puede ser de otro coche que la ocupó
            # en una corrida anterior.
            carpeta_vieja = find_car_folder(n, car["modelo"], car.get("precio", ""))
            fotos_src = sorted(carpeta_vieja.glob("foto_*.jpg")) if carpeta_vieja else []
            dest_retirado = WEB_FOTOS / f"{n:02d}"
            dest_retirado.mkdir(exist_ok=True)
            if fotos_src:
                fotos_urls = []
                for i, foto in enumerate(fotos_src[:8], start=1):
                    dst = dest_retirado / f"foto_{i:02d}.jpg"
                    shutil.copy2(foto, dst)
                    fotos_urls.append(f"/web_fotos/{n:02d}/{dst.name}")
            else:
                for _viejo in dest_retirado.glob("foto_*.jpg"):
                    _viejo.unlink()
                fotos_urls = []
        elif car.get("fuente") == "motorflash":
            fotos_urls = [f"/{f.lstrip('/')}" for f in car.get("fotos", []) if (BASE_DIR / f).exists()]
        else:
            fotos_urls = rutas.get(n, [])
        fotos_por_coche[n] = fotos_urls

    # ── Paso 2: generar el sitio completo (index + fichas) una vez por cada
    # perfil de asesor, en su propia carpeta de salida — compartiendo las
    # mismas fotos/CSS/JS (rutas absolutas desde la raíz del dominio). ──────
    for perfil in PERFILES:
        datos = datos_perfil(perfil)
        out_dir = datos["out_dir"]
        coches_dir = out_dir / "coches"
        coches_dir.mkdir(parents=True, exist_ok=True)

        for car in todos_los_coches:
            n = car["n"]
            if n in sin_foto:
                continue
            slug = slug_coche(car["modelo"])
            html_coche = build_coche_html(car, fotos_por_coche[n], perfil)
            (coches_dir / f"{n:02d}-{slug}.html").write_text(html_coche, encoding="utf-8")

        archivadas = 0
        for f in coches_dir.glob("*.html"):
            if f.name not in slugs_validos:
                f.unlink()
                archivadas += 1
        if archivadas:
            print(f"  {archivadas} ficha(s) huérfana(s) eliminada(s) de {coches_dir} (coche ya no existe)")

        html_index = build_index_html(coches, rutas, perfil)
        (out_dir / "index.html").write_text(html_index, encoding="utf-8")
        print(f"  index.html regenerado para {perfil['nombre']} en {out_dir}")

    print(f"  {len(todos_los_coches)} fichas individuales generadas por perfil")
    print()
    print("  Listo. Sube index.html, coches/, alejandro/ y web_fotos/ a GitHub Pages para compartirlo.")
```

What changed and why:
- `coches_dir = BASE_DIR / "coches"; coches_dir.mkdir(exist_ok=True)` (module-level, before the loop) is REMOVED — each profile now creates its own `coches_dir` inside the new per-profile loop.
- The single `for car in todos_los_coches:` loop that used to both resolve photos AND write the ficha HTML is split into **Paso 1** (resolve `fotos_por_coche[n]` once — unchanged logic, only the `f"web_fotos/..."` strings gained a leading `/`, and the MotorFlash branch now normalizes its JSON-sourced paths with `f"/{f.lstrip('/')}"` so they're absolute too) and **Paso 2** (write HTML, now inside `for perfil in PERFILES:`).
- `build_coche_html(car, fotos_urls)` → `build_coche_html(car, fotos_por_coche[n], perfil)`.
- `build_index_html(coches, rutas)` → `build_index_html(coches, rutas, perfil)`, written to `out_dir / "index.html"` instead of the module-level `HTML_PATH`.
- Orphan-ficha cleanup (`archivadas`) now runs per-profile, against that profile's own `coches_dir`.

- [ ] **Step 2: Run the full generator and check both profiles came out**

Run:

```bash
cd ~/Desktop/catalogo_automoviles_rueda && python3 generar_web.py
```

Expected: no traceback; output ends with a line like `Listo. Sube index.html, coches/, alejandro/ y web_fotos/ a GitHub Pages para compartirlo.`

Then run:

```bash
cd ~/Desktop/catalogo_automoviles_rueda && \
  test -f index.html && echo "OK: index.html (raíz)" && \
  test -d coches && echo "OK: coches/" && \
  test -f alejandro/index.html && echo "OK: alejandro/index.html" && \
  test -d alejandro/coches && echo "OK: alejandro/coches/" && \
  grep -c "Alejandro Morales Pájaro" alejandro/index.html && \
  grep -c "Andrés Vázquez" index.html
```

Expected: all four `OK:` lines print, followed by two counts ≥ 1.

- [ ] **Step 3: Commit**

```bash
cd ~/Desktop/catalogo_automoviles_rueda
git add generar_web.py
git commit -m "$(cat <<'EOF'
Generate the catalog once per advisor profile in main()

main() now writes index.html + coches/*.html into each profile's own
output directory (root for Andrés, alejandro/ for Alejandro), sharing
the same resolved photo list computed once up front.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Add the `CNAME` file for the custom domain

**Files:**
- Create: `CNAME` (repo root)

- [ ] **Step 1: Create the file**

```bash
cd ~/Desktop/catalogo_automoviles_rueda && echo "automovilesruedaocasion.com" > CNAME
```

- [ ] **Step 2: Verify**

```bash
cat ~/Desktop/catalogo_automoviles_rueda/CNAME
```

Expected output: `automovilesruedaocasion.com`

- [ ] **Step 3: Commit**

```bash
cd ~/Desktop/catalogo_automoviles_rueda
git add CNAME
git commit -m "$(cat <<'EOF'
Add CNAME for custom domain automovilesruedaocasion.com

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

Note: this file alone does not activate the custom domain — GitHub also needs the DNS records (user's IONOS side, done separately) and the `gh api` call in Task 9 Step 4 to set `cname` on the repo's Pages configuration.

---

## Task 9: Local verification, then (separately, with confirmation) publish

**Files:** none (verification only)

- [ ] **Step 1: Serve the generated site locally**

```bash
cd ~/Desktop/catalogo_automoviles_rueda && python3 -m http.server 8000
```

- [ ] **Step 2: Manual checklist (open in a browser, e.g. via the built-in Browser pane)**

Check `http://localhost:8000/index.html` (Andrés):
- [ ] Header shows "Andrés Vázquez · 610 02 90 56"
- [ ] Footer shows Andrés's email and phone
- [ ] Floating WhatsApp button's link (inspect the `href`) contains `wa.me/34610029056`
- [ ] Click into any car card → its ficha page loads with photos visible
- [ ] On that ficha, "‹ Volver al catálogo" goes back to `http://localhost:8000/index.html` (not `/alejandro/`)
- [ ] Open the financing calculator (VWFS and BBVA tabs) on that ficha → the phone/name shown is Andrés's, and clicking the WhatsApp buttons produces a `wa.me/34610029056` link

Check `http://localhost:8000/alejandro/index.html` (Alejandro):
- [ ] Header shows "Alejandro Morales Pájaro · 685 90 77 41"
- [ ] Footer shows `alejandro.morales@automovilesrueda.com`
- [ ] Floating WhatsApp button's `href` contains `wa.me/34685907741`
- [ ] Click into any car card → photos load correctly (same shared `/web_fotos/...` files as the root site)
- [ ] "‹ Volver al catálogo" goes back to `http://localhost:8000/alejandro/index.html` (not the root)
- [ ] Financing calculator on that ficha shows Alejandro's name/phone, and its WhatsApp buttons produce `wa.me/34685907741` links

- [ ] **Step 3: Stop the local server**

```bash
# Ctrl+C in the terminal running http.server, or:
pkill -f "http.server 8000"
```

- [ ] **Step 4: Configure the custom domain on GitHub Pages (via API — does not require Safari/browser access)**

```bash
gh api -X PUT repos/andresvazquez11/automoviles-rueda-catalogo/pages \
  -f cname="automovilesruedaocasion.com"
```

Expected: HTTP 204 (no output) or a JSON body echoing the updated Pages config — no error. If this returns a permissions error, the `gh` token needs the `repo` scope refreshed (`gh auth refresh -s repo`) before retrying.

- [ ] **Step 5: STOP — do not push yet**

Everything above this line is safe to do without asking again (local files, local server, a `gh api` call that only configures Pages metadata). Pushing the commits from Tasks 1-8 to `origin/main` makes them live on the public GitHub Pages site immediately. **Get the user's explicit go-ahead before running `git push`.** Once they confirm:

```bash
cd ~/Desktop/catalogo_automoviles_rueda && git push origin main
```

- [ ] **Step 6: After DNS propagates and the push is live, enforce HTTPS**

```bash
gh api -X PUT repos/andresvazquez11/automoviles-rueda-catalogo/pages \
  -f https_enforced=true
```

Expected: no error. If it errors with something like "domain not verified yet", wait for DNS to propagate (check with `dig automovilesruedaocasion.com +short` — should list the 4 GitHub Pages IPs) and retry.

- [ ] **Step 7: Final live check**

Open `https://automovilesruedaocasion.com/` and `https://automovilesruedaocasion.com/alejandro/` in a browser and repeat the Step 2 checklist against the live URLs.

---

## Self-Review Notes

- **Spec coverage:** All 5 goals from the design spec are covered — custom domain (Tasks 8-9), root = Andrés (Task 7), `/alejandro/` = Alejandro (Task 7), unchanged daily workflow (Task 7 keeps `python3 generar_web.py` as the single entry point), no photo duplication (Task 3 + Task 7's shared `fotos_por_coche`). The financing-widget hardcoded-contact issue was discovered during planning (not in the original spec) and is covered by Tasks 4-5 — it was a necessary correction for the feature to actually work, not scope creep, since without it Alejandro's ficha pages would show Andrés's phone number in the calculator.
- **Placeholder scan:** none found — every step has literal before/after code and literal shell commands with expected output.
- **Type consistency:** `perfil` is always the same shape (`{"carpeta", "nombre", "telefono", "email"}` from `PERFILES`) across `footer_whatsapp_html`, `build_coche_html`, `build_index_html`, and `datos_perfil`. `datos_perfil(perfil)` is the single place that derives `nombre_corto`/`telefono_wa`/`telefono_tel_href`/`out_dir`/`dominio_pagina` — no other function recomputes these independently, avoiding drift.
