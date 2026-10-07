"""Coches vendidos y página 404 "Este coche ya se ha vendido + similares".

Cuando un coche sale del catálogo, generar_web.py borra su ficha
(coches/{modelo}-{id}.html). Antes de borrarla, `registrar_desde_html` guarda
sus datos básicos en vendidos.json (clave = nombre del archivo sin .html), así
el enlace que el asesor mandó por WhatsApp sigue sirviendo:

GitHub Pages sirve /404.html para cualquier dirección que no existe. Esa página
(`build_404_html`) lleva dentro los coches disponibles y el registro de
vendidos y, según el enlace roto:
  · coche que sigue publicado con otra dirección → salta a su ficha;
  · coche vendido → "Este SEAT León … ya se ha vendido" + coches similares;
  · enlace antiguo por número (06-cupra-formentor.html) → coches de ese modelo;
  · cualquier otra cosa → "Página no encontrada" + coches destacados.
"""
import datetime
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent
VENDIDOS_JSON = BASE_DIR / "vendidos.json"
DIAS_CONSERVAR = 365

_RE_COCHE = re.compile(r"^const COCHE = (\{.*\});\s*$", re.M)


def cargar() -> dict:
    try:
        return json.loads(VENDIDOS_JSON.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def guardar(vendidos: dict) -> None:
    limite = (datetime.date.today() - datetime.timedelta(days=DIAS_CONSERVAR)).isoformat()
    vigentes = {k: v for k, v in vendidos.items() if v.get("baja", "9999") >= limite}
    VENDIDOS_JSON.write_text(json.dumps(vigentes, ensure_ascii=False, indent=1, sort_keys=True),
                             encoding="utf-8")


def datos_desde_html(texto: str) -> "dict | None":
    """Datos básicos del coche a partir del `const COCHE = {...};` de su ficha."""
    m = _RE_COCHE.search(texto)
    if not m:
        return None   # redirección antigua u otra página: nada que guardar
    try:
        c = json.loads(m.group(1))
    except ValueError:
        return None
    return {k: c.get(k, "") for k in ("modelo", "version", "precio", "km", "fecha", "combustible", "cambio")}


def registrar_desde_html(vendidos: dict, ficha: Path, baja: "str | None" = None) -> bool:
    """Apunta en `vendidos` el coche de esta ficha (si es una ficha de coche)."""
    try:
        datos = datos_desde_html(ficha.read_text(encoding="utf-8"))
    except OSError:
        return False
    if not datos or not datos.get("modelo"):
        return False
    datos["baja"] = baja or datetime.date.today().isoformat()
    vendidos[ficha.stem] = datos
    return True


def build_404_html(disponibles: list, vendidos: dict, asesores: dict) -> str:
    """disponibles: [{archivo, modelo, version, precio, km, fecha, combustible, foto}]
    asesores: {"": {nombre, telefono, telefono_wa}, "alejandro": {...}} (clave = carpeta)."""
    datos = json.dumps({"coches": disponibles, "vendidos": vendidos, "asesores": asesores},
                       ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return PLANTILLA.replace("__DATOS__", datos)


PLANTILLA = r'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex">
<title>Automóviles Rueda · Coches de ocasión</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@500;600;700&family=Work+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root { --ink:#14110f; --rojo:#C8232B; --fondo:#f2f1ed; --borde:#e2ded7; --gris:#6b645e; }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--fondo); color: var(--ink); font-family: 'Work Sans', Arial, sans-serif; }
  a { color: inherit; }
  .cab { background: var(--ink); border-bottom: 3px solid var(--rojo); padding: 14px 16px; }
  .cab a { color: #fff; text-decoration: none; font: 700 22px 'Oswald', sans-serif; text-transform: uppercase; letter-spacing: .5px; }
  .cab small { display: block; color: rgba(255,255,255,.6); font-size: 12px; margin-top: 2px; }
  .wrap { max-width: 980px; margin: 0 auto; padding: 22px 16px 60px; }
  .aviso { background: #fff; border: 1px solid var(--borde); border-left: 5px solid var(--rojo); border-radius: 12px; padding: 20px 20px 18px; }
  .etq { display: inline-block; background: var(--rojo); color: #fff; font: 700 12px 'Work Sans'; letter-spacing: 1.2px;
    text-transform: uppercase; padding: 4px 10px; border-radius: 6px; }
  h1 { font: 700 clamp(24px, 5vw, 34px)/1.1 'Oswald', sans-serif; text-transform: uppercase; margin: 10px 0 6px; }
  .det { color: var(--gris); font-size: 15px; line-height: 1.5; margin: 0; }
  .acc { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 16px; }
  .btn { display: inline-flex; align-items: center; gap: 8px; padding: 12px 16px; border-radius: 10px; font-weight: 700;
    font-size: 14px; text-decoration: none; letter-spacing: .3px; }
  .btn.wa { background: #25D366; color: #fff; }
  .btn.cat { background: var(--ink); color: #fff; }
  h2 { font: 600 20px 'Oswald', sans-serif; text-transform: uppercase; letter-spacing: .6px; margin: 30px 0 12px;
    border-bottom: 2px solid var(--rojo); padding-bottom: 6px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 14px; }
  .card { background: #fff; border: 1px solid var(--borde); border-radius: 12px; overflow: hidden; text-decoration: none;
    display: flex; flex-direction: column; transition: transform .15s ease, box-shadow .15s ease; }
  @media (hover: hover) { .card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(20,17,15,.12); } }
  .card img { width: 100%; aspect-ratio: 4 / 3; object-fit: cover; display: block; background: #e8e5df; }
  .card .cu { padding: 10px 12px 12px; display: flex; flex-direction: column; gap: 3px; flex: 1; }
  .card b { font: 700 17px 'Oswald', sans-serif; text-transform: uppercase; }
  .card .v { font-size: 12.5px; color: var(--gris); line-height: 1.35; }
  .card .pr { margin-top: auto; padding-top: 6px; display: flex; justify-content: space-between; align-items: baseline; }
  .card .pr span { font-size: 12.5px; color: var(--gris); }
  .card .pr strong { font: 700 20px 'Oswald', sans-serif; color: var(--rojo); }
  .vacio { color: var(--gris); }
</style>
</head>
<body>
<header class="cab"><a id="lnk-cab" href="/">Automóviles Rueda</a><small>Coches seminuevos SEAT · CUPRA · Das WeltAuto</small></header>
<main class="wrap">
  <section class="aviso" id="aviso"></section>
  <h2 id="tit-sim">Coches similares disponibles</h2>
  <div class="grid" id="similares"></div>
</main>
<script id="rd-datos" type="application/json">__DATOS__</script>
<script>
(function () {
  const D = JSON.parse(document.getElementById('rd-datos').textContent);
  const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const num = p => parseInt(String(p || '').replace(/\D/g, ''), 10) || 0;
  const marca = m => String(m || '').split(' ')[0].toLowerCase();
  const slugModelo = m => String(m || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

  // ¿Perfil de Alejandro? (/alejandro/coches/…) → sus enlaces y su WhatsApp
  const partes = location.pathname.split('/').filter(Boolean);
  const carpeta = partes[0] === 'alejandro' ? 'alejandro' : '';
  const base = carpeta ? '/' + carpeta : '';
  const asesor = D.asesores[carpeta] || D.asesores[''];
  document.getElementById('lnk-cab').href = base + '/';

  // Nombre del archivo pedido: …/coches/seat-leon-151336815.html → seat-leon-151336815
  const enCoches = partes.includes('coches');
  const archivo = enCoches ? decodeURIComponent(partes[partes.length - 1] || '').replace(/\.html?$/, '') : '';

  // 1) El coche sigue publicado (mismo número de anuncio, otro nombre) → a su ficha
  const idPedido = (archivo.match(/-((?:mf)?\d{6,})$/) || [])[1];
  if (idPedido) {
    const sigue = D.coches.find(c => c.archivo.replace(/\.html$/, '').endsWith('-' + idPedido));
    if (sigue) { location.replace(base + '/coches/' + sigue.archivo + location.search + location.hash); return; }
  }

  // 2) ¿Qué coche era?
  const vendido = D.vendidos[archivo] || null;
  const antiguo = /^\d{2}-/.test(archivo);                      // enlace viejo por número
  const modeloSlug = vendido ? slugModelo(vendido.modelo)
    : archivo.replace(/^\d{2}-/, '').replace(/-(?:mf)?\d{6,}$/, '');
  const ref = vendido || D.coches.find(c => slugModelo(c.modelo) === modeloSlug) || null;

  const aviso = document.getElementById('aviso');
  const textoWa = vendido
    ? `Hola ${asesor.nombre_corto}, vi que el ${vendido.modelo} ${vendido.version} ya se ha vendido. ¿Tenéis algo parecido?`
    : `Hola ${asesor.nombre_corto}, estoy buscando un coche. ¿Me ayudas?`;
  const botones = `<div class="acc">
      <a class="btn wa" href="https://wa.me/${esc(asesor.telefono_wa)}?text=${encodeURIComponent(textoWa)}" target="_blank" rel="noopener">Preguntar a ${esc(asesor.nombre_corto)} por WhatsApp</a>
      <a class="btn cat" href="${base}/">Ver todos los coches</a></div>`;
  if (vendido) {
    const det = [vendido.version, vendido.km ? vendido.km + ' km' : '', vendido.fecha, vendido.combustible].filter(Boolean).join(' · ');
    aviso.innerHTML = `<span class="etq">Vendido</span>
      <h1>${esc(vendido.modelo)} · ya se ha vendido</h1>
      <p class="det">${esc(det)}${vendido.precio ? ' · ' + esc(vendido.precio) + ' €' : ''}</p>
      <p class="det" style="margin-top:8px">Este coche ya tiene nuevo dueño, pero tenemos otros muy parecidos. Míralos aquí abajo o escríbenos y te buscamos uno a tu medida.</p>${botones}`;
  } else if (enCoches) {
    aviso.innerHTML = `<span class="etq">No disponible</span>
      <h1>Este coche ya no está disponible</h1>
      <p class="det">${antiguo ? 'Este enlace es de una versión anterior de la web. ' : ''}Probablemente ya se ha vendido, pero tenemos otros coches que te pueden interesar.</p>${botones}`;
  } else {
    aviso.innerHTML = `<span class="etq">404</span><h1>Página no encontrada</h1>
      <p class="det">La dirección no existe o ha cambiado. Estos son algunos de nuestros coches disponibles.</p>${botones}`;
    document.getElementById('tit-sim').textContent = 'Coches disponibles';
  }

  // 3) Similares: mismo modelo > misma marca, y precio parecido
  const precioRef = ref ? num(ref.precio) : 0;
  const puntos = c => {
    let p = 0;
    if (ref && slugModelo(c.modelo) === slugModelo(ref.modelo)) p += 100;
    else if (ref && marca(c.modelo) === marca(ref.modelo)) p += 40;
    if (ref && c.combustible && c.combustible === ref.combustible) p += 10;
    if (precioRef) p -= Math.min(60, Math.abs(num(c.precio) - precioRef) / precioRef * 100);
    return p;
  };
  const lista = D.coches.slice().sort((a, b) => puntos(b) - puntos(a)).slice(0, 6);
  document.getElementById('similares').innerHTML = lista.length ? lista.map(c => `
    <a class="card" href="${base}/coches/${esc(c.archivo)}">
      <img src="${esc(c.foto)}" alt="${esc(c.modelo)}" loading="lazy">
      <div class="cu"><b>${esc(c.modelo)}</b><span class="v">${esc(c.version)}</span>
        <div class="pr"><span>${esc([c.km ? c.km + ' km' : '', c.fecha].filter(Boolean).join(' · '))}</span><strong>${esc(c.precio)} €</strong></div></div>
    </a>`).join('') : '<p class="vacio">Ahora mismo no hay coches publicados. Escríbenos y te avisamos.</p>';
})();
</script>
</body>
</html>
'''
