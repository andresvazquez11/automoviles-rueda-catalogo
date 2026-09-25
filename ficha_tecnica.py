"""
ficha_tecnica.py
================
Ficha técnica completa de cada coche (características principales,
equipamiento extra y de serie, dimensiones, consumo, motor, datos eléctricos)
leída del anuncio en Das WeltAuto o MotorFlash.

- `python3 ficha_tecnica.py` visita SOLO los coches que aún no tienen ficha
  guardada (o cuya versión cambió) y la guarda en fichas_tecnicas.json, ya
  traducida al inglés. Cada coche se lee una sola vez, así la actualización
  diaria no se hace más lenta.
- generar_web.py usa `bloques_html()` para pintar los 4 bloques de la ficha.
"""

from __future__ import annotations

import asyncio, hashlib, html, json, re, sys
from pathlib import Path

BASE_DIR     = Path(__file__).parent
DATOS_PATH   = BASE_DIR / "datos_coches.json"
FICHAS_PATH  = BASE_DIR / "fichas_tecnicas.json"
CONFIG_PATH  = BASE_DIR / "config.txt"
DASWELTAUTO  = "https://www.dasweltauto.es"


def clave_ficha(car: dict) -> str:
    """Mismo identificador estable que generar_web.id_estable_coche: la ficha
    va por el ID del anuncio, nunca por "n" (que cambia en cada actualización)."""
    if car.get("motorflash_id"):
        return f"mf-{car['motorflash_id']}"
    url = car.get("url") or ""
    listing_id = url.rstrip("/").split("/")[-1]
    if listing_id.isdigit():
        return f"dwa-{listing_id}"
    return ""


# ── Lectura del HTML ─────────────────────────────────────────────────────────

_RUIDO_TOKENS = {"-->", "Ver más", "Ver menos"}

def _tokens(html_src: str) -> list[str]:
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html_src, flags=re.S | re.I)
    out = [re.sub(r"\s+", " ", html.unescape(x)).strip() for x in re.split(r"<[^>]+>", s)]
    return [x for x in out if x and x not in _RUIDO_TOKENS]


def _idx(t: list[str], valor: str, desde: int = 0, hasta: int | None = None) -> int:
    for i in range(max(desde, 0), len(t) if hasta is None else min(hasta, len(t))):
        if t[i] == valor:
            return i
    return -1


def _pares(t: list[str], ini: int, fin: int, claves: dict[str, str]) -> dict[str, str]:
    """Lee 'Etiqueta', 'valor' entre ini y fin. `claves` mapea la etiqueta de
    la web (sin ':') a nuestra clave. Se queda con la PRIMERA aparición."""
    d: dict[str, str] = {}
    if ini < 0:
        return d
    fin = len(t) if fin < 0 else fin
    k = ini
    while k < fin - 1:
        lab = t[k].rstrip(":").strip()
        clave = claves.get(lab)
        if clave and clave not in d:
            valor = t[k + 1]
            if valor.rstrip(":") in claves or valor.startswith(("l/100", "g/km")):
                k += 1          # etiqueta sin valor (DWA deja celdas vacías)
                continue
            if valor not in ("-", "- g/km"):
                d[clave] = valor
            k += 2
        else:
            k += 1
    return d


def _lista_hasta(t: list[str], ini: int, paradas: set[str], maximo: int = 80) -> list[str]:
    out = []
    k = ini
    while k < len(t) and t[k] not in paradas and len(out) < maximo:
        out.append(t[k].split("\t")[0].strip())
        k += 1
    return out


GRUPOS_SERIE = ("Exterior", "Interior", "Confort", "Seguridad")


def _serie(t: list[str], ini: int, fin: int) -> dict[str, list[str]]:
    serie: dict[str, list[str]] = {}
    grupo = None
    for k in range(ini, fin):
        if t[k] in GRUPOS_SERIE:
            grupo = t[k]
            serie.setdefault(grupo, [])
        elif grupo:
            serie[grupo].append(t[k])
    return {g: v for g, v in serie.items() if v}


