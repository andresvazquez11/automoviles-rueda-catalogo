"""
comparador.py — datos de cada coche para el comparador completo de la portada.

Por coche devuelve {"v": textos a mostrar, "n": números para marcar el mejor
dato, "eq": equipamiento (serie + extras)}. Las filas, etiquetas ES/EN y la
regla de "mejor dato" viven en assets/comparador.js. Sin ficha técnica solo
salen los datos básicos de datos_coches.json (precio, km, fecha, combustible,
cambio, etiqueta DGT).
"""
from __future__ import annotations

import re

from confianza_dwa import garantia_corta

_NUM = re.compile(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?")

# clave del comparador → (bloque de la ficha, clave en la ficha)
_CAMPOS = {
    "cv": ("gen", "potencia"), "par": ("gen", "par"), "acel": ("gen", "aceleracion"),
    "vmax": ("gen", "vmax"), "traccion": ("gen", "traccion"),
    "consumo": ("gen", "consumo"), "co2": ("gen", "co2"),
    "aut_el": ("gen", "autonomia_electrica"), "aut": ("gen", "autonomia"),
    "maletero": ("gen", "maletero"),
    "largo": ("dims", "largo"), "ancho": ("dims", "ancho"), "alto": ("dims", "alto"),
    "batalla": ("dims", "batalla"), "peso": ("dims", "peso"),
}


def _n(texto) -> "float | int | None":
    """Primer número de un texto español ('1.717 Kg' → 1717, '7,9 s' → 7.9)."""
    if not texto:
        return None
    s = str(texto).strip()
    if s.lower().startswith("hasta"):
        return None
    m = _NUM.search(s)
    if not m:
        return None
    num = float(m.group(0).replace(".", "").replace(",", "."))
    return int(num) if num.is_integer() else num


def _limpio(texto: str) -> str:
    """'5,2 l/100 km (ciclo WLTP)' → '5,2 l/100 km'; '204 CV (150 kW)' → '204 CV'."""
    return re.sub(r"\s*\(.*?\)", "", str(texto)).strip()


def _dgt(combustible: str) -> str:
    c = (combustible or "").lower()
    if "eléctrico" in c or "electrico" in c:
        return "CERO"
    if "mild" in c:
        return "ECO"
    if "híbrido" in c or "hibrido" in c:
        return "CERO"
    return "C"


def datos(car: dict, ficha: "dict | None") -> dict:
    gen = (ficha or {}).get("gen") or {}
    v = {
        "precio": f'{car.get("precio", "")} €',
        "km": f'{car.get("km", "")} km',
        "fecha": car.get("fecha", ""),
        "comb": gen.get("combustible") or car.get("combustible", ""),
        "dgt": gen.get("etiqueta") or _dgt(car.get("combustible", "")),
        "cambio": gen.get("cambio") or car.get("cambio", ""),
    }
    n = {"precio": _n(car.get("precio")), "km": _n(car.get("km"))}

    garantia = garantia_corta(gen.get("garantia")).replace(" de garantía", "")
    if garantia:
        v["garantia"] = garantia
        n["garantia"] = _n(garantia)

    for clave, (bloque, campo) in _CAMPOS.items():
        texto = ((ficha or {}).get(bloque) or {}).get(campo)
        if texto:
            v[clave] = _limpio(texto)
            num = _n(texto)
            if num is not None:
                n[clave] = num

    extras = [i for grupo in ((ficha or {}).get("extras") or {}).values() for i in grupo]
    serie = [i for grupo in ((ficha or {}).get("serie") or {}).values() for i in grupo]
    if ficha:
        v["extras"] = str(len(extras))
        n["extras"] = len(extras)
    en = (ficha or {}).get("en") or {}
    # [texto ES, texto EN] — el EN sale de la traducción ya guardada en la ficha
    eq = [[i, en.get(i, i)] for i in extras + serie]
    return {"v": v, "n": n, "eq": eq}


def json_todos(coches: list[dict], fichas: dict, id_de, clave_de) -> str:
    """comparador.json: {id de tarjeta: datos(...)} para los coches publicados."""
    import json
    todo = {id_de(c): datos(c, fichas.get(clave_de(c))) for c in coches if c.get("estado") != "Retirado"}
    return json.dumps(todo, ensure_ascii=False, separators=(",", ":"))
