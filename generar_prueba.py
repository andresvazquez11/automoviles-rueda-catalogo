#!/usr/bin/env python3
"""Genera una versión de PRUEBA del catálogo con el rediseño (hero con foto
de estilo de vida + parallax, hover de fotos exteriores, modo oscuro,
comparador) mientras reutiliza TAL CUAL — importando las funciones reales,
no copiándolas — el encabezado, buscador/filtro/orden, destacados, pie de
página y botón de WhatsApp que ya funcionan hoy en producción.

No toca generar_web.py ni ningún archivo de producción — solo LEE de ahí
(funciones + web_fotos/ + coches/ ya publicados) y escribe todo en prueba/,
aparte. Genera una página por asesor (Andrés en prueba/, Alejandro en
prueba/alejandro/), igual que hace generar_web.py en producción.
"""
import json
import shutil
import sys
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

from generar_web import (  # noqa: E402  (import tras sys.path.insert, a propósito)
    PERFILES, build_index_html,
    _cargar_cache_traducciones, traducir_coche,
)
from catalogo_rueda_v2 import _es_foto_exterior  # noqa: E402

JSON_PATH = BASE / "datos_coches.json"
WEB_FOTOS = BASE / "web_fotos"
OUT_DIR = BASE / "prueba"
HERO_SRC = Path("/tmp/mockup_assets/hero-ibiza.png")

MAX_FOTOS_TARJETA = 8


def cargar_coches_y_traducciones() -> tuple[list[dict], dict[int, dict]]:
    """Mismos coches que ve producción (todo menos 'Retirado'). Traducciones
    se toman de la caché ya generada por la corrida diaria real — no se
    llama a Gemini acá (client=None), así que esto no depende de tener
    GOOGLE_API_KEY configurada localmente."""
    todos = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    coches = [c for c in todos if c.get("estado") != "Retirado"]

    cache_trad = _cargar_cache_traducciones()
    traducciones = {car["n"]: traducir_coche(car, cache_trad, None) for car in coches}
    return coches, traducciones


def fotos_exteriores_web(n: int) -> list[str]:
    """Fotos YA publicadas en /web_fotos/{n}/ (no copia nada nuevo), filtradas
    a solo las que el mismo detector de portada/PDF considera 'exterior' —
    así el hover/nav de la tarjeta no cae en una foto del salpicadero."""
    carpeta = WEB_FOTOS / f"{n:02d}"
    if not carpeta.exists():
        return []
    todas = sorted(carpeta.glob("foto_*.jpg"))
    exteriores = [f for f in todas if _es_foto_exterior(f)]
    elegidas = exteriores[:MAX_FOTOS_TARJETA] if exteriores else todas[:1]
    return [f"/web_fotos/{n:02d}/{f.name}" for f in elegidas]


def construir_rutas(coches: list[dict]) -> dict[int, list[str]]:
    """rutas[n] = fotos exteriores, para los coches scrapeados de DWA.
    Los de fuente 'motorflash' no pasan por acá — build_index_html ya sabe
    resolver esos directo desde car['fotos']."""
    return {
        c["n"]: fotos_exteriores_web(c["n"])
        for c in coches
        if c.get("fuente") != "motorflash"
    }


def hero_html(total_disponible: int) -> str:
    return f'''
<div class="rd-hero">
  <div class="rd-hero-overlay"></div>
  <div class="rd-hero-copy">
    <div class="rd-hero-eyebrow">Seminuevos con garantía oficial</div>
    <h1>Encontrá tu<br>próximo coche</h1>
    <p>Seminuevos SEAT, CUPRA y Multimarca en Vélez-Málaga, revisados, con garantía oficial y financiación a medida.</p>
  </div>
  <div class="rd-hero-bar">
    <div class="rd-hero-count">{total_disponible} coches disponibles ahora</div>
    <a href="#rd-grid" class="rd-hero-cta">Ver catálogo completo</a>
  </div>
</div>
'''