# Grupos para el "Resumen" de extras de DWA (MotorFlash ya los trae agrupados)
_GRUPOS_EXTRAS = [
    ("Seguridad y asistentes", r"drive pack|assist|asistente|precrash|cansancio|carril|esquiva|aviso|alarma|c[aá]mara|limitador|crucero|park|aparcamiento|frenada|airbag|safe|ángulo muerto|angulo muerto|head.?up"),
    ("Confort", r"calefacci|climatronic|climatiz|asiento|keyless|port[oó]n|volante|confort|techo|cortinilla|cristales|lunas|el[eé]ctric"),
    ("Tecnología y conectividad", r"infotainment|navegaci|app-connect|full link|wireless|voz|telefon|sonido|beats|altavoces|digital cockpit|pantalla|carplay|android"),
    ("Diseño", r"faro|matrix|led|llanta|edge|pack|pintura|deportivo|fr |estilo|design|diseño"),
]
# Opciones de fábrica que son configuración interna, no algo que el cliente valore
_EXTRAS_RUIDO = re.compile(
    r"^(BRS |Anclaje asientos|Servicio online|Preparación para sistema|Sistema de limitación de velocidad$"
    r"|Sin |Con ocu|Documentación|Manual de instrucciones|Idioma|Paquete de país|Placa de)", re.I)


def _agrupar_extras(extras: list[str]) -> dict[str, list[str]]:
    grupos = {n: [] for n, _ in _GRUPOS_EXTRAS}
    grupos["Otros extras"] = []
    for x in extras:
        for nombre, patron in _GRUPOS_EXTRAS:
            if re.search(patron, x, re.I):
                grupos[nombre].append(x)
                break
        else:
            grupos["Otros extras"].append(x)
    return {g: v for g, v in grupos.items() if v}


def extraer_dwa(html_src: str) -> dict:
    t = _tokens(html_src)
    ini = _idx(t, "Datos generales")
    if ini < 0:
        raise ValueError("no se encontró la sección 'Datos generales'")
    fin_gen = _idx(t, "Equipamiento opcional", ini)
    ex = _idx(t, "Exterior", ini)
    ce = _idx(t, "Consumo y emisiones", ini)
    fin_gen = fin_gen if fin_gen > 0 else ex

    gen = _pares(t, ini, fin_gen, {
        "Kilometros": "km", "Matriculación": "matriculacion", "Combustible": "combustible",
        "Cambio": "cambio", "Potencia": "potencia", "Consumo": "consumo", "Emisiones": "co2",
        "Tracción": "traccion", "Puertas": "puertas", "Color": "color", "Garantia": "garantia",
        "Batería garantizada": "garantia_bateria", "Autonomía eléctrica": "autonomia_electrica",
        "Capacidad de batería": "bateria", "Consumo de electricidad": "consumo_electrico",
        "Autonomía": "autonomia", "Neumáticos": "neumaticos", "Par motor": "par",
        "Velocidad máxima": "vmax", "Aceleración": "aceleracion",
    })
    m = _idx(t, "Maletero", ini, fin_gen)
    if m > 0:
        valor = t[m + 2] if t[m + 1] == "Maletero" else t[m + 1]
        if re.search(r"\d", valor):
            gen["maletero"] = re.sub(r"^de\s+", "", valor)

    # Equipamiento opcional: pintura, tapizado y extras (versión sin códigos)
    pintura = tapizado = ""
    extras: list[str] = []
    if fin_gen > 0 and t[fin_gen] == "Equipamiento opcional":
        p = _idx(t, "Color de pintura", fin_gen, ex)
        pintura = t[p + 1] if p > 0 else ""
        tp = _idx(t, "Color de tapizado", fin_gen, ex)
        tapizado = t[tp + 1] if tp > 0 else ""
        e1 = _idx(t, "Extras", fin_gen, ex)
        e2 = _idx(t, "Extras", e1 + 1, ex) if e1 > 0 else -1
        if e2 > 0:
            extras = _lista_hasta(t, e2 + 1, {"Exterior", "Garantía total", "Interior"})
        elif e1 > 0:   # solo la lista con códigos: quitar el código ("PF2 ...")
            extras = [re.sub(r"^[0-9A-Z]{3,4}\s+", "", x)
                      for x in _lista_hasta(t, e1 + 1, {"Exterior", "Garantía total", "Interior", "Tipo de pintura"})]
    extras = [x for x in dict.fromkeys(extras) if x and not _EXTRAS_RUIDO.search(x)]

    serie = _serie(t, ex, ce if ce > 0 else len(t)) if ex > 0 else {}

    dim_i = _idx(t, "Dimensiones", ce if ce > 0 else ini)
    dims = _pares(t, dim_i, dim_i + 30, {"Batalla": "batalla", "Largo": "largo", "Ancho": "ancho",
                                         "Alto": "alto", "Peso": "peso"})
    pre_i = _idx(t, "Prestaciones", dim_i if dim_i > 0 else ini)
    pre = _pares(t, pre_i, pre_i + 20, {"Velocidad máxima": "vmax", "Aceleración": "aceleracion",
                                        "Consumo carretera": "consumo_carretera",
                                        "Consumo urbano": "consumo_urbano",
                                        "Consumo mixto": "consumo", "Neumáticos": "neumaticos"})
    for k, v in pre.items():
        gen.setdefault(k, v)

    return _normalizar({
        "fuente": "dwa",
        "gen": gen, "dims": dims, "pintura": pintura, "tapizado": tapizado,
        "extras": _agrupar_extras(extras), "serie": serie,
    })


