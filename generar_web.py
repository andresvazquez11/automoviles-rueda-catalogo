#!/usr/bin/env python3
"""
Automóviles Rueda — Generador de Catálogo Web
==============================================
Lee datos_coches.json, copia fotos a web_fotos/ y genera index.html
"""

import json, shutil, sys
from pathlib import Path

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

# ── URL foto principal Das WeltAuto (siempre exterior) ───────────────────────

def dwa_foto_url(url_relativa: str) -> str:
    """Construye URL de foto exterior principal desde URL relativa del anuncio.
    Formato: ID del anuncio → rellenado a 11 dígitos → partido en pares de 2."""
    if not url_relativa:
        return ""
    listing_id = url_relativa.rstrip('/').split('/')[-1]
    padded = listing_id.zfill(11)
    path = '/'.join(padded[i:i+2] for i in range(0, len(padded), 2))
    return f"{DASWELTAUTO}/esp/fotos_anuncios/{path}/x01.jpg"

# ── Utilidades de carpeta ────────────────────────────────────────────────────

def find_car_folder(n: int, modelo: str, precio: str = ""):
    """Busca carpeta por número+modelo+precio. Funciona con o sin · RESERVADO."""
    if not FOTOS_DIR.exists():
        return None
    prefijo_modelo = f"{n:02d} - {modelo}"
    precio_str = str(precio).replace(",", ".")

    # 1. Exacto: número + modelo + precio (con o sin RESERVADO)
    if precio:
        for candidata in sorted(FOTOS_DIR.iterdir()):
            if (candidata.is_dir()
                    and candidata.name.startswith(prefijo_modelo)
                    and precio_str in candidata.name):
                return candidata

    # 2. Número + modelo (sin precio, por si cambió)
    for candidata in sorted(FOTOS_DIR.iterdir()):
        if candidata.is_dir() and candidata.name.startswith(prefijo_modelo):
            return candidata

    return None

# ── Copiar fotos ─────────────────────────────────────────────────────────────

def copiar_fotos(coches: list[dict]) -> dict[int, list[str]]:
    WEB_FOTOS.mkdir(exist_ok=True)
    rutas: dict[int, list[str]] = {}
    for coche in coches:
        n = coche["n"]
        carpeta = find_car_folder(n, coche["modelo"], coche.get("precio", ""))
        dest = WEB_FOTOS / f"{n:02d}"
        dest.mkdir(exist_ok=True)
        urls: list[str] = []
        if carpeta and carpeta.exists():
            fotos_src = sorted(carpeta.glob("foto_*.jpg"))
            for i, foto in enumerate(fotos_src[:8], start=1):
                dst = dest / f"foto_{i:02d}.jpg"
                shutil.copy2(foto, dst)
                urls.append(f"web_fotos/{n:02d}/foto_{i:02d}.jpg")
        rutas[n] = urls
    return rutas

# ── Generar HTML ─────────────────────────────────────────────────────────────

import re as _re
from datetime import date as _date, timedelta as _timedelta

HISTORIAL_PRECIOS = BASE_DIR / "historial_precios.json"

def _cargar_historial_precios() -> dict:
    if not HISTORIAL_PRECIOS.exists():
        return {}
    try:
        return json.loads(HISTORIAL_PRECIOS.read_text(encoding="utf-8"))
    except Exception:
        return {}

def precio_maximo_historico(url_coche: str, precio_actual: int, hist: dict) -> int:
    """Devuelve el precio máximo de los últimos 10 días si es superior al actual.
    Retorna 0 si no hay bajada de precio."""
    registros = hist.get(url_coche, [])
    if len(registros) < 2:
        return 0
    # Solo precios anteriores (excluir el más reciente = precio actual)
    anteriores = [r["precio"] for r in registros[:-1]]
    maximo = max(anteriores) if anteriores else 0
    return maximo if maximo > precio_actual else 0

def extract_vr_eur(ejemplo: str) -> float:
    """Extrae el valor residual (cuota final) en EUR del texto verbatim de DWA."""
    if not ejemplo:
        return 0.0
    m = _re.search(r'cuota final en el mes \d+ de ([0-9.,]+)', ejemplo, _re.I)
    if m:
        try:
            return round(float(m.group(1).replace('.', '').replace(',', '.')), 2)
        except Exception:
            pass
    return 0.0

def extract_seguro_eur(ejemplo: str, precio: int) -> float:
    """Extrae el Seguro de Protección Plus en EUR del texto verbatim de DWA.
    Fórmula: importe_total_financiado - precio - comision_apertura.
    Fallback: 6,15% del precio (valor real verificado en todos los coches DWA)."""
    fallback = round(precio * 0.0615, 2)
    if not ejemplo:
        return fallback
    comision_m = _re.search(r'Comisi[oó]n de apertura financiada[:\s]+([0-9.,]+)', ejemplo)
    importe_m  = _re.search(r'Importe total financiado[:\s]+([0-9.,]+)', ejemplo)
    if comision_m and importe_m:
        try:
            comision = float(comision_m.group(1).replace('.', '').replace(',', '.'))
            importe  = float(importe_m.group(1).replace('.', '').replace(',', '.'))
            val = round(importe - precio - comision, 2)
            if 0 < val < precio * 0.15:   # sanity check: entre 0 y 15% del precio
                return val
        except Exception:
            pass
    return fallback

def etiqueta_dgt(combustible: str) -> str:
    """Etiqueta medioambiental DGT según combustible (coches modernos DWA).
    - CERO: Eléctrico + e-Hybrid PHEV (los que llevan pegatina 0 en el coche)
    - ECO:  Mild Hybrid
    - C:    Gasolina / Diésel Euro 6
    """
    c = combustible.lower()
    if "eléctrico" in c or "electrico" in c:
        return "CERO"
    elif "mild" in c:
        return "ECO"   # Mild Hybrid → ECO
    elif "híbrido" in c or "hibrido" in c:
        return "CERO"  # e-Hybrid PHEV → etiqueta 0 (igual que eléctrico)
    else:
        return "C"   # Gasolina / Diésel modernos Euro 6 en DWA

def _cuota_display(c: dict) -> float:
    """Devuelve la cuota a mostrar con 2 decimales: primero la de DWA, si no la calculada."""
    dwa = c.get("financiacion", {}).get("cuota")
    if dwa:
        try:
            return round(float(str(dwa).replace(",", ".")), 2)
        except Exception:
            pass
    return calcular_cuota(c["precio"])

def calcular_cuota(precio) -> float:
    """Cuota mensual estimada — TIN 6,99%, 48 meses, sin entrada (VW Financial Services)."""
    try:
        p = int(str(precio).replace(".", "").replace(",", "").split()[0])
    except Exception:
        return 0.0
    TIN, MESES = 0.0699, 48
    r = TIN / 12
    return round(p * r * (1 + r) ** MESES / ((1 + r) ** MESES - 1), 2)

