"""Traducción al alemán de la web (tercer idioma, junto a español e inglés).

Un solo diccionario {texto en español: texto en alemán} en traducciones_de.json
sirve para TODO: textos fijos de la web, ficha técnica, versión/color/
equipamiento de cada coche. Cada texto se traduce UNA vez con Gemini y queda
guardado; el JSON se sube al repo (lo commitea GitHub Actions).

Uso desde generar_web.py:
  - aleman.de(es, en)        → alemán si ya está en el diccionario; si no, lo
                               apunta como pendiente y devuelve el inglés (la
                               web nunca se ve rota, solo en inglés ese rato).
  - aleman.traducir_pendientes(client) → traduce de golpe lo apuntado y guarda.
"""
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
RUTA = BASE_DIR / "traducciones_de.json"
MODELO = "gemini-3.6-flash"
LOTE = 120   # textos por llamada a Gemini

_cache: "dict[str, str] | None" = None
PENDIENTES: "dict[str, str]" = {}   # es → en (el inglés da contexto a la traducción)


def _cargar() -> dict:
    global _cache
    if _cache is None:
        try:
            _cache = json.loads(RUTA.read_text(encoding="utf-8")) if RUTA.exists() else {}
        except Exception:
            _cache = {}
    return _cache


def guardar() -> None:
    RUTA.write_text(json.dumps(_cargar(), ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


def _traducible(es: str) -> bool:
    # Números, precios, km, fechas, siglas cortas… se quedan igual.
    letras = sum(ch.isalpha() for ch in es)
    return letras >= 2


def de(es: str, en: str = "") -> str:
    """Texto en alemán para `es`. Si aún no está traducido, devuelve el inglés
    (o el español si no hay inglés) y lo apunta para traducirlo."""
    if not es:
        return es
    cache = _cargar()
    if es in cache:
        return cache[es]
    if not _traducible(es):
        return es
    PENDIENTES.setdefault(es, en or es)
    return en or es


def traducir_pendientes(client) -> int:
    """Traduce los textos apuntados con Gemini, en lotes. Devuelve cuántos
    quedaron traducidos. Sin client (sin API key) no hace nada."""
    if not PENDIENTES or client is None:
        return 0
    cache = _cargar()
    items = [(es, en) for es, en in PENDIENTES.items() if es not in cache]
    hechos = 0
    for i in range(0, len(items), LOTE):
        lote = items[i:i + LOTE]
        entrada = [{"id": j, "es": es, "en": en} for j, (es, en) in enumerate(lote)]
        prompt = (
            "Eres traductor profesional para la web de un concesionario de coches de "
            "ocasión en España (SEAT, CUPRA, Das WeltAuto). Traduce al ALEMÁN cada "
            "texto del campo \"es\" (el campo \"en\" es la versión inglesa, solo como "
            "contexto). Tono comercial, natural y de tú a usted formal (\"Sie\") como "
            "en webs de concesionarios alemanes. Usa la terminología técnica de coches "
            "habitual en Alemania (p. ej. Erstzulassung, Getriebe, Kraftstoff, "
            "Ausstattung). Mantén números, precios, unidades, emojis, flechas y "
            "nombres propios/marcas/modelos tal cual. Devuelve SOLO un JSON: una "
            "lista de objetos {\"id\": <id>, \"de\": \"<traducción>\"}, sin markdown.\n\n"
            + json.dumps(entrada, ensure_ascii=False)
        )
        try:
            r = client.models.generate_content(model=MODELO, contents=prompt)
            texto = (r.text or "").strip()
            texto = texto.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            for obj in json.loads(texto):
                j = obj.get("id")
                trad = (obj.get("de") or "").strip()
                if isinstance(j, int) and 0 <= j < len(lote) and trad:
                    cache[lote[j][0]] = trad
                    hechos += 1
        except Exception as e:
            print(f"  ⚠️  Traducción al alemán falló en un lote ({len(lote)} textos): {e}")
    for es in list(PENDIENTES):
        if es in cache:
            del PENDIENTES[es]
    guardar()
    return hechos


def mapa(textos) -> dict:
    """{es: de} solo para los textos dados que ya estén traducidos (para pasar
    al JavaScript de la página lo mínimo necesario)."""
    cache = _cargar()
    return {t: cache[t] for t in textos if t and t in cache}
