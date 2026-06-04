"""
integrar_motorflash.py
Ejecutado automáticamente al final de actualizar_catalogo.py.

Flujo:
  1. Scrapea MotorFlash (todas las páginas)
  2. Compara contra datos_coches.json (DWA)
  3. Los coches exclusivos de MF se añaden a datos_coches.json
     con fuente="motorflash" y sus fotos en web_fotos/
  4. Los coches MF que ya no están en MotorFlash se eliminan
"""

import asyncio
import json
import re
import shutil
import sys
import time
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlparse, parse_qs
import requests

BASE_DIR   = Path(__file__).parent
DWA_JSON   = BASE_DIR / "datos_coches.json"
MF_JSON    = BASE_DIR / "motorflash" / "datos_motorflash.json"
WEB_FOTOS  = BASE_DIR / "web_fotos"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 Chrome/120 Safari/537.36"
}

LISTING_URL_P1 = "https://www.motorflash.com/concesionario/automoviles-rueda/coches-segunda-mano/60874/"
LISTING_URL_PN = "https://www.motorflash.com/concesionario/automoviles-rueda/coches-segunda-mano/60874/?estado=usados&pagina={n}"

# ── Utilidades ─────────────────────────────────────────────

def norm_precio(p):
    limpio = re.sub(r"[^\d]", "", str(p))
    return int(limpio) if limpio else 0

def norm_km(k):
    limpio = re.sub(r"[^\d]", "", str(k))
    return int(limpio) if limpio else 0

def clave_mf(c):
    """Clave única por coche: precio + km redondeado a decena."""
    return (norm_precio(c.get("precio", "0")), round(norm_km(c.get("km", "0")), -1))

def extraer_url_foto(data_src):
    if not data_src:
        return ""
    if "filter?path=" in data_src:
        qs = parse_qs(urlparse(data_src).query)
        if "path" in qs:
            return unquote(qs["path"][0]).split("?")[0]
    return data_src

def descargar_foto(url, destino):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200 and len(r.content) > 1000:
            destino.write_bytes(r.content)
            return True
    except Exception:
        pass
    return False

# ── Scraper MotorFlash ──────────────────────────────────────

async def scrape_motorflash():
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent=HEADERS["User-Agent"]
        )
        page = await ctx.new_page()

        coches_raw = []
        ids_vistos = set()

        for num_pagina in range(1, 20):
            url = LISTING_URL_P1 if num_pagina == 1 else LISTING_URL_PN.format(n=num_pagina)
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(2000)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1500)

            pagina_coches = await page.evaluate("""() => {
                const cards = Array.from(document.querySelectorAll('.itemCar[data-ad-id]'));
                return cards.map(card => {
                    const adId = card.getAttribute('data-ad-id');
                    const nameEl = card.querySelector('p.name');
                    let marca = '', version = '';
                    if (nameEl) {
                        const span = nameEl.querySelector('span');
                        version = span ? span.textContent.trim() : '';
                        if (span) span.remove();
                        marca = nameEl.textContent.trim();
                        if (span) nameEl.appendChild(span);
                    }
                    const resumeItems = Array.from(card.querySelectorAll('ul.resume li'));
                    const km         = resumeItems[0] ? resumeItems[0].textContent.trim() : '';
                    const anio       = resumeItems[1] ? resumeItems[1].textContent.trim() : '';
                    const combustible= resumeItems[2] ? resumeItems[2].textContent.trim() : '';
                    const cambio     = resumeItems[3] ? resumeItems[3].textContent.trim() : '';
                    const precioEl   = card.querySelector('.gridPrices .price');
                    const precio     = precioEl ? precioEl.textContent.trim() : '';
                    const favEl      = card.querySelector('span.fav[data-category]');
                    const category   = favEl ? favEl.getAttribute('data-category') : '';
                    const tipo       = category.includes('KM0') ? 'KM0' : 'VO';
                    const linkEl     = card.querySelector('a.imageLink');
                    const urlRel     = linkEl ? linkEl.getAttribute('href') : '';
                    const equipItems = Array.from(card.querySelectorAll('.infoLayer ul li'));
                    const equipamiento = equipItems.map(li => li.textContent.trim()).filter(t => t.length > 0);
                    const imgEls     = Array.from(card.querySelectorAll('.swiper-slide img'));
                    const dataSrcs   = imgEls.map(img =>
                        img.getAttribute('data-src') || img.getAttribute('src') || ''
                    ).filter(s => s && !s.includes('initial.png') && !s.includes('distintivo'));
                    return { adId, marca, version, km, anio, combustible, cambio,
                             precio, tipo, urlRel, equipamiento, dataSrcs };
                });
            }""")

            if not pagina_coches:
                break

            nuevos = 0
            for c in pagina_coches:
                if c["adId"] not in ids_vistos:
                    ids_vistos.add(c["adId"])
                    coches_raw.append(c)
                    nuevos += 1

            hay_siguiente = await page.query_selector(f'a[href*="pagina={num_pagina + 1}"]')
            if not hay_siguiente:
                break

        await browser.close()

    # Normalizar nombres
    resultado = []
    for c in coches_raw:
        precio_limpio = re.sub(r"[^\d.]", "", c["precio"].replace("€","").replace("\xa0","")).strip()
        # Quitar punto de miles: "18.200" → "18.200" (mantener formato DWA)
        resultado.append({
            "fuente":         "motorflash",
            "motorflash_id":  c["adId"],
            "tipo":           c["tipo"],
            "modelo":         re.sub(r"\s+", " ", c["marca"]).strip(),
            "version":        re.sub(r"\s+", " ", c.get("version", "")).strip(),
            "combustible":    c["combustible"],
            "km":             c["km"],
            "fecha":          c["anio"],
            "cambio":         c["cambio"],
            "color":          "",
            "precio":         precio_limpio,
            "ubicacion":      "Málaga",
            "estado":         "Disponible",
            "url_motorflash": "https://www.motorflash.com" + c["urlRel"] if c["urlRel"].startswith("/") else c["urlRel"],
            "equipamiento":   c["equipamiento"],
            "_data_srcs":     c["dataSrcs"],   # temporal para descarga de fotos
        })

    return resultado