def extraer_mf(html_src: str) -> dict:
    t = _tokens(html_src)
    ini = _idx(t, "Características principales")
    if ini < 0:
        raise ValueError("no se encontró 'Características principales'")
    es = _idx(t, "Equipamiento de serie", ini)
    ee = _idx(t, "Equipamiento extra", ini)
    dt = _idx(t, "Datos técnicos", ini)

    gen = _pares(t, ini, es if es > 0 else ini + 30, {
        "Matriculación": "matriculacion", "Kilómetros": "km", "Combustible": "combustible",
        "Potencia": "potencia", "Cambio": "cambio", "Puertas": "puertas", "Plazas": "plazas",
        "Color": "color", "Carrocería": "carroceria",
    })
    serie = _serie(t, es, ee if ee > 0 else dt) if es > 0 else {}

    extras: dict[str, list[str]] = {}
    if ee > 0:
        grupo = None
        k = _idx(t, "Extras incluidos", ee) + 1
        while 0 < k < len(t) and not t[k].startswith("PVP nuevo") and t[k] != "Datos técnicos":
            if t[k] in ("Seguridad", "Confort", "Extras"):
                grupo = {"Seguridad": "Seguridad y asistentes", "Extras": "Otros extras"}.get(t[k], t[k])
                extras.setdefault(grupo, [])
            elif grupo:
                extras[grupo].append(t[k])
            k += 1
        # "Extras incluidos": opciones de fábrica con su precio (código, nombre, precio)
        e = _idx(t, "EXTRAS", ee, dt)
        opciones = []
        if e > 0:
            k = e + 1
            while k + 2 < dt and t[k] != "Extras:":
                if re.fullmatch(r"[0-9A-Z]{2,4}", t[k]) and "€" in t[k + 2]:
                    opciones.append(t[k + 1])
                    k += 3
                else:
                    k += 1
        opciones = [x for x in opciones if not _EXTRAS_RUIDO.search(x)]
        if opciones:
            extras = {"Opciones de fábrica": opciones, **extras}

    tec = _pares(t, dt, dt + 80, {
        "Altura": "alto", "Anchura": "ancho", "Longitud": "largo", "Capacidad maletero": "maletero",
        "Batalla": "batalla", "Peso": "peso", "Peso Máximo Admitido": "peso_max",
        "Capacidad del depósito": "deposito", "Velocidad Máxima": "vmax", "Aceleración": "aceleracion",
        "Emisión CO2": "co2", "Consumo Carretera": "consumo_carretera", "Consumo Urbano": "consumo_urbano",
        "Consumo Combinado-Mixto": "consumo", "Número de Cilindros": "cilindros", "Cilindrada": "cilindrada",
        "Par Motor": "par", "Estándar de emisiones": "normativa", "Tipo de Cambio": "tipo_cambio",
        "Tracción": "traccion", "Neumáticos delanteros": "neumaticos",
        "Autonomía": "autonomia_electrica", "Capacidad batería": "bateria",
    }) if dt > 0 else {}
    dims = {k: tec.pop(k) for k in ("alto", "ancho", "largo", "batalla", "peso", "peso_max", "deposito")
            if k in tec}
    if "maletero" in tec:
        gen["maletero"] = tec.pop("maletero")
        # MF publica a veces la capacidad con los asientos abatidos (p.ej. 1.598 l)
        litros = re.sub(r"\D", "", gen["maletero"])
        if litros and int(litros) > 1000:
            gen["maletero"] = "hasta " + gen["maletero"]
    tec.pop("tipo_cambio", None)
    gen.update({k: v for k, v in tec.items() if k not in gen})

    etiqueta = re.search(r'alt="Distintivo ambiental ([^"]+)"', html_src)
    if etiqueta:
        gen["etiqueta"] = etiqueta.group(1)
    return _normalizar({"fuente": "mf", "gen": gen, "dims": dims, "pintura": "", "tapizado": "",
                        "extras": extras, "serie": serie})