EXTRA_CSS = '''
/* ── Añadidos de la página de prueba (no toca assets/estilos.css real) ── */
.rd-banner-prueba { background: #ffb020; color: #1a1400; text-align: center; font-size: 13px; font-weight: 700; padding: 8px 0; }

/* Las tarjetas (--rd-surface #fff) se perdían contra el fondo (--rd-bg
   #f2f1ed, casi el mismo blanco) — separamos más el fondo y reforzamos
   la sombra de las tarjetas. */
:root { --rd-bg: #e7e4db; }
.rd-card { box-shadow: 0 10px 26px rgba(20,17,15,0.14), 0 2px 8px rgba(20,17,15,0.08); }

.rd-dark-toggle { cursor: pointer; border: none; background: rgba(255,255,255,0.14); color: #fff; padding: 8px 14px; border-radius: 999px; font-family: var(--rd-font); font-size: 12.5px; font-weight: 600; white-space: nowrap; }

.rd-hero { position: relative; width: 100%; height: 560px; overflow: hidden;
  background-image: url(/prueba/assets/hero.jpg); background-size: cover; background-position: center 40%;
  background-attachment: fixed; }
.rd-hero-overlay { position: absolute; inset: 0;
  background: linear-gradient(100deg, rgba(0,0,0,.72) 0%, rgba(0,0,0,.45) 38%, rgba(0,0,0,.05) 62%, rgba(0,0,0,0) 78%); }
.rd-hero-copy { position: relative; z-index: 2; max-width: 600px; padding: 80px 0 0 48px; }
.rd-hero-eyebrow { color: var(--rd-red); font-family: var(--rd-display); font-weight: 600; font-size: 14px; letter-spacing: 3px; text-transform: uppercase; margin-bottom: 16px; }
.rd-hero h1 { margin: 0 0 18px 0; font-family: var(--rd-display); font-weight: 700; font-size: 58px; line-height: .98; letter-spacing: -1px; text-transform: uppercase; color: #fff; }
.rd-hero p { margin: 0; font-size: 17px; line-height: 1.5; color: #e8e8e8; max-width: 440px; }
.rd-hero-bar { position: absolute; z-index: 3; bottom: 32px; right: 48px; width: 260px;
  background: rgba(13,13,13,.55); backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
  border: 1px solid rgba(255,255,255,.18); border-radius: 16px; padding: 16px 18px; }
.rd-hero-count { font-size: 12.5px; color: #d9d9d9; margin-bottom: 12px; }
.rd-hero-cta { display: block; text-align: center; text-decoration: none; background: var(--rd-red); color: #fff; font-weight: 700; font-size: 14px; padding: 11px 0; border-radius: 10px; }

/* Modo oscuro: sobreescribe las mismas variables que ya usa todo estilos.css,
   así header, buscador, tarjetas, destacados y pie de página cambian juntos
   sin tener que repintar cada componente a mano. Única excepción: el header
   ya usa --rd-ink como FONDO (siempre oscuro), así que se fija aparte. */
body.rd-dark {
  --rd-bg: #0d0d0d;
  --rd-surface: #1a1a1a;
  --rd-ink: #f2f2f2;
  --rd-ink-soft: #c9c6c0;
  --rd-muted: #8f8b85;
  --rd-border: #2e2e2e;
}
body.rd-dark .rd-header { background: #14110f; }
body.rd-dark .rd-card { box-shadow: 0 10px 26px rgba(0,0,0,0.5), 0 2px 8px rgba(0,0,0,0.3); }

/* Comparador */
.rd-compare-btn { cursor: pointer; width: calc(100% - 28px); margin: 0 14px 14px 14px; background: transparent; color: var(--rd-ink); border: 1px solid var(--rd-border); border-radius: 10px; padding: 9px 0; font-family: var(--rd-font); font-size: 12.5px; font-weight: 600; }
.rd-compare-btn.activo { background: var(--rd-red); color: #fff; border-color: var(--rd-red); }

.rd-tray { display: none; position: fixed; z-index: 60; bottom: 24px; left: 50%; transform: translateX(-50%);
  background: #14110f; border-radius: 999px; padding: 10px 10px 10px 20px; align-items: center; gap: 14px;
  box-shadow: 0 20px 50px rgba(0,0,0,.35); }
.rd-tray-label { color: #cfcfcf; font-size: 13px; white-space: nowrap; }
.rd-tray-chips { display: flex; gap: 6px; }
.rd-tray-chip { background: #2a2622; color: #fff; font-size: 12px; padding: 6px 10px; border-radius: 999px; display: flex; align-items: center; gap: 6px; white-space: nowrap; }
.rd-tray-x { cursor: pointer; opacity: .6; }
.rd-tray-btn { background: var(--rd-red); color: #fff; border: none; border-radius: 999px; padding: 10px 18px; font-family: var(--rd-font); font-size: 13px; font-weight: 700; cursor: pointer; white-space: nowrap; }

.rd-overlay { display: none; position: fixed; inset: 0; z-index: 70; background: rgba(0,0,0,.6); align-items: center; justify-content: center; padding: 40px; }
.rd-overlay-panel { background: var(--rd-surface); color: var(--rd-ink); border-radius: 20px; max-width: 860px; width: 100%; max-height: 86vh; overflow: auto; padding: 28px; }
.rd-overlay-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.rd-overlay-title { font-family: var(--rd-display); font-weight: 700; font-size: 22px; text-transform: uppercase; }
.rd-overlay-close { background: none; border: none; font-size: 20px; cursor: pointer; color: var(--rd-ink); }
.rd-cmp-wrap { display: flex; align-items: flex-start; overflow-x: auto; }
.rd-cmp-col { width: 220px; flex-shrink: 0; border-left: 1px solid var(--rd-border); }
.rd-cmp-col:first-child { border-left: none; }
.rd-cmp-col img { width: 100%; height: 150px; object-fit: cover; display: block; border-radius: 10px 10px 0 0; }
.rd-cmp-col-body { padding: 12px 14px; }
.rd-cmp-modelo { font-family: var(--rd-display); font-weight: 700; font-size: 16px; text-transform: uppercase; }
.rd-cmp-version { font-size: 12px; color: var(--rd-ink-soft); margin: 2px 0 10px 0; }
.rd-cmp-precio { font-family: var(--rd-display); font-weight: 700; font-size: 20px; color: var(--rd-red); margin-bottom: 10px; }
.rd-cmp-pills { display: flex; flex-direction: column; gap: 5px; font-size: 12.5px; color: var(--rd-ink-soft); border-top: 1px solid var(--rd-border); padding-top: 10px; }
'''


