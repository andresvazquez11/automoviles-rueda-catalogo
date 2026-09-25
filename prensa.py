"""
prensa.py — bloque "Lo que dice la prensa" de la ficha de coche.

Las citas viven en prensa.json, por MODELO (no por coche): se buscan una vez
y sirven para todas las unidades de ese modelo. Son frases reales,
verificadas palabra por palabra en el artículo original, con medio, autor,
fecha y enlace. Nunca se generan ni se parafrasean automáticamente.
"""
from __future__ import annotations

import json, re, unicodedata
from html import escape as e
from pathlib import Path

PRENSA_PATH = Path(__file__).parent / "prensa.json"
_MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
          "septiembre", "octubre", "noviembre", "diciembre"]
_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
           "September", "October", "November", "December"]


def cargar() -> dict:
    try:
        return json.loads(PRENSA_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _anio_matriculacion(car: dict) -> int:
    m = re.search(r"(\d{4})", str(car.get("fecha", "")))
    return int(m.group(1)) if m else 0


def _clave(modelo: str) -> str:
    """'CUPRA León' y 'CUPRA Leon', 'ŠKODA Karoq' y 'Skoda Karoq' → misma clave."""
    sin_tildes = unicodedata.normalize("NFD", modelo)
    return "".join(ch for ch in sin_tildes if not unicodedata.combining(ch)).lower().strip()


def _aplica(cita: dict, car: dict, anio: int) -> bool:
    version = car.get("version", "")
    return ((not cita.get("desde") or anio >= cita["desde"])
            and (not cita.get("hasta") or (anio and anio <= cita["hasta"]))
            and (not cita.get("version_contiene") or cita["version_contiene"].lower() in version.lower())
            and (not cita.get("version_empieza") or version.startswith(cita["version_empieza"])))


def bloque_html(car: dict, prensa: dict, i18n_span) -> str:
    por_clave = {_clave(k): v for k, v in prensa.items() if not k.startswith("_")}
    datos = por_clave.get(_clave(car.get("modelo", "")))
    if not datos:
        return ""
    anio = _anio_matriculacion(car)
    citas = [c for c in datos.get("citas", []) if _aplica(c, car, anio)]
    ncap = datos.get("euroncap")
    if not citas:   # solo estrellas, sin ninguna cita → no merece un bloque propio
        return ""

    tarjetas = []
    for c in citas[:3]:
        a, m, _ = (c["fecha"].split("-") + ["", "", ""])[:3]
        fecha_es = f"{_MESES[int(m) - 1]} {a}" if m else a
        fecha_en = f"{_MONTHS[int(m) - 1]} {a}" if m else a
        nota = f' · <b>{i18n_span("Nota", "Score")} {e(c["nota"])}</b>' if c.get("nota") else ""
        tarjetas.append(
            f'<figure class="pr-cita"><blockquote>{e(c["texto"])}</blockquote>'
            f'<figcaption><strong>{e(c["medio"])}</strong>'
            f'<span>{e(c["autor"])} · {i18n_span(fecha_es, fecha_en)}{nota}</span>'
            f'<a href="{e(c["url"])}" target="_blank" rel="noopener nofollow">'
            f'{i18n_span("Leer la prueba ↗", "Read the review ↗")}</a></figcaption></figure>')

    ncap_html = ""
    if ncap:
        ncap_html = (f'<a class="pr-ncap" href="{e(ncap["url"])}" target="_blank" rel="noopener nofollow">'
                     f'<span class="pr-estrellas">{"★" * int(ncap.get("estrellas", 5))}</span>'
                     f'{i18n_span("Euro NCAP · máxima nota en seguridad", "Euro NCAP · top safety rating")}</a>')

    modelo = car.get("modelo", "")
    aviso = i18n_span(f"Opiniones publicadas sobre el {modelo} en pruebas de prensa especializada, "
                      "no sobre esta unidad concreta.",
                      f"Published press opinions about the {modelo} (quotes in Spanish), "
                      "not about this specific car.")
    return (f'<section class="ft-card pr-card"><div class="ft-head">'
            f'<h3 class="ft-h">{i18n_span("Lo que dice la prensa", "What the press says")}</h3>{ncap_html}</div>'
            f'<div class="pr-citas">{"".join(tarjetas)}</div>'
            f'<p class="pr-nota">{aviso}</p>'
            f'</section>')