def _normalizar(f: dict) -> dict:
    g = f["gen"]
    # Potencia siempre como "204 CV (150 kW)" — el CV es lo que entiende el cliente
    m = re.search(r"CV,\s*(\d+)\s*Nm", g.get("potencia", ""))   # MF: "85 kW (115 CV, 200 Nm)"
    if m:
        g.setdefault("par", f"{m.group(1)} Nm")
    m = re.search(r"(\d+)\s*kW\s*\((\d+)\s*CV", g.get("potencia", ""), re.I)
    if m:
        g["potencia"] = f"{m.group(2)} CV ({m.group(1)} kW)"
    if g.get("cambio"):
        g["cambio"] = g["cambio"][0].upper() + g["cambio"][1:]
    if g.get("garantia"):
        g["garantia"] = g["garantia"].replace(" de garantía de fábrica", " (de fábrica)")
        m = re.fullmatch(r"Garantía Das WeltAuto \((.+)\)", g["garantia"])
        if m:
            g["garantia"] = f"{m.group(1)} (Das WeltAuto)"
    if g.get("traccion"):
        g["traccion"] = {"Delantero": "Delantera", "Trasero": "Trasera"}.get(g["traccion"], g["traccion"])
    # Eléctricos: DWA repite el consumo en kWh dentro de "Consumo" (con un "g/km" suelto)
    if "kWh" in g.get("consumo", ""):
        g.setdefault("consumo_electrico", re.sub(r"\s*g/km$", "", g["consumo"]))
        g.pop("consumo")
    for k in ("aceleracion",):
        if g.get(k):
            g[k] = g[k].replace(" segundos", " s").replace(" s.", " s")
    for k in ("vmax",):
        if g.get(k):
            g[k] = g[k].replace("Km/h", "km/h")
    for k in ("consumo", "consumo_urbano", "consumo_carretera"):
        if g.get(k):
            g[k] = re.sub(r"\s*l/100\s*km", " l/100 km", g[k], flags=re.I)
            if not re.search(r"\d", g[k]):
                g.pop(k)
    for k in ("consumo", "consumo_urbano", "consumo_carretera", "co2"):
        if g.get(k):
            g[k] = re.sub(r"(\d)\.(\d)", r"\1,\2", g[k]).replace(",0 g/km", " g/km")
    if g.get("co2"):
        g["co2"] = re.sub(r"g\s*r?/km", "g/km", g["co2"])
        if not re.search(r"[1-9]", g["co2"]):
            g.pop("co2")
    return f


# ── Traducción (una llamada a Gemini por coche, guardada con la ficha) ──────

def _textos_traducibles(f: dict) -> list[str]:
    g = f["gen"]
    textos = [f.get("pintura", ""), f.get("tapizado", "")]
    textos += [g.get(k, "") for k in ("combustible", "cambio", "traccion", "color", "carroceria", "garantia", "maletero",
                                      "garantia_bateria", "cilindros")]
    for grupos in (f.get("extras", {}), f.get("serie", {})):
        for items in grupos.values():
            textos += items
    return [x for x in dict.fromkeys(textos) if x and re.search(r"[A-Za-zÁÉÍÓÚáéíóúñ]{3}", x)]


