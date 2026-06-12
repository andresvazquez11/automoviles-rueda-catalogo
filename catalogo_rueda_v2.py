"""
Automóviles Rueda — Generador de Catálogo v2
=============================================
- Scraping dinámico del listado (siempre actualizado)
- Descarga de fotos reales
- Extracción de equipamiento por ficha
- PDF con 1 coche/página + sección de equipamiento
- 39 imágenes para redes sociales
"""

import asyncio, re, sys, json
from pathlib import Path
from io import BytesIO

# ── Dependencias ──────────────────────────────────────────
for pkg in ["playwright", "fpdf2", "pillow", "requests"]:
    try:
        __import__(pkg.replace("-","_").replace("2",""))
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

from playwright.async_api import async_playwright
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont
import requests

# ── Rutas ─────────────────────────────────────────────────
LISTING    = "https://www.dasweltauto.es/esp/concesionario-seat-automoviles-rueda"
OUTPUT_DIR = Path.home() / "Desktop" / "catalogo_automoviles_rueda"
PDF_PATH   = OUTPUT_DIR / "catalogo_automoviles_rueda.pdf"
PHOTOS_DIR = OUTPUT_DIR / "fotos"

CACHE_PATH = OUTPUT_DIR / "datos_coches.json"

for d in [OUTPUT_DIR, PHOTOS_DIR]:
    d.mkdir(exist_ok=True)

def nombre_carpeta(n: int, modelo: str, precio: str = "", estado: str = "Disponible") -> str:
    """Genera el nombre de carpeta: '01 - SEAT León - 18.900€' o '01 - SEAT León - 18.900€ · RESERVADO'"""
    base = f"{n:02d} - {modelo}"
    nombre = f"{base} - {precio}€" if precio else base
    if estado and estado != "Disponible":
        nombre += " · RESERVADO"
    return nombre

def buscar_carpeta_coche(n: int, modelo: str) -> "Path | None":
    """Encuentra la carpeta de un coche por número Y modelo.
    IMPORTANTE: NO usar fallback por número solo — causa contaminación de fotos
    cuando los números se redistribuyen al venderse un coche."""
    prefijo = f"{n:02d} - {modelo}"
    for candidata in sorted(PHOTOS_DIR.iterdir()):
        if candidata.is_dir() and candidata.name.startswith(prefijo):
            return candidata
    return None


def sincronizar_estado_carpeta(n: int, modelo: str, precio: str, estado: str) -> "Path | None":
    """
    Renombra la carpeta del coche para reflejar su estado actual:
    - Disponible  → sin sufijo   '01 - SEAT Arona - 22.900€'
    - RESERVADO   → con sufijo   '01 - SEAT Arona - 22.900€ · RESERVADO'
    Devuelve la carpeta (renombrada o no). No crea carpeta si no existe.
    """
    nombre_correcto = nombre_carpeta(n, modelo, precio, estado)
    ruta_correcta   = PHOTOS_DIR / nombre_correcto

    if ruta_correcta.exists():
        return ruta_correcta  # ya tiene el nombre correcto

    # Buscar la carpeta actual (puede tener nombre diferente)
    actual = buscar_carpeta_coche(n, modelo)
    if actual is None:
        return None  # no existe aún — se creará cuando se descarguen fotos

    if actual != ruta_correcta:
        actual.rename(ruta_correcta)

    return ruta_correcta


def carpeta_coche(n: int, modelo: str, precio: str = "") -> Path:
    """Devuelve/crea la carpeta del coche. NUNCA renombra otra carpeta —
    cada coche obtiene su propia carpeta nueva si no existe.
    Esto evita que fotos de un coche contaminen otro al cambiar de número o precio."""
    nueva = PHOTOS_DIR / nombre_carpeta(n, modelo, precio)
    nueva.mkdir(exist_ok=True)
    return nueva

def crear_webloc(carpeta: Path, url_relativa: str):
    """Crea un acceso directo .webloc (macOS) que abre el coche en Das WeltAuto."""
    if not url_relativa:
        return
    url = "https://www.dasweltauto.es" + url_relativa
    contenido = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>URL</key>
    <string>{url}</string>