# ── Comparación DWA vs MF ────────────────────────────────────

def encontrar_exclusivos_mf(dwa_coches, mf_coches):
    """Devuelve coches de MF que no están en DWA (por precio+km)."""
    dwa_claves = {}
    for c in dwa_coches:
        k = clave_mf(c)
        dwa_claves[k] = dwa_claves.get(k, 0) + 1

    exclusivos = []
    contados = {}
    for c in mf_coches:
        k = clave_mf(c)
        usados = contados.get(k, 0)
        disponibles_dwa = dwa_claves.get(k, 0)
        if usados >= disponibles_dwa:
            exclusivos.append(c)
        contados[k] = usados + 1

    return exclusivos


# ── Descargar fotos y asignar rutas web_fotos/ ──────────────

def preparar_fotos_mf(coche_mf, idx):
    """Descarga fotos del coche MF a web_fotos/{idx:02d}/ y devuelve lista de rutas."""
    carpeta = WEB_FOTOS / f"{idx:02d}"
    carpeta.mkdir(parents=True, exist_ok=True)

    fotos_descargadas = []
    data_srcs = coche_mf.get("_data_srcs", [])
    if not data_srcs:
        return []

    primera = extraer_url_foto(data_srcs[0])
    if "_g0" in primera:
        base = re.sub(r"_g\d+\.jpg", "", primera)
        for n in range(1, 9):
            url_foto = f"{base}_g{n:02d}.jpg"
            dest = carpeta / f"foto_{n:02d}.jpg"
            if descargar_foto(url_foto, dest):
                fotos_descargadas.append(f"web_fotos/{idx:02d}/foto_{n:02d}.jpg")
            else:
                break
            time.sleep(0.2)
    else:
        for n, ds in enumerate(data_srcs[:8], 1):
            url_foto = extraer_url_foto(ds)
            if url_foto:
                dest = carpeta / f"foto_{n:02d}.jpg"
                if descargar_foto(url_foto, dest):
                    fotos_descargadas.append(f"web_fotos/{idx:02d}/foto_{n:02d}.jpg")
            time.sleep(0.2)

    return fotos_descargadas


# ── Punto de entrada ─────────────────────────────────────────

def main():
    print("\n  📡 MotorFlash — Scraping...")

    # 1) Scrapear MF
    mf_coches = asyncio.run(scrape_motorflash())
    MF_JSON.parent.mkdir(exist_ok=True)
    MF_JSON.write_text(json.dumps(mf_coches, ensure_ascii=False, indent=2))
    print(f"  MotorFlash: {len(mf_coches)} coches encontrados")

    # 2) Leer DWA actual
    dwa_coches = json.loads(DWA_JSON.read_text(encoding="utf-8"))
    dwa_solo = [c for c in dwa_coches if c.get("fuente") != "motorflash"]

    # 3) Exclusivos de MF
    exclusivos = encontrar_exclusivos_mf(dwa_solo, mf_coches)
    print(f"  Exclusivos MotorFlash (no en DWA): {len(exclusivos)}")

    # 4) Construir lista final: DWA (solo DWA) + exclusivos MF
    #    Los MF que ya no están en MotorFlash simplemente no se añaden (desaparecen)
    lista_final = list(dwa_solo)  # copia de coches DWA

    n_start = max((c["n"] for c in lista_final), default=0) + 1
    for i, c in enumerate(exclusivos):
        idx = n_start + i
        print(f"  + [{idx:02d}] {c['modelo']} {c['precio']}€ ({c['tipo']}) — descargando fotos...")
        fotos = preparar_fotos_mf(c, idx)
        c["n"]    = idx
        c["fotos"] = fotos
        c.pop("_data_srcs", None)
        lista_final.append(c)

    # 5) Re-numerar todo secuencialmente y guardar
    for i, c in enumerate(lista_final, 1):
        c["n"] = i

    DWA_JSON.write_text(json.dumps(lista_final, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✓ datos_coches.json actualizado: {len(dwa_solo)} DWA + {len(exclusivos)} MF = {len(lista_final)} total")

    # 6) Guardar comparacion.json actualizado (para referencia; el PDF lo recalcula en vivo)
    comp_out = MF_JSON.parent / "comparacion.json"
    en_ambos_list = [c for c in dwa_solo if clave_mf(c) in {clave_mf(m) for m in mf_coches}]
    solo_dwa_list  = [c for c in dwa_solo if clave_mf(c) not in {clave_mf(m) for m in mf_coches}]
    comp_out.write_text(json.dumps({
        "resumen": {
            "total_dwa":            len(dwa_solo),
            "total_motorflash":     len(mf_coches),
            "en_ambas_plataformas": len(en_ambos_list),
            "solo_en_dwa":          len(solo_dwa_list),
            "solo_en_motorflash":   len(exclusivos),
        },
        "solo_motorflash": exclusivos,
        "solo_dwa":        solo_dwa_list,
        "en_ambos":        en_ambos_list,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✓ comparacion.json actualizado")


if __name__ == "__main__":
    main()