EXTRA_JS = '''
// ── Añadidos de la página de prueba: hover de fotos, modo oscuro, comparador ──
(function() {
  // Hover: recorre las mismas fotos (ya filtradas a exteriores) que usan
  // las flechas ‹ › — reutiliza la clase "activa" que ya entienden.
  document.querySelectorAll('.rd-card-media').forEach((media) => {
    const imgs = [...media.querySelectorAll('.rd-card-photos img')];
    const dots = [...media.querySelectorAll('.rd-card-dot')];
    if (imgs.length < 2) return;
    const setZone = (zone) => {
      imgs.forEach((img, i) => img.classList.toggle('activa', i === zone));
      dots.forEach((d, i) => d.classList.toggle('activa', i === zone));
    };
    media.addEventListener('mousemove', (e) => {
      const rect = media.getBoundingClientRect();
      const ratio = (e.clientX - rect.left) / rect.width;
      setZone(Math.min(imgs.length - 1, Math.max(0, Math.floor(ratio * imgs.length))));
    });
    media.addEventListener('mouseleave', () => setZone(0));
  });

  // Modo oscuro
  const toggle = document.getElementById('rd-dark-toggle');
  const label = document.getElementById('rd-dark-label');
  toggle.addEventListener('click', () => {
    document.body.classList.toggle('rd-dark');
    label.textContent = document.body.classList.contains('rd-dark') ? '☀️ Modo claro' : '🌙 Modo oscuro';
  });

  // Comparador — trabaja directo sobre las tarjetas reales (data-id, data-precio,
  // y el texto que ya está en pantalla), sin una lista de datos aparte.
  let compareIds = new Set();
  const tray = document.getElementById('rd-tray');
  const overlay = document.getElementById('rd-overlay');
  const cmpCols = document.getElementById('rd-cmp-cols');

  function datosDeTarjeta(card) {
    const img = card.querySelector('.rd-card-photos img.activa') || card.querySelector('.rd-card-photos img');
    return {
      id: card.dataset.id,
      modelo: card.querySelector('.rd-card-modelo').textContent,
      version: card.querySelector('.rd-card-version').textContent,
      precio: card.querySelector('.rd-card-precio').textContent,
      pills: [...card.querySelectorAll('.rd-pill')].map((p) => p.textContent),
      foto: img ? img.src : '',
    };
  }

  function toggleCompare(card) {
    const id = card.dataset.id;
    const btn = card.querySelector('.rd-compare-btn');
    if (compareIds.has(id)) {
      compareIds.delete(id);
      btn.textContent = '+ Comparar';
      btn.classList.remove('activo');
    } else {
      if (compareIds.size >= 3) { alert('Máximo 3 coches para comparar'); return; }
      compareIds.add(id);
      btn.textContent = '✓ Comparando';
      btn.classList.add('activo');
    }
    renderTray();
  }

  function tarjetaConId(id) {
    return document.querySelector('.rd-card[data-id="' + id + '"]');
  }

  function renderTray() {
    if (compareIds.size === 0) { tray.style.display = 'none'; tray.innerHTML = ''; return; }
    tray.style.display = 'flex';
    const chips = [...compareIds].map((id) => {
      const card = tarjetaConId(id);
      const modelo = card ? card.querySelector('.rd-card-modelo').textContent : id;
      return '<span class="rd-tray-chip">' + modelo + ' <span data-id="' + id + '" class="rd-tray-x">✕</span></span>';
    }).join('');
    tray.innerHTML =
      '<span class="rd-tray-label">Comparando ' + compareIds.size + '</span>' +
      '<div class="rd-tray-chips">' + chips + '</div>' +
      '<button id="rd-tray-btn" class="rd-tray-btn">Ver comparación</button>';
    tray.querySelectorAll('.rd-tray-x').forEach((x) => x.addEventListener('click', (e) => {
      e.preventDefault();
      const card = tarjetaConId(e.target.dataset.id);
      if (card) toggleCompare(card); else { compareIds.delete(e.target.dataset.id); renderTray(); }
    }));
    document.getElementById('rd-tray-btn').addEventListener('click', () => {
      const datos = [...compareIds].map((id) => tarjetaConId(id)).filter(Boolean).map(datosDeTarjeta);
      cmpCols.innerHTML = datos.map((c) => (
        '<div class="rd-cmp-col">' +
          '<img src="' + c.foto + '">' +
          '<div class="rd-cmp-col-body">' +
            '<div class="rd-cmp-modelo">' + c.modelo + '</div>' +
            '<div class="rd-cmp-version">' + c.version + '</div>' +
            '<div class="rd-cmp-precio">' + c.precio + '</div>' +
            '<div class="rd-cmp-pills">' + c.pills.map((p) => '<span>' + p + '</span>').join('') + '</div>' +
          '</div>' +
        '</div>'
      )).join('');
      overlay.style.display = 'flex';
    });
  }

  document.getElementById('rd-overlay-close').addEventListener('click', () => { overlay.style.display = 'none'; });

  document.querySelectorAll('.rd-card').forEach((card) => {
    const btn = document.createElement('button');
    btn.className = 'rd-compare-btn';
    btn.type = 'button';
    btn.textContent = '+ Comparar';
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      toggleCompare(card);
    });
    card.querySelector('.rd-card-body').appendChild(btn);
  });
})();
'''