</dict>
</plist>"""
    (carpeta / "Ver en Das WeltAuto.webloc").write_text(contenido, encoding="utf-8")

def _dwa_foto_url(url_relativa: str) -> str:
    """Construye la URL de foto exterior x01.jpg de Das WeltAuto (igual que generar_web.py)."""
    if not url_relativa:
        return ""
    listing_id = str(url_relativa).rstrip("/").split("/")[-1]
    padded = listing_id.zfill(11)
    path = "/".join(padded[i:i+2] for i in range(0, len(padded), 2))
    return f"https://www.dasweltauto.es/esp/fotos_anuncios/{path}/x01.jpg"


def _es_foto_exterior(path: Path) -> bool:
    """Detecta si una foto es exterior por brillo de esquinas (fondo blanco showroom)."""
    try:
        from PIL import Image
        img = Image.open(str(path)).convert("L").resize((100, 75))
        w, h = img.size
        cx, cy = max(1, w // 7), max(1, h // 7)
        def cb(x0, y0, x1, y1):
            patch = img.crop((x0, y0, x1, y1))
            d = list(patch.getdata())
            return sum(d) / len(d) if d else 0
        avg = (cb(0, 0, cx, cy) + cb(w-cx, 0, w, cy) +
               cb(0, h-cy, cx, h) + cb(w-cx, h-cy, w, h)) / 4
        return avg > 150
    except Exception:
        return True  # si falla el análisis, asumir exterior


def _primera_foto_exterior(carpeta: Path) -> "Path | None":
    """Devuelve la primera foto exterior de la carpeta (esquinas blancas = showroom)."""
    fotos = sorted(carpeta.glob("foto_*.jpg"))
    if not fotos:
        return None
    for f in fotos:
        if _es_foto_exterior(f):
            return f
    return fotos[0]  # si ninguna es claramente exterior, devolver la primera


def _descargar_foto_dwa(car: dict, carpeta: Path) -> "Path | None":
    """Descarga x01.jpg de Das WeltAuto y lo guarda como foto_exterior_dwa.jpg.
    Solo si no existe ya. Devuelve la ruta o None si falla."""
    cache = carpeta / "foto_exterior_dwa.jpg"
    if cache.exists():
        return cache
    url = _dwa_foto_url(car.get("url", ""))
    if not url:
        return None
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req, timeout=10).read()
        if len(data) > 10000:
            cache.write_bytes(data)
            return cache
    except Exception:
        pass
    return None


def get_foto_principal(n: int, modelo: str, precio: str = "", car: dict = None) -> Path:
    """
    Foto exterior principal del coche para el PDF.
    Usa foto_01.jpg — que ya es la foto exterior correcta de Das WeltAuto.
    No descarga ni crea foto_exterior_dwa.jpg (evita duplicados en carpeta).
    Los coches "fuente=motorflash" no tienen carpeta en fotos/ — sus fotos
    están en web_fotos/{n:02d}/ (descargadas por integrar_motorflash.py).
    """
    carpeta = buscar_carpeta_coche(n, modelo)
    if carpeta is not None:
        exterior = _primera_foto_exterior(carpeta)
        if exterior:
            return exterior

    if car and car.get("fuente") == "motorflash":
        web_foto = OUTPUT_DIR / "web_fotos" / f"{n:02d}" / "foto_01.jpg"
        if web_foto.exists():
            return web_foto

    return PHOTOS_DIR / f"coche_{n:02d}.jpg"

# ── Equipamiento clave a destacar (palabras que indican valor) ──
EQUIP_KEYWORDS = [
    "Navegador", "Camara", "Cámara", "LED", "Llantas", "Apple CarPlay",
    "Android Auto", "Climatizador", "Clima", "Calefacci", "Tapicería",
    "Cuero", "Piel", "Asiento", "Techo", "Panoramic", "Keyless",
    "Pack", "Sport", "Cruise", "Adaptativo", "Frenada", "Pre-colisi",
    "Aparcamiento", "Sensores", "Reconocimiento", "Ambiente", "Matrix",
    "Digital", "Sonido", "Bluetooth", "Carga inalámbrica", "Virtual",
    "Head-up", "HUD", "360", "Retroceso", "Frontal", "Parktronic",
    "Asistente", "Carril", "Velocidad", "BEATS", "Harman", "BOSE",
    "Iluminación", "interior envolvente", "Sin llave", "Inalámbrica",
    "USB", "WLAN", "Wi-Fi"
]

def filtrar_equipamiento(items: list[str]) -> list[str]:
    """Devuelve hasta 10 ítems de mayor interés comercial (texto completo, sin recortar)."""
    puntuados = []
    for item in items:
        if len(item) < 6 or len(item) > 220:  # subido de 100 a 220
            continue
        # Descartar colores, códigos y pintura
        if any(x in item for x in ["metalizado", "tela)", "color ", "código", "Pintura"]):
            continue
        score = sum(1 for kw in EQUIP_KEYWORDS if kw.lower() in item.lower())
        puntuados.append((score, item))
    puntuados.sort(key=lambda x: -x[0])
    # Primero los que tienen palabras clave, luego el resto
    resultado = [it for sc, it in puntuados if sc > 0]
    resto     = [it for sc, it in puntuados if sc == 0]
    return (resultado + resto)[:10]

def color_marca(modelo: str):
    m = modelo.upper()
    if "CUPRA"      in m: return (40,30,15),   (198,151,71)
    elif "SEAT"     in m: return (15,25,50),    (255,80,0)
    else:                  return (10,10,10),    (0,160,220)

# ── Scraping del listado ───────────────────────────────────
async def obtener_coches_del_listado(page) -> list[dict]:
    """Navega al listado, carga todos los coches y extrae datos básicos + URL."""
    print("  Accediendo al listado de Automóviles Rueda...")
    await page.goto(LISTING, wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(2500)

    # Cerrar cookies si aparecen
    await page.evaluate("""
        const btns = document.querySelectorAll('button');
        const btn  = Array.from(btns).find(b => b.textContent.includes('Rechazar') || b.textContent.includes('Aceptar'));
        if (btn) btn.click();
    """)
    await page.wait_for_timeout(800)

    # Leer el total real que indica la página (ej: "39 Coches de segunda mano de Automóviles Rueda")
    total_pagina = await page.evaluate("""
        () => {
            const m = document.body.innerText.match(/(\\d+)\\s+Coches de segunda mano de Automóviles Rueda/);
            return m ? parseInt(m[1]) : null;
        }
    """)
    print(f"  Total según la página: {total_pagina} coches de Automóviles Rueda")

    # Hacer clic en "Ver más" SOLO hasta alcanzar el total real de la página
    # Evita cargar coches de otros concesionarios
    for intento in range(10):
        cargados = await page.evaluate("document.querySelectorAll('h2.nombre').length")
        if total_pagina and cargados >= total_pagina:
            break  # Ya tenemos todos los de Automóviles Rueda, parar
        mas = await page.query_selector(".showMore.primaryBtn")
        if not mas:
            break
        await page.evaluate("document.querySelector('.showMore.primaryBtn').click()")
        await page.wait_for_timeout(1800)

    total = await page.evaluate("document.querySelectorAll('h2.nombre').length")
    print(f"  Coches cargados: {total} (objetivo: {total_pagina})")

    cars = await page.evaluate("""
        () => {
            const nombres = document.querySelectorAll('h2.nombre');
            const seen    = new Set();   // para deduplicar por URL
            const results = [];
            let idx = 1;
            nombres.forEach(h2 => {
                const card = h2.closest('.vehicleTeaser, .results-item-wrap, article, li') ||
                             h2.parentElement.parentElement.parentElement;
                const text  = card.textContent.replace(/\\s+/g, ' ').trim();

                // Filtro 1: solo coches de Automóviles Rueda
                if (!text.includes('AUTOMÓVILES RUEDA') && !text.includes('Automóviles Rueda')) return;

                const links = card.querySelectorAll('a[href]');
                const dLink = Array.from(links).find(a => /\\/\\d{6,}$/.test(a.pathname));
                const url   = dLink ? dLink.pathname : null;

                // Filtro 2: deduplicar por URL (evita "También podría interesarte")
                if (!url || seen.has(url)) return;
                seen.add(url);

                const priceM = text.match(/PVP\\s+([\\d.]+)\\s*€\\s*IVA inc/);
                const kmM    = text.match(/([\\d.]+)\\s*km\\s+(\\d{2}\\/\\d{4})/);
                const fuelM  = text.match(/(Gasolina|Di[eé]sel|El[eé]ctrico|H[ií]brido|Mild Hybrid)/);
                const transM = text.match(/(Manual|Autom[aá]tico)/);
                const colorM = text.match(/Tracci[oó]n\\s+(?:Delantera|Trasera|Total|4x4)\\s+(\\w+)/);
                const velez  = text.includes('VELEZ') || text.includes('Vélez');
                const stateM = text.match(/(Reservar|Av[ií]same si queda disponible|Vendido|Reservado)/);
                results.push({
                    n:          idx++,
                    modelo:     h2.textContent.replace(/\\s+/g,' ').trim().split(' ').slice(0,2).join(' '),
                    version:    h2.textContent.replace(/\\s+/g,' ').trim().split(' ').slice(2).join(' '),
                    combustible:fuelM  ? fuelM[1]  : '',
                    km:         kmM    ? kmM[1]    : '',
                    fecha:      kmM    ? kmM[2]    : '',
                    cambio:     transM ? transM[1] : '',
                    color:      colorM ? colorM[1] : '',
                    precio:     priceM ? priceM[1] : '',
                    ubicacion:  velez  ? 'Vélez-Málaga' : 'Málaga',
                    estado:     (stateM && stateM[1] !== 'Reservar') ? 'No disponible' : 'Disponible',
                    url:        url,
                    equipamiento: []
                });
            });
            return results;
        }
    """)
    print(f"  Coches únicos de Automóviles Rueda: {len(cars)}")
    return cars

# ── Visita la ficha de detalle ─────────────────────────────
async def enriquecer_coche(page, car: dict):
    """Descarga foto y extrae equipamiento de la ficha individual."""
    n   = car["n"]
    url = car.get("url")
    if not url:
        print(f"  [{n}] Sin URL, saltando ficha")
        car["equipamiento"] = []
        return

    # ── Carpeta del coche: "01 - SEAT León", "02 - CUPRA Formentor", … ──
    foto_dir = carpeta_coche(n, car["modelo"], car.get("precio", ""))
    foto_dir.mkdir(exist_ok=True)

    # Migración: si existe la foto plana antigua la movemos a la carpeta
    foto_plana = PHOTOS_DIR / f"coche_{n:02d}.jpg"
    if foto_plana.exists() and not (foto_dir / "foto_01.jpg").exists():
        foto_plana.rename(foto_dir / "foto_01.jpg")

    foto_principal = foto_dir / "foto_01.jpg"
    print(f"  [{n:02d}/{car.get('_total',39)}] {car['modelo']} {car['version'][:40]}")

    try:
        await page.goto("https://www.dasweltauto.es" + url,
                        wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(1500)

        # Cerrar cookies si aparecen
        await page.evaluate("""
            const btns = document.querySelectorAll('button');
            const btn  = Array.from(btns).find(b => b.textContent.includes('Rechazar') || b.textContent.includes('Aceptar'));
            if (btn) btn.click();
        """)
        await page.wait_for_timeout(400)

        # ── Descargar galería de fotos exteriores ──────────
        if not foto_principal.exists():
            # ESTRATEGIA CORRECTA: las URLs de Das WeltAuto contienen el número de foto
            # (x01.jpg, x02.jpg...x14.jpg). El DOM las presenta en orden aleatorio
            # (la activa primero, luego el resto), por eso descargamos en orden x01→xN.
            # x01 = PORTADA del anuncio (foto principal exterior).
            # g01, g02... = miniaturas (size=200), las descartamos.
            gallery_urls = await page.evaluate("""
                () => {
                    const entries = [];
                    const seenNums = new Set();

                    document.querySelectorAll('img').forEach(img => {
                        ['src','data-src','data-lazy','data-original'].forEach(attr => {
                            const raw = img.getAttribute(attr) || '';
                            if (!raw.includes('motorflash') || raw.length < 60) return;

                            // Decodificar URL para poder hacer regex en el path real
                            let decoded;
                            try { decoded = decodeURIComponent(raw); }
                            catch(e) { decoded = raw; }

                            // Buscar el nombre de archivo x01.jpg, x02.jpg... (fotos full-size)
                            // Las miniaturas usan g01.jpg, g02.jpg (las descartamos)
                            const match = decoded.match(/\\/x(\\d+)\\.jpg/i);
                            if (!match) return;

                            const num = parseInt(match[1], 10);
                            if (seenNums.has(num)) return;
                            seenNums.add(num);
                            entries.push({url: raw, num: num});
                        });
                    });

                    // CLAVE: ordenar por número → x01 primero = PORTADA del anuncio
                    entries.sort((a, b) => a.num - b.num);
                    return entries.map(e => e.url);
                }
            """)

            descargadas = 0
            MAX_FOTOS = 8  # máximo 8 ángulos exteriores por coche
            for src in gallery_urls:
                if descargadas >= MAX_FOTOS:
                    break
                try:
                    r = requests.get(src, timeout=15,
                                     headers={"User-Agent": "Mozilla/5.0"})
                    # >20 KB = foto real (descartamos thumbnails pequeños)
                    if r.status_code == 200 and len(r.content) > 20000:
                        idx = descargadas + 1
                        (foto_dir / f"foto_{idx:02d}.jpg").write_bytes(r.content)
                        descargadas += 1
                except Exception:
                    pass

            if descargadas == 0:
                # Fallback: screenshot del área de la foto
                await page.screenshot(path=str(foto_principal),
                                      clip={"x": 63, "y": 120,
                                            "width": 908, "height": 620})
                descargadas = 1

            print(f"      Fotos descargadas: {descargadas} → {foto_dir.name}/")
        else:
            n_fotos = len(list(foto_dir.glob("foto_*.jpg")))
            print(f"      Fotos ya existentes: {n_fotos} → {foto_dir.name}/")

        car["fotos"] = sorted(str(f) for f in foto_dir.glob("foto_*.jpg"))
        car["carpeta"] = str(foto_dir)

        # Acceso directo al coche en Das WeltAuto
        crear_webloc(foto_dir, url)

        # ── Extraer equipamiento ───────────────────────────
        # 1) Hacer clic en la pestaña Equipamiento vía JS
        await page.evaluate("""
            const links = document.querySelectorAll('a, button');
            const tab   = Array.from(links).find(el =>
                el.textContent && el.textContent.trim().includes('Equipamiento'));
            if (tab) tab.click();
        """)
        await page.wait_for_timeout(900)

        # 2) Extraer texto COMPLETO de los elementos de equipamiento usando textContent
        #    (textContent ignora CSS overflow/truncation; innerText lo respeta y recorta)
        items_js = await page.evaluate("""
            () => {
                const textos = new Set();
                // Buscar todos los elementos de lista o items que contengan texto de equipo
                const selectores = [
                    'ul li', 'ol li',
                    '[class*="equip"] span', '[class*="equip"] p', '[class*="equip"] div',
                    '[class*="feature"] span', '[class*="feature"] li',
                    '[class*="item"] span', '[class*="detail"] li',
                ];
                for (const sel of selectores) {
                    document.querySelectorAll(sel).forEach(el => {
                        const t = (el.textContent || '').replace(/\\s+/g, ' ').trim();
                        if (t.length > 5 && t.length < 250) textos.add(t);
                    });
                }
                return Array.from(textos);
            }
        """)

        # 3) Fallback: leer el cuerpo completo sin límite de caracteres (textContent)
        if len(items_js) < 5:
            body = await page.evaluate("document.body.textContent")
            start = -1
            for marca in ["Equipamiento opcional", "Equipamiento de serie", "EQUIPAMIENTO"]:
                idx = body.find(marca)
                if idx > -1:
                    start = idx
                    break
            if start == -1:
                for kw in EQUIP_KEYWORDS:
                    idx = body.find(kw)
                    if idx > -1:
                        start = max(0, idx - 100)
                        break
            # Sin límite de 2500 — tomamos todo hasta el final de la sección (~8000 chars)
            equip_raw = body[start:start + 8000] if start > -1 else ""
            items_js  = [l.replace('\t', ' ').strip()
                         for l in equip_raw.replace('\r', '\n').split("\n")
                         if l.strip()]

        # 4) Filtrar ruido (precios, plazos, botones, etc.)
        EXCLUIR = ["€", "PVP", "Reservar", "Financ", "Tel", "TAE", "TIN",
                   "cuota", "Entrada", "Precio al", "Importe", "plazo",
                   "Ver ", "Más info", "Contactar", "Solicitar", "Llamar"]
        lineas = [l for l in items_js if
                  8 < len(l) < 220 and
                  not any(x in l for x in EXCLUIR)]

        car["equipamiento"] = filtrar_equipamiento(lineas)
        print(f"      Equipamiento: {len(car['equipamiento'])} ítems destacados")

        # ── Extraer financiación de Das WeltAuto ───────────────
        # Esperar a que el JS de la calculadora rellene la cuota
        await page.wait_for_timeout(2500)
        fin = await page.evaluate("""
            () => {
                const body = document.body.textContent || '';
                const result = {};

                // Cuota mensual: buscar el valor numérico junto a "€/mes"
                // DWA renderiza algo como "249,00 €/mes" o "249 €/mes"
                const cuotaPatterns = [
                    /cuota mensual[\\s\\S]{0,100}?(\\d{1,4}[.,]\\d{2})\\s*€\\/mes/i,
                    /(\\d{1,4}[.,]\\d{2})\\s*€\\/mes/i,
                    /€\\/mes[\\s\\S]{0,20}?(\\d{1,4}[.,]\\d{2})/i,
                ];
                for (const re of cuotaPatterns) {
                    const m = body.match(re);
                    if (m) { result.cuota = m[1].replace(',', '.'); break; }
                }

                // TIN
                const tinM = body.match(/T\\.I\\.N\\.?[:\\s]*(\\d+[,.]\\d+)\\s*%/i);
                if (tinM) result.tin = tinM[1].replace(',', '.');

                // TAE
                const taeM = body.match(/T\\.A\\.E\\.?[:\\s]*(\\d+[,.]\\d+)\\s*%/i);
                if (taeM) result.tae = taeM[1].replace(',', '.');

                // Número de cuotas / meses
                const mesesM = body.match(/(\\d+)\\s+cuotas?\\s+de/i)
                             || body.match(/Meses de financiaci[oó]n[:\\s]*(\\d+)/i);
                if (mesesM) result.meses = mesesM[1];

                // Entrada
                const entradaM = body.match(/Entrada[:\\s]*(\\d+[.,]\\d{2})[\\s€]/i)
                               || body.match(/Sin entrada/i);
                result.entrada = entradaM
                    ? (typeof entradaM[1] !== 'undefined' ? entradaM[1].replace(',','.') : '0')
                    : null;

                // Tipo de financiación: Autocredit primero (más específico)
                result.tipo = body.match(/Autocredit/i) ? 'Autocredit'
                            : body.match(/Lineal/i)     ? 'Lineal'
                            : '';

                // Ejemplo verbatim: copiar el párrafo completo de condiciones de DWA
                const ejIdx = body.indexOf('Ejemplo de cuota');
                if (ejIdx > -1) {
                    result.ejemplo = body.substring(ejIdx, ejIdx + 700)
                                         .replace(/\\s+/g, ' ').trim();
                }

                return result;
            }
        """)

        if fin and fin.get("cuota"):
            car["financiacion"] = fin
            print(f"      Financiación: {fin.get('cuota')}€/mes · {fin.get('tipo','?')} · TIN {fin.get('tin','?')}% · {fin.get('meses','?')} meses")
        else:
            car["financiacion"] = {}
            print(f"      Financiación: no disponible")

    except Exception as e:
        print(f"      ⚠️  Error: {e}")
        car["equipamiento"] = []
        car["financiacion"] = {}

# ── Imagen para redes sociales (1080×1080) ─────────────────
def crear_imagen_social(car: dict, foto_path: Path) -> Path:
    W, H = 1080, 1080
    img  = Image.new("RGB", (W, H), (20,20,20))
    draw = ImageDraw.Draw(img)
    fondo, acento = color_marca(car["modelo"])

    # Fondos
    img.paste(Image.new("RGB", (W, int(H*0.57)), fondo),          (0, 0))
    img.paste(Image.new("RGB", (W, int(H*0.43)), (245,245,245)),  (0, int(H*0.57)))

    foto_h = int(H * 0.55)
    if foto_path.exists():
        try:
            ci = Image.open(foto_path).convert("RGB")
            ci.thumbnail((W, foto_h), Image.LANCZOS)
            img.paste(ci, ((W-ci.width)//2, (foto_h-ci.height)//2))
        except Exception:
            pass

    # Barra de acento
    draw.rectangle([0, foto_h, W, foto_h+8], fill=acento)

    try:
        fb = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 50)
        fm = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
        fs = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
        fp = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 58)
    except Exception:
        fb = fm = fs = fp = ImageFont.load_default()

    y = foto_h + 16
    draw.text((40, y), car["modelo"], font=fb, fill=fondo)
    y += 58
    vs = car["version"][:52] + ("…" if len(car["version"])>52 else "")
    draw.text((40, y), vs, font=fs, fill=(80,80,80))
    y += 38

    # Precio
    precio_str = f"{car['precio']} EUR"
    bb = draw.textbbox((0,0), precio_str, font=fp)
    draw.text((W - (bb[2]-bb[0]) - 30, foto_h+18), precio_str, font=fp, fill=acento)

    draw.rectangle([40, y, W-40, y+2], fill=acento)
    y += 14

    specs = [
        f"  {car['combustible']}   |   {car['fecha']}   |   {car['km']} km",
        f"  {car['cambio']}   |   {car['color']}",
        f"  Automoviles Rueda  {car['ubicacion']}",
    ]
    for s in specs:
        draw.text((40, y), s, font=fs, fill=(40,40,40))
        y += 32

    # Top 3 equipamiento
    if car.get("equipamiento"):
        y += 4
        draw.rectangle([40, y, W-40, y+2], fill=(200,200,200))
        y += 10
        for eq in car["equipamiento"][:3]:
            eq_s = ("- " + eq[:48]).encode("latin-1","replace").decode("latin-1")
            draw.text((40, y), eq_s, font=fs, fill=(60,60,60))
            y += 29
            if y > H - 60:
                break

    if car["estado"] != "Disponible":
        draw.rectangle([0,0,240,68], fill=(200,0,0))
        draw.text((10,10), "RESERVADO", font=fm, fill=(255,255,255))

    draw.rectangle([0, H-48, W, H], fill=fondo)
    draw.text((40, H-38), "AUTOMOVILES RUEDA  |  Das WeltAuto", font=fs, fill=(255,255,255))

    out = SOCIAL_DIR / f"coche_{car['n']:02d}_{car['modelo'].replace(' ','_')}.jpg"
    img.save(out, "JPEG", quality=95)
    return out

# ── Página resumen de cambios ──────────────────────────────
def _pagina_resumen(pdf, resumen: dict):
    """Primera página del PDF con el informe de cambios."""
    from datetime import datetime
    F = resumen.get("font", "Helvetica")
    pdf.add_page()
    pdf.set_fill_color(10, 10, 10)
    pdf.rect(0, 0, 297, 210, "F")

    # Título
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(F, "B", 20)
    pdf.set_xy(10, 8)
    pdf.cell(277, 10, "AUTOMÓVILES RUEDA  ·  Informe de actualización", ln=True)

    pdf.set_text_color(160, 160, 160)
    pdf.set_font(F, "", 9)
    pdf.set_xy(10, 20)
    pdf.cell(277, 5, f"Generado: {datetime.now().strftime('%d/%m/%Y  %H:%M')}  |  Concesionario Oficial SEAT & CUPRA  ·  Das WeltAuto", ln=True)

    # Línea divisoria
    pdf.set_draw_color(198, 151, 71)
    pdf.set_line_width(0.8)
    pdf.line(10, 27, 287, 27)

    # Cajitas de resumen
    totales = resumen.get("totales", {})
    cajas = [
        ("TOTAL COCHES",    str(totales.get("actual", "-")),     (40, 40, 40),    (255, 255, 255)),
        ("DISPONIBLES",     str(totales.get("disponibles", "-")), (0, 100, 50),    (255, 255, 255)),
        ("NO DISPONIBLES",  str(totales.get("no_disp", "-")),     (120, 0, 0),     (255, 255, 255)),
        ("NUEVOS",          str(len(resumen.get("nuevos", []))),  (0, 80, 140),    (255, 255, 255)),
        ("VENDIDOS",        str(len(resumen.get("vendidos", []))), (140, 60, 0),   (255, 255, 255)),
        ("CAMBIOS",         str(len(resumen.get("cambios", []))), (80, 0, 120),    (255, 255, 255)),
    ]
    x = 10
    for titulo, valor, fondo, texto in cajas:
        pdf.set_fill_color(*fondo)
        pdf.rect(x, 31, 44, 22, "F")
        pdf.set_text_color(*texto)
        pdf.set_font(F, "B", 16)
        pdf.set_xy(x, 33)
        pdf.cell(44, 9, valor, align="C")
        pdf.set_font(F, "", 6.5)
        pdf.set_xy(x, 43)
        pdf.cell(44, 4, titulo, align="C")
        x += 46

    y = 60
    col_w = 88

    nuevos   = resumen.get("nuevos",   [])
    vendidos = resumen.get("vendidos", [])
    cambios  = resumen.get("cambios",  [])
    page_map = resumen.get("page_map", {})

    def safe(txt): return txt  # TTF: unicode nativo, no necesita latin-1

    def _seccion_links(titulo, items, acento, x_col, formato_fn, url_fn=None):
        nonlocal y
        if not items:
            return
        pdf.set_text_color(*acento)
        pdf.set_font(F, "B", 8)
        pdf.set_xy(x_col, y)
        pdf.cell(col_w, 5, safe(titulo))
        pdf.set_draw_color(*acento)
        pdf.set_line_width(0.4)
        pdf.line(x_col, y + 5.5, x_col + col_w, y + 5.5)
        pdf.set_text_color(220, 220, 220)
        pdf.set_font(F, "", 7)
        yi = y + 8
        for item in items[:12]:
            if yi > 195:
                break
            txt = safe(formato_fn(item))
            pdf.set_xy(x_col, yi)
            # Enlace interno si tenemos página del coche
            url = url_fn(item) if url_fn else None
            page = page_map.get(url)
            if page:
                link_id = pdf.add_link()
                pdf.set_link(link_id, page=page)
                pdf.set_text_color(120, 180, 255)
                pdf.cell(col_w - 14, 4, txt)
                pdf.set_text_color(*acento)
                pdf.cell(14, 4, "  ver ->", link=link_id)
            else:
                pdf.cell(col_w, 4, txt)
            yi += 4.5

    n_act = resumen.get("n_actualizacion", 1)

    # ── SECCIÓN SUPERIOR: cambios de ESTA actualización ─────
    pdf.set_text_color(130, 130, 130)
    pdf.set_font(F, "", 7)
    pdf.set_xy(10, y - 5)
    pdf.cell(277, 4, safe(f"Actualización #{n_act} del día  —  cambios respecto a la actualización anterior:"))

    _seccion_links("+ COCHES NUEVOS", nuevos, (0, 180, 80), 10,
        lambda c: f"  {c['modelo']} {c['version'][:32]}  |  {c['precio']} EUR",
        lambda c: c.get("url"))
    _seccion_links("- VENDIDOS / RETIRADOS", vendidos, (220, 60, 60), 10 + col_w + 5,
        lambda c: f"  {c['modelo']} {c['version'][:32]}  |  {c['precio']} EUR",
        lambda c: c.get("url"))
    _seccion_links("~ CAMBIOS DE PRECIO O ESTADO", cambios, (180, 120, 0), 10 + (col_w + 5) * 2,
        lambda e: f"  {e['coche']['modelo']} {e['coche']['version'][:22]}  |  {'; '.join(e['cambios'][:1])[:35]}",
        lambda e: e["coche"].get("url"))

    if not nuevos and not vendidos and not cambios:
        pdf.set_text_color(100, 200, 100)
        pdf.set_font(F, "B", 10)
        pdf.set_xy(10, 75)
        pdf.cell(277, 6, "Sin cambios en esta actualización", align="C")

    # ── DIVISOR ──────────────────────────────────────────────
    y_div = 130
    pdf.set_draw_color(60, 60, 60)
    pdf.set_line_width(0.4)
    pdf.line(10, y_div, 287, y_div)

    # ── SECCIÓN INFERIOR: resumen acumulado del DÍA ──────────
    cambios_hoy = resumen.get("cambios_hoy", {})
    nuevos_hoy   = cambios_hoy.get("nuevos",   [])
    vendidos_hoy = cambios_hoy.get("vendidos", [])
    cambios_hoy_ = cambios_hoy.get("cambios",  [])
    n_acts_hoy   = cambios_hoy.get("actualizaciones", n_act)

    pdf.set_text_color(198, 151, 71)
    pdf.set_font(F, "B", 8)
    pdf.set_xy(10, y_div + 2)
    pdf.cell(277, 5, safe(f"RESUMEN DEL DÍA (acumulado — {n_acts_hoy} actualizaciones):"))

    y = y_div + 9
    col_w2 = 88

    if not nuevos_hoy and not vendidos_hoy and not cambios_hoy_:
        pdf.set_text_color(100, 160, 100)
        pdf.set_font(F, "", 8)
        pdf.set_xy(10, y + 2)
        pdf.cell(277, 5, "Sin cambios acumulados hoy respecto al inicio del día")
    else:
        def _mini(titulo, items, acento, x_col, formato_fn, url_fn=None):
            if not items:
                return
            pdf.set_text_color(*acento)
            pdf.set_font(F, "B", 7)
            pdf.set_xy(x_col, y)
            pdf.cell(col_w2, 4, safe(titulo))
            pdf.set_draw_color(*acento)
            pdf.set_line_width(0.3)
            pdf.line(x_col, y + 4.5, x_col + col_w2, y + 4.5)
            pdf.set_text_color(200, 200, 200)
            pdf.set_font(F, "", 6.5)
            yi = y + 6
            for item in items[:8]:
                if yi > 202:
                    break
                txt = safe(formato_fn(item))
                pdf.set_xy(x_col, yi)
                url = url_fn(item) if url_fn else None
                page = page_map.get(url)
                if page:
                    link_id = pdf.add_link()
                    pdf.set_link(link_id, page=page)
                    pdf.set_text_color(120, 180, 255)
                    pdf.cell(col_w2 - 12, 3.5, txt)
                    pdf.set_text_color(*acento)
                    pdf.cell(12, 3.5, "ver ->", link=link_id)
                else:
                    pdf.cell(col_w2, 3.5, txt)
                yi += 3.8

        _mini("+ NUEVOS HOY", nuevos_hoy, (0, 160, 70), 10,
            lambda c: f"  {c['modelo']} {c['version'][:30]}  |  {c['precio']} EUR",
            lambda c: c.get("url"))
        _mini("- VENDIDOS HOY", vendidos_hoy, (200, 50, 50), 10 + col_w2 + 5,
            lambda c: f"  {c['modelo']} {c['version'][:30]}  |  {c['precio']} EUR",
            lambda c: c.get("url"))
        _mini("~ CAMBIOS HOY", cambios_hoy_, (160, 100, 0), 10 + (col_w2 + 5) * 2,
            lambda e: f"  {e['coche']['modelo']} {e['coche']['version'][:20]}  |  {'; '.join(e['cambios'][:1])[:33]}",
            lambda e: e["coche"].get("url"))

    # Pie
    pdf.set_text_color(80, 80, 80)
    pdf.set_font(F, "", 7)
    pdf.set_xy(10, 204)
    pdf.cell(277, 4, "Av. Rey Juan Carlos I, 15  ·  Vélez-Málaga  |  610 029 056  |  dasweltauto.es/esp/concesionario-seat-automoviles-rueda", align="C")

# ── Fuente moderna (Avenir Next — macOS) ───────────────────
FONT_PATH_REG  = "/System/Library/Fonts/Avenir Next.ttc"
FONT_PATH_BOLD = "/System/Library/Fonts/Avenir Next.ttc"

def _cargar_fuentes(pdf):
    """Carga Avenir Next (TTF, unicode). Fallback a Helvetica si no existe."""
    from pathlib import Path as _P
    if _P(FONT_PATH_REG).exists():
        pdf.add_font("AR",  "",  FONT_PATH_REG,  uni=True)
        pdf.add_font("AR",  "B", FONT_PATH_BOLD, uni=True)
        return "AR"
    return "Helvetica"   # fallback si no está en el sistema

# ── Crear PDF ──────────────────────────────────────────────
def crear_pdf(cars: list[dict], resumen: dict = None):
    print(f"\n  Generando PDF con {len(cars)} coches...")
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(False)

    # Cargar fuente moderna
    FONT = _cargar_fuentes(pdf)

    # Pre-calcular mapa url → página (página 1 = resumen, coches desde página 2)
    page_map = {car["url"]: i + 2 for i, car in enumerate(cars) if car.get("url")}
    resumen_con_mapa = {**(resumen or {}), "page_map": page_map, "font": FONT}

    # Página 1: resumen de cambios con links internos
    _pagina_resumen(pdf, resumen_con_mapa)

    for car in cars:
        pdf.add_page()
        foto_path = get_foto_principal(car['n'], car['modelo'], car.get('precio', ''), car)
        fondo, acento = color_marca(car["modelo"])

        # Fondo oscuro
        pdf.set_fill_color(*fondo)
        pdf.rect(0, 0, 297, 210, "F")

        # ── Foto principal + 2 filas de miniaturas ───────────
        # Buscar todas las fotos de este coche (hasta 8)
        _carpeta_fotos = None
        _prefijo = f"{car['n']:02d} - {car['modelo']}"
        for _c in sorted(PHOTOS_DIR.iterdir()):
            if _c.is_dir() and _c.name.startswith(_prefijo):
                _carpeta_fotos = _c
                break
        if _carpeta_fotos is None and car.get("fuente") == "motorflash":
            _web_carpeta = OUTPUT_DIR / "web_fotos" / f"{car['n']:02d}"
            if _web_carpeta.is_dir():
                _carpeta_fotos = _web_carpeta
        todas_fotos = sorted(_carpeta_fotos.glob("foto_*.jpg"))[:8] if _carpeta_fotos else []

        # ── Foto principal: proporción original, sin deformación ──
        MAIN_W   = 154.0   # ancho disponible columna izquierda (mm)
        MAIN_X   = 4.0
        MAIN_Y   = 5.0
        main_bottom = MAIN_Y  # posición Y donde termina la foto principal

        if foto_path.exists():
            try:
                pi        = Image.open(foto_path).convert("RGB")
                img_w, img_h = pi.size
                # Altura proporcional: mantiene ratio sin deformar
                main_h    = MAIN_W * (img_h / img_w)
                buf = BytesIO()
                pi.save(buf, format="JPEG", quality=88)
                buf.seek(0)
                tmp = PHOTOS_DIR / f"tmp_{car['n']:02d}.jpg"
                tmp.write_bytes(buf.read())
                # Solo especificamos w → fpdf calcula h automáticamente
                pdf.image(str(tmp), x=MAIN_X, y=MAIN_Y, w=MAIN_W)
                main_bottom = MAIN_Y + main_h
            except Exception as e:
                print(f"  ⚠️  Foto PDF {car['n']}: {e}")

        # ── 2 filas de miniaturas con proporción correcta ─────────
        # Cada miniatura: 37mm ancho × ratio de la imagen = ~28mm alto (para 4:3)
        # Fila 1: hasta 4 fotos | Fila 2: hasta 3 fotos
        THUMB_W   = 37.0
        THUMB_GAP = 2.0    # espacio entre miniaturas
        ROW_GAP   = 2.5    # espacio entre fila 1 y fila 2
        ROW_Y1    = main_bottom + 3.0  # fila 1 empieza justo debajo de la foto principal

        if len(todas_fotos) > 1:
            miniaturas = todas_fotos[1:]   # excluir foto_01 (ya mostrada grande)
            fila1 = miniaturas[:4]
            fila2 = miniaturas[4:7]

            def _dibujar_fila(fotos_fila, y_fila, n_car):
                """Dibuja una fila de miniaturas centrada, proporción original."""
                n = len(fotos_fila)
                if n == 0:
                    return 0.0
                total_w = n * THUMB_W + (n - 1) * THUMB_GAP
                x_start = MAIN_X + (MAIN_W - total_w) / 2.0  # centrado

                fila_h = 0.0
                for ti, foto_mini in enumerate(fotos_fila):
                    try:
                        pm        = Image.open(foto_mini).convert("RGB")
                        mw, mh    = pm.size
                        t_h       = THUMB_W * (mh / mw)  # altura proporcional real
                        fila_h    = max(fila_h, t_h)

                        buf_m = BytesIO()
                        pm.save(buf_m, format="JPEG", quality=72)
                        buf_m.seek(0)
                        tmp_m = PHOTOS_DIR / f"tmp_m_{n_car:02d}_{ti:02d}.jpg"
                        tmp_m.write_bytes(buf_m.read())

                        x_t = x_start + ti * (THUMB_W + THUMB_GAP)
                        pdf.image(str(tmp_m), x=x_t, y=y_fila, w=THUMB_W)
                    except Exception:
                        pass
                return fila_h

            fila1_h = _dibujar_fila(fila1, ROW_Y1, car['n'])
            if fila2:
                _dibujar_fila(fila2, ROW_Y1 + fila1_h + ROW_GAP, car['n'])

        # Línea de acento vertical
        pdf.set_fill_color(*acento)
        pdf.rect(161, 0, 4, 210, "F")

        # ── Columna derecha ─────────────────────────────
        xr = 169

        # Modelo
        pdf.set_text_color(*acento)
        pdf.set_font(FONT, "B", 20)
        pdf.set_xy(xr, 6)
        pdf.cell(122, 10, car["modelo"], ln=True)

        # Versión
        pdf.set_text_color(200, 200, 200)
        pdf.set_font(FONT, "", 8)
        pdf.set_xy(xr, 17)
        pdf.cell(122, 5, car["version"][:72], ln=True)

        # Línea separadora
        pdf.set_draw_color(*acento)
        pdf.set_line_width(0.6)
        pdf.line(xr, 24, 291, 24)

        # Precio
        pdf.set_text_color(*acento)
        pdf.set_font(FONT, "B", 28)
        pdf.set_xy(xr, 26)
        pdf.cell(122, 13, f"{car['precio']} €", ln=True)

        pdf.set_text_color(150, 150, 150)
        pdf.set_font(FONT, "", 7)
        pdf.set_xy(xr, 40)
        pdf.cell(122, 4, "IVA incluido  ·  Garantía Das WeltAuto", ln=True)

        # Especificaciones
        pdf.set_text_color(*acento)
        pdf.set_font(FONT, "B", 8)
        pdf.set_xy(xr, 47)
        pdf.cell(122, 5, "ESPECIFICACIONES", ln=True)

        specs = [
            ("Combustible",   car["combustible"]),
            ("Kilometraje",   f"{car['km']} km"),
            ("Matriculación", car["fecha"]),
            ("Cambio",        car["cambio"]),
            ("Color",         car["color"]),
            ("Ubicación",     car["ubicacion"]),
        ]
        y = 53
        for lbl, val in specs:
            pdf.set_text_color(130, 130, 130)
            pdf.set_font(FONT, "", 7)
            pdf.set_xy(xr, y)
            pdf.cell(34, 4.2, lbl)
            pdf.set_text_color(245, 245, 245)
            pdf.set_font(FONT, "B", 7)
            pdf.cell(88, 4.2, val, ln=True)
            y += 5

        # ── Equipamiento ─────────────────────────────────
        y += 2
        pdf.set_draw_color(*acento)
        pdf.set_line_width(0.3)
        pdf.line(xr, y, 291, y)
        y += 4

        pdf.set_text_color(*acento)
        pdf.set_font(FONT, "B", 8)
        pdf.set_xy(xr, y)
        pdf.cell(122, 5, "EQUIPAMIENTO DESTACADO", ln=True)
        y += 6

        equip = car.get("equipamiento", [])
        if equip:
            for item in equip[:10]:
                if y > 170:   # dejar margen antes del footer
                    break
                pdf.set_text_color(210, 210, 210)
                pdf.set_font(FONT, "", 7)
                pdf.set_xy(xr, y)
                # multi_cell ajusta el texto automáticamente — sin corte a mitad de palabra
                pdf.multi_cell(122, 3.8, "· " + item)
                y = pdf.get_y() + 1   # avanzar al siguiente ítem respetando el salto de línea
        else:
            pdf.set_text_color(120, 120, 120)
            pdf.set_font(FONT, "", 7)
            pdf.set_xy(xr, y)
            pdf.cell(122, 4, "(Equipamiento no disponible)", ln=True)

        # ── Franja inferior izquierda (branding + estado) ────
        FOOTER_Y = 182.0
        pdf.set_fill_color(0, 0, 0)
        pdf.rect(0, FOOTER_Y, 162, 210 - FOOTER_Y, "F")

        pdf.set_text_color(*acento)
        pdf.set_font(FONT, "B", 11)
        pdf.set_xy(5, FOOTER_Y + 3)
        pdf.cell(152, 6, "AUTOMÓVILES RUEDA", ln=True)

        pdf.set_text_color(140, 140, 140)
        pdf.set_font(FONT, "", 6.5)
        pdf.set_xy(5, FOOTER_Y + 10)
        pdf.cell(152, 3.5, "Concesionario Oficial SEAT & CUPRA  ·  Vélez-Málaga", ln=True)

        # Estado (DISPONIBLE / RESERVADO)
        col_estado = (0, 130, 55) if car["estado"] == "Disponible" else (180, 0, 0)
        txt_estado = "DISPONIBLE" if car["estado"] == "Disponible" else "RESERVADO"
        pdf.set_fill_color(*col_estado)
        pdf.rect(5, FOOTER_Y + 16, 50, 8, "F")
        pdf.set_text_color(255, 255, 255)
        pdf.set_font(FONT, "B", 7.5)
        pdf.set_xy(6, FOOTER_Y + 17.5)
        pdf.cell(48, 5, txt_estado)

        # Enlace a Das WeltAuto
        url_coche = car.get("url", "")
        if url_coche:
            full_url = "https://www.dasweltauto.es" + url_coche
            pdf.set_text_color(80, 140, 220)
            pdf.set_font(FONT, "", 6.5)
            pdf.set_xy(5, FOOTER_Y + 17)
            pdf.cell(152, 5, "", ln=True)   # spacer
            pdf.set_xy(58, FOOTER_Y + 17.5)
            pdf.cell(100, 5, "Ver en Das WeltAuto  ->", link=full_url)

        # Volver al resumen (página 1)
        link_resumen = pdf.add_link()
        pdf.set_link(link_resumen, page=1)
        pdf.set_text_color(*acento)
        pdf.set_font(FONT, "B", 6.5)
        pdf.set_xy(220, 205)
        pdf.cell(50, 4, "<- Volver al resumen", link=link_resumen, align="R")

        # Número de coche
        pdf.set_text_color(70, 70, 70)
        pdf.set_font(FONT, "", 6)
        pdf.set_xy(272, 205)
        pdf.cell(20, 4, f"{car['n']}/{len(cars)}")

    pdf.output(str(PDF_PATH))
    print(f"  PDF guardado: {PDF_PATH}")

    # Limpiar archivos temporales de procesamiento de imágenes
    for tmp in PHOTOS_DIR.glob("tmp_*.jpg"):
        tmp.unlink(missing_ok=True)

# ── Main ───────────────────────────────────────────────────
async def main():
    print()
    print("=" * 58)
    print("  AUTOMÓVILES RUEDA — Catálogo Das WeltAuto v2")
    print("  Con equipamiento detallado por coche")
    print("=" * 58)
    print(f"  Salida: {OUTPUT_DIR}")
    print()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx     = await browser.new_context(
            viewport    = {"width":1400,"height":900},
            user_agent  = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 Chrome/120 Safari/537.36")
        )
        page = await ctx.new_page()

        # 1) Obtener todos los coches del listado
        cars = await obtener_coches_del_listado(page)
        total = len(cars)
        for c in cars:
            c["_total"] = total
        print()

        # 2) Visitar cada ficha: foto + equipamiento
        print("  Visitando fichas individuales (foto + equipamiento)...")
        print()
        for car in cars:
            await enriquecer_coche(page, car)
            # Imagen social (usa la foto principal de la carpeta)
            foto_path   = get_foto_principal(car['n'], car['modelo'], car.get('precio', ''), car)
            social_path = crear_imagen_social(car, foto_path)
            print(f"      Imagen social → {social_path.name}")

        await browser.close()

    # 3) Guardar datos en JSON (caché para regeneraciones rápidas)
    CACHE_PATH.write_text(json.dumps(cars, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Datos guardados en: {CACHE_PATH.name}")

    # 4) PDF con todos los datos
    crear_pdf(cars)

    # 5) Resumen
    con_equip = sum(1 for c in cars if c.get("equipamiento"))
    print()
    print("=" * 58)
    print(f"  ✅  ¡Completado!  {total} coches procesados")
    print(f"      Equipamiento extraído: {con_equip}/{total} fichas")
    print(f"      PDF:    {PDF_PATH.name}")
    print(f"      Redes:  {SOCIAL_DIR}/")
    print("=" * 58)
    print()


def regenerar_solo_pdf():
    """Regenera el PDF en segundos usando el caché JSON (sin navegar la web)."""
    if not CACHE_PATH.exists():
        print("No hay caché de datos. Ejecuta el script completo primero.")
        return
    cars = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    print(f"  Regenerando PDF con {len(cars)} coches desde caché...")
    crear_pdf(cars)
    print("  ✅ PDF regenerado.")

if __name__ == "__main__":
    asyncio.run(main())
