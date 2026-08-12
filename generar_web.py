#!/usr/bin/env python3
"""
Automóviles Rueda — Generador de Catálogo Web
==============================================
Lee datos_coches.json, copia fotos a web_fotos/ y genera index.html
"""

import json, shutil, sys
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
  <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 0 1-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 0 1-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 0 1 2.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0 0 12.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 0 0 5.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 0 0-3.48-8.413z"/></svg>
  <span class="rd-wa-label">WhatsApp</span>
</a>
'''

def descargar_portada_dwa(url_relativa: str, destino: Path) -> bool:
    """Descarga solo la foto de portada (x01.jpg) directamente de DWA por la
    URL del anuncio — identidad segura (no depende de "n"). Sirve para coches
    reservados: DWA sigue mostrando su foto aunque ya no estén en venta."""
    foto_url = dwa_foto_url(url_relativa)
    if not foto_url:
        return False
    try:
        r = requests.get(foto_url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200 and len(r.content) > 20000:
            destino.write_bytes(r.content)
            return True
    except Exception:
        pass
    return False

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
        if coche.get("fuente") == "motorflash":
            # Los coches de MotorFlash no tienen carpeta en fotos/ (esa es solo
            # para lo scrapeado de DWA) — sus fotos ya están en web_fotos/{n:02d}/
            # puestas por integrar_motorflash.py, con su propio control de
            # identidad por motorflash_id. No tocar esa carpeta aquí.
            continue
        if n in rutas:
            print(f"  ⚠️  n={n} duplicado en la lista de coches activos — {coche['modelo']} "
                  f"pisaría las fotos de otro coche con el mismo número, se omite")
            continue
        carpeta = find_car_folder(coche["n"], coche["modelo"], coche.get("precio", ""))
        dest = WEB_FOTOS / f"{n:02d}"
        dest.mkdir(exist_ok=True)
        urls: list[str] = []
        fotos_src = sorted(carpeta.glob("foto_*.jpg")) if (carpeta and carpeta.exists()) else []
        if fotos_src:
            for i, foto in enumerate(fotos_src[:8], start=1):
                dst = dest / f"foto_{i:02d}.jpg"
                shutil.copy2(foto, dst)
                urls.append(f"web_fotos/{n:02d}/foto_{i:02d}.jpg")
        else:
            # No se encontró carpeta local con fotos para ESTE coche. IMPORTANTE:
            # "n" no es un identificador estable — casi todos los coches cambian de
            # número en cada actualización (ver investigación de redescarga de fotos),
            # así que web_fotos/{n:02d}/ puede contener las fotos de OTRO coche que
            # tuvo ese mismo número en una corrida anterior. Reusarlas "porque están
            # ahí" (como se hacía antes) mostraba fotos de un coche distinto — el
            # mismo error de fondo que catalogo_rueda_v2.py ya documenta evitar en
            # buscar_carpeta_coche(): "NO usar fallback por número solo". Aquí es
            # mejor no mostrar foto que mostrar la de otro coche.
            for _viejo in dest.glob("foto_*.jpg"):
                _viejo.unlink()
            # Último intento: DWA sigue publicando la foto de portada de coches
            # reservados aunque ya no estén a la venta — la bajamos directo por
            # la URL propia del anuncio (identidad segura, no por "n").
            if descargar_portada_dwa(coche.get("url", ""), dest / "foto_01.jpg"):
                urls = [f"web_fotos/{n:02d}/foto_01.jpg"]
                print(f"  📸 n={n} {coche['modelo']}: foto de portada recuperada de DWA")
            else:
                print(f"  ⛔ n={n} {coche['modelo']}: sin ninguna foto verificable — no se publica")
        rutas[n] = urls
    return rutas

# ── Generar HTML ─────────────────────────────────────────────────────────────

import re as _re

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
    """Cuota mensual estimada — TIN 7,5%, 48 meses, sin entrada (VW Financial Services)."""
    try:
        p = int(str(precio).replace(".", "").replace(",", "").split()[0])
    except Exception:
        return 0.0
    TIN, MESES = 0.075, 48
    r = TIN / 12
    return round(p * r * (1 + r) ** MESES / ((1 + r) ** MESES - 1), 2)

import re as _re_slug

def slug_coche(modelo: str) -> str:
    s = modelo.lower()
    for a, b in [('á','a'),('é','e'),('í','i'),('ó','o'),('ú','u'),('ñ','n')]:
        s = s.replace(a, b)
    s = _re_slug.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s

DOMINIO_WEB = "https://andresvazquez11.github.io/automoviles-rueda-catalogo"

CALCULADORA_CSS = '''/* Puente de variables: la calculadora (portada de generar_web.py) usa nombres
   de variable "cortos" (--surface, --text, --red, ...) definidos originalmente
   en el <style> del index.html antiguo. Este archivo solo carga assets/estilos.css,
   que expone las mismas variables con prefijo --rd-. Este bloque las alía para
   que el CSS pegado abajo (verbatim) resuelva a la misma paleta sin modificar
   ni una línea de ese CSS. */