def _cliente_gemini():
    key = None
    if CONFIG_PATH.exists():
        for linea in CONFIG_PATH.read_text(encoding="utf-8").splitlines():
            if linea.strip().startswith("GOOGLE_API_KEY="):
                key = linea.split("=", 1)[1].strip() or None
    if not key:
        return None
    try:
        from google import genai
        return genai.Client(api_key=key)
    except Exception:
        return None


def traducir(f: dict, client) -> dict[str, str]:
    """{texto_es: texto_en}. Si falla, devuelve {} y la ficha se ve en español."""
    textos = _textos_traducibles(f)
    if not textos or client is None:
        return {}
    prompt = ("Traduce al inglés cada texto de esta lista (ficha técnica de un coche usado en un "
              "concesionario de España), tono natural para un comprador angloparlante. Devuelve SOLO "
              "un JSON: una lista con el mismo número de elementos y en el mismo orden, sin "
              "explicaciones ni markdown:\n\n" + json.dumps(textos, ensure_ascii=False))
    try:
        r = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
        texto = (r.text or "").strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        lista = json.loads(texto)
        if isinstance(lista, list) and len(lista) == len(textos):
            return {es: str(en) for es, en in zip(textos, lista) if en}
    except Exception as e:
        print(f"    ⚠️  traducción falló: {e.__class__.__name__}")
    return {}


# ── Descarga (solo coches sin ficha guardada) ───────────────────────────────

def _huella(car: dict) -> str:
    return hashlib.sha1(f'{car.get("modelo")}|{car.get("version")}'.encode()).hexdigest()[:10]


def _coincide(car: dict, f: dict, html_src: str) -> bool:
    """El anuncio leído ES este coche (DWA recicla URLs de coches vendidos)."""
    if f["fuente"] == "mf":
        return f"-{car['motorflash_id']}" in html_src
    km_web = re.sub(r"\D", "", f["gen"].get("km", ""))
    km_car = re.sub(r"\D", "", str(car.get("km", "")))
    return (not km_web or not km_car or km_web == km_car) and car.get("version", "")[:20] in html.unescape(html_src)


async def _descargar(pendientes: list[dict]) -> dict[str, dict]:
    from playwright.async_api import async_playwright
    nuevas: dict[str, dict] = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36")
        page = await ctx.new_page()
        for car in pendientes:
            es_mf = car.get("fuente") == "motorflash"
            url = car.get("url_motorflash") if es_mf else DASWELTAUTO + car["url"]
            etiqueta = f'[{car["n"]:02d}] {car["modelo"]}'
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=40000)
                await page.wait_for_timeout(3500)
                src = await page.content()
                f = extraer_mf(src) if es_mf else extraer_dwa(src)
                if not _coincide(car, f, src):
                    print(f"  ⚠️  {etiqueta}: el anuncio ya no corresponde a este coche — se omite")
                    continue
                f["huella"] = _huella(car)
                nuevas[clave_ficha(car)] = f
                print(f"  ✓ {etiqueta}: {sum(map(len, f['serie'].values()))} de serie, "
                      f"{sum(map(len, f['extras'].values()))} extras, {len(f['dims'])} medidas")
            except Exception as e:
                print(f"  ⚠️  {etiqueta}: no se pudo leer la ficha ({e.__class__.__name__}: {str(e)[:80]})")
        await browser.close()
    return nuevas