def build_html(coches: list[dict], rutas: dict[int, list[str]]) -> str:
    # Todos menos vendidos (actualmente "Disponible" o "No disponible")
    visibles = [c for c in coches if c.get("estado") not in ("Vendido",)]

    total_disp = sum(1 for c in visibles if c.get("estado") == "Disponible")
    total_res  = sum(1 for c in visibles if c.get("estado") == "No disponible")

    _hist = _cargar_historial_precios()

    def _precio_ant(c):
        url = c.get("url", "")
        try:
            p = int(str(c["precio"]).replace(".", "").replace(",", "").split()[0])
        except Exception:
            p = 0
        return precio_maximo_historico(url, p, _hist)

    cars_js = json.dumps([{
        "n":           c["n"],
        "modelo":      c["modelo"],
        "version":     c["version"],
        "combustible": c["combustible"],
        "km":          c["km"],
        "fecha":       c["fecha"],
        "cambio":      c.get("cambio", ""),
        "color":       c.get("color", ""),
        "precio":          c["precio"],
        "precio_anterior": _precio_ant(c),  # >0 si bajó en últimos 10 días
        "cuota":           _cuota_display(c),
        "fin_tin":     c.get("financiacion", {}).get("tin", ""),
        "fin_tae":     c.get("financiacion", {}).get("tae", ""),
        "fin_meses":   c.get("financiacion", {}).get("meses", ""),
        "fin_entrada": c.get("financiacion", {}).get("entrada", ""),
        "fin_tipo":    c.get("financiacion", {}).get("tipo", ""),
        "fin_ejemplo": c.get("financiacion", {}).get("ejemplo", ""),
        "fin_vr":      extract_vr_eur(c.get("financiacion", {}).get("ejemplo", "")),
        "fin_seguro":  extract_seguro_eur(
                           c.get("financiacion", {}).get("ejemplo", ""),
                           int(str(c["precio"]).replace(".", "").replace(",", "").split()[0])
                       ),
        "fin_fuente":  "dwa" if c.get("financiacion", {}).get("cuota") else "calc",
        "fin_fecha_iso": (lambda f: f"{f.split('/')[1]}-{f.split('/')[0]}" if f and "/" in f and len(f.split("/"))==2 else "")(c.get("fecha", "")),
        "etiqueta":    etiqueta_dgt(c.get("combustible", "")),
        "estado":      c["estado"],          # "Disponible" o "No disponible"
        "url":         DASWELTAUTO + c["url"] if c.get("url") else "",
        "foto_main":   dwa_foto_url(c.get("url", "")),  # siempre exterior
        "equipamiento":c.get("equipamiento", []),
        "fotos":       rutas.get(c["n"], []),
    } for c in visibles], ensure_ascii=False, indent=2)

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Automóviles Rueda — Catálogo</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  :root {{
    --bg:         #eef1f7;
    --surface:    #ffffff;
    --surface2:   #e6eaf3;
    --border:     #d2d8e8;
    --red:        #C8232B;
    --red-dark:   #8B0000;
    --green:      #16a34a;
    --orange:     #ea580c;
    --text:       #1a2744;
    --muted:      #6b7a99;
    --header-bg:  #0d1b35;
    --radius:     12px;
  }}

  html {{ scroll-behavior: smooth; }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'Inter', system-ui, sans-serif;
    min-height: 100vh;
  }}

  /* ── Header ── */
  header {{
    background: var(--header-bg);
    border-bottom: 3px solid var(--red);
    padding: 0 24px;
    position: sticky;
    top: 0;
    z-index: 100;
  }}
  .header-inner {{
    max-width: 1280px;
    margin: 0 auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 68px;
    gap: 16px;
    flex-wrap: wrap;
  }}
  .logo {{
    display: flex;
    align-items: center;
    gap: 12px;
    text-decoration: none;
  }}
  .logo-badge {{
    width: 40px;
    height: 40px;
    background: linear-gradient(135deg, var(--red) 0%, var(--red-dark) 100%);
    border-radius: 9px;
    display: grid;
    place-items: center;
    font-size: 19px;
    font-weight: 800;
    color: white;
    flex-shrink: 0;
  }}
  .logo-text {{ line-height: 1.25; }}
  .logo-name  {{ font-size: 16px; font-weight: 700; color: #fff; letter-spacing: -0.2px; }}
  .logo-sub   {{ font-size: 10px; color: #8a9fc0; text-transform: uppercase; letter-spacing: 0.4px; }}

  /* Datos comercial en header */
  .comercial-info {{
    display: flex;
    align-items: center;
    gap: 20px;
    flex-wrap: wrap;
  }}
  .comercial-name {{
    font-size: 13px;
    font-weight: 700;
    color: #fff;
    white-space: nowrap;
  }}
  .comercial-contact {{
    display: flex;
    gap: 14px;
    flex-wrap: wrap;
  }}
  .comercial-contact a {{
    font-size: 12px;
    color: #8a9fc0;
    text-decoration: none;
    display: flex;
    align-items: center;
    gap: 5px;
    white-space: nowrap;
    transition: color 0.15s;
  }}
  .comercial-contact a:hover {{ color: #fff; }}

  /* WhatsApp destacado */
  .btn-whatsapp {{
    display: inline-flex; align-items: center; gap: 7px;
    background: #25D366; color: #fff !important;
    font-size: 13px; font-weight: 700;
    padding: 8px 16px; border-radius: 20px;
    text-decoration: none !important;
    white-space: nowrap;
    transition: background 0.15s, transform 0.15s;
    box-shadow: 0 2px 8px rgba(37,211,102,0.35);
  }}
  .btn-whatsapp:hover {{ background: #128C7E; transform: translateY(-1px); }}

  /* ── Hero ── */
  .hero {{
    background: linear-gradient(135deg, var(--header-bg) 0%, #1a3060 100%);
    padding: 44px 24px 36px;
    text-align: center;
    border-bottom: 1px solid var(--border);
  }}
  .hero h1 {{
    font-size: clamp(26px, 4.5vw, 44px);
    font-weight: 800;
    letter-spacing: -1px;
    line-height: 1.1;
    margin-bottom: 10px;
    color: #fff;
  }}
  .hero h1 span {{ color: #ff6b6b; }}
  .hero p {{ color: #8a9fc0; font-size: 15px; max-width: 460px; margin: 0 auto; }}

  /* ── Controles ── */
  .controls {{
    padding: 18px 24px;
    max-width: 1280px;
    margin: 0 auto;
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    align-items: center;
  }}
  .filter-group {{
    display: flex;
    gap: 6px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 4px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  }}
  .filter-btn {{
    background: none; border: none;
    color: var(--muted);
    font-family: inherit; font-size: 13px; font-weight: 500;
    padding: 7px 14px;
    border-radius: 7px;
    cursor: pointer;
    transition: all 0.15s;
    white-space: nowrap;
  }}
  .filter-btn.active  {{ background: var(--red); color: #fff; font-weight: 700; }}
  .filter-btn:not(.active):hover {{ color: var(--text); background: var(--surface2); }}

  .search-wrap {{
    flex: 1; min-width: 180px; max-width: 300px; position: relative;
  }}
  .search-wrap svg {{
    position: absolute; left: 11px; top: 50%; transform: translateY(-50%);
    color: var(--muted); pointer-events: none;
  }}
  .search-input {{
    width: 100%;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 9px;
    color: var(--text);
    font-family: inherit; font-size: 13px;
    padding: 9px 11px 9px 36px;
    outline: none;
    transition: border-color 0.15s;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  }}
  .search-input::placeholder {{ color: var(--muted); }}
  .search-input:focus {{ border-color: var(--red); }}

  .counter {{
    margin-left: auto; font-size: 13px; color: var(--muted); white-space: nowrap;
  }}
  .counter strong {{ color: var(--text); }}

  /* ── Grid ── */
  .grid {{
    max-width: 1280px;
    margin: 0 auto;
    padding: 4px 24px 56px;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 18px;
  }}

  /* ── Card ── */
  .card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    cursor: pointer;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
    transition: transform 0.18s, box-shadow 0.18s, border-color 0.18s;
    display: flex; flex-direction: column;
  }}
  .card:hover {{
    transform: translateY(-3px);
    box-shadow: 0 10px 28px rgba(0,0,0,0.14);
    border-color: rgba(200,35,43,0.35);
  }}

  .card-img {{
    position: relative; aspect-ratio: 16/9;
    background: var(--surface2); overflow: hidden;
  }}
  .card-img img {{
    width: 100%; height: 100%; object-fit: cover;
    transition: transform 0.4s;
  }}
  .card:hover .card-img img {{ transform: scale(1.04); }}
  .no-foto {{
    width: 100%; height: 100%;
    display: grid; place-items: center;
    color: var(--muted); font-size: 13px;
    background: var(--surface2);
  }}

  .reservado-overlay {{
    position: absolute; inset: 0;
    background: rgba(255,255,255,0.25);
  }}

  .badge-estado {{
    position: absolute; top: 10px; left: 10px;
    font-size: 11px; font-weight: 700;
    padding: 4px 10px; border-radius: 20px;
    letter-spacing: 0.4px; text-transform: uppercase;
  }}
  .badge-disponible {{ background: rgba(22,163,74,0.12); color: #15803d; border: 1px solid rgba(22,163,74,0.3); }}
  .badge-reservado  {{ background: rgba(234,88,12,0.12); color: #c2410c; border: 1px solid rgba(234,88,12,0.3); }}

  .foto-count {{
    position: absolute; bottom: 8px; right: 8px;
    background: rgba(0,0,0,0.45); color: #fff;
    font-size: 11px; padding: 3px 8px; border-radius: 10px;
    backdrop-filter: blur(4px);
  }}

  .card-body {{
    padding: 14px 16px 16px;
    flex: 1; display: flex; flex-direction: column; gap: 9px;
  }}
  .card-title  {{ font-size: 17px; font-weight: 700; letter-spacing: -0.2px; }}
  .card-version {{ font-size: 12px; color: var(--muted); line-height: 1.4; margin-top: -3px; }}

  .card-specs {{
    display: flex; flex-wrap: wrap; gap: 5px;
  }}
  .spec-pill {{
    background: var(--surface2); border: 1px solid var(--border);
    border-radius: 6px; font-size: 11px; padding: 3px 8px;
    color: var(--muted); display: flex; align-items: center; gap: 3px;
  }}

  .card-footer {{
    display: flex; align-items: center; justify-content: space-between;
    margin-top: auto; padding-top: 10px; border-top: 1px solid var(--border);
  }}
  .card-price {{ font-size: 22px; font-weight: 800; color: var(--red); letter-spacing: -0.4px; }}
  .card-price span {{ font-size: 13px; font-weight: 500; color: var(--muted); }}
  .card-cuota {{ font-size: 12px; color: var(--muted); margin-top: 2px; }}
  .card-cuota strong {{ color: #4a5568; font-weight: 600; }}

  /* ── Bajada de precio ── */
  .oferta-badge {{
    position: absolute; top: 10px; right: 10px; z-index: 3;
    background: var(--red); color: #fff;
    font-size: 11px; font-weight: 800; letter-spacing: 1px;
    text-transform: uppercase; padding: 4px 9px;
    border-radius: 4px;
    animation: oferta-pulse 2s ease-in-out infinite;
    box-shadow: 0 2px 8px rgba(200,35,43,0.5);
  }}
  @keyframes oferta-pulse {{
    0%,100% {{ transform: scale(1);     box-shadow: 0 2px 8px rgba(200,35,43,0.5); }}
    50%      {{ transform: scale(1.06); box-shadow: 0 4px 16px rgba(200,35,43,0.7); }}
  }}
  .card-price-drop {{
    display: flex; align-items: center; gap: 6px; margin-bottom: 1px;
  }}
  .card-price-old {{
    font-size: 14px; font-weight: 500; color: var(--muted);
    text-decoration: line-through; text-decoration-color: var(--red);
    text-decoration-thickness: 2px;
  }}
  .price-drop-arrow {{
    font-size: 15px; font-weight: 800; color: #16a34a;
    animation: arrow-bounce 1.2s ease-in-out infinite;
  }}
  @keyframes arrow-bounce {{
    0%,100% {{ transform: translateY(0); }}
    50%      {{ transform: translateY(3px); }}
  }}
  .card-price-new {{
    font-size: 25px !important; /* ligeramente más grande que el normal */
  }}
  .card-cuota .fin-tipo-badge {{
    display: inline-block; font-size: 9px; font-weight: 700;
    letter-spacing: 0.5px; text-transform: uppercase;
    background: var(--surface2); border: 1px solid var(--border);
    border-radius: 4px; padding: 1px 5px; margin-left: 4px;
    vertical-align: middle; color: var(--muted);
  }}

  .etiqueta-dgt {{
    position: absolute !important; bottom: 8px !important; left: 8px !important;
    width: 68px !important; height: 68px !important;
    max-width: 68px !important; max-height: 68px !important;
    display: block; object-fit: contain;
    filter: drop-shadow(0 2px 5px rgba(0,0,0,0.55));
    pointer-events: none;
  }}

  .sort-select {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 9px;
    color: var(--text);
    font-family: inherit; font-size: 13px;
    padding: 9px 11px;
    outline: none;
    cursor: pointer;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    transition: border-color 0.15s;
  }}
  .sort-select:focus {{ border-color: var(--red); }}

  /* ── Calculadora de Financiación v2 (full port) ── */
  .modal-financiacion {{
    background: #0d1120;
    border-top: 2px solid rgba(200,35,43,0.3);
    color: #f0f4ff;
    overflow: hidden;
  }}
  /* Car info bar */
  .cv2-car-bar {{
    padding: 14px 20px 12px;
    border-bottom: 1px solid rgba(255,255,255,0.07);
    display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;
  }}
  .cv2-car-modelo {{ font-weight: 700; font-size: 14px; color: #fff; line-height: 1.25; }}
  .cv2-car-precio {{ font-size: 14px; font-weight: 800; color: #C8232B; font-variant-numeric: tabular-nums; }}
  .cv2-cat-badge {{
    display: inline-block; font-size: 10px; font-weight: 700;
    letter-spacing: 1px; padding: 3px 9px; border: 1px solid;
    vertical-align: middle;
  }}
  .cv2-cat-badge.vs {{ color:#22C55E; border-color:#22C55E; background:rgba(34,197,94,.1); }}
  .cv2-cat-badge.vo {{ color:#F59E0B; border-color:#F59E0B; background:rgba(245,158,11,.1); }}
  .cv2-cat-badge.vu {{ color:rgba(240,244,255,.45); border-color:rgba(255,255,255,.2); background:rgba(255,255,255,.05); }}
  /* Panel (inputs area) */
  .cv2-panel {{ padding: 16px 20px; border-bottom: 1px solid rgba(255,255,255,0.06); }}
  /* Section label */
  .cv2-slbl {{
    font-size: 10px; font-weight: 700; letter-spacing: 2.5px;
    text-transform: uppercase; color: #C8232B; margin-bottom: 10px;
    display: flex; align-items: center; gap: 8px;
  }}
  .cv2-slbl::after {{ content:''; flex:1; height:1px; background:rgba(200,35,43,.2); }}
  /* Mode tabs LINEAL / FLEX */
  .cv2-mode-tabs {{
    display: grid; grid-template-columns: 1fr 1fr;
    border: 1px solid rgba(255,255,255,0.1); margin-bottom: 8px;
  }}
  .cv2-mode-tab {{
    background: transparent; border: none; cursor: pointer;
    padding: 10px 8px; font-family: inherit;
    font-size: 13px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;
    color: rgba(240,244,255,0.4); transition: all 0.15s; position: relative;
  }}
  .cv2-mode-tab.active {{ background:rgba(200,35,43,.12); color:#C8232B; }}
  .cv2-mode-tab.active::after {{
    content:''; position:absolute; bottom:0; left:10%; right:10%; height:2px; background:#C8232B;
  }}
  .cv2-mode-tab:hover:not(.active):not(:disabled) {{ color:#fff; background:rgba(255,255,255,.04); }}
  .cv2-mode-tab:disabled {{ opacity:.3; cursor:not-allowed; }}
  .cv2-flex-note {{ display:none; font-size:11px; color:#F59E0B; margin-bottom:8px; }}
  .cv2-flex-note.visible {{ display:block; }}
  /* Campaign pills */
  .cv2-camp-pills {{ display:flex; gap:6px; }}
  .cv2-camp-pill {{
    flex:1; text-align:center;
    background:transparent; border:1px solid rgba(255,255,255,.1);
    color:rgba(240,244,255,.45); cursor:pointer;
    font-family:inherit; font-size:12px; font-weight:700;
    padding:8px 10px; letter-spacing:.3px; transition:all .15s;
  }}
  .cv2-camp-pill.active {{ background:rgba(34,197,94,.1); border-color:#22C55E; color:#22C55E; }}
  .cv2-camp-pill:hover:not(.active):not(:disabled) {{ border-color:rgba(255,255,255,.25); color:#fff; }}
  .cv2-camp-pill:disabled {{ opacity:.3; cursor:not-allowed; pointer-events:none; }}
  .cv2-camp-auto {{
    font-size:12px; color:rgba(240,244,255,.45);
    padding:8px 12px; border:1px solid rgba(255,255,255,.1); font-family:inherit;
  }}
  /* TIN block */
  .cv2-tin-block {{
    display:flex; align-items:center; gap:12px;
    border:1px solid rgba(255,255,255,.1); padding:10px 14px;
    background:rgba(34,197,94,.04); margin-bottom:4px;
  }}
  .cv2-tin-val {{ font-size:24px; font-weight:800; color:#22C55E; line-height:1; font-variant-numeric:tabular-nums; }}
  .cv2-tin-sfx {{ font-size:13px; color:rgba(240,244,255,.35); }}
  .cv2-tin-lbl {{ flex:1; font-size:11px; color:rgba(240,244,255,.4); line-height:1.4; }}
  .cv2-tin-link {{
    background:none; border:none; cursor:pointer; font-family:inherit;
    font-size:11px; color:rgba(240,244,255,.28); text-decoration:underline; padding:0;
  }}
  .cv2-tin-link:hover {{ color:#fff; }}
  .cv2-tin-manual {{
    display:none; border:1px solid #C8232B; padding:10px 14px;
    align-items:center; gap:8px; margin-bottom:4px;
  }}
  .cv2-tin-manual.visible {{ display:flex; }}
  .cv2-tin-manual input {{
    background:transparent; border:none; outline:none;
    font-family:inherit; font-size:20px; font-weight:700;
    color:#fff; width:6ch; text-align:right; -moz-appearance:textfield;
  }}
  .cv2-tin-manual input::-webkit-outer-spin-button,
  .cv2-tin-manual input::-webkit-inner-spin-button {{ -webkit-appearance:none; }}
  .cv2-tin-restore {{
    background:none; border:none; cursor:pointer; font-family:inherit;
    font-size:11px; color:#F59E0B; text-decoration:underline; padding:0; display:none;
  }}
  /* Field label */
  .cv2-flbl {{
    font-size:11px; font-weight:600; letter-spacing:1.5px; text-transform:uppercase;
    color:rgba(240,244,255,.35); margin-bottom:8px;
    display:flex; justify-content:space-between; align-items:center;
  }}
  .cv2-flbl span {{ font-size:13px; font-weight:700; color:#fff; letter-spacing:0; text-transform:none; }}
  /* Pills (plazo & km) */
  .cv2-pills {{ display:flex; gap:5px; flex-wrap:wrap; }}
  .cv2-pill {{
    background:transparent; border:1px solid rgba(255,255,255,.1);
    color:rgba(240,244,255,.45); cursor:pointer;
    font-family:inherit; font-size:12px; font-weight:700;
    padding:6px 10px; transition:all .15s;
    flex:1; min-width:0; text-align:center;
  }}
  .cv2-pill.active {{ background:#C8232B; border-color:#C8232B; color:#fff; }}
  .cv2-pill:hover:not(.active):not(:disabled) {{ border-color:rgba(255,255,255,.3); color:#fff; }}
  .cv2-pill:disabled {{ opacity:.25; cursor:not-allowed; pointer-events:none; }}
  /* Slider */
  .cv2-slider-row {{
    display:flex; justify-content:space-between;
    font-size:11px; color:rgba(240,244,255,.3); margin-top:6px;
  }}
  input[type=range].cv2-slider {{
    -webkit-appearance:none; appearance:none;
    width:100%; height:4px; outline:none; cursor:pointer; border-radius:0;
    background:linear-gradient(90deg, #C8232B var(--pct,0%), rgba(255,255,255,.1) var(--pct,0%));
  }}
  input[type=range].cv2-slider::-webkit-slider-thumb {{
    -webkit-appearance:none;
    width:18px; height:18px; background:#C8232B;
    clip-path:polygon(50% 0%,100% 50%,50% 100%,0% 50%);
    cursor:pointer; border:none; transition:transform .1s;
  }}
  input[type=range].cv2-slider::-webkit-slider-thumb:hover {{ transform:scale(1.3); }}
  input[type=range].cv2-slider::-moz-range-thumb {{
    width:18px; height:18px; background:#C8232B; border:none; border-radius:0; cursor:pointer;
  }}
  /* Maintenance */
  .cv2-mant-badge {{
    display:none; font-size:12px; font-weight:700; color:#22C55E;
    padding:6px 10px; border:1px solid rgba(34,197,94,.3);
    background:rgba(34,197,94,.08); letter-spacing:.3px; margin-bottom:8px;
  }}
  .cv2-mant-badge.visible {{ display:block; }}
  .cv2-mant-info {{
    display:none; font-size:11px; color:rgba(240,244,255,.4);
    margin-top:8px; line-height:1.6;
    border-left:2px solid rgba(255,255,255,.1); padding-left:10px;
  }}
  .cv2-mant-info.visible {{ display:block; }}
  .cv2-mant-unavail {{
    display:none; font-size:11px; color:rgba(240,244,255,.3); margin-top:6px;
  }}
  .cv2-mant-unavail.visible {{ display:block; }}
  /* Info chips row */
  .cv2-info-chips {{
    padding:8px 20px; border-bottom:1px solid rgba(255,255,255,.06);
    display:flex; gap:6px; flex-wrap:wrap; align-items:center;
  }}
  .cv2-chip {{
    font-size:11px; font-weight:600; letter-spacing:.5px;
    padding:3px 9px; border:1px solid rgba(255,255,255,.12); color:rgba(240,244,255,.45);
  }}
  .cv2-chip.green {{ color:#22C55E; border-color:rgba(34,197,94,.35); background:rgba(34,197,94,.08); }}
  .cv2-chip.amber {{ color:#F59E0B; border-color:rgba(245,158,11,.35); background:rgba(245,158,11,.08); }}
  .cv2-chip.red   {{ color:#C8232B; border-color:rgba(200,35,43,.35);  background:rgba(200,35,43,.08); }}
  /* Credit warning */
  .cv2-credit-warn {{
    display:none; margin:0 20px 8px; padding:10px 14px;
    background:rgba(245,158,11,.08); border:1px solid rgba(245,158,11,.3);
    font-size:12px; color:#F59E0B; line-height:1.5;
  }}
  .cv2-credit-warn.visible {{ display:block; }}
  /* Cuota hero */
  .cv2-cuota-hero {{
    padding:24px 20px 16px; text-align:center;
    background:linear-gradient(180deg,rgba(200,35,43,.07) 0%,transparent 100%);
    border-bottom:1px solid rgba(255,255,255,.06);
  }}
  .cv2-cuota-lbl {{
    font-size:10px; font-weight:600; letter-spacing:2.5px; text-transform:uppercase;
    color:rgba(240,244,255,.4); margin-bottom:8px;
  }}
  .cv2-cuota-val {{
    font-weight:800; font-size:clamp(36px,8vw,52px);
    color:#C8232B; line-height:1; letter-spacing:-1px;
    font-variant-numeric:tabular-nums; transition:opacity .15s;
  }}
  .cv2-cuota-unit {{ font-size:17px; font-weight:400; color:rgba(240,244,255,.4); margin-left:4px; }}
  .cv2-cuota-final {{
    display:none; margin:10px auto 0; padding:7px 16px;
    background:rgba(245,158,11,.08); border:1px solid rgba(245,158,11,.2);
    max-width:260px; justify-content:space-between; align-items:center; gap:12px;
  }}
  .cv2-cuota-final.visible {{ display:flex; }}
  .cv2-cf-lbl {{ font-size:11px; color:#F59E0B; letter-spacing:.8px; }}
  .cv2-cf-val {{ font-size:14px; font-weight:700; color:#F59E0B; font-variant-numeric:tabular-nums; }}
  /* Breakdown */
  .cv2-breakdown {{ padding:0 20px 4px; }}
  .cv2-br-row {{
    display:flex; justify-content:space-between; align-items:center;
    padding:9px 0; border-bottom:1px solid rgba(255,255,255,.04); font-size:13px;
  }}
  .cv2-br-row:last-child {{ border-bottom:none; }}
  .cv2-br-lbl {{ color:rgba(240,244,255,.4); font-size:12px; }}
  .cv2-br-val {{ font-weight:600; font-size:13px; color:rgba(240,244,255,.9); font-variant-numeric:tabular-nums; }}
  .cv2-br-row.hidden {{ display:none; }}
  .cv2-br-row.bonif .cv2-br-val {{ color:#22C55E; }}
  .cv2-br-row.mant  .cv2-br-val {{ color:#F59E0B; }}
  .cv2-br-row.total {{
    background:rgba(200,35,43,.07); margin:6px -20px 0; padding:11px 20px; border-bottom:none;
  }}
  .cv2-br-row.total .cv2-br-lbl {{ color:#fff; font-weight:700; }}
  .cv2-br-row.total .cv2-br-val {{ font-size:15px; font-weight:700; }}
  /* CTA */
  .cv2-cta {{ padding:16px 20px 20px; border-top:1px solid rgba(255,255,255,.07); display:flex; flex-direction:column; gap:10px; }}
  .cv2-btn-wa {{
    display:flex; align-items:center; justify-content:center; gap:9px;
    width:100%; padding:13px 16px; background:#25D366; color:#fff;
    font-family:inherit; font-size:13px; font-weight:700;
    letter-spacing:.5px; text-transform:uppercase;
    text-decoration:none; border:none; cursor:pointer;
    transition:background .2s, transform .12s;
  }}
  .cv2-btn-wa:hover {{ background:#1ebe57; transform:translateY(-1px); }}
  .cv2-legal {{ font-size:10px; color:rgba(240,244,255,.22); line-height:1.6; }}

  .btn-dwa {{
    background: none; border: 1px solid var(--border); color: var(--muted);
    font-family: inherit; font-size: 11px; font-weight: 600;
    padding: 6px 11px; border-radius: 7px; cursor: pointer;
    text-decoration: none; display: inline-flex; align-items: center; gap: 3px;
    transition: all 0.15s; white-space: nowrap;
  }}
  .btn-dwa:hover {{ border-color: var(--red); color: var(--red); }}

  /* ── Modal ── */
  .modal-backdrop {{
    display: none; position: fixed; inset: 0;
    background: rgba(13,27,53,0.8);
    z-index: 200; overflow-y: auto; padding: 16px;
    backdrop-filter: blur(6px);
  }}
  .modal-backdrop.open {{ display: flex; align-items: flex-start; justify-content: center; }}
  .modal {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 16px; width: 100%; max-width: 820px;
    overflow: hidden; margin: auto;
    box-shadow: 0 32px 80px rgba(13,27,53,0.35);
  }}

  .modal-gallery {{ position: relative; aspect-ratio: 16/9; background: var(--surface2); overflow: hidden; }}
  .gallery-slides {{ display: flex; transition: transform 0.35s cubic-bezier(0.4,0,0.2,1); height: 100%; }}
  .gallery-slide  {{ min-width: 100%; height: 100%; }}
  .gallery-slide img {{ width: 100%; height: 100%; object-fit: cover; }}
  .gallery-btn {{
    position: absolute; top: 50%; transform: translateY(-50%);
    background: rgba(255,255,255,0.85); border: none; color: var(--text);
    font-size: 20px; width: 38px; height: 38px; border-radius: 50%;
    cursor: pointer; display: grid; place-items: center;
    transition: background 0.15s; z-index: 2;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  }}
  .gallery-btn:hover {{ background: var(--red); color: #fff; }}
  .gallery-btn.prev {{ left: 12px; }}
  .gallery-btn.next {{ right: 12px; }}
  .gallery-dots {{
    position: absolute; bottom: 12px; left: 50%; transform: translateX(-50%);
    display: flex; gap: 6px;
  }}
  .gallery-dot {{
    width: 7px; height: 7px; border-radius: 50%;
    background: rgba(255,255,255,0.5); cursor: pointer;
    transition: background 0.15s, transform 0.15s;
  }}
  .gallery-dot.active {{ background: #fff; transform: scale(1.3); }}
  .modal-close {{
    position: absolute; top: 12px; right: 12px;
    background: rgba(255,255,255,0.85); border: none;
    color: var(--text); width: 34px; height: 34px; border-radius: 50%;
    cursor: pointer; font-size: 17px; display: grid; place-items: center;
    z-index: 3; transition: all 0.15s;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  }}
  .modal-close:hover {{ background: var(--red); color: #fff; }}

  .modal-body {{ padding: 22px; display: flex; flex-direction: column; gap: 18px; }}
  .modal-header {{
    display: flex; align-items: flex-start;
    justify-content: space-between; gap: 16px; flex-wrap: wrap;
  }}
  .modal-modelo  {{ font-size: 24px; font-weight: 800; letter-spacing: -0.4px; line-height: 1.1; }}
  .modal-version {{ font-size: 13px; color: var(--muted); margin-top: 4px; line-height: 1.4; }}
  .modal-price-block {{ text-align: right; flex-shrink: 0; }}
  .modal-price     {{ font-size: 30px; font-weight: 800; color: var(--red); letter-spacing: -0.8px; }}
  .modal-price-sub {{ font-size: 12px; color: var(--muted); margin-top: 2px; }}

  .specs-grid {{
    display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px;
  }}
  .spec-item {{
    background: var(--surface2); border: 1px solid var(--border);
    border-radius: 8px; padding: 9px 11px;
  }}
  .spec-label {{ font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 3px; }}
  .spec-value {{ font-size: 13px; font-weight: 600; }}

  .equip-section h3 {{
    font-size: 13px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.5px; color: var(--muted); margin-bottom: 10px;
  }}
  .equip-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 6px; }}
  .equip-item {{ display: flex; align-items: flex-start; gap: 7px; font-size: 12px; color: #4a5568; line-height: 1.4; }}
  .equip-check {{ color: var(--green); font-size: 13px; flex-shrink: 0; margin-top: 1px; }}

  .modal-cta {{ display: flex; justify-content: flex-end; }}
  .btn-cta {{
    background: linear-gradient(135deg, var(--red) 0%, var(--red-dark) 100%);
    color: #fff; border: none; font-family: inherit; font-size: 14px; font-weight: 700;
    padding: 13px 26px; border-radius: 9px; cursor: pointer;
    text-decoration: none; display: inline-flex; align-items: center; gap: 7px;
    transition: opacity 0.15s, transform 0.15s;
  }}
  .btn-cta:hover {{ opacity: 0.9; transform: translateY(-1px); }}

  /* ── Botón flotante WhatsApp ── */
  .whatsapp-float {{
    position: fixed;
    bottom: 22px;
    right: 22px;
    z-index: 150;
    display: flex;
    align-items: center;
    gap: 9px;
    background: #25D366;
    color: #fff;
    font-family: inherit;
    font-size: 14px;
    font-weight: 700;
    padding: 13px 20px 13px 16px;
    border-radius: 50px;
    text-decoration: none;
    box-shadow: 0 4px 18px rgba(37,211,102,0.5);
    transition: background 0.15s, transform 0.15s, box-shadow 0.15s;
  }}
  .whatsapp-float:hover {{
    background: #128C7E;
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(37,211,102,0.45);
  }}
  .whatsapp-float svg {{ flex-shrink: 0; }}
  /* En desktop se puede dejar visible también, o solo icono */
  @media (min-width: 641px) {{
    .whatsapp-float {{ padding: 12px 16px; border-radius: 50%; }}
    .whatsapp-float .wa-label {{ display: none; }}
  }}

  /* ── Footer ── */
  footer {{
    border-top: 1px solid var(--border);
    background: var(--surface);
    padding: 28px 24px;
    text-align: center;
    color: var(--muted); font-size: 12px;
  }}
  footer a {{ color: var(--red); text-decoration: none; }}
  footer a:hover {{ text-decoration: underline; }}

  /* ── Empty state ── */
  .empty-state {{ grid-column: 1/-1; text-align: center; padding: 80px 24px; color: var(--muted); }}
  .empty-state div {{ font-size: 48px; margin-bottom: 14px; }}

  /* ── Responsive ── */
  @media (max-width: 640px) {{
    .comercial-info {{ display: none; }}
    .controls {{ padding: 14px 16px; gap: 10px; }}
    .counter {{ width: 100%; }}
    .grid {{ padding: 4px 14px 40px; gap: 14px; grid-template-columns: 1fr; }}
    .modal-body {{ padding: 14px; }}
    .modal-header {{ flex-direction: column; }}
    .modal-price-block {{ text-align: left; }}
    .modal-cta {{ justify-content: stretch; }}
    .btn-cta {{ width: 100%; justify-content: center; }}
    .equip-grid {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>

<header>
  <div class="header-inner">
    <a class="logo" href="#">
      <div class="logo-badge">R</div>
      <div class="logo-text">
        <div class="logo-name">Automóviles Rueda</div>
        <div class="logo-sub">Concesionario SEAT · CUPRA · Volkswagen</div>
      </div>
    </a>
    <div class="comercial-info">
      <span class="comercial-name">{COMERCIAL_NOMBRE}</span>
      <div class="comercial-contact">
        <a href="tel:{COMERCIAL_TELEFONO.replace(' ','')}">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12 19.79 19.79 0 0 1 1.61 3.39a2 2 0 0 1 2-2.18h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 8.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
          {COMERCIAL_TELEFONO}
        </a>
        <a href="mailto:{COMERCIAL_EMAIL}">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>
          {COMERCIAL_EMAIL}
        </a>
      </div>
      <a class="btn-whatsapp" href="https://wa.me/34{COMERCIAL_TELEFONO.replace(' ','').replace('+34','')}?text=Hola%20Andr%C3%A9s%2C%20te%20escribo%20desde%20el%20cat%C3%A1logo%20de%20coches.%20Me%20interesa%20uno%20de%20los%20veh%C3%ADculos." target="_blank" rel="noopener">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 0 1-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 0 1-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 0 1 2.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0 0 12.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 0 0 5.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 0 0-3.48-8.413z"/></svg>
        WhatsApp
      </a>
    </div>
  </div>
</header>

<section class="hero">
  <h1>Vehículos <span>seminuevos</span> de confianza</h1>
  <p>Todos los coches con garantía oficial Das WeltAuto. Calidad certificada, precio transparente.</p>
</section>

<div class="controls">
  <div class="filter-group">
    <button class="filter-btn active" data-filter="todos">Todos ({total_disp + total_res})</button>
    <button class="filter-btn" data-filter="Disponible">Disponible ({total_disp})</button>
    <button class="filter-btn" data-filter="Reservado">Reservado ({total_res})</button>
  </div>
  <div class="search-wrap">
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
    <input class="search-input" id="search" type="text" placeholder="Buscar modelo..." autocomplete="off">
  </div>
  <select class="sort-select" id="sort-select">
    <option value="default">Ordenar</option>
    <option value="precio-asc">Precio ↑ menor primero</option>
    <option value="precio-desc">Precio ↓ mayor primero</option>
    <option value="km-asc">Km ↑ menos km</option>
    <option value="km-desc">Km ↓ más km</option>
  </select>
  <div class="counter" id="counter">Mostrando <strong id="cnt-showing">{total_disp + total_res}</strong> vehículos</div>
</div>

<div class="grid" id="grid"></div>

<div class="modal-backdrop" id="modal-backdrop">
  <div class="modal" id="modal">
    <div class="modal-gallery" id="modal-gallery">
      <div class="gallery-slides" id="gallery-slides"></div>
      <button class="gallery-btn prev" id="gallery-prev">&#8249;</button>
      <button class="gallery-btn next" id="gallery-next">&#8250;</button>
      <div class="gallery-dots" id="gallery-dots"></div>
      <button class="modal-close" id="modal-close">&#215;</button>
    </div>
    <div class="modal-body">
      <div class="modal-header">
        <div>
          <div class="modal-modelo" id="m-modelo"></div>
          <div class="modal-version" id="m-version"></div>
        </div>
        <div class="modal-price-block">
          <div class="modal-price" id="m-precio"></div>
          <div class="modal-price-sub" id="m-estado-pill"></div>
        </div>
      </div>
      <div class="specs-grid" id="m-specs"></div>
      <div class="equip-section" id="equip-section">
        <h3>Equipamiento</h3>
        <div class="equip-grid" id="m-equip"></div>
      </div>
      <div class="modal-financiacion" id="m-financiacion">
        <!-- Car info bar (auto-populated) -->
        <div class="cv2-car-bar">
          <div>
            <div class="cv2-car-modelo" id="cv2-modelo">—</div>
            <div style="display:flex;align-items:center;gap:8px;margin-top:4px;">
              <span class="cv2-car-precio" id="cv2-precio">—</span>
              <span class="cv2-cat-badge" id="cv2-cat-badge"></span>
            </div>
          </div>
          <div style="font-size:10px;color:rgba(240,244,255,0.28);text-align:right;line-height:1.6;letter-spacing:.5px;text-transform:uppercase;">Calculadora<br>Financiación VWFS</div>
        </div>

        <!-- Inputs panel -->
        <div class="cv2-panel">
          <!-- Modalidad -->
          <div class="cv2-slbl">Modalidad de pago</div>
          <div class="cv2-mode-tabs">
            <button class="cv2-mode-tab active" id="cv2-tab-lineal" onclick="cv2SetMode('lineal')">LINEAL</button>
            <button class="cv2-mode-tab" id="cv2-tab-flex" onclick="cv2SetMode('flex')">FLEX</button>
          </div>
          <div class="cv2-flex-note" id="cv2-flex-note">⚠ FLEX no disponible para vehículos VU (&gt;60 meses)</div>

          <!-- Campaña -->
          <div class="cv2-slbl" style="margin-top:16px;">Campaña</div>
          <div class="cv2-camp-pills" id="cv2-camp-seat" style="display:none">
            <button class="cv2-camp-pill active" id="cv2-entry" onclick="cv2SetCampana('ENTRY')">ENTRY · 6,99%</button>
            <button class="cv2-camp-pill" id="cv2-gama-seat" onclick="cv2SetCampana('GAMA')">GAMA · 8,99%</button>
          </div>
          <div class="cv2-camp-pills" id="cv2-camp-cupra" style="display:none">
            <button class="cv2-camp-pill active" id="cv2-gama-cupra" onclick="cv2SetCampana('GAMA')">GAMA · 8,99%</button>
            <button class="cv2-camp-pill" id="cv2-approved" onclick="cv2SetCampana('APPROVED')">APPROVED · 5,50%</button>
          </div>
          <div id="cv2-camp-otra" style="display:none">
            <div class="cv2-camp-auto" id="cv2-otra-label">Automático según importe financiado</div>
          </div>

          <!-- TIN -->
          <div style="margin-top:14px;">
            <div class="cv2-tin-block">
              <div>
                <span class="cv2-tin-val" id="cv2-tin-val">6,99</span>
                <span class="cv2-tin-sfx"> % TIN</span>
              </div>
              <div class="cv2-tin-lbl" id="cv2-tin-lbl">ENTRY · SEAT</div>
            </div>
            <button class="cv2-tin-link" id="cv2-tin-btn" onclick="cv2ToggleTin()">✎ personalizar TIN</button>
            <div class="cv2-tin-manual" id="cv2-tin-manual">
              <input type="number" id="cv2-tin-input" value="6.99" min="0" max="30" step="0.01"
                inputmode="decimal" oninput="cv2TinInput(this.value)">
              <span class="cv2-tin-sfx">% TIN</span>
            </div>
            <button class="cv2-tin-restore" id="cv2-tin-restore" onclick="cv2RestoreTin()">↩ restaurar TIN automático</button>
          </div>

          <!-- Entrada -->
          <div style="margin-top:18px;">
            <div class="cv2-flbl">Entrada inicial <span id="cv2-disp-entrada">0 €</span></div>
            <input type="range" class="cv2-slider" id="cv2-sl-entrada"
              min="0" max="0" step="100" value="0" oninput="cv2SliderMove(this.value)">
            <div class="cv2-slider-row">
              <span>0 €</span>
              <span id="cv2-lbl-max">máx. — €</span>
            </div>
          </div>

          <!-- Plazo -->
          <div style="margin-top:16px;">
            <div class="cv2-flbl">Plazo <span id="cv2-disp-meses">60 meses</span></div>
            <div class="cv2-pills" id="cv2-pills-meses">
              <button class="cv2-pill" id="cv2-pl-24" onclick="cv2SetMeses(24)">24m</button>
              <button class="cv2-pill" id="cv2-pl-36" onclick="cv2SetMeses(36)">36m</button>
              <button class="cv2-pill" id="cv2-pl-48" onclick="cv2SetMeses(48)">48m</button>
              <button class="cv2-pill active" id="cv2-pl-60" onclick="cv2SetMeses(60)">60m</button>
              <button class="cv2-pill" id="cv2-pl-72" onclick="cv2SetMeses(72)">72m</button>
              <button class="cv2-pill" id="cv2-pl-84" onclick="cv2SetMeses(84)">84m</button>
              <button class="cv2-pill" id="cv2-pl-96" onclick="cv2SetMeses(96)">96m</button>
            </div>
          </div>

          <!-- Km (FLEX only) -->
          <div id="cv2-field-km" style="display:none;margin-top:16px;">
            <div class="cv2-flbl">Km / año <span id="cv2-disp-km">15.000 km</span></div>
            <div class="cv2-pills" id="cv2-pills-km">
              <button class="cv2-pill" onclick="cv2SetKm(10000)">10k</button>
              <button class="cv2-pill active" onclick="cv2SetKm(15000)">15k</button>
              <button class="cv2-pill" onclick="cv2SetKm(20000)">20k</button>
              <button class="cv2-pill" onclick="cv2SetKm(25000)">25k</button>
              <button class="cv2-pill" onclick="cv2SetKm(30000)">30k</button>
            </div>
          </div>

          <!-- Mantenimiento -->
          <div style="margin-top:16px;" id="cv2-field-mant">
            <div class="cv2-flbl">
              Mantenimiento VWFS
              <span id="cv2-disp-mant" style="font-size:12px;color:#F59E0B;font-weight:700;letter-spacing:0;text-transform:none;"></span>
            </div>
            <div id="cv2-cupra-tipo-wrap" style="display:none;margin-bottom:10px;">
              <div style="font-size:10px;letter-spacing:1px;text-transform:uppercase;color:rgba(240,244,255,0.35);margin-bottom:6px;">Tipo motor CUPRA</div>
              <div class="cv2-pills" id="cv2-pills-cupra-tipo">
                <button class="cv2-pill active" id="cv2-ct-termico" onclick="cv2SetCupraTipo('TERMICO')">Térmico / Híbrido</button>
                <button class="cv2-pill" id="cv2-ct-electrico" onclick="cv2SetCupraTipo('ELECTRICO')">Eléctrico</button>
              </div>
            </div>
            <div class="cv2-mant-badge" id="cv2-mant-badge">
              ✓ 2 años / 40.000 km incluidos gratis (APPROVED) + Coche de sustitución
            </div>
            <div class="cv2-pills" id="cv2-pills-mant">
              <button class="cv2-pill active" id="cv2-mt-0" onclick="cv2SetMant(0)">Sin mant.</button>
              <button class="cv2-pill" id="cv2-mt-2" onclick="cv2SetMant(2)">2 años</button>
              <button class="cv2-pill" id="cv2-mt-4" onclick="cv2SetMant(4)">4 años</button>
            </div>
            <div class="cv2-mant-info" id="cv2-mant-info"></div>
            <div class="cv2-mant-unavail" id="cv2-mant-unavail">⚠ Mantenimiento no disponible para VU o marcas ajenas al grupo</div>
          </div>
        </div>

        <!-- Info chips -->
        <div class="cv2-info-chips">
          <span class="cv2-chip" id="cv2-chip-cat" style="display:none"></span>
          <span class="cv2-chip green" id="cv2-chip-camp"></span>
          <span class="cv2-chip red" id="cv2-chip-tin"></span>
        </div>

        <!-- Credit warning -->
        <div class="cv2-credit-warn" id="cv2-credit-warn"></div>

        <!-- Cuota hero -->
        <div class="cv2-cuota-hero">
          <div class="cv2-cuota-lbl" id="cv2-cuota-lbl">Cuota mensual estimada</div>
          <div>
            <span class="cv2-cuota-val" id="cv2-cuota-val">—</span>
            <span class="cv2-cuota-unit">€ / mes</span>
          </div>
          <div class="cv2-cuota-final" id="cv2-cuota-final">
            <span class="cv2-cf-lbl" id="cv2-cf-lbl">Cuota final</span>
            <span class="cv2-cf-val" id="cv2-cf-val">—</span>
          </div>
        </div>

        <!-- Breakdown -->
        <div class="cv2-breakdown">
          <div class="cv2-br-row">
            <span class="cv2-br-lbl">Precio al contado</span>
            <span class="cv2-br-val" id="cv2-br-precio">—</span>
          </div>
          <div class="cv2-br-row bonif hidden" id="cv2-br-bonif-row">
            <span class="cv2-br-lbl">Bonificación VWFS</span>
            <span class="cv2-br-val" id="cv2-br-bonif">—</span>
          </div>
          <div class="cv2-br-row">
            <span class="cv2-br-lbl">Entrada inicial</span>
            <span class="cv2-br-val" id="cv2-br-entrada">—</span>
          </div>
          <div class="cv2-br-row">
            <span class="cv2-br-lbl">T.I.N.</span>
            <span class="cv2-br-val" id="cv2-br-tin">—</span>
          </div>
          <div class="cv2-br-row">
            <span class="cv2-br-lbl">Nº de cuotas</span>
            <span class="cv2-br-val" id="cv2-br-ncuotas">—</span>
          </div>
          <div class="cv2-br-row mant hidden" id="cv2-br-mant-row">
            <span class="cv2-br-lbl" id="cv2-br-mant-lbl">Mantenimiento</span>
            <span class="cv2-br-val" id="cv2-br-mant-v">—</span>
          </div>
          <div class="cv2-br-row total">
            <span class="cv2-br-lbl">Precio total a plazos</span>
            <span class="cv2-br-val" id="cv2-br-total">—</span>
          </div>
        </div>

        <!-- CTA -->
        <div class="cv2-cta">
          <a class="cv2-btn-wa" id="cv2-btn-wa" href="#" target="_blank" rel="noopener">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
            Solicitar financiación · WhatsApp
          </a>
          <div class="cv2-legal" id="cv2-legal"></div>
        </div>
      </div>
      <div class="modal-cta">
        <a class="btn-cta" id="m-link" href="#" target="_blank" rel="noopener">
          Ver ficha completa en Das WeltAuto
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
        </a>
      </div>
    </div>
  </div>
</div>

<footer>
  <p>
    <strong>Automóviles Rueda</strong> · {COMERCIAL_NOMBRE} ·
    <a href="tel:{COMERCIAL_TELEFONO.replace(' ', '')}">{COMERCIAL_TELEFONO}</a> ·
    <a href="mailto:{COMERCIAL_EMAIL}">{COMERCIAL_EMAIL}</a>
  </p>
  <p style="margin-top:8px">
    <a href="https://www.dasweltauto.es/esp/concesionario-seat-automoviles-rueda" target="_blank" rel="noopener">Ver todos los coches en Das WeltAuto ↗</a>
  </p>
  <p style="margin-top:12px; font-size:11px; color:#9aa8c0;">
    * Cuotas orientativas calculadas con TIN 6,99%, 48 meses y sin entrada (VW Financial Services). Sujeto a aprobación financiera. Consulta condiciones exactas con {COMERCIAL_NOMBRE}.
  </p>
</footer>

<!-- Botón flotante WhatsApp (siempre visible, especialmente en móvil) -->
<a class="whatsapp-float"
   href="https://wa.me/34{COMERCIAL_TELEFONO.replace(' ','').replace('+34','')}?text=Hola%20Andr%C3%A9s%2C%20te%20escribo%20desde%20el%20cat%C3%A1logo%20de%20coches.%20Me%20interesa%20uno%20de%20los%20veh%C3%ADculos."
   target="_blank" rel="noopener" aria-label="Enviar WhatsApp a Andrés Vázquez">
  <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 0 1-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 0 1-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 0 1 2.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0 0 12.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 0 0 5.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 0 0-3.48-8.413z"/></svg>
  <span class="wa-label">WhatsApp</span>
</a>

<script>
const COCHES = {cars_js};

// "No disponible" se muestra como Reservado en toda la interfaz
function estadoLabel(estado) {{
  return estado === 'No disponible' ? 'Reservado' : estado;
}}
function fmtCuota(v) {{
  if (!v && v !== 0) return '';
  return Number(v).toLocaleString('es-ES', {{minimumFractionDigits: 2, maximumFractionDigits: 2}});
}}

function esReservado(estado) {{
  return estado === 'No disponible';
}}

// Normaliza texto eliminando tildes para búsqueda sin acentos
function norm(str) {{
  return (str || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
}}

let filtroActivo = 'todos';
let busqueda = '';
let ordenActivo = 'default';
let slideActual = 0;
let fotosModal = [];

const grid       = document.getElementById('grid');
const backdrop   = document.getElementById('modal-backdrop');
const slides     = document.getElementById('gallery-slides');
const dotsEl     = document.getElementById('gallery-dots');
const prevBtn    = document.getElementById('gallery-prev');
const nextBtn    = document.getElementById('gallery-next');
const closeBtn   = document.getElementById('modal-close');
const cntShowing = document.getElementById('cnt-showing');
const searchInput = document.getElementById('search');

function fuelIcon(c) {{
  return {{'Gasolina':'⛽','Diésel':'🛢️','Eléctrico':'⚡','Híbrido':'🔋','Mild Hybrid':'🔋','GNC':'💧'}}[c] || '⛽';
}}

function etiquetaSVG(e) {{
  const urls = {{
    'CERO': 'https://commons.wikimedia.org/wiki/Special:FilePath/DistAmbDGT_CeroEmisiones.svg',
    'ECO':  'https://commons.wikimedia.org/wiki/Special:FilePath/DistAmbDGT_ECO.svg',
    'C':    'https://commons.wikimedia.org/wiki/Special:FilePath/DistAmbDGT_C.svg',
  }};
  const url = urls[e];
  if (!url) return '';
  return `<img class="etiqueta-dgt" src="${{url}}" alt="Etiqueta ${{e}}" width="68" height="68" loading="lazy">`;
}}

function cardHTML(c) {{
  const reservado = esReservado(c.estado);
  const label = estadoLabel(c.estado);
  const badgeCls = reservado ? 'badge-reservado' : 'badge-disponible';

  // Foto principal = foto exterior de Das WeltAuto (siempre exterior)
  const mainFoto = c.foto_main || (c.fotos.length ? c.fotos[0] : null);
  const imgEl = mainFoto
    ? `<img src="${{mainFoto}}" alt="${{c.modelo}}" loading="lazy" onerror="this.onerror=null;this.src='${{c.fotos[0]||''}}';">`
    : `<div class="no-foto">Sin foto</div>`;

  const specs = [
    `${{fuelIcon(c.combustible)}} ${{c.combustible}}`,
    `🛣️ ${{c.km}} km`,
    `📅 ${{c.fecha}}`,
    c.cambio ? `⚙️ ${{c.cambio}}` : null,
    c.color  ? `🎨 ${{c.color}}` : null,
  ].filter(Boolean).map(s => `<span class="spec-pill">${{s}}</span>`).join('');

  return `
  <article class="card" data-n="${{c.n}}" tabindex="0" role="button">
    <div class="card-img">
      ${{imgEl}}
      <span class="badge-estado ${{badgeCls}}">${{label}}</span>
      ${{reservado ? '<div class="reservado-overlay"></div>' : ''}}
      ${{c.fotos.length > 1 ? `<span class="foto-count">📷 ${{c.fotos.length}}</span>` : ''}}
      ${{c.etiqueta ? etiquetaSVG(c.etiqueta) : ''}}
      ${{c.precio_anterior > 0 ? '<span class="oferta-badge">OFERTA</span>' : ''}}
    </div>
    <div class="card-body">
      <div>
        <div class="card-title">${{c.modelo}}</div>
        <div class="card-version">${{c.version}}</div>
      </div>
      <div class="card-specs">${{specs}}</div>
      <div class="card-footer">
        <div>
          ${{c.precio_anterior > 0 ? `
            <div class="card-price-drop">
              <span class="card-price-old">${{c.precio_anterior.toLocaleString('es-ES')}} €</span>
              <span class="price-drop-arrow">↓</span>
            </div>
            <div class="card-price card-price-new">${{c.precio.toLocaleString ? c.precio.toLocaleString('es-ES') : c.precio}}<span>€</span></div>
          ` : `<div class="card-price">${{c.precio}}<span>€</span></div>`}}
          ${{c.cuota ? `<div class="card-cuota">Desde <strong>${{fmtCuota(c.cuota)}} €/mes</strong>${{c.fin_tipo ? ` <span class="fin-tipo-badge">${{c.fin_tipo}}</span>` : ''}} *</div>` : ''}}
        </div>
        ${{c.url ? `<a class="btn-dwa" href="${{c.url}}" target="_blank" rel="noopener" onclick="event.stopPropagation()">DWA ↗</a>` : ''}}
      </div>
    </div>
  </article>`;
}}

function filtrar() {{
  const q = busqueda.toLowerCase();
  let lista = COCHES.filter(c => {{
    const matchFiltro =
      filtroActivo === 'todos' ||
      (filtroActivo === 'Disponible' && c.estado === 'Disponible') ||
      (filtroActivo === 'Reservado'  && esReservado(c.estado));
    const nq = norm(q);
    const matchSearch = !nq || norm(c.modelo).includes(nq) || norm(c.version).includes(nq);
    return matchFiltro && matchSearch;
  }});
  const kmNum = c => parseInt((c.km || '0').replace(/\./g, '').replace(/[^\d]/g, '')) || 0;
  if      (ordenActivo === 'precio-asc')  lista.sort((a,b) => a.precio - b.precio);
  else if (ordenActivo === 'precio-desc') lista.sort((a,b) => b.precio - a.precio);
  else if (ordenActivo === 'km-asc')      lista.sort((a,b) => kmNum(a) - kmNum(b));
  else if (ordenActivo === 'km-desc')     lista.sort((a,b) => kmNum(b) - kmNum(a));
  return lista;
}}

function render() {{
  const lista = filtrar();
  cntShowing.textContent = lista.length;
  if (!lista.length) {{
    grid.innerHTML = '<div class="empty-state"><div>🔍</div><p>No se encontraron vehículos.</p></div>';
    return;
  }}
  grid.innerHTML = lista.map(cardHTML).join('');
  grid.querySelectorAll('.card').forEach(card => {{
    card.addEventListener('click', () => abrirModal(+card.dataset.n));
    card.addEventListener('keydown', e => {{ if (e.key==='Enter'||e.key===' ') abrirModal(+card.dataset.n); }});
  }});
}}

document.querySelectorAll('.filter-btn').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    filtroActivo = btn.dataset.filter;
    render();
  }});
}});
searchInput.addEventListener('input', e => {{ busqueda = e.target.value; render(); }});
document.getElementById('sort-select').addEventListener('change', e => {{ ordenActivo = e.target.value; render(); }});

// ── Calculadora VWFS — Motor completo (portado de calculadora.html) ───────────

// Tabla VR% calibrada con datos reales DWA (63% para 60m/15k)
const VR_TABLE = {{
  24: {{10000:79,15000:75,20000:70,25000:65,30000:60}},
  36: {{10000:75,15000:71,20000:66,25000:61,30000:56}},
  48: {{10000:71,15000:67,20000:62,25000:57,30000:52}},
  60: {{10000:67,15000:63,20000:58,25000:53,30000:48}},
  72: {{10000:63,15000:59,20000:54,25000:49,30000:44}},
}};

// ── Estado CV2 ────────────────────────────────────────────────────────────────
const CV2 = {{
  precio:        0,
  entrada:       0,
  meses:         60,
  tab:           'lineal',    // 'lineal' | 'flex'
  km:            15000,
  marca:         'SEAT',      // 'SEAT' | 'CUPRA' | 'OTRA'
  matriculaMes:  null,
  matriculaAnio: null,
  campana:       'ENTRY',     // 'ENTRY' | 'GAMA' | 'APPROVED'
  tinOverride:   null,
  mantAnios:     0,
  cupraTipo:     'TERMICO',   // 'TERMICO' | 'ELECTRICO'
  modelo:        '',
}};

const CV2_ALL_PLAZOS = [24, 36, 48, 60, 72, 84, 96];

// ── Precios de mantenimiento VWFS ─────────────────────────────────────────────
const CV2_MANT = {{
  SEAT:                 {{ 2: 250,  4: 499, mandatory: false }},
  CUPRA_APPROVED:       {{ 2: 0,    4: 400, mandatory: true  }},
  CUPRA_GAMA_TERMICO:   {{ 2: 350,  4: 750, mandatory: true  }},
  CUPRA_GAMA_ELECTRICO: {{ 2: 100,  4: 450, mandatory: true  }},
}};

function cv2GetMantKey() {{
  const {{ marca, campana, cupraTipo }} = CV2;
  if (marca === 'SEAT')  return 'SEAT';
  if (marca === 'OTRA')  return null;
  if (campana === 'APPROVED') return 'CUPRA_APPROVED';
  return cupraTipo === 'ELECTRICO' ? 'CUPRA_GAMA_ELECTRICO' : 'CUPRA_GAMA_TERMICO';
}}

function cv2GetMantInfo() {{
  const {{ meses }} = CV2;
  const rules = cv2GetRules();
  const key   = cv2GetMantKey();
  const tbl   = key ? CV2_MANT[key] : null;
  const isVU  = rules.categoria === 'VU';
  const isAvail = !!tbl && !isVU;
  if (!isAvail) return {{ precioTotal:0, mensual:0, label:'', isAvail:false, mandatory:false, has4y:false, free:false, activeMeses:0 }};
  if (tbl.mandatory && CV2.mantAnios === 0) CV2.mantAnios = 2;
  const activeMeses = CV2.mantAnios > 0 ? CV2.mantAnios : 0;
  const precioTotal = activeMeses > 0 ? (tbl[activeMeses] ?? 0) : 0;
  const mensual     = activeMeses > 0 && meses > 0 ? Math.round(precioTotal / meses * 100) / 100 : 0;
  const kms         = activeMeses === 4 ? '60.000' : '40.000';
  const label       = activeMeses > 0 ? `Mantenimiento ${{activeMeses}} años / ${{kms}} km` : '';
  const free        = activeMeses > 0 && precioTotal === 0;
  const has4y       = tbl[4] !== null && tbl[4] !== undefined;
  return {{ precioTotal, mensual, label, isAvail:true, mandatory:tbl.mandatory, has4y, free, activeMeses, key }};
}}

// ── Formato números ───────────────────────────────────────────────────────────
const cv2Fmt  = n => Math.round(n).toLocaleString('es-ES');
const cv2Fmt2 = n => n.toLocaleString('es-ES', {{ minimumFractionDigits:2, maximumFractionDigits:2 }});

// ── Motor de reglas VWFS ──────────────────────────────────────────────────────
function cv2GetRules() {{
  const {{ marca, matriculaMes, matriculaAnio, tab, precio, entrada, campana }} = CV2;

  let antigMeses = null;
  if (matriculaMes && matriculaAnio && matriculaAnio >= 2000) {{
    const now = new Date();
    const diff = (now.getFullYear() - matriculaAnio) * 12 + (now.getMonth() + 1 - matriculaMes);
    antigMeses = Math.max(0, diff);
  }}

  const categoria = antigMeses === null ? null
    : antigMeses <= 24 ? 'VS'
    : antigMeses <= 60 ? 'VO' : 'VU';

  const producto   = tab === 'lineal' ? 'LINEAL' : 'FLEX';
  const importeNeto = Math.max(0, precio - entrada);
  const maxGlobal  = producto === 'FLEX' ? 120 : 144;

  let plazosDisp = [...CV2_ALL_PLAZOS];
  if (antigMeses !== null) {{
    plazosDisp = plazosDisp.filter(p => antigMeses + p <= maxGlobal);
  }}

  if (producto === 'FLEX') {{
    if (categoria === 'VU') {{
      plazosDisp = [];
    }} else {{
      plazosDisp = plazosDisp.filter(p => p <= 60);
    }}
  }} else {{
    if (categoria === 'VS') {{ plazosDisp = plazosDisp.filter(p => p <= 96); }}
    else if (categoria === 'VO') {{ plazosDisp = plazosDisp.filter(p => p <= 84); }}
    else if (categoria === 'VU') {{ plazosDisp = plazosDisp.filter(p => p <= 48); }}
  }}

  let creditoMinimo = 0, bonificacion = 0, tin_auto = 6.99, campanaLabel = '';

  if (marca === 'SEAT') {{
    if (campana === 'ENTRY' && categoria !== 'VU') {{
      tin_auto = 6.99; bonificacion = 0; creditoMinimo = 10000; campanaLabel = 'ENTRY · SEAT';
      if (producto === 'LINEAL') plazosDisp = plazosDisp.filter(p => p >= 48);
    }} else {{
      tin_auto = 8.99;
      if (categoria === 'VU') {{
        bonificacion = 400; creditoMinimo = 7000; campanaLabel = 'GAMA · SEAT · VU';
        plazosDisp = plazosDisp.filter(p => p <= 48);
      }} else if (categoria === 'VO') {{
        bonificacion = 750; creditoMinimo = producto === 'LINEAL' ? 9500 : 10000; campanaLabel = 'GAMA · SEAT · VO';
        if (producto === 'LINEAL') plazosDisp = plazosDisp.filter(p => p >= 60 && p <= 84);
      }} else {{
        bonificacion = 750; creditoMinimo = producto === 'LINEAL' ? 13000 : 10000;
        campanaLabel = categoria ? 'GAMA · SEAT · VS' : 'GAMA · SEAT';
        if (producto === 'LINEAL' && categoria === 'VS') plazosDisp = plazosDisp.filter(p => p >= 60 && p <= 96);
      }}
    }}
  }} else if (marca === 'CUPRA') {{
    if (campana === 'APPROVED' && (categoria === 'VS' || categoria === null)) {{
      tin_auto = 5.50; bonificacion = 0;
      creditoMinimo = producto === 'FLEX' ? 13500 : 10000; campanaLabel = 'APPROVED · CUPRA';
      if (producto === 'LINEAL') plazosDisp = plazosDisp.filter(p => p >= 36);
    }} else {{
      tin_auto = 8.99; bonificacion = 1800;
      creditoMinimo = producto === 'FLEX' ? 16500 : 13500;
      campanaLabel = categoria ? 'GAMA · CUPRA · ' + (categoria || '') : 'GAMA · CUPRA';
      if (producto === 'LINEAL') plazosDisp = plazosDisp.filter(p => p >= 48);
    }}
  }} else {{
    plazosDisp = plazosDisp.filter(p => p >= 48 && p <= 96);
    if (importeNeto >= 20000) {{ tin_auto = 8.99; bonificacion = 1200; creditoMinimo = 20000; campanaLabel = 'TOP · Otras Marcas'; }}
    else if (importeNeto >= 15000) {{ tin_auto = 8.99; bonificacion = 800;  creditoMinimo = 15000; campanaLabel = 'Premium · Otras Marcas'; }}
    else if (importeNeto >= 10000) {{ tin_auto = 8.99; bonificacion = 400;  creditoMinimo = 10000; campanaLabel = 'Entry · Otras Marcas'; }}
    else {{ tin_auto = 7.50; bonificacion = 0; creditoMinimo = 6000; campanaLabel = 'Básica · Otras Marcas'; }}
  }}

  const tinFinal = CV2.tinOverride !== null ? CV2.tinOverride : tin_auto;
  return {{ tinFinal, tin_auto, bonificacion, creditoMinimo, campanaLabel, plazosDisp, categoria, antigMeses }};
}}

// ── Cálculo cuota ─────────────────────────────────────────────────────────────
function cv2Calc() {{
  const {{ precio, entrada, meses, tab, km }} = CV2;
  const rules = cv2GetRules();
  const tin   = rules.tinFinal;
  const bonif = rules.bonificacion;
  const r = tin / 100 / 12;
  const rn = Math.pow(1 + r, meses);
  const precioEf = Math.max(0, precio - bonif);
  const neto     = Math.max(0, precioEf - entrada);
  const seg0     = precioEf * 0.061545;
  const seg      = precioEf > 0 ? Math.round(seg0 * Math.pow(neto / precioEf, 1.5) * 100) / 100 : 0;
  const base     = neto + seg;
  const capital  = Math.round(base * 1.035 * 100) / 100;
  const comision = Math.round((capital - base) * 100) / 100;
  let vr = 0, cuota = 0;
  if (tab === 'flex') {{
    const tbl = VR_TABLE[meses] || VR_TABLE[60];
    const pct = tbl[km] !== undefined ? tbl[km] : 46;
    vr = Math.round(precio * pct / 100);
    cuota = (rn > 1 && r > 0) ? (capital * r * rn - vr * r) / (rn - 1) : capital / meses;
  }} else {{
    cuota = (rn > 1 && r > 0) ? capital * r / (1 - 1 / rn) : capital / meses;
  }}
  cuota = Math.round(cuota * 100) / 100;
  const total = Math.round((cuota * meses + entrada + vr) * 100) / 100;
  return {{ seg, comision, capital, cuota, total, vr, bonif, precioEf, rules }};
}}

// ── Actualizar UI de campaña ──────────────────────────────────────────────────
function cv2UpdateCampanaUI() {{
  const {{ marca, campana }} = CV2;
  const rules = cv2GetRules();
  const cat   = rules.categoria;

  document.getElementById('cv2-camp-seat').style.display  = marca === 'SEAT'  ? 'flex' : 'none';
  document.getElementById('cv2-camp-cupra').style.display = marca === 'CUPRA' ? 'flex' : 'none';
  document.getElementById('cv2-camp-otra').style.display  = marca === 'OTRA'  ? 'block' : 'none';

  if (marca === 'SEAT') {{
    const entryBtn = document.getElementById('cv2-entry');
    const gamaBtn  = document.getElementById('cv2-gama-seat');
    const isVU     = cat === 'VU';
    entryBtn.disabled = isVU;
    if (isVU && campana === 'ENTRY') CV2.campana = 'GAMA';
    const ac = CV2.campana;
    entryBtn.classList.toggle('active', ac === 'ENTRY' && !isVU);
    gamaBtn.classList.toggle('active', ac === 'GAMA' || isVU);
  }}
  if (marca === 'CUPRA') {{
    const gamaBtn     = document.getElementById('cv2-gama-cupra');
    const approvedBtn = document.getElementById('cv2-approved');
    const canApproved = cat === 'VS' || cat === null;
    approvedBtn.disabled = !canApproved;
    if (!canApproved && campana === 'APPROVED') CV2.campana = 'GAMA';
    const ac = CV2.campana;
    gamaBtn.classList.toggle('active', ac === 'GAMA');
    approvedBtn.classList.toggle('active', ac === 'APPROVED' && canApproved);
  }}
  if (marca === 'OTRA') {{
    const r2 = cv2GetRules();
    document.getElementById('cv2-otra-label').textContent = r2.campanaLabel + ' · mín. ' + cv2Fmt(r2.creditoMinimo) + ' €';
  }}
}}

// ── Actualizar TIN display ────────────────────────────────────────────────────
function cv2UpdateTinUI(rules) {{
  const tinDisp = rules.tinFinal.toFixed(2).replace('.', ',');
  document.getElementById('cv2-tin-val').textContent = tinDisp;
  document.getElementById('cv2-tin-lbl').textContent = rules.campanaLabel;
  const inp = document.getElementById('cv2-tin-input');
  if (inp) inp.value = rules.tinFinal.toFixed(2);
}}

// ── Actualizar pills de plazo ─────────────────────────────────────────────────
function cv2UpdatePlazoPills(plazosDisp) {{
  CV2_ALL_PLAZOS.forEach(p => {{
    const el = document.getElementById('cv2-pl-' + p);
    if (!el) return;
    const avail = plazosDisp.includes(p);
    el.disabled = !avail;
    el.classList.toggle('active', CV2.meses === p);
    el.style.opacity = avail ? '' : '0.25';
    el.style.cursor  = avail ? '' : 'not-allowed';
    el.style.pointerEvents = avail ? '' : 'none';
  }});
  if (!plazosDisp.includes(CV2.meses) && plazosDisp.length > 0) {{
    const newMeses = plazosDisp[plazosDisp.length - 1];
    CV2.meses = newMeses;
    document.getElementById('cv2-disp-meses').textContent = newMeses + ' meses';
    CV2_ALL_PLAZOS.forEach(p => {{
      const el = document.getElementById('cv2-pl-' + p);
      if (el) el.classList.toggle('active', p === newMeses);
    }});
  }}
  // Note FLEX no disponible para VU
  const isVU = cv2GetRules().categoria === 'VU';
  const flexNote = document.getElementById('cv2-flex-note');
  if (flexNote) flexNote.classList.toggle('visible', CV2.tab === 'lineal' && isVU);
}}

// ── Render principal ──────────────────────────────────────────────────────────
function cv2Render() {{
  const {{ precio, entrada, meses, tab, km, marca, campana, mantAnios, cupraTipo }} = CV2;
  const res      = cv2Calc();
  const rules    = res.rules;
  const mantInfo = cv2GetMantInfo();
  const cuotaTotal = Math.round((res.cuota + mantInfo.mensual) * 100) / 100;

  cv2UpdateCampanaUI();
  cv2UpdateTinUI(rules);
  cv2UpdatePlazoPills(rules.plazosDisp);

  // FLEX tab disabled si VU
  const flexTab = document.getElementById('cv2-tab-flex');
  if (rules.categoria === 'VU') {{
    flexTab.disabled = true;
    if (tab === 'flex') {{
      CV2.tab = 'lineal';
      document.getElementById('cv2-tab-lineal').classList.add('active');
      flexTab.classList.remove('active');
      document.getElementById('cv2-field-km').style.display = 'none';
    }}
  }} else {{
    flexTab.disabled = false;
  }}

  // Categoria badge (car bar)
  const catEl = document.getElementById('cv2-cat-badge');
  if (rules.categoria) {{
    const catNames = {{ VS:'VS · '+rules.antigMeses+'m', VO:'VO · '+rules.antigMeses+'m', VU:'VU · '+rules.antigMeses+'m' }};
    catEl.textContent = catNames[rules.categoria];
    catEl.className   = 'cv2-cat-badge ' + rules.categoria.toLowerCase();
  }} else {{
    catEl.textContent = '';
    catEl.className   = 'cv2-cat-badge';
  }}

  // ── Mantenimiento UI ──────────────────────────────────────────────────────
  const mantKey  = cv2GetMantKey();
  const mantTbl  = mantKey ? CV2_MANT[mantKey] : null;
  const isVU     = rules.categoria === 'VU';
  const mantAvail = !!mantTbl && !isVU;

  if (!mantAvail) CV2.mantAnios = 0;

  const showCupraTipo = marca === 'CUPRA' && campana !== 'APPROVED';
  const cupraTipoWrap = document.getElementById('cv2-cupra-tipo-wrap');
  if (cupraTipoWrap) cupraTipoWrap.style.display = showCupraTipo ? 'block' : 'none';
  const ctTerm = document.getElementById('cv2-ct-termico');
  const ctElec = document.getElementById('cv2-ct-electrico');
  if (ctTerm) ctTerm.classList.toggle('active', cupraTipo === 'TERMICO');
  if (ctElec) ctElec.classList.toggle('active', cupraTipo === 'ELECTRICO');

  const isApprovedFixed = marca === 'CUPRA' && campana === 'APPROVED' && mantAvail;

  // APPROVED free badge
  const mantBadge = document.getElementById('cv2-mant-badge');
  if (mantBadge) mantBadge.classList.toggle('visible', isApprovedFixed && CV2.mantAnios === 2);

  if (!isApprovedFixed && mantAvail && mantTbl) {{
    const p0 = document.getElementById('cv2-mt-0');
    const p2 = document.getElementById('cv2-mt-2');
    const p4 = document.getElementById('cv2-mt-4');
    if (p2) {{ p2.style.display = ''; p2.textContent = mantTbl[2] === 0 ? '2 años · GRATIS' : `2 años · ${{cv2Fmt(mantTbl[2])}} €`; }}
    if (p4) {{ p4.textContent = mantTbl[4] != null ? `4 años · ${{cv2Fmt(mantTbl[4])}} €` : '4 años'; p4.disabled = mantTbl[4] == null; p4.style.opacity = p4.disabled ? '0.3' : ''; p4.style.pointerEvents = p4.disabled ? 'none' : ''; }}
    if (p0) p0.style.display = mantTbl.mandatory ? 'none' : '';
  }} else if (isApprovedFixed) {{
    const p0 = document.getElementById('cv2-mt-0');
    const p2 = document.getElementById('cv2-mt-2');
    const p4 = document.getElementById('cv2-mt-4');
    if (p2) p2.style.display = 'none';
    if (p0) p0.style.display = 'none';
    if (p4) {{ p4.textContent = `4 años · ${{cv2Fmt(CV2_MANT.CUPRA_APPROVED[4])}} € (ampliar)`; p4.disabled = false; p4.style.opacity = ''; p4.style.pointerEvents = ''; }}
  }}

  [0, 2, 4].forEach(v => {{
    const el2 = document.getElementById('cv2-mt-' + v);
    if (el2) el2.classList.toggle('active', v === CV2.mantAnios);
  }});

  const mantUnavail = document.getElementById('cv2-mant-unavail');
  if (mantUnavail) mantUnavail.classList.toggle('visible', !mantAvail);

  const mantInfoEl = document.getElementById('cv2-mant-info');
  const dispMant   = document.getElementById('cv2-disp-mant');
  if (!isApprovedFixed && mantInfo.precioTotal > 0) {{
    if (mantInfoEl) {{ mantInfoEl.classList.add('visible'); mantInfoEl.innerHTML = `<strong style="color:#F59E0B">${{cv2Fmt2(mantInfo.mensual)}} €/mes</strong> durante ${{CV2.meses}} meses · Total: ${{cv2Fmt2(mantInfo.precioTotal)}} €`; }}
    if (dispMant) dispMant.textContent = `+${{cv2Fmt2(mantInfo.mensual)}} €/mes`;
  }} else if (isApprovedFixed && CV2.mantAnios === 2) {{
    if (mantInfoEl) mantInfoEl.classList.remove('visible');
    if (dispMant) dispMant.textContent = '✓ 2 años gratis';
  }} else {{
    if (mantInfoEl) mantInfoEl.classList.remove('visible');
    if (dispMant) dispMant.textContent = '';
  }}

  // Cuota hero label
  const heroLbl = document.getElementById('cv2-cuota-lbl');
  if (heroLbl) heroLbl.textContent = mantInfo.mensual > 0 ? 'Cuota total (financiación + mantenimiento)' : 'Cuota mensual estimada';

  // Hero cuota (flash)
  const cuotaEl = document.getElementById('cv2-cuota-val');
  if (cuotaEl) {{ cuotaEl.classList.remove('cv2-updating'); void cuotaEl.offsetWidth; cuotaEl.textContent = cv2Fmt2(cuotaTotal); cuotaEl.classList.add('cv2-updating'); }}

  // Cuota final FLEX
  const cfRow = document.getElementById('cv2-cuota-final');
  if (cfRow) {{
    cfRow.classList.toggle('visible', tab === 'flex' && res.vr > 0);
    const cfLbl = document.getElementById('cv2-cf-lbl');
    const cfVal = document.getElementById('cv2-cf-val');
    if (cfLbl) cfLbl.textContent = 'Cuota final mes ' + CV2.meses;
    if (cfVal) cfVal.textContent = cv2Fmt2(res.vr) + ' €';
  }}

  // Info chips
  const chipCat  = document.getElementById('cv2-chip-cat');
  const chipCamp = document.getElementById('cv2-chip-camp');
  const chipTin  = document.getElementById('cv2-chip-tin');
  if (chipCat) {{
    if (rules.categoria) {{
      chipCat.textContent = rules.categoria + ' · ' + rules.antigMeses + 'm';
      chipCat.style.display = '';
      chipCat.className = 'cv2-chip ' + (rules.categoria === 'VS' ? 'green' : rules.categoria === 'VO' ? 'amber' : '');
    }} else {{
      chipCat.style.display = 'none';
    }}
  }}
  if (chipCamp) chipCamp.textContent = rules.campanaLabel;
  if (chipTin)  chipTin.textContent  = 'TIN ' + rules.tinFinal.toFixed(2).replace('.', ',') + '%';

  // Breakdown
  const gId = id => document.getElementById(id);
  if (gId('cv2-br-precio'))   gId('cv2-br-precio').textContent   = cv2Fmt(precio) + ' €';
  if (gId('cv2-br-entrada'))  gId('cv2-br-entrada').textContent  = cv2Fmt(entrada) + ' €';
  if (gId('cv2-br-tin'))      gId('cv2-br-tin').textContent      = rules.tinFinal.toFixed(2).replace('.', ',') + ' %';
  if (gId('cv2-br-ncuotas')) gId('cv2-br-ncuotas').textContent  = CV2.meses;
  const totalConMant = Math.round((res.total + mantInfo.precioTotal) * 100) / 100;
  if (gId('cv2-br-total'))    gId('cv2-br-total').textContent    = cv2Fmt2(totalConMant) + ' €';

  // Mant row
  const mantRow = gId('cv2-br-mant-row');
  if (mantRow) {{
    mantRow.classList.toggle('hidden', mantInfo.precioTotal <= 0);
    if (gId('cv2-br-mant-lbl')) gId('cv2-br-mant-lbl').textContent = mantInfo.label;
    if (gId('cv2-br-mant-v'))   gId('cv2-br-mant-v').textContent   = '+' + cv2Fmt2(mantInfo.mensual) + ' €/mes';
  }}

  // Bonif row
  const bonifRow = gId('cv2-br-bonif-row');
  if (bonifRow) {{
    bonifRow.classList.toggle('hidden', res.bonif <= 0);
    if (gId('cv2-br-bonif')) gId('cv2-br-bonif').textContent = '−' + cv2Fmt(res.bonif) + ' €';
  }}

  // Crédito mínimo warning
  const importeFinanciado = Math.max(0, res.precioEf - entrada);
  const warnEl = gId('cv2-credit-warn');
  if (warnEl) {{
    if (rules.creditoMinimo > 0 && importeFinanciado < rules.creditoMinimo) {{
      warnEl.classList.add('visible');
      warnEl.textContent = '⚠ Importe financiado (' + cv2Fmt(importeFinanciado) + ' €) inferior al mínimo de la campaña ' + rules.campanaLabel + ' (' + cv2Fmt(rules.creditoMinimo) + ' €). Consulta condiciones con Andrés.';
    }} else {{
      warnEl.classList.remove('visible');
    }}
  }}

  // Texto legal
  const modeStr2 = tab === 'lineal' ? 'francés' : 'francés con cuota final';
  let legalTxt = `Ejemplo de cuota a ${{CV2.meses}} meses: ${{cv2Fmt2(res.cuota)}} €`;
  if (tab === 'flex' && res.vr > 0) {{
    const anos = Math.round(CV2.meses / 12);
    legalTxt += `, y si lo deseas, al cabo de ${{anos}} año${{anos !== 1 ? 's' : ''}} podrás cambiarlo, devolverlo o quedártelo pagando una cuota final en el mes ${{CV2.meses}} de ${{cv2Fmt2(res.vr)}} € (calculada con ${{Math.round(km/1000)}}.000 km anuales)`;
  }}
  legalTxt += `. Campaña: ${{rules.campanaLabel}}. `;
  if (res.bonif > 0) legalTxt += `Bonificación VWFS: ${{cv2Fmt(res.bonif)}} €. `;
  legalTxt += `Entrada inicial: ${{cv2Fmt(entrada)}} €. Seguro de Protección Plus opcional y financiado: ${{cv2Fmt2(res.seg)}} €. Comisión de apertura financiada: ${{cv2Fmt2(res.comision)}} €. Importe total financiado: ${{cv2Fmt2(res.capital)}} €. TIN ${{rules.tinFinal.toFixed(2).replace('.', ',')}}\%. Precio total a plazos: ${{cv2Fmt2(res.total)}} €. Sistema de amortización ${{modeStr2}}. `;
  if (mantInfo.precioTotal > 0) {{
    legalTxt += `${{mantInfo.label}}: ${{cv2Fmt2(mantInfo.precioTotal)}} € (${{cv2Fmt2(mantInfo.mensual)}} €/mes dividido en ${{CV2.meses}} cuotas). Cuota total mensual incluyendo mantenimiento: ${{cv2Fmt2(cuotaTotal)}} €. `;
  }}
  legalTxt += `Condiciones exactas con Andrés · 610 02 90 56.`;
  const legalEl = gId('cv2-legal');
  if (legalEl) legalEl.textContent = legalTxt;

  // WhatsApp link
  cv2BuildWaLink(res, rules, mantInfo, cuotaTotal);
}}

// ── WhatsApp mensaje ──────────────────────────────────────────────────────────
function cv2BuildWaLink(res, rules, mantInfo, cuotaTotal) {{
  const {{ precio, entrada, marca, tab }} = CV2;
  const modeStr = tab === 'lineal' ? 'LINEAL' : 'FLEX';
  const modeloStr = CV2.modelo || 'el vehículo';
  let msg = `🚗 *Simulación Financiación — ${{modeloStr}}*\n`;
  msg += `━━━━━━━━━━━━━━━\n`;
  msg += `Marca: *${{marca}}*${{rules.categoria ? ' · ' + rules.categoria : ''}}\n`;
  msg += `Campaña: *${{rules.campanaLabel}}*\n`;
  msg += `Precio al contado: *${{cv2Fmt(precio)}} €*\n`;
  if (res.bonif > 0) msg += `Bonificación VWFS: *−${{cv2Fmt(res.bonif)}} €*\n`;
  msg += `Entrada inicial: *${{cv2Fmt(entrada)}} €*\n`;
  msg += `Modalidad: *${{modeStr}}*\n`;
  msg += `Plazo: *${{CV2.meses}} meses*\n`;
  msg += `TIN: *${{rules.tinFinal.toFixed(2).replace('.', ',')}}\%*\n`;
  msg += `Seguro Protección Plus: *${{cv2Fmt2(res.seg)}} €*\n`;
  msg += `Comisión apertura (3,5\%): *${{cv2Fmt2(res.comision)}} €*\n`;
  msg += `Importe financiado: *${{cv2Fmt2(res.capital)}} €*\n`;
  msg += `━━━━━━━━━━━━━━━\n`;
  msg += `📅 *Cuota financiación: ${{cv2Fmt2(res.cuota)}} €/mes*\n`;
  if (tab === 'flex' && res.vr > 0) msg += `🔑 Cuota final mes ${{CV2.meses}}: *${{cv2Fmt2(res.vr)}} €*\n`;
  if (mantInfo && mantInfo.precioTotal > 0) {{
    msg += `🔧 ${{mantInfo.label}}: *+${{cv2Fmt2(mantInfo.mensual)}} €/mes* (${{cv2Fmt2(mantInfo.precioTotal)}} € total)\n`;
    msg += `📅 *CUOTA TOTAL: ${{cv2Fmt2(cuotaTotal)}} €/mes*\n`;
  }}
  const totalConMant = Math.round(((res.total || 0) + (mantInfo ? mantInfo.precioTotal : 0)) * 100) / 100;
  msg += `💰 Total a plazos: *${{cv2Fmt2(totalConMant)}} €*\n`;
  msg += `━━━━━━━━━━━━━━━\n`;
  msg += `_Cálculo orientativo. Condiciones exactas con Andrés · 610 02 90 56_`;
  const waEl = document.getElementById('cv2-btn-wa');
  if (waEl) waEl.href = `https://wa.me/34610029056?text=${{encodeURIComponent(msg)}}`;
}}

// ── Handlers de usuario ───────────────────────────────────────────────────────
function cv2SetMode(m) {{
  if (m === 'flex') {{
    const rules = cv2GetRules();
    if (rules.categoria === 'VU') return;
    if (CV2.marca === 'OTRA') return;
  }}
  CV2.tab = m;
  document.getElementById('cv2-tab-lineal').classList.toggle('active', m === 'lineal');
  document.getElementById('cv2-tab-flex').classList.toggle('active', m === 'flex');
  document.getElementById('cv2-field-km').style.display = m === 'flex' ? 'block' : 'none';
  cv2Render();
}}

function cv2SetCampana(c) {{
  CV2.campana = c;
  CV2.tinOverride = null;
  if (CV2.marca === 'CUPRA') {{
    if (CV2.mantAnios === 0) CV2.mantAnios = 2;
    if (c === 'APPROVED' && CV2.mantAnios === 4) CV2.mantAnios = 2;
  }}
  const manualWrap = document.getElementById('cv2-tin-manual');
  if (manualWrap) manualWrap.classList.remove('visible');
  const tinBtn = document.getElementById('cv2-tin-btn');
  if (tinBtn) tinBtn.textContent = '✎ personalizar TIN';
  cv2Render();
}}

function cv2SetMeses(m) {{
  CV2.meses = m;
  CV2_ALL_PLAZOS.forEach(p => {{
    const el = document.getElementById('cv2-pl-' + p);
    if (el) el.classList.toggle('active', p === m);
  }});
  const dispMeses = document.getElementById('cv2-disp-meses');
  if (dispMeses) dispMeses.textContent = m + ' meses';
  cv2Render();
}}

function cv2SetKm(k) {{
  CV2.km = k;
  document.querySelectorAll('#cv2-pills-km .cv2-pill').forEach((el, i) => {{
    el.classList.toggle('active', [10000,15000,20000,25000,30000][i] === k);
  }});
  const dispKm = document.getElementById('cv2-disp-km');
  if (dispKm) dispKm.textContent = k.toLocaleString('es-ES') + ' km';
  cv2Render();
}}

function cv2SetMant(n) {{
  CV2.mantAnios = n;
  [0,2,4].forEach(v => {{
    const el = document.getElementById('cv2-mt-' + v);
    if (el) el.classList.toggle('active', v === n);
  }});
  cv2Render();
}}

function cv2SetCupraTipo(t) {{
  CV2.cupraTipo = t;
  cv2Render();
}}

function cv2SliderMove(val) {{
  const slider = document.getElementById('cv2-sl-entrada');
  const eur = parseInt(val) || 0;
  const max = parseInt(slider.max) || 1;
  const pct = max > 0 ? (eur / max * 100) : 0;
  slider.style.setProperty('--pct', pct + '\%');
  CV2.entrada = eur;
  const dispE = document.getElementById('cv2-disp-entrada');
  if (dispE) dispE.textContent = eur.toLocaleString('es-ES') + ' €';
  cv2Render();
}}

function cv2ToggleTin() {{
  const manualWrap = document.getElementById('cv2-tin-manual');
  const btn = document.getElementById('cv2-tin-btn');
  const restore = document.getElementById('cv2-tin-restore');
  if (manualWrap.classList.contains('visible')) {{
    manualWrap.classList.remove('visible');
    if (restore) restore.style.display = 'none';
    if (btn) btn.textContent = '✎ personalizar TIN';
    CV2.tinOverride = null;
    cv2Render();
  }} else {{
    manualWrap.classList.add('visible');
    if (restore) restore.style.display = '';
    if (btn) btn.textContent = '✕ cerrar personalización';
    const rules = cv2GetRules();
    const inp = document.getElementById('cv2-tin-input');
    if (inp) inp.value = rules.tin_auto.toFixed(2);
    CV2.tinOverride = rules.tin_auto;
    cv2Render();
  }}
}}

function cv2TinInput(val) {{
  const v = parseFloat(val);
  if (!isNaN(v) && v >= 0 && v <= 30) {{ CV2.tinOverride = v; cv2Render(); }}
}}

function cv2RestoreTin() {{
  CV2.tinOverride = null;
  const manualWrap = document.getElementById('cv2-tin-manual');
  const btn = document.getElementById('cv2-tin-btn');
  const restore = document.getElementById('cv2-tin-restore');
  if (manualWrap) manualWrap.classList.remove('visible');
  if (restore) restore.style.display = 'none';
  if (btn) btn.textContent = '✎ personalizar TIN';
  cv2Render();
}}

// ── Bootstrap por coche ───────────────────────────────────────────────────────
function initCalc(c) {{
  const precio = typeof c.precio === 'number' ? c.precio : (parseInt(String(c.precio||'0').replace(/[^\d]/g,''))||0);
  CV2.precio   = precio;
  CV2.entrada  = 0;
  CV2.km       = 15000;
  CV2.tab      = 'lineal';
  CV2.tinOverride = null;
  CV2.modelo   = ((c.modelo||'') + ' ' + (c.version||'')).trim();

  // Auto-detect marca
  const modeloStr = c.modelo || '';
  if (modeloStr.includes('CUPRA')) {{
    CV2.marca   = 'CUPRA';
    CV2.campana = 'GAMA';
    CV2.mantAnios = 2;
  }} else if (modeloStr.includes('SEAT')) {{
    CV2.marca   = 'SEAT';
    CV2.campana = 'ENTRY';
    CV2.mantAnios = 2;
  }} else {{
    CV2.marca   = 'OTRA';
    CV2.campana = 'GAMA';
    CV2.mantAnios = 0;
  }}

  // Auto-detect cupraTipo
  const comb = (c.combustible||'').toLowerCase();
  CV2.cupraTipo = /el[eé]ctric/.test(comb) ? 'ELECTRICO' : 'TERMICO';

  // Auto-detect fecha matrícula desde fin_fecha_iso ("YYYY-MM")
  CV2.matriculaMes  = null;
  CV2.matriculaAnio = null;
  if (c.fin_fecha_iso && c.fin_fecha_iso.includes('-')) {{
    const parts = c.fin_fecha_iso.split('-').map(Number);
    if (parts.length === 2 && parts[0] >= 2000) {{
      CV2.matriculaAnio = parts[0];
      CV2.matriculaMes  = parts[1];
    }}
  }}

  // Car bar
  const modeloEl = document.getElementById('cv2-modelo');
  const precioEl = document.getElementById('cv2-precio');
  if (modeloEl) modeloEl.textContent = c.modelo || '—';
  if (precioEl) precioEl.textContent = Number(precio).toLocaleString('es-ES') + ' €';

  // Slider entrada
  const slider = document.getElementById('cv2-sl-entrada');
  const maxEntrada = Math.max(0, Math.floor((precio - 10000) / 100) * 100);
  slider.min   = 0;
  slider.max   = maxEntrada;
  slider.step  = 100;
  slider.value = 0;
  slider.style.setProperty('--pct', '0\%');
  const dispE = document.getElementById('cv2-disp-entrada');
  if (dispE) dispE.textContent = '0 €';
  const maxLbl = document.getElementById('cv2-lbl-max');
  if (maxLbl) maxLbl.textContent = maxEntrada > 0 ? `máx. ${{Number(maxEntrada).toLocaleString('es-ES')}} €` : 'máx. — €';

  // Plazo por defecto: 60m si disponible
  const rules0 = cv2GetRules();
  const pd0    = rules0.plazosDisp;
  CV2.meses    = pd0.includes(60) ? 60 : pd0.includes(48) ? 48 : (pd0[pd0.length-1] || 60);
  const dispM  = document.getElementById('cv2-disp-meses');
  if (dispM) dispM.textContent = CV2.meses + ' meses';

  // km display
  const dispKm = document.getElementById('cv2-disp-km');
  if (dispKm) dispKm.textContent = '15.000 km';

  // FLEX tab: hide km row initially (lineal mode)
  const kmRow = document.getElementById('cv2-field-km');
  if (kmRow) kmRow.style.display = 'none';

  // Tab UI reset
  const tabLin = document.getElementById('cv2-tab-lineal');
  const tabFlex = document.getElementById('cv2-tab-flex');
  if (tabLin) {{ tabLin.classList.add('active'); }}
  if (tabFlex) {{ tabFlex.classList.remove('active'); tabFlex.disabled = false; }}

  // TIN manual reset
  const manualWrap = document.getElementById('cv2-tin-manual');
  const tinBtn     = document.getElementById('cv2-tin-btn');
  const tinRestore = document.getElementById('cv2-tin-restore');
  if (manualWrap) manualWrap.classList.remove('visible');
  if (tinBtn) tinBtn.textContent = '✎ personalizar TIN';
  if (tinRestore) tinRestore.style.display = 'none';

  cv2Render();
}}

function abrirModal(n) {{
  const c = COCHES.find(x => x.n === n);
  if (!c) return;
  // Galería: usa fotos locales; si no hay, usa la foto principal exterior
  fotosModal = c.fotos.length ? c.fotos : (c.foto_main ? [c.foto_main] : []);
  slideActual = 0;

  slides.innerHTML = fotosModal.length
    ? fotosModal.map((f,i) => `<div class="gallery-slide"><img src="${{f}}" alt="Foto ${{i+1}}" loading="lazy"></div>`).join('')
    : `<div class="gallery-slide" style="display:grid;place-items:center;color:var(--muted);width:100%;height:100%">Sin fotos</div>`;
  slides.style.transform = 'translateX(0)';

  dotsEl.innerHTML = fotosModal.length > 1
    ? fotosModal.map((_,i) => `<div class="gallery-dot ${{i===0?'active':''}}" data-i="${{i}}"></div>`).join('') : '';
  dotsEl.querySelectorAll('.gallery-dot').forEach(d =>
    d.addEventListener('click', () => goSlide(+d.dataset.i)));

  const showNav = fotosModal.length > 1;
  prevBtn.style.display = showNav ? '' : 'none';
  nextBtn.style.display = showNav ? '' : 'none';

  document.getElementById('m-modelo').textContent = c.modelo;
  document.getElementById('m-version').textContent = c.version;
  document.getElementById('m-precio').textContent = c.precio + ' €';
  document.getElementById('m-estado-pill').textContent = esReservado(c.estado) ? '🟠 Reservado' : '✅ Disponible';

  const specs = [
    ['Combustible', c.combustible],
    ['Kilómetros',  c.km + ' km'],
    ['Matrícula',   c.fecha],
    ['Cambio',      c.cambio],
    ['Color',       c.color],
    ['Ubicación',   c.ubicacion],
  ].filter(([,v]) => v);
  document.getElementById('m-specs').innerHTML = specs.map(([l,v]) =>
    `<div class="spec-item"><div class="spec-label">${{l}}</div><div class="spec-value">${{v}}</div></div>`).join('');

  const equip = c.equipamiento || [];
  const equipSection = document.getElementById('equip-section');
  if (equip.length) {{
    document.getElementById('m-equip').innerHTML = equip.map(e =>
      `<div class="equip-item"><span class="equip-check">✓</span><span>${{e}}</span></div>`).join('');
    equipSection.style.display = '';
  }} else {{
    equipSection.style.display = 'none';
  }}

  // Calculadora de financiación
  initCalc(c);

  const link = document.getElementById('m-link');
  if (c.url) {{ link.href = c.url; link.style.display = ''; }}
  else {{ link.style.display = 'none'; }}

  backdrop.classList.add('open');
  document.body.style.overflow = 'hidden';
  backdrop.scrollTop = 0;
}}

function cerrarModal() {{
  backdrop.classList.remove('open');
  document.body.style.overflow = '';
}}

function goSlide(i) {{
  if (!fotosModal.length) return;
  slideActual = (i + fotosModal.length) % fotosModal.length;
  slides.style.transform = `translateX(${{-slideActual * 100}}%)`;
  dotsEl.querySelectorAll('.gallery-dot').forEach((d,idx) =>
    d.classList.toggle('active', idx === slideActual));
}}

prevBtn.addEventListener('click', () => goSlide(slideActual - 1));
nextBtn.addEventListener('click', () => goSlide(slideActual + 1));
closeBtn.addEventListener('click', cerrarModal);
backdrop.addEventListener('click', e => {{ if (e.target === backdrop) cerrarModal(); }});
document.addEventListener('keydown', e => {{
  if (!backdrop.classList.contains('open')) return;
  if (e.key === 'Escape') cerrarModal();
  if (e.key === 'ArrowLeft')  goSlide(slideActual - 1);
  if (e.key === 'ArrowRight') goSlide(slideActual + 1);
}});

let touchStartX = 0;
slides.addEventListener('touchstart', e => {{ touchStartX = e.touches[0].clientX; }}, {{passive:true}});
slides.addEventListener('touchend', e => {{
  const dx = e.changedTouches[0].clientX - touchStartX;
  if (Math.abs(dx) > 50) goSlide(slideActual + (dx < 0 ? 1 : -1));
}});

render();
</script>
<script data-goatcounter="https://andresvazquez11.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
</body>
</html>"""

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not JSON_PATH.exists():
        print(f"❌  No se encontró {JSON_PATH}")
        sys.exit(1)

    coches = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    print(f"✅  {len(coches)} coches cargados de datos_coches.json")

    print("📸  Copiando fotos a web_fotos/ …")
    rutas = copiar_fotos(coches)
    total_fotos = sum(len(v) for v in rutas.values())
    print(f"    {total_fotos} fotos copiadas")

    print("🌐  Generando index.html …")
    html = build_html(coches, rutas)
    HTML_PATH.write_text(html, encoding="utf-8")
    print(f"    ✅  {HTML_PATH}")
    print()
    print("  Listo. Sube index.html y web_fotos/ a GitHub Pages para compartirlo.")

if __name__ == "__main__":
    main()