:root {
  --surface: var(--rd-surface);
  --surface2: var(--rd-bg);
  --border: var(--rd-border);
  --text: var(--rd-ink);
  --muted: var(--rd-muted);
  --red: var(--rd-red);
  --red-dark: var(--rd-red-dark);
  --green: var(--rd-green);
}

  /* ── Calculadora de Financiación v2 (full port) ── */
  .modal-financiacion {
    background: #0d1120;
    border-top: 2px solid rgba(200,35,43,0.3);
    color: #f0f4ff;
    overflow: hidden;
  }
  /* Car info bar */
  .cv2-car-bar {
    padding: 14px 20px 12px;
    border-bottom: 1px solid rgba(255,255,255,0.07);
    display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;
  }
  .cv2-car-modelo { font-weight: 700; font-size: 14px; color: #fff; line-height: 1.25; }
  .cv2-car-precio { font-size: 14px; font-weight: 800; color: #C8232B; font-variant-numeric: tabular-nums; }
  .cv2-cat-badge {
    display: inline-block; font-size: 10px; font-weight: 700;
    letter-spacing: 1px; padding: 3px 9px; border: 1px solid;
    vertical-align: middle;
  }
  .cv2-cat-badge.vs { color:#22C55E; border-color:#22C55E; background:rgba(34,197,94,.1); }
  .cv2-cat-badge.vo { color:#F59E0B; border-color:#F59E0B; background:rgba(245,158,11,.1); }
  .cv2-cat-badge.vu { color:rgba(240,244,255,.45); border-color:rgba(255,255,255,.2); background:rgba(255,255,255,.05); }
  /* Panel (inputs area) */
  .cv2-panel { padding: 16px 20px; border-bottom: 1px solid rgba(255,255,255,0.06); }
  /* Section label */
  .cv2-slbl {
    font-size: 10px; font-weight: 700; letter-spacing: 2.5px;
    text-transform: uppercase; color: #C8232B; margin-bottom: 10px;
    display: flex; align-items: center; gap: 8px;
  }
  .cv2-slbl::after { content:''; flex:1; height:1px; background:rgba(200,35,43,.2); }
  /* Mode tabs LINEAL / FLEX */
  .cv2-mode-tabs {
    display: grid; grid-template-columns: 1fr 1fr;
    border: 1px solid rgba(255,255,255,0.1); margin-bottom: 8px;
  }
  .cv2-mode-tab {
    background: transparent; border: none; cursor: pointer;
    padding: 10px 8px; font-family: inherit;
    font-size: 13px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;
    color: rgba(240,244,255,0.4); transition: all 0.15s; position: relative;
  }
  .cv2-mode-tab.active { background:rgba(200,35,43,.12); color:#C8232B; }
  .cv2-mode-tab.active::after {
    content:''; position:absolute; bottom:0; left:10%; right:10%; height:2px; background:#C8232B;
  }
  .cv2-mode-tab:hover:not(.active):not(:disabled) { color:#fff; background:rgba(255,255,255,.04); }
  .cv2-mode-tab:disabled { opacity:.3; cursor:not-allowed; }
  .cv2-flex-note { display:none; font-size:11px; color:#F59E0B; margin-bottom:8px; }
  .cv2-flex-note.visible { display:block; }
  /* Campaign pills */
  .cv2-camp-pills { display:flex; gap:6px; }
  .cv2-camp-pill {
    flex:1; text-align:center;
    background:transparent; border:1px solid rgba(255,255,255,.1);
    color:rgba(240,244,255,.45); cursor:pointer;
    font-family:inherit; font-size:12px; font-weight:700;
    padding:8px 10px; letter-spacing:.3px; transition:all .15s;
  }
  .cv2-camp-pill.active { background:rgba(34,197,94,.1); border-color:#22C55E; color:#22C55E; }
  .cv2-camp-pill:hover:not(.active):not(:disabled) { border-color:rgba(255,255,255,.25); color:#fff; }
  .cv2-camp-pill:disabled { opacity:.3; cursor:not-allowed; pointer-events:none; }
  .cv2-camp-auto {
    font-size:12px; color:rgba(240,244,255,.45);
    padding:8px 12px; border:1px solid rgba(255,255,255,.1); font-family:inherit;
  }
  /* TIN block */
  .cv2-tin-block {
    display:flex; align-items:center; gap:12px;
    border:1px solid rgba(255,255,255,.1); padding:10px 14px;
    background:rgba(34,197,94,.04); margin-bottom:4px;
  }
  .cv2-tin-val { font-size:24px; font-weight:800; color:#22C55E; line-height:1; font-variant-numeric:tabular-nums; }
  .cv2-tin-sfx { font-size:13px; color:rgba(240,244,255,.35); }
  .cv2-tin-lbl { flex:1; font-size:11px; color:rgba(240,244,255,.4); line-height:1.4; }
  .cv2-tin-link {
    background:none; border:none; cursor:pointer; font-family:inherit;
    font-size:11px; color:rgba(240,244,255,.28); text-decoration:underline; padding:0;
  }
  .cv2-tin-link:hover { color:#fff; }
  .cv2-tin-manual {
    display:none; border:1px solid #C8232B; padding:10px 14px;
    align-items:center; gap:8px; margin-bottom:4px;
  }
  .cv2-tin-manual.visible { display:flex; }
  .cv2-tin-manual input {
    background:transparent; border:none; outline:none;
    font-family:inherit; font-size:20px; font-weight:700;
    color:#fff; width:6ch; text-align:right; -moz-appearance:textfield;
  }
  .cv2-tin-manual input::-webkit-outer-spin-button,
  .cv2-tin-manual input::-webkit-inner-spin-button { -webkit-appearance:none; }
  .cv2-tin-restore {
    background:none; border:none; cursor:pointer; font-family:inherit;
    font-size:11px; color:#F59E0B; text-decoration:underline; padding:0; display:none;
  }
  /* Field label */
  .cv2-flbl {
    font-size:11px; font-weight:600; letter-spacing:1.5px; text-transform:uppercase;
    color:rgba(240,244,255,.35); margin-bottom:8px;
    display:flex; justify-content:space-between; align-items:center;
  }
  .cv2-flbl span { font-size:13px; font-weight:700; color:#fff; letter-spacing:0; text-transform:none; }
  /* Pills (plazo & km) */
  .cv2-pills { display:flex; gap:5px; flex-wrap:wrap; }
  .cv2-pill {
    background:transparent; border:1px solid rgba(255,255,255,.1);
    color:rgba(240,244,255,.45); cursor:pointer;
    font-family:inherit; font-size:12px; font-weight:700;
    padding:6px 10px; transition:all .15s;
    flex:1; min-width:0; text-align:center;
  }
  .cv2-pill.active { background:#C8232B; border-color:#C8232B; color:#fff; }
  .cv2-pill:hover:not(.active):not(:disabled) { border-color:rgba(255,255,255,.3); color:#fff; }
  .cv2-pill:disabled { opacity:.25; cursor:not-allowed; pointer-events:none; }
  /* Slider */
  .cv2-slider-row {
    display:flex; justify-content:space-between;
    font-size:11px; color:rgba(240,244,255,.3); margin-top:6px;
  }
  input[type=range].cv2-slider {
    -webkit-appearance:none; appearance:none;
    width:100%; height:4px; outline:none; cursor:pointer; border-radius:0;
    background:linear-gradient(90deg, #C8232B var(--pct,0%), rgba(255,255,255,.1) var(--pct,0%));
  }
  input[type=range].cv2-slider::-webkit-slider-thumb {
    -webkit-appearance:none;
    width:18px; height:18px; background:#C8232B;
    clip-path:polygon(50% 0%,100% 50%,50% 100%,0% 50%);
    cursor:pointer; border:none; transition:transform .1s;
  }
  input[type=range].cv2-slider::-webkit-slider-thumb:hover { transform:scale(1.3); }
  input[type=range].cv2-slider::-moz-range-thumb {
    width:18px; height:18px; background:#C8232B; border:none; border-radius:0; cursor:pointer;
  }
  /* Maintenance */
  .cv2-mant-badge {
    display:none; font-size:12px; font-weight:700; color:#22C55E;
    padding:6px 10px; border:1px solid rgba(34,197,94,.3);
    background:rgba(34,197,94,.08); letter-spacing:.3px; margin-bottom:8px;
  }
  .cv2-mant-badge.visible { display:block; }
  .cv2-mant-info {
    display:none; font-size:11px; color:rgba(240,244,255,.4);
    margin-top:8px; line-height:1.6;
    border-left:2px solid rgba(255,255,255,.1); padding-left:10px;
  }
  .cv2-mant-info.visible { display:block; }
  .cv2-mant-unavail {
    display:none; font-size:11px; color:rgba(240,244,255,.3); margin-top:6px;
  }
  .cv2-mant-unavail.visible { display:block; }
  /* Info chips row */
  .cv2-info-chips {
    padding:8px 20px; border-bottom:1px solid rgba(255,255,255,.06);
    display:flex; gap:6px; flex-wrap:wrap; align-items:center;
  }
  .cv2-chip {
    font-size:11px; font-weight:600; letter-spacing:.5px;
    padding:3px 9px; border:1px solid rgba(255,255,255,.12); color:rgba(240,244,255,.45);
  }
  .cv2-chip.green { color:#22C55E; border-color:rgba(34,197,94,.35); background:rgba(34,197,94,.08); }
  .cv2-chip.amber { color:#F59E0B; border-color:rgba(245,158,11,.35); background:rgba(245,158,11,.08); }
  .cv2-chip.red   { color:#C8232B; border-color:rgba(200,35,43,.35);  background:rgba(200,35,43,.08); }
  /* Credit warning */
  .cv2-credit-warn {
    display:none; margin:0 20px 8px; padding:10px 14px;
    background:rgba(245,158,11,.08); border:1px solid rgba(245,158,11,.3);
    font-size:12px; color:#F59E0B; line-height:1.5;
  }
  .cv2-credit-warn.visible { display:block; }
  /* Arona BB/REMA toggle */
  .cv2-arona-wrap { display:none; margin-top:10px; }
  .cv2-arona-wrap.visible { display:flex; align-items:center; gap:8px; }
  .cv2-arona-btn {
    display:inline-flex; align-items:center; gap:5px;
    padding:5px 10px; border-radius:4px; border:1px dashed rgba(34,197,94,.35);
    background:rgba(34,197,94,.05); color:rgba(240,244,255,.45);
    font-size:11px; font-weight:600; letter-spacing:.4px; cursor:pointer; transition:all .15s;
  }
  .cv2-arona-btn:hover { border-color:rgba(34,197,94,.6); color:rgba(240,244,255,.8); }
  .cv2-arona-btn.active { border-style:solid; border-color:#22C55E; background:rgba(34,197,94,.12); color:#22C55E; }
  .cv2-arona-lbl { font-size:10px; color:rgba(240,244,255,.28); }
  /* Cuota hero */
  .cv2-cuota-hero {
    padding:24px 20px 16px; text-align:center;
    background:linear-gradient(180deg,rgba(200,35,43,.07) 0%,transparent 100%);
    border-bottom:1px solid rgba(255,255,255,.06);
  }
  .cv2-cuota-lbl {
    font-size:10px; font-weight:600; letter-spacing:2.5px; text-transform:uppercase;
    color:rgba(240,244,255,.4); margin-bottom:8px;
  }
  .cv2-cuota-val {
    font-weight:800; font-size:clamp(36px,8vw,52px);
    color:#C8232B; line-height:1; letter-spacing:-1px;
    font-variant-numeric:tabular-nums; transition:opacity .15s;
  }
  .cv2-cuota-unit { font-size:17px; font-weight:400; color:rgba(240,244,255,.4); margin-left:4px; }
  .cv2-cuota-final {
    display:none; margin:10px auto 0; padding:7px 16px;
    background:rgba(245,158,11,.08); border:1px solid rgba(245,158,11,.2);
    max-width:260px; justify-content:space-between; align-items:center; gap:12px;
  }
  .cv2-cuota-final.visible { display:flex; }
  .cv2-cf-lbl { font-size:11px; color:#F59E0B; letter-spacing:.8px; }
  .cv2-cf-val { font-size:14px; font-weight:700; color:#F59E0B; font-variant-numeric:tabular-nums; }
  /* Breakdown */
  .cv2-breakdown { padding:0 20px 4px; }
  .cv2-br-row {
    display:flex; justify-content:space-between; align-items:center;
    padding:9px 0; border-bottom:1px solid rgba(255,255,255,.04); font-size:13px;
  }
  .cv2-br-row:last-child { border-bottom:none; }
  .cv2-br-lbl { color:rgba(240,244,255,.4); font-size:12px; }
  .cv2-br-val { font-weight:600; font-size:13px; color:rgba(240,244,255,.9); font-variant-numeric:tabular-nums; }
  .cv2-br-row.hidden { display:none; }
  .cv2-br-row.bonif .cv2-br-val { color:#22C55E; }
  .cv2-br-row.mant  .cv2-br-val { color:#F59E0B; }
  .cv2-br-row.total {
    background:rgba(200,35,43,.07); margin:6px -20px 0; padding:11px 20px; border-bottom:none;
  }
  .cv2-br-row.total .cv2-br-lbl { color:#fff; font-weight:700; }
  .cv2-br-row.total .cv2-br-val { font-size:15px; font-weight:700; }
  /* CTA */
  .cv2-cta { padding:16px 20px 20px; border-top:1px solid rgba(255,255,255,.07); display:flex; flex-direction:column; gap:10px; }
  .cv2-btn-wa {
    display:flex; align-items:center; justify-content:center; gap:9px;
    width:100%; padding:13px 16px; background:#25D366; color:#fff;
    font-family:inherit; font-size:13px; font-weight:700;
    letter-spacing:.5px; text-transform:uppercase;
    text-decoration:none; border:none; cursor:pointer;
    transition:background .2s, transform .12s;
  }
  .cv2-btn-wa:hover { background:#1ebe57; transform:translateY(-1px); }
  .cv2-legal { font-size:10px; color:rgba(240,244,255,.22); line-height:1.6; }

  .btn-dwa {
    background: none; border: 1px solid var(--border); color: var(--muted);
    font-family: inherit; font-size: 11px; font-weight: 600;
    padding: 6px 11px; border-radius: 7px; cursor: pointer;
    text-decoration: none; display: inline-flex; align-items: center; gap: 3px;
    transition: all 0.15s; white-space: nowrap;
  }
  .btn-dwa:hover { border-color: var(--red); color: var(--red); }
  .btn-mf { border-color: #E87722 !important; color: #E87722 !important; }
  .btn-mf:hover { border-color: #c45e0e !important; color: #c45e0e !important; }

  /* ── Modal ── */
  .modal-gallery { position: relative; aspect-ratio: 16/9; background: var(--surface2); overflow: hidden; }
  .gallery-slides { display: flex; transition: transform 0.35s cubic-bezier(0.4,0,0.2,1); height: 100%; }
  .gallery-slide  { min-width: 100%; height: 100%; }
  .gallery-slide img { width: 100%; height: 100%; object-fit: cover; }
  .gallery-btn {
    position: absolute; top: 50%; transform: translateY(-50%);
    background: rgba(255,255,255,0.85); border: none; color: var(--text);
    font-size: 20px; width: 38px; height: 38px; border-radius: 50%;
    cursor: pointer; display: grid; place-items: center;
    transition: background 0.15s; z-index: 2;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  }
  .gallery-btn:hover { background: var(--red); color: #fff; }
  .gallery-btn.prev { left: 12px; }
  .gallery-btn.next { right: 12px; }
  .gallery-dots {
    position: absolute; bottom: 12px; left: 50%; transform: translateX(-50%);
    display: flex; gap: 6px;
  }
  .gallery-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: rgba(255,255,255,0.5); cursor: pointer;
    transition: background 0.15s, transform 0.15s;
  }
  .gallery-dot.active { background: #fff; transform: scale(1.3); }

  .equip-section h3 {
    font-size: 13px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.5px; color: var(--muted); margin-bottom: 10px;
  }
  .equip-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 6px; }
  .equip-item { display: flex; align-items: flex-start; gap: 7px; font-size: 12px; color: #4a5568; line-height: 1.4; }
  .equip-check { color: var(--green); font-size: 13px; flex-shrink: 0; margin-top: 1px; }'''

CALCULADORA_HTML_INTERIOR = '''      <!-- Car info bar (auto-populated) -->
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
          <button class="cv2-camp-pill active" id="cv2-entry" onclick="cv2SetCampana('ENTRY')">ENTRY · 7,5%</button>
          <button class="cv2-camp-pill" id="cv2-gama-seat" onclick="cv2SetCampana('GAMA')">GAMA · 8,99%</button>
        </div>
        <div class="cv2-camp-pills" id="cv2-camp-cupra" style="display:none">
          <button class="cv2-camp-pill active" id="cv2-gama-cupra" onclick="cv2SetCampana('GAMA')">GAMA · 8,99%</button>
          <button class="cv2-camp-pill" id="cv2-approved" onclick="cv2SetCampana('APPROVED')">APPROVED · 5,95%</button>
        </div>
        <div id="cv2-camp-otra" style="display:none">
          <div class="cv2-camp-auto" id="cv2-otra-label">Automático según importe financiado</div>
        </div>

        <!-- Arona Buy Back / REMA (solo visible en Arona, activación manual) -->
        <div class="cv2-arona-wrap" id="cv2-arona-wrap">
          <button class="cv2-arona-btn" id="cv2-arona-btn" onclick="cv2ToggleAronaBB()">
            ⬡ ARONA BB/REMA
          </button>
          <span class="cv2-arona-lbl" id="cv2-arona-lbl">descuento especial inactivo</span>
        </div>

        <!-- TIN -->
        <div style="margin-top:14px;">
          <div class="cv2-tin-block">
            <div>
              <span class="cv2-tin-val" id="cv2-tin-val">7,5</span>
              <span class="cv2-tin-sfx"> % TIN</span>
            </div>
            <div class="cv2-tin-lbl" id="cv2-tin-lbl">ENTRY · SEAT</div>
          </div>
          <button class="cv2-tin-link" id="cv2-tin-btn" onclick="cv2ToggleTin()">✎ personalizar TIN</button>
          <div class="cv2-tin-manual" id="cv2-tin-manual">
            <input type="number" id="cv2-tin-input" value="7.5" min="0" max="30" step="0.01"
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
      </div>'''

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
{footer_whatsapp_html()}
</body>
</html>
'''


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
    # `fotos` la resuelve quien llama (ver Task 4): rutas.get(idx, []) para DWA,
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

    precio_num = int(str(car["precio"]).replace(".", "").replace(",", "").split()[0])
    km_num = int(str(car.get("km", "0")).replace(".", "").replace(",", "").split()[0] or 0)
    buscar_txt = f'{car["modelo"]} {car["version"]}'.lower()

    return f'''<a class="rd-card" href="{href}" data-precio="{precio_num}" data-km="{km_num}" data-estado="{estado_lbl}" data-buscar="{buscar_txt}">
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
    hist = _cargar_historial_precios()
    visibles = [c for c in cars if c.get("estado") != "Retirado"]
    total_disp = sum(1 for c in visibles if c["estado"] == "Disponible")
    total_res  = sum(1 for c in visibles if c["estado"] == "No disponible")
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

<div class="rd-grid" id="rd-grid">
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

// ── Buscador / filtro / orden — opera sobre las tarjetas ya generadas
// (enlaces reales), sin re-renderizar nada por JS. ──────────────────
(function() {{
  const grid = document.getElementById('rd-grid');
  const cards = [...grid.querySelectorAll('.rd-card')];
  const cntEl = document.getElementById('rd-cnt');
  const emptyMsg = document.createElement('div');
  emptyMsg.className = 'rd-empty-state';
  emptyMsg.innerHTML = '<div>🔍</div><p>No se encontraron vehículos.</p>';

  let filtro = 'todos';
  let busqueda = '';
  let orden = 'default';

  function norm(str) {{
    return (str || '').normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase();
  }}

  function aplicar() {{
    const q = norm(busqueda);
    let visibles = cards.filter(c => {{
      const matchFiltro = filtro === 'todos' || c.dataset.estado === filtro;
      const matchBusqueda = !q || norm(c.dataset.buscar).includes(q);
      return matchFiltro && matchBusqueda;
    }});

    if (orden === 'precio-asc')  visibles.sort((a,b) => +a.dataset.precio - +b.dataset.precio);
    if (orden === 'precio-desc') visibles.sort((a,b) => +b.dataset.precio - +a.dataset.precio);
    if (orden === 'km-asc')      visibles.sort((a,b) => +a.dataset.km - +b.dataset.km);
    if (orden === 'km-desc')     visibles.sort((a,b) => +b.dataset.km - +a.dataset.km);

    cards.forEach(c => c.style.display = 'none');
    visibles.forEach(c => {{ c.style.display = ''; grid.appendChild(c); }});

    if (emptyMsg.parentNode) emptyMsg.remove();
    if (!visibles.length) grid.appendChild(emptyMsg);

    cntEl.textContent = visibles.length;
  }}

  document.querySelectorAll('.rd-filter-btn').forEach(btn => {{
    btn.addEventListener('click', () => {{
      document.querySelectorAll('.rd-filter-btn').forEach(b => b.classList.remove('activo'));
      btn.classList.add('activo');
      filtro = btn.dataset.filter;
      aplicar();
    }});
  }});
  document.getElementById('rd-search').addEventListener('input', e => {{ busqueda = e.target.value; aplicar(); }});
  document.getElementById('rd-sort').addEventListener('change', e => {{ orden = e.target.value; aplicar(); }});
}})();
</script>
{footer_whatsapp_html()}
</body>
</html>
'''


# ── Main ─────────────────────────────────────────────────────────────────────

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
        tiene_foto = (c.get("fotos") if c.get("fuente") == "motorflash" else rutas.get(c["n"]))
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
    HTML_PATH.write_text(html_index, encoding="utf-8")
    print(f"  index.html regenerado con el catálogo nuevo")
    print()
    print("  Listo. Sube index.html, coches/ y web_fotos/ a GitHub Pages para compartirlo.")

if __name__ == "__main__":
    main()