def cargar_fichas() -> dict:
    if FICHAS_PATH.exists():
        try:
            return json.loads(FICHAS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def main():
    coches = json.loads(DATOS_PATH.read_text(encoding="utf-8"))
    fichas = cargar_fichas()
    vigentes = {clave_ficha(c) for c in coches} - {""}
    # Olvidar fichas de coches que ya no están en la lista
    fichas = {k: v for k, v in fichas.items() if k in vigentes}

    pendientes = [c for c in coches
                  if c.get("estado") != "Retirado" and clave_ficha(c)
                  and (c.get("url_motorflash") if c.get("fuente") == "motorflash" else c.get("url"))
                  and fichas.get(clave_ficha(c), {}).get("huella") != _huella(c)]
    print(f"\n  📋 Fichas técnicas: {len(fichas)} guardadas, {len(pendientes)} por leer")
    if pendientes:
        fichas.update(asyncio.run(_descargar(pendientes)))
    # Traducir las nuevas y reintentar las que otro día quedaron sin traducir
    sin_ingles = [f for f in fichas.values() if not f.get("en") and _textos_traducibles(f)]
    if sin_ingles:
        client = _cliente_gemini()
        for f in sin_ingles:
            f["en"] = traducir(f, client)
        print(f"  🌐 {sum(1 for f in sin_ingles if f['en'])}/{len(sin_ingles)} ficha(s) traducida(s) al inglés")
    FICHAS_PATH.write_text(json.dumps(fichas, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  ✓ fichas_tecnicas.json: {len(fichas)} coches")


# ── HTML de los 4 bloques ────────────────────────────────────────────────────

_ICONOS = {
    "cal":    '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    "km":     '<path d="M4 17a8 8 0 1 1 16 0"/><path d="M12 17l4-5"/><circle cx="12" cy="17" r="1.3"/>',
    "fuel":   '<path d="M5 21V5a2 2 0 0 1 2-2h6a2 2 0 0 1 2 2v16M3 21h14M7 8h6"/><path d="M15 10h2a2 2 0 0 1 2 2v5a1.5 1.5 0 0 0 3 0V9l-3-3"/>',
    "bolt":   '<path d="M13 2L4 14h7l-1 8 9-12h-7z"/>',
    "gear":   '<circle cx="6" cy="6" r="2"/><circle cx="12" cy="6" r="2"/><circle cx="18" cy="6" r="2"/><circle cx="6" cy="18" r="2"/><circle cx="12" cy="18" r="2"/><path d="M6 8v8M12 8v8M18 8v4H6"/>',
    "wheel":  '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3"/><path d="M12 3v6M12 15v6M3 12h6M15 12h6"/>',
    "door":   '<path d="M5 21V8l6-5h8v18z"/><path d="M5 11h14M15 15h2"/>',
    "seat":   '<path d="M7 3h5l1 10H8z"/><path d="M8 13h9l1 5H7"/><path d="M8 18v3M17 18v3"/>',
    "paint":  '<path d="M19 11c0 5-3 9-7 9s-7-4-7-9c0-4 7-9 7-9s7 5 7 9z"/>',
    "car":    '<path d="M3 16v-3l2-5h14l2 5v3z"/><circle cx="7.5" cy="16.5" r="1.8"/><circle cx="16.5" cy="16.5" r="1.8"/>',
    "bag":    '<rect x="4" y="7" width="16" height="13" rx="2"/><path d="M9 7V4h6v3"/>',
    "shield": '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
    "leaf":   '<path d="M5 19c0-9 6-14 15-14 0 9-5 15-14 15"/><path d="M5 19l7-7"/>',
}

_ETIQUETAS = {  # clave → (es, en)
    "matriculacion": ("Matriculación", "Registered"), "km": ("Kilómetros", "Mileage"),
    "combustible": ("Combustible", "Fuel"), "potencia": ("Potencia", "Power"),
    "cambio": ("Cambio", "Gearbox"), "traccion": ("Tracción", "Drive"),
    "puertas": ("Puertas", "Doors"), "plazas": ("Plazas", "Seats"), "color": ("Color", "Colour"),
    "carroceria": ("Carrocería", "Body type"), "maletero": ("Maletero", "Boot"),
    "garantia": ("Garantía", "Warranty"), "etiqueta": ("Etiqueta DGT", "Emissions label"),
    "largo": ("Largo", "Length"), "ancho": ("Ancho", "Width"), "alto": ("Alto", "Height"),
    "batalla": ("Batalla", "Wheelbase"), "peso": ("Peso", "Weight"),
    "peso_max": ("Peso máximo admitido", "Max. permitted weight"), "deposito": ("Depósito", "Fuel tank"),
    "consumo": ("Consumo combinado (WLTP)", "Combined consumption (WLTP)"),
    "consumo_urbano": ("Consumo urbano", "Urban consumption"),
    "consumo_carretera": ("Consumo carretera", "Extra-urban consumption"),
    "co2": ("Emisiones CO₂", "CO₂ emissions"), "autonomia": ("Autonomía total", "Total range"),
    "par": ("Par motor", "Torque"), "vmax": ("Velocidad máxima", "Top speed"),
    "aceleracion": ("Aceleración 0-100 km/h", "0-100 km/h"), "cilindrada": ("Cilindrada", "Displacement"),
    "cilindros": ("Cilindros", "Cylinders"), "normativa": ("Normativa de emisiones", "Emissions standard"),
    "neumaticos": ("Neumáticos", "Tyres"),
    "autonomia_electrica": ("Autonomía eléctrica", "Electric range"), "bateria": ("Batería", "Battery"),
    "consumo_electrico": ("Consumo eléctrico", "Electric consumption"),
    "garantia_bateria": ("Garantía de batería", "Battery warranty"),
}
_GRUPOS_EN = {
    "Seguridad y asistentes": "Safety & driver assistance", "Confort": "Comfort",
    "Tecnología y conectividad": "Technology & connectivity", "Diseño": "Design",
    "Otros extras": "Other extras", "Opciones de fábrica": "Factory options",
    "Exterior": "Exterior", "Interior": "Interior", "Seguridad": "Safety",
}


def bloques_html(f: dict, car: dict, i18n_span) -> str:
    """Los 4 bloques de la ficha. `i18n_span(es, en)` es el de generar_web.py
    (toggle de idioma del header)."""
    from html import escape as e
    g, dims, en = f["gen"], f["dims"], f.get("en", {})

    def t(texto: str) -> str:
        return i18n_span(texto, en.get(texto, texto))

    def lab(clave: str) -> str:
        return i18n_span(*_ETIQUETAS[clave])

    def ico(k: str) -> str:
        return f'<svg viewBox="0 0 24 24" aria-hidden="true">{_ICONOS[k]}</svg>'

    # 1 — Características principales (hasta 10, en el orden que más importa)
    valores = dict(g)
    valores.setdefault("matriculacion", car.get("fecha", ""))
    valores.setdefault("combustible", car.get("combustible", ""))
    valores.setdefault("cambio", car.get("cambio", ""))
    if car.get("km"):
        valores["km"] = f'{car["km"]} km'.replace(" km km", " km")
    if f.get("pintura"):
        valores["color"] = f["pintura"]
    orden = [("matriculacion", "cal"), ("km", "km"), ("combustible", "fuel"), ("potencia", "bolt"),
             ("cambio", "gear"), ("traccion", "wheel"), ("puertas", "door"), ("plazas", "seat"),
             ("color", "paint"), ("carroceria", "car"), ("maletero", "bag"), ("garantia", "shield"),
             ("etiqueta", "leaf")]
    tiles = [(k, i) for k, i in orden if valores.get(k)][:10]
    tiles_html = "".join(
        f'<div class="ft-tile">{ico(i)}<div><span>{lab(k)}</span><strong>{t(valores[k])}</strong></div></div>'
        for k, i in tiles)
    out = [f'<section class="ft-card"><h3 class="ft-h">{i18n_span("Características principales", "Key features")}</h3>'
           f'<div class="ft-tiles">{tiles_html}</div></section>']

    def grupos_html(grupos: dict, clase: str) -> str:
        return "".join(
            f'<div class="ft-grupo"><h4>{i18n_span(n, _GRUPOS_EN.get(n, n))} <em>{len(v)}</em></h4>'
            f'<ul class="{clase}">' + "".join(f"<li>{t(x)}</li>" for x in v) + "</ul></div>"
            for n, v in grupos.items() if v)

    def plegable(id_: str, contenido: str, total: int, es: str, en_: str) -> str:
        if total <= 8:
            return f'<div class="ft-grupos">{contenido}</div>'
        return (f'<div class="ft-grupos ft-plegable" id="{id_}">{contenido}</div>'
                f'<button class="ft-vermas" data-es="{e(es)}" data-en="{e(en_)}" onclick="ftToggle(this,\'{id_}\')">'
                f'{i18n_span(es, en_)}</button>')

    # 2 — Equipamiento extra
    total_extras = sum(len(v) for v in f["extras"].values())
    if total_extras:
        chips = "".join(
            f'<span class="ft-chip"><b>{i18n_span(a, b)}</b> {t(v)}</span>'
            for a, b, v in [("Pintura", "Paint", f.get("pintura")), ("Tapicería", "Upholstery", f.get("tapizado"))] if v)
        out.append(
            f'<section class="ft-card"><div class="ft-head"><h3 class="ft-h">{i18n_span("Equipamiento extra", "Optional equipment")}</h3>'
            f'<span class="ft-count">{i18n_span(f"{total_extras} extras", f"{total_extras} extras")}</span></div>'
            + (f'<div class="ft-chips">{chips}</div>' if chips else "")
            + plegable("ft-extras", grupos_html(f["extras"], "ft-check"), total_extras,
                       f"Ver los {total_extras} extras", f"See all {total_extras} extras")
            + "</section>")

    # 3 — Equipamiento de serie
    total_serie = sum(len(v) for v in f["serie"].values())
    if total_serie:
        out.append(
            f'<section class="ft-card"><h3 class="ft-h">{i18n_span("Equipamiento de serie", "Standard equipment")}</h3>'
            + plegable("ft-serie", grupos_html(f["serie"], "ft-list"), total_serie,
                       "Ver todo el equipamiento de serie", "See all standard equipment")
            + "</section>")

    # 4 — Datos técnicos (pestañas; solo las que tienen datos)
    def tabla(claves: list[str], fuente: dict) -> str:
        filas = [(k, fuente[k]) for k in claves if fuente.get(k)]
        return '<dl class="ft-dl">' + "".join(f"<div><dt>{lab(k)}</dt><dd>{t(v)}</dd></div>" for k, v in filas) + "</dl>" if filas else ""

    dims_todas = {**dims, "maletero": g.get("maletero", ""), "puertas": g.get("puertas", "")}
    grandes = "".join(f'<div><strong>{e(dims[k])}</strong><span>{lab(k)}</span></div>'
                      for k in ("largo", "ancho", "alto") if dims.get(k))
    pestanas = [
        (("Dimensiones", "Dimensions"),
         (f'<div class="ft-dims">{grandes}</div>' if grandes else "")
         + tabla(["batalla", "peso", "peso_max", "maletero", "deposito", "puertas"], dims_todas)),
        (("Consumo", "Consumption"), tabla(["consumo", "consumo_urbano", "consumo_carretera", "co2", "autonomia"], g)),
        (("Motor", "Engine"), tabla(["potencia", "par", "vmax", "aceleracion", "cilindrada", "cilindros",
                                     "cambio", "traccion", "normativa", "neumaticos"], g)),
        (("Eléctrico", "Electric"), tabla(["autonomia_electrica", "bateria", "consumo_electrico", "garantia_bateria"], g)),
    ]
    pestanas = [(n, c) for n, c in pestanas if c]
    if pestanas:
        botones = "".join(f'<button class="ft-tab{" on" if i == 0 else ""}" onclick="ftTab(this,{i})">{i18n_span(*n)}</button>'
                          for i, (n, _) in enumerate(pestanas))
        paneles = "".join(f'<div class="ft-panel{" on" if i == 0 else ""}">{c}</div>' for i, (_, c) in enumerate(pestanas))
        out.append(f'<section class="ft-card"><h3 class="ft-h">{i18n_span("Datos técnicos", "Technical data")}</h3>'
                   f'<div class="ft-tabs">{botones}</div>{paneles}</section>')

    out.append('''<script>
function ftToggle(b,id){const p=document.getElementById(id);const a=p.classList.toggle('abierto');
 const en=document.documentElement.lang==='en'||(window.rdIdiomaActual&&window.rdIdiomaActual()==='en');
 const s=b.querySelector('.rd-i18n');const es=a?'Ver menos':b.dataset.es,eng=a?'See less':b.dataset.en;
 s.dataset.es=es;s.dataset.en=eng;s.textContent=en?eng:es;}
function ftTab(b,i){const c=b.closest('.ft-card');c.querySelectorAll('.ft-tab').forEach((x,k)=>x.classList.toggle('on',k===i));
 c.querySelectorAll('.ft-panel').forEach((x,k)=>x.classList.toggle('on',k===i));}
</script>''')
    return "\n".join(out)


if __name__ == "__main__":
    main()
