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

  /* ── Calculadora de Financiación ── */
  .modal-financiacion {{
    background: #0d1b35;
    border-radius: 16px;
    padding: 22px 20px 18px;
    color: #f0f4ff;
    position: relative;
    overflow: hidden;
  }}
  .modal-financiacion::before {{
    content: '';
    position: absolute;
    top: -50px; right: -50px;
    width: 200px; height: 200px;
    background: radial-gradient(circle, rgba(200,35,43,0.16) 0%, transparent 70%);
    pointer-events: none;
  }}
  .calc-title {{
    font-size: 11px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1px; color: rgba(240,244,255,0.45); margin-bottom: 14px;
  }}
  /* Campaign badge — auto-selected, info-only */
  .calc-campaign-badge {{
    display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
    margin-bottom: 14px; min-height: 24px;
  }}
  .camp-badge {{
    display: inline-flex; align-items: center;
    background: rgba(200,35,43,0.18);
    border: 1px solid rgba(200,35,43,0.4);
    color: rgba(240,244,255,0.9);
    font-size: 11px; font-weight: 700; letter-spacing: 0.3px;
    padding: 4px 10px; border-radius: 20px;
    text-transform: uppercase;
  }}
  .camp-badge.camp-none {{
    background: rgba(255,255,255,0.07);
    border-color: rgba(255,255,255,0.12);
    color: rgba(240,244,255,0.4);
  }}
  .camp-cat {{
    font-size: 11px; color: rgba(240,244,255,0.35); font-weight: 600;
  }}
  .calc-chip.disabled {{
    opacity: 0.28; cursor: not-allowed;
    border-color: rgba(255,255,255,0.07);
    pointer-events: none;
  }}
  .calc-slider-label {{
    display: flex; justify-content: space-between; align-items: center;
    font-size: 12px; color: rgba(240,244,255,0.5); margin-bottom: 8px;
  }}
  .calc-slider-val {{ font-size: 15px; font-weight: 700; color: #fff; }}
  .calc-slider {{
    -webkit-appearance: none; appearance: none;
    width: 100%; height: 4px;
    background: linear-gradient(to right, #C8232B var(--pct,0%), rgba(255,255,255,0.14) var(--pct,0%));
    border-radius: 2px; outline: none; cursor: pointer;
    margin-bottom: 18px;
  }}
  .calc-slider::-webkit-slider-thumb {{
    -webkit-appearance: none;
    width: 20px; height: 20px;
    background: #C8232B;
    border: 3px solid #fff;
    border-radius: 50%;
    box-shadow: 0 2px 10px rgba(200,35,43,0.65);
    cursor: pointer;
    transition: transform 0.1s;
  }}
  .calc-slider::-webkit-slider-thumb:active {{ transform: scale(1.15); }}
  .calc-chips-label {{
    font-size: 11px; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.5px; color: rgba(240,244,255,0.4); margin-bottom: 8px;
  }}
  .calc-chips {{
    display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 16px;
  }}
  .calc-chip {{
    border: 1.5px solid rgba(255,255,255,0.14);
    background: rgba(255,255,255,0.05);
    color: rgba(240,244,255,0.6);
    font-family: inherit; font-size: 12px; font-weight: 700;
    padding: 5px 12px; border-radius: 20px;
    cursor: pointer; transition: all 0.18s ease;
    white-space: nowrap;
  }}
  .calc-chip.active {{
    background: rgba(200,35,43,0.18);
    border-color: #C8232B;
    color: #fff;
    box-shadow: 0 0 0 1px rgba(200,35,43,0.35);
  }}
  .calc-chip:hover:not(.active) {{
    border-color: rgba(255,255,255,0.32);
    color: #fff;
    background: rgba(255,255,255,0.09);
  }}
  .calc-km-row {{ display: none; }}
  .calc-km-row.visible {{ display: block; }}
  .calc-result {{
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 14px;
  }}
  .calc-result-row {{
    display: flex; justify-content: space-between; align-items: baseline;
    padding: 5px 0;
  }}
  .calc-result-row + .calc-result-row {{
    border-top: 1px solid rgba(255,255,255,0.06);
  }}
  .calc-result-lbl {{
    font-size: 12px; color: rgba(240,244,255,0.45);
  }}
  .calc-result-val {{
    font-size: 13px; font-weight: 600; color: rgba(240,244,255,0.85);
    font-variant-numeric: tabular-nums;
  }}
  /* Cuota featured (arriba, protagonista como DWA) */
  .calc-cuota-featured {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 14px 16px 14px;
    border-bottom: 1px solid rgba(200,35,43,0.35);
    margin-bottom: 4px;
  }}
  .calc-cuota-featured-lbl {{
    font-size: 11px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.8px; color: rgba(240,244,255,0.55);
  }}
  .calc-cuota-featured-val {{
    font-size: 30px; font-weight: 800; color: #C8232B;
    font-variant-numeric: tabular-nums;
    text-shadow: 0 0 24px rgba(200,35,43,0.45);
    line-height: 1;
  }}
  /* Desglose debajo */
  .calc-desglose {{ padding: 2px 0; }}
  .cr-total-row .calc-result-lbl {{ color: rgba(240,244,255,0.8); font-weight: 700; }}
  .cr-total-row .cr-total-val {{ color: #fff; font-size: 14px; font-weight: 700; }}
  .cr-vr-val {{ color: #f9c74f !important; font-weight: 700 !important; }}
  .btn-calc-cta {{
    display: flex; align-items: center; justify-content: center; gap: 8px;
    width: 100%;
    background: #25D366;
    color: #fff; font-family: inherit; font-size: 14px; font-weight: 700;
    padding: 13px 16px; border-radius: 11px; border: none; cursor: pointer;
    text-decoration: none;
    transition: background 0.2s, transform 0.12s;
    margin-bottom: 10px;
    box-sizing: border-box;
  }}
  .btn-calc-cta:hover {{ background: #1ebe59; transform: translateY(-1px); }}
  .btn-calc-cta:active {{ transform: translateY(0); }}
  .calc-legal {{
    font-size: 10px; color: rgba(240,244,255,0.3); line-height: 1.55;
    text-align: center;
  }}

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
        <div class="calc-title">💰 Calculadora de Financiación</div>
        <div id="calc-campaign-badge" class="calc-campaign-badge"></div>
        <div class="calc-slider-label">
          <span>Entrada <span id="calc-entrada-max-lbl" style="font-size:11px;opacity:0.55;font-weight:400"></span></span>
          <span class="calc-slider-val" id="calc-entrada-display">0 €</span>
        </div>
        <input type="range" class="calc-slider" id="calc-entrada-slider"
          min="0" max="0" step="100" value="0"
          oninput="calcSliderMove(this.value)">
        <div class="calc-chips-label">Plazo (meses)</div>
        <div class="calc-chips" id="calc-plazo-chips"></div>
        <div class="calc-km-row visible" id="calc-km-row">
          <div class="calc-chips-label">Km / año</div>
          <div class="calc-chips" id="calc-km-chips"></div>
        </div>
        <div class="calc-result">
          <!-- CUOTA MENSUAL — protagonista, igual que DWA -->
          <div class="calc-cuota-featured">
            <div class="calc-cuota-featured-lbl">Cuota mensual</div>
            <div class="calc-cuota-featured-val" id="cr-cuota">—</div>
          </div>
          <!-- Desglose — mismo orden y campos que Das WeltAuto -->
          <div class="calc-desglose">
            <div class="calc-result-row">
              <span class="calc-result-lbl">Precio al contado</span>
              <span class="calc-result-val" id="cr-precio">—</span>
            </div>
            <div class="calc-result-row">
              <span class="calc-result-lbl">Descuento por financiar</span>
              <span class="calc-result-val cr-muted">—</span>
            </div>
            <div class="calc-result-row">
              <span class="calc-result-lbl">Entrada inicial</span>
              <span class="calc-result-val" id="cr-entrada">—</span>
            </div>
            <div class="calc-result-row">
              <span class="calc-result-lbl">T.I.N.</span>
              <span class="calc-result-val" id="cr-tin">—</span>
            </div>
            <div class="calc-result-row">
              <span class="calc-result-lbl">T.A.E.</span>
              <span class="calc-result-val" id="cr-tae">—</span>
            </div>
            <div class="calc-result-row">
              <span class="calc-result-lbl">Nº de cuotas</span>
              <span class="calc-result-val" id="cr-ncuotas">—</span>
            </div>
            <div class="calc-result-row" id="cr-vr-row" style="display:none">
              <span class="calc-result-lbl" id="cr-vr-lbl">Cuota final mes N</span>
              <span class="calc-result-val cr-vr-val" id="cr-vr">—</span>
            </div>
            <div class="calc-result-row cr-total-row">
              <span class="calc-result-lbl">Precio total a plazos</span>
              <span class="calc-result-val cr-total-val" id="cr-total">—</span>
            </div>
          </div>
        </div>
        <a class="btn-calc-cta" id="calc-cta-link" href="#" target="_blank" rel="noopener">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
          Solicitar financiación con Andrés
        </a>
        <div class="calc-legal" id="calc-legal">* Cálculo orientativo. Condiciones exactas sujetas a aprobación de VW Financial Services.</div>
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

// ── Calculadora Auto-Campaña VWFS ────────────────────────────────────────────

// Tabla VR% calibrada con datos reales DWA (63% para 60m/15k)
const VR_TABLE = {{
  24: {{10000:79,15000:75,20000:70,25000:65,30000:60}},
  36: {{10000:75,15000:71,20000:66,25000:61,30000:56}},
  48: {{10000:71,15000:67,20000:62,25000:57,30000:52}},
  60: {{10000:67,15000:63,20000:58,25000:53,30000:48}},
  72: {{10000:63,15000:59,20000:54,25000:49,30000:44}},
}};

function parsePrecio(v) {{
  return typeof v === 'number' ? v : (parseInt(String(v||'0').replace(/[^\d]/g,''))||0);
}}

function computeAntiq(fechaIso) {{
  if (!fechaIso) return null;
  const parts = fechaIso.split('-').map(Number);
  if (parts.length < 2) return null;
  const [y, m] = parts;
  const now = new Date();
  return (now.getFullYear() - y) * 12 + (now.getMonth() + 1 - m);
}}

function getFinancingRulesAuto(marca, antigMeses, importeNeto, producto, campana) {{
  const cat = (antigMeses === null || antigMeses < 0) ? 'VS'
            : antigMeses <= 24 ? 'VS'
            : antigMeses <= 60 ? 'VO' : 'VU';
  const maxGlobal = producto === 'FLEX' ? 120 : 144;
  const mDesde = antigMeses !== null && antigMeses >= 0 ? antigMeses : 0;
  function fp(raw) {{ return raw.filter(p => mDesde + p <= maxGlobal); }}

  if (marca === 'SEAT') {{
    if (campana === 'ENTRY' && producto === 'FLEX' && (cat==='VS'||cat==='VO'))
      return {{tin:6.99,bonificacion:0,mesesDisponibles:fp([36,48,60]),creditoMinimo:10000,campanaLabel:'SEAT ENTRY · FLEX',categoria:cat}};
    if (campana === 'ENTRY' && producto === 'LINEAL' && (cat==='VS'||cat==='VO'))
      return {{tin:6.99,bonificacion:0,mesesDisponibles:fp([48,60,72,84,96]),creditoMinimo:10000,campanaLabel:'SEAT ENTRY · LINEAL',categoria:cat}};
    if (campana === 'GAMA' && producto === 'FLEX' && (cat==='VS'||cat==='VO'))
      return {{tin:8.99,bonificacion:750,mesesDisponibles:fp([36,48,60]),creditoMinimo:10000,campanaLabel:'SEAT GAMA · FLEX',categoria:cat}};
    if (campana === 'GAMA' && producto === 'LINEAL') {{
      if (cat==='VS') return {{tin:8.99,bonificacion:750,mesesDisponibles:fp([60,72,84,96]),creditoMinimo:13000,campanaLabel:'SEAT GAMA · LINEAL',categoria:cat}};
      if (cat==='VO') return {{tin:8.99,bonificacion:750,mesesDisponibles:fp([60,72,84]),creditoMinimo:9500,campanaLabel:'SEAT GAMA · LINEAL',categoria:cat}};
      if (cat==='VU') return {{tin:8.99,bonificacion:400,mesesDisponibles:fp([36,48]),creditoMinimo:7000,campanaLabel:'SEAT GAMA · LINEAL',categoria:cat}};
    }}
  }}
  if (marca === 'CUPRA') {{
    if (campana === 'APPROVED' && producto === 'FLEX' && cat==='VS')
      return {{tin:5.50,bonificacion:0,mesesDisponibles:fp([36,48,60]),creditoMinimo:13500,campanaLabel:'CUPRA APPROVED · FLEX',categoria:cat}};
    if (campana === 'APPROVED' && producto === 'LINEAL' && cat==='VS')
      return {{tin:5.50,bonificacion:0,mesesDisponibles:fp([36,48,60,72,84,96]),creditoMinimo:10000,campanaLabel:'CUPRA APPROVED · LINEAL',categoria:cat}};
    if (campana === 'GAMA' && producto === 'FLEX' && (cat==='VS'||cat==='VO'))
      return {{tin:8.99,bonificacion:1800,mesesDisponibles:fp([36,48,60]),creditoMinimo:16500,campanaLabel:'CUPRA GAMA · FLEX',categoria:cat}};
    if (campana === 'GAMA' && producto === 'LINEAL') {{
      if (cat==='VS') return {{tin:8.99,bonificacion:1800,mesesDisponibles:fp([48,60,72,84,96]),creditoMinimo:13500,campanaLabel:'CUPRA GAMA · LINEAL',categoria:cat}};
      if (cat==='VO') return {{tin:8.99,bonificacion:1400,mesesDisponibles:fp([48,60,72,84,96]),creditoMinimo:13500,campanaLabel:'CUPRA GAMA · LINEAL',categoria:cat}};
    }}
  }}
  if (marca === 'OTRA' && producto === 'LINEAL' && campana === 'OTRA') {{
    let tin, bonif;
    if      (importeNeto < 10000) {{ tin=7.50; bonif=0;    }}
    else if (importeNeto < 15000) {{ tin=8.99; bonif=400;  }}
    else if (importeNeto < 20000) {{ tin=8.99; bonif=800;  }}
    else                          {{ tin=8.99; bonif=1200; }}
    return {{tin,bonificacion:bonif,mesesDisponibles:fp([48,60,72,84,96]),creditoMinimo:6000,campanaLabel:'Financiación · LINEAL',categoria:cat}};
  }}
  return null;
}}

function calcCuotaAuto(precio, entrada, meses, km, tin, bonif, producto, seguroBase) {{
  const precioEf = precio - bonif;
  const r  = tin / 100 / 12;
  const rn = Math.pow(1 + r, meses);
  const neto = precioEf - entrada;
  const seg0 = seguroBase || Math.round(precio * 0.061545);
  const seg = precio > 0 ? Math.round(seg0 * Math.pow(Math.max(0,neto) / precio, 1.5) * 100) / 100 : seg0;
  const base = neto + seg;
  const capital  = Math.round(base * 1.035 * 100) / 100;
  const comision = Math.round((capital - base) * 100) / 100;
  let vr = 0, cuota = 0;
  if (producto === 'FLEX') {{
    const tbl = VR_TABLE[meses] || VR_TABLE[60];
    const pct = tbl[km] !== undefined ? tbl[km] : 63;
    vr = Math.round(precioEf * pct / 100);
    cuota = (rn > 1 && r > 0) ? (capital * r * rn - vr * r) / (rn - 1) : capital / meses;
  }} else {{
    cuota = (rn > 1 && r > 0) ? capital * r / (1 - 1/rn) : capital / meses;
  }}
  cuota = Math.round(cuota * 100) / 100;
  const total = Math.round((cuota * meses + entrada + vr) * 100) / 100;
  return {{ cuota, capital, comision, seg, vr, total, entrada }};
}}

function getBestOption(car, entrada, meses, km) {{
  const precio = parsePrecio(car.precio);
  const modelo = car.modelo || '';
  const marca = modelo.includes('CUPRA') ? 'CUPRA' : modelo.includes('SEAT') ? 'SEAT' : 'OTRA';
  const antigMeses = computeAntiq(car.fin_fecha_iso || '');
  const seguroBase = (car.fin_seguro && car.fin_seguro > 0) ? car.fin_seguro : Math.round(precio * 0.061545);
  const combos = marca === 'OTRA'
    ? [{{campana:'OTRA',    producto:'LINEAL'}}]
    : [
        {{campana:'APPROVED',producto:'FLEX'}},  {{campana:'APPROVED',producto:'LINEAL'}},
        {{campana:'ENTRY',   producto:'FLEX'}},  {{campana:'ENTRY',   producto:'LINEAL'}},
        {{campana:'GAMA',    producto:'FLEX'}},  {{campana:'GAMA',    producto:'LINEAL'}},
      ];
  let best = null;
  for (const {{campana, producto}} of combos) {{
    const rules = getFinancingRulesAuto(marca, antigMeses, precio - entrada, producto, campana);
    if (!rules) continue;
    if (!rules.mesesDisponibles.includes(meses)) continue;
    const impNeto = precio - rules.bonificacion - entrada;
    if (impNeto < rules.creditoMinimo) continue;
    const res = calcCuotaAuto(precio, entrada, meses, km, rules.tin, rules.bonificacion, producto, seguroBase);
    if (!best || res.cuota < best.cuota) {{
      best = {{ ...res, campana, producto, rules, tin: rules.tin, bonif: rules.bonificacion,
               marca, campanaLabel: rules.campanaLabel, categoria: rules.categoria }};
    }}
  }}
  return best;
}}

function getValidPlazos(car, entrada) {{
  const precio = parsePrecio(car.precio);
  const modelo = car.modelo || '';
  const marca = modelo.includes('CUPRA') ? 'CUPRA' : modelo.includes('SEAT') ? 'SEAT' : 'OTRA';
  const antigMeses = computeAntiq(car.fin_fecha_iso || '');
  const valid = new Set();
  const combos = marca === 'OTRA'
    ? [{{campana:'OTRA',    producto:'LINEAL'}}]
    : [
        {{campana:'APPROVED',producto:'FLEX'}},  {{campana:'APPROVED',producto:'LINEAL'}},
        {{campana:'ENTRY',   producto:'FLEX'}},  {{campana:'ENTRY',   producto:'LINEAL'}},
        {{campana:'GAMA',    producto:'FLEX'}},  {{campana:'GAMA',    producto:'LINEAL'}},
      ];
  for (const {{campana, producto}} of combos) {{
    const rules = getFinancingRulesAuto(marca, antigMeses, precio - entrada, producto, campana);
    if (!rules) continue;
    if ((precio - rules.bonificacion - entrada) < rules.creditoMinimo) continue;
    rules.mesesDisponibles.forEach(p => valid.add(p));
  }}
  // fallback si nada aplica: todos los plazos
  if (valid.size === 0) [36,48,60,72,84,96].forEach(p => valid.add(p));
  return valid;
}}

let calcState = {{ car: null, precio: 0, entrada: 0, meses: 60, km: 15000, best: null }};

function fmtEur(v) {{
  return Number(v).toLocaleString('es-ES', {{minimumFractionDigits:2,maximumFractionDigits:2}}) + ' €';
}}

function renderCalc() {{
  const s = calcState;
  if (!s.car) return;
  const best = getBestOption(s.car, s.entrada, s.meses, s.km);
  s.best = best;

  const badge = document.getElementById('calc-campaign-badge');
  if (!best) {{
    document.getElementById('cr-cuota').textContent    = 'Sin financiación disponible';
    document.getElementById('cr-precio').textContent   = '—';
    document.getElementById('cr-entrada').textContent  = '—';
    document.getElementById('cr-tin').textContent      = '—';
    document.getElementById('cr-tae').textContent      = '—';
    document.getElementById('cr-ncuotas').textContent  = s.meses;
    document.getElementById('cr-total').textContent    = '—';
    document.getElementById('cr-vr-row').style.display = 'none';
    if (badge) badge.innerHTML = '<span class="camp-badge camp-none">Sin campaña disponible para este plazo/entrada</span>';
    return;
  }}

  document.getElementById('cr-precio').textContent   = fmtEur(s.precio);
  document.getElementById('cr-entrada').textContent  = fmtEur(best.entrada);
  document.getElementById('cr-tin').textContent      = Number(best.tin).toFixed(2).replace('.',',') + ' %';
  document.getElementById('cr-tae').textContent      = '—';
  document.getElementById('cr-ncuotas').textContent  = s.meses;
  document.getElementById('cr-total').textContent    = fmtEur(best.total);
  document.getElementById('cr-cuota').textContent    = fmtEur(best.cuota) + '/mes';

  const vrRow = document.getElementById('cr-vr-row');
  if (best.producto === 'FLEX') {{
    vrRow.style.display = '';
    document.getElementById('cr-vr-lbl').textContent = `Cuota final mes ${{s.meses}}`;
    document.getElementById('cr-vr').textContent     = fmtEur(best.vr);
  }} else {{
    vrRow.style.display = 'none';
  }}

  // Badge campaña (info, el cliente no elige)
  if (badge) {{
    const bonifTxt = best.bonif > 0 ? ` · Dto. ${{best.bonif.toLocaleString('es-ES')}} €` : '';
    badge.innerHTML = `<span class="camp-badge">${{best.campanaLabel}}${{bonifTxt}}</span>`
      + `<span class="camp-cat">Vehículo ${{best.categoria || ''}}</span>`;
  }}

  // Texto legal dinámico
  const legal = document.getElementById('calc-legal');
  if (legal) {{
    const tinStr = Number(best.tin).toFixed(2).replace('.',',');
    legal.textContent = `Cálculo orientativo: ${{fmtEur(best.cuota)}}/mes · ${{s.meses}} meses · TIN ${{tinStr}}% · Entrada ${{fmtEur(best.entrada)}}. Sujeto a aprobación de VW Financial Services. Condiciones exactas con {COMERCIAL_NOMBRE} · {COMERCIAL_TELEFONO}.`;
  }}
}}

function calcSliderMove(val) {{
  const slider = document.getElementById('calc-entrada-slider');
  const max = parseInt(slider.max) || 1;
  const eur = parseInt(val) || 0;
  const pct = max > 0 ? (eur / max * 100) : 0;
  slider.style.setProperty('--pct', pct + '%');
  calcState.entrada = eur;
  document.getElementById('calc-entrada-display').textContent = eur.toLocaleString('es-ES') + ' €';
  // Actualizar pills según nueva entrada
  const valid = getValidPlazos(calcState.car, eur);
  updatePlazoPills(valid, calcState.meses);
  renderCalc();
}}

function calcChipMeses(m, el) {{
  calcState.meses = m;
  el.closest('.calc-chips').querySelectorAll('.calc-chip').forEach(c => c.classList.remove('active'));
  el.classList.add('active');
  renderCalc();
}}

function calcChipKm(k, el) {{
  calcState.km = k;
  el.closest('.calc-chips').querySelectorAll('.calc-chip').forEach(c => c.classList.remove('active'));
  el.classList.add('active');
  renderCalc();
}}

function updatePlazoPills(validSet, mesSel) {{
  const chips = document.getElementById('calc-plazo-chips');
  if (!chips) return;
  chips.querySelectorAll('.calc-chip').forEach(btn => {{
    const m = parseInt(btn.dataset.meses);
    const avail = validSet.has(m);
    btn.disabled = !avail;
    btn.classList.toggle('disabled', !avail);
    btn.classList.toggle('active', m === mesSel && avail);
  }});
  if (!validSet.has(mesSel)) {{
    const first = [36,48,60,72,84,96].find(p => validSet.has(p));
    if (first) {{
      calcState.meses = first;
      chips.querySelectorAll('.calc-chip').forEach(btn => {{
        btn.classList.toggle('active', parseInt(btn.dataset.meses) === first);
      }});
    }}
  }}
}}

function initCalc(c) {{
  calcState.car    = c;
  calcState.precio = parsePrecio(c.precio);
  calcState.entrada = 0;
  calcState.km     = 15000;

  // Plazo por defecto: 60m si disponible, si no el menor disponible
  const valid = getValidPlazos(c, 0);
  calcState.meses = valid.has(60) ? 60 : valid.has(48) ? 48 : ([36,48,60,72,84,96].find(p => valid.has(p)) || 60);

  // Slider entrada
  const slider = document.getElementById('calc-entrada-slider');
  const maxEntrada = Math.max(0, Math.floor((calcState.precio - 10000) / 100) * 100);
  slider.min   = 0;
  slider.max   = maxEntrada;
  slider.step  = 100;
  slider.value = 0;
  slider.style.setProperty('--pct', '0%');
  document.getElementById('calc-entrada-display').textContent = '0 €';
  const maxLbl = document.getElementById('calc-entrada-max-lbl');
  if (maxLbl) maxLbl.textContent = maxEntrada > 0 ? `(máx. ${{maxEntrada.toLocaleString('es-ES')}} €)` : '';

  // Plazo chips con data-meses
  const plazos = [36,48,60,72,84,96];
  document.getElementById('calc-plazo-chips').innerHTML = plazos.map(m =>
    `<button class="calc-chip ${{m===calcState.meses?'active':''}} ${{!valid.has(m)?'disabled':''}}"
      ${{!valid.has(m)?'disabled':''}} data-meses="${{m}}"
      onclick="calcChipMeses(${{m}},this)">${{m}}</button>`
  ).join('');

  // Km chips
  const kms = [10000,15000,20000,25000,30000];
  document.getElementById('calc-km-chips').innerHTML = kms.map(k =>
    `<button class="calc-chip ${{k===calcState.km?'active':''}}" onclick="calcChipKm(${{k}},this)">${{Math.round(k/1000)}}k</button>`
  ).join('');

  // Asegurar km row visible
  const kmRow = document.getElementById('calc-km-row');
  if (kmRow) kmRow.classList.add('visible');

  // WhatsApp CTA
  const modelo = ((c.modelo||'') + ' ' + (c.version||'')).trim();
  const preciof = calcState.precio.toLocaleString('es-ES');
  const msg = encodeURIComponent(`Hola Andrés, me interesa el ${{modelo}} (${{preciof}} €). ¿Podéis informarme sobre la financiación?`);
  document.getElementById('calc-cta-link').href = `https://wa.me/34610029056?text=${{msg}}`;

  renderCalc();
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
