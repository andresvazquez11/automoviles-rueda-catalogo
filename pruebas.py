"""
pruebas.py — bloque "Míralo en acción · pruebas en vídeo" al final de la ficha.

Los vídeos viven en pruebas.json, por MODELO (como prensa.json): pruebas reales
de medios especializados en YouTube, con el id comprobado. Se filtran por año
de matriculación y versión para no mezclar generaciones. Nunca se inventan.
"""
from __future__ import annotations

import json
from html import escape as e
from pathlib import Path

from prensa import _anio_matriculacion, _aplica, _clave

PRUEBAS_PATH = Path(__file__).parent / "pruebas.json"
MAX_VIDEOS = 3


def cargar() -> dict:
    try:
        return json.loads(PRUEBAS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def bloque_html(car: dict, datos: dict, i18n_span) -> str:
    por_clave = {_clave(k): v for k, v in datos.items() if not k.startswith("_")}
    entrada = por_clave.get(_clave(car.get("modelo", "")))
    if not entrada:
        return ""
    anio = _anio_matriculacion(car)
    videos = [v for v in entrada.get("videos", []) if _aplica(v, car, anio)][:MAX_VIDEOS]
    if not videos:
        return ""

    tarjetas = "".join(
        f'<a class="rd-video" href="https://www.youtube.com/watch?v={e(v["youtube"])}" target="_blank" rel="noopener nofollow">'
        f'<span class="rd-video-thumb"><img src="https://img.youtube.com/vi/{e(v["youtube"])}/hqdefault.jpg" '
        f'alt="{e(v["titulo"])}" loading="lazy"></span>'
        f'<b>{e(v["titulo"])}</b><small>{e(v["medio"])} · YouTube</small></a>'
        for v in videos)
    modelo = car.get("modelo", "")
    aviso = i18n_span(f"Pruebas del {modelo} publicadas por medios especializados, no de esta unidad concreta.",
                      f"Reviews of the {modelo} by specialist media (in Spanish), not of this specific car.")
    return (f'<section class="ft-card rd-videos-card"><div class="ft-head">'
            f'<h3 class="ft-h">{i18n_span("Míralo en acción · pruebas en vídeo", "See it in action · video reviews")}</h3></div>'
            f'<div class="rd-videos">{tarjetas}</div>'
            f'<p class="pr-nota">{aviso}</p></section>')