def inyectar_prueba(html_real: str, hero: str, ficha_prefix: str) -> str:
    """Toma el index.html REAL (ya armado por build_index_html) y le agrega
    encima: banner de prueba, botón de modo oscuro en el header real, el
    hero, y el CSS/JS extra — sin tocar nada de lo que ya funciona."""
    assert "</head>" in html_real and "</header>" in html_real and "</body>" in html_real, \
        "build_index_html cambió de forma — revisar los anclajes de inyectar_prueba()"

    html = html_real.replace(
        "</head>",
        f'<meta name="robots" content="noindex, nofollow">\n<style>{EXTRA_CSS}</style>\n</head>',
    )
    html = html.replace(
        "</header>",
        '  <button id="rd-dark-toggle" class="rd-dark-toggle"><span id="rd-dark-label">🌙 Modo oscuro</span></button>\n'
        "</header>\n" + hero,
    )
    comparador_html = '''
<div id="rd-tray" class="rd-tray"></div>
<div id="rd-overlay" class="rd-overlay">
  <div class="rd-overlay-panel">
    <div class="rd-overlay-head">
      <div class="rd-overlay-title">Comparar coches</div>
      <button id="rd-overlay-close" class="rd-overlay-close" type="button">✕</button>
    </div>
    <div class="rd-cmp-wrap">
      <div id="rd-cmp-cols" class="rd-cmp-cols"></div>
    </div>
  </div>
</div>
'''
    html = html.replace("</body>", f"{comparador_html}<script>{EXTRA_JS}</script>\n</body>")
    html = html.replace(
        "<body>",
        '<body>\n<div class="rd-banner-prueba">🧪 PÁGINA DE PRUEBA — rediseño en exploración, no es la versión en producción</div>',
        1,
    )

    # Los links a las fichas son relativos ("coches/NN-slug.html") porque en
    # producción viven al lado de index.html — acá la página vive un nivel
    # más adentro (prueba/ o prueba/alejandro/), así que se reescriben a la
    # ruta real absoluta para no crear un prueba/coches/ que no existe.
    html = html.replace('href="coches/', f'href="{ficha_prefix}coches/')
    return html


def main():
    coches, traducciones = cargar_coches_y_traducciones()
    print(f"Coches cargados para la página de prueba: {len(coches)}")

    rutas = construir_rutas(coches)
    total_disponible = sum(1 for c in coches if c["estado"] == "Disponible")

    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "assets").mkdir(exist_ok=True)
    if HERO_SRC.exists():
        shutil.copy(HERO_SRC, OUT_DIR / "assets" / "hero.jpg")
        print("Foto del hero copiada a prueba/assets/hero.jpg")
    else:
        print(f"⚠️  No se encontró {HERO_SRC} — el hero va a quedar sin foto de fondo.")

    for perfil in PERFILES:
        html_real = build_index_html(coches, rutas, perfil, traducciones)
        ficha_prefix = f"/{perfil['carpeta']}/" if perfil["carpeta"] else "/"
        html_prueba = inyectar_prueba(html_real, hero_html(total_disponible), ficha_prefix)

        out_dir = OUT_DIR / perfil["carpeta"] if perfil["carpeta"] else OUT_DIR
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(html_prueba, encoding="utf-8")
        print(f"✅ {out_dir / 'index.html'} generado para {perfil['nombre']} ({len(html_prueba)} caracteres)")


if __name__ == "__main__":
    main()
