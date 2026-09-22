#!/usr/bin/env python3
"""Genera una versión de PRUEBA del catálogo con el nuevo diseño (hero con
foto de estilo de vida + parallax, hover de fotos, specs siempre visibles,
comparador, modo oscuro), con datos y fotos REALES del catálogo actual.

No toca generar_web.py ni ningún archivo de producción — escribe todo en
prueba/, aparte. Las fichas de cada coche no se duplican: se enlaza
directamente a las fichas reales que ya existen en coches/.
"""
import json
import shutil
from pathlib import Path

BASE = Path(__file__).parent
JSON_PATH = BASE / "datos_coches.json"
COCHES_DIR = BASE / "coches"
WEB_FOTOS = BASE / "web_fotos"
OUT_DIR = BASE / "prueba"
HERO_SRC = Path("/tmp/mockup_assets/hero-ibiza.png")

ACCENT = "#c8102e"


def cargar_coches() -> list[dict]:
    """Carga datos_coches.json y arma la lista de coches para la página de
    prueba: solo los que tienen ficha real Y al menos una foto real."""
    coches = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    resultado = []
    for c in coches:
        if c.get("estado") == "Retirado":
            continue
        n = c["n"]
        fichas = sorted(COCHES_DIR.glob(f"{n:02d}-*.html"))
        if not fichas:
            continue
        fotos = sorted(WEB_FOTOS.glob(f"{n:02d}/foto_*.jpg"))
        if not fotos:
            continue
        resultado.append({
            "n": n,
            "modelo": c["modelo"],
            "version": c.get("version", ""),
            "precio": c.get("precio", ""),
            "km": c.get("km", ""),
            "cambio": c.get("cambio", ""),
            "combustible": c.get("combustible", ""),
            "estado": c.get("estado", ""),
            "ficha": f"/coches/{fichas[0].name}",
            "fotos": [f"/web_fotos/{n:02d}/{f.name}" for f in fotos[:3]],
            "total_fotos": len(fotos),
        })
    return resultado


if __name__ == "__main__":
    coches = cargar_coches()
    print(f"Coches cargados para la página de prueba: {len(coches)}")
