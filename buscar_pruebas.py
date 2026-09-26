#!/usr/bin/env python3
"""
buscar_pruebas.py — busca y añade SOLO vídeos de pruebas para los coches del
catálogo que todavía no tienen ninguno en pruebas.json.

Lo lanza la actualización automática (GitHub Actions) antes de generar la web,
así que cuando entra un modelo nuevo (o un año/generación sin vídeos) se busca
en YouTube sin que nadie tenga que acordarse:

1. Por cada (modelo, año de matriculación) del catálogo sin vídeos que le apliquen,
   busca "prueba {modelo} {año} review español" en YouTube.
2. Se queda con hasta 3 vídeos que sean pruebas de ESE modelo (el título nombra el
   modelo y dice prueba/review/test…, sin años de otra generación, sin Shorts ni
   directos largos), priorizando medios conocidos (km77, coches.net, Diariomotor…).
3. Comprueba cada id con el oEmbed de YouTube (existe y es público).
4. Los añade a pruebas.json con desde/hasta = año ±1 y "auto" = fecha, y lo anota
   en informe_cambios.txt (sale en el correo de la actualización).

Si YouTube no responde, no rompe nada: se reintenta en la siguiente corrida. Si no
encuentra nada, no vuelve a buscar ese modelo/año hasta pasados 7 días.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path

import requests

import pruebas
from prensa import _anio_matriculacion, _aplica, _clave

BASE = Path(__file__).parent
DATOS_PATH = BASE / "datos_coches.json"
INFORME = BASE / "informe_cambios.txt"
MAX_VIDEOS = 3
DIAS_REINTENTO = 7
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept-Language": "es-ES,es;q=0.9"}

MEDIOS_CONOCIDOS = {
    "km77.com", "coches.net", "diariomotor", "motor.es", "holycars tv", "periodismo del motor",
    "centimetros cubicos", "coches.com", "autopista", "motorpasion", "autocasion", "actualidad motor",
    "motor1 espana", "soymotor coches", "soymotor.com", "autofacil", "carwow espana", "testcoches - carlos gonzalez",
    "motor 22cv", "highmotor", "la voz de galicia",
}
EXCLUIR = ("comparativa", " vs ", " vs. ", "cual es mejor", "desguace", "accidente", "averia")
PALABRAS_PRUEBA = ("prueba", "review", "test", "analisis", "a fondo", "opinion", "probamos", "impresiones")


def _norm(s: str) -> str:
    s = (s or "").replace("․", ".")   # 'Motor․es' usa un punto especial
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


# ── Reglas (sin red, con tests) ──────────────────────────────────────────────

def _nombres_modelo(modelo: str, version: str) -> list[str]:
    """'Nissan Qashqai' → ['qashqai']; 'Abarth 500' + versión '… 595 …' → ['500', 'abarth 595']."""
    palabras = _norm(modelo).split()
    marca = palabras[0] if palabras else ""
    ultima = palabras[-1] if palabras else ""
    # "500", "Serie", "Clase" solos son ambiguos (Fiat 500, cualquier serie…) → con la marca delante
    generica = ultima.isdigit() or ultima in {"serie", "clase", "class"}
    nombres = [f"{marca} {ultima}" if generica and marca != ultima else ultima] if ultima else []
    for num in re.findall(r"\b(\d{3})\b", version or ""):
        nombres.append(f"{marca} {num}")
    return nombres


def elegir(candidatos: list[dict], modelo: str, version: str, anio: int, hoy_anio: "int | None" = None) -> list[dict]:
    hoy_anio = hoy_anio or date.today().year
    nombres = _nombres_modelo(modelo, version)
    buenos = []
    for c in candidatos:
        t = _norm(c.get("titulo", ""))
        if not any(re.search(rf"\b{re.escape(n)}\b", t) for n in nombres):
            continue
        if not any(p in t for p in PALABRAS_PRUEBA):
            continue
        if any(x in t for x in EXCLUIR):
            continue
        seg = c.get("segundos") or 0
        if seg < 120 or seg > 45 * 60:          # Shorts / directos
            continue
        if anio:
            # Otra generación: el título nombra un año que no encaja con el del coche
            # (un vídeo "2026" suele ser de un modelo más nuevo que un coche de 2025)…
            anios = [int(a) for a in re.findall(r"\b(20[0-3]\d)\b", t)]
            if anios and not any(anio - 3 <= a <= anio for a in anios):
                continue
            # …o se publicó después del año del coche (suele ser ya la generación
            # siguiente) o mucho antes.
            pub = c.get("anio_publicacion")
            if pub and not (anio - 3 <= pub <= anio):
                continue
            # "Nuevo X" publicado el mismo año que un coche ya no nuevo = la generación siguiente
            if pub == anio and anio < hoy_anio and re.search(r"\b(nuevo|nueva|new)\b", t):
                continue
        buenos.append(c)
    # medios conocidos primero, manteniendo el orden de relevancia de YouTube
    buenos.sort(key=lambda c: 0 if _norm(c.get("canal", "")) in MEDIOS_CONOCIDOS else 1)
    return buenos[:MAX_VIDEOS]


def pendientes(coches: list[dict], datos: dict, buscados: dict, hoy: str) -> list[tuple[str, str, int]]:
    """(modelo, versión de ejemplo, año) de los coches publicados que no tienen ningún vídeo."""
    por_clave = {_clave(k): v for k, v in datos.items() if not k.startswith("_")}
    hoy_d = date.fromisoformat(hoy)
    vistos, salida = set(), []
    for car in coches:
        if car.get("estado") == "Retirado":
            continue
        anio = _anio_matriculacion(car)
        clave = (_clave(car.get("modelo", "")), anio)
        if clave in vistos:
            continue
        vistos.add(clave)
        entrada = por_clave.get(clave[0]) or {}
        if any(_aplica(v, car, anio) for v in entrada.get("videos", [])):
            continue
        ultimo = buscados.get(f"{car['modelo']}|{anio}")
        if ultimo and (hoy_d - date.fromisoformat(ultimo)).days < DIAS_REINTENTO:
            continue
        salida.append((car["modelo"], car.get("version", ""), anio))
    return salida


def titulo_corto(titulo: str) -> str:
    """Quita emojis y la coletilla '| canal' del título original de YouTube."""
    t = "".join(ch for ch in titulo if unicodedata.category(ch)[0] in "LNPZ" or ch in "€/+-|")
    partes = [p.strip() for p in t.split("|") if p.strip()]
    t = partes[0] if partes and len(partes[0]) >= 12 else " · ".join(partes[:2])
    return re.sub(r"\s{2,}", " ", t).strip(" -·/")[:90]


# ── Red ──────────────────────────────────────────────────────────────────────

def _segundos(txt: str) -> int:
    n = [int(x) for x in re.findall(r"\d+", txt or "")]
    s = 0
    for x in n:
        s = s * 60 + x
    return s


def anio_publicacion(texto: str, hoy: date) -> "int | None":
    """'hace 7 años' / 'hace 7 a' → hoy.year - 7; 'hace 5 meses' / 'hace 5 m' → año de hace 5 meses."""
    m = re.search(r"(\d+)\s*([a-z]+)", _norm(texto))
    if not m:
        return None
    n, unidad = int(m.group(1)), m.group(2)
    if unidad in ("a", "ano", "anos", "year", "years", "y"):
        return hoy.year - n
    if unidad in ("m", "mes", "meses", "month", "months", "mo"):
        mes = hoy.month - n
        return hoy.year + (mes - 1) // 12
    return hoy.year


def buscar_youtube(consulta: str) -> list[dict]:
    r = requests.get("https://www.youtube.com/results",
                     params={"search_query": consulta, "hl": "es", "gl": "ES"},
                     headers=UA, cookies={"CONSENT": "YES+1", "SOCS": "CAI"}, timeout=25)
    r.raise_for_status()
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", r.text, re.S)
    if not m:
        return []
    datos = json.loads(m.group(1))

    def recorrer(o):
        if isinstance(o, dict):
            if "videoRenderer" in o:
                yield o["videoRenderer"]
            for v in o.values():
                yield from recorrer(v)
        elif isinstance(o, list):
            for v in o:
                yield from recorrer(v)

    salida = []
    for v in recorrer(datos):
        try:
            salida.append({
                "id": v["videoId"],
                "titulo": "".join(r_["text"] for r_ in v["title"]["runs"]),
                "canal": v.get("ownerText", {}).get("runs", [{}])[0].get("text", "").strip(),
                "segundos": _segundos(v.get("lengthText", {}).get("simpleText", "")),
                "anio_publicacion": anio_publicacion(v.get("publishedTimeText", {}).get("simpleText", ""),
                                                     date.today()),
            })
        except (KeyError, IndexError):
            continue
    return salida[:20]


def verificar(video_id: str) -> "dict | None":
    try:
        r = requests.get("https://www.youtube.com/oembed",
                         params={"format": "json", "url": f"https://www.youtube.com/watch?v={video_id}"},
                         headers=UA, timeout=15)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


# ── Principal ────────────────────────────────────────────────────────────────

def main() -> int:
    hoy = datetime.now().date().isoformat()
    coches = json.loads(DATOS_PATH.read_text(encoding="utf-8"))
    datos = pruebas.cargar()
    buscados = datos.setdefault("_buscados", {})
    tareas = pendientes(coches, datos, buscados, hoy)
    if not tareas:
        print("🎬  Pruebas en vídeo: todos los coches tienen vídeos.")
        return 0

    informe = []
    for modelo, version, anio in tareas:
        consulta = f"prueba {modelo} {anio or ''} review español".replace("  ", " ")
        try:
            candidatos = buscar_youtube(consulta)
        except Exception as e:
            print(f"  ⚠️  YouTube no respondió para {modelo} {anio}: {e} — se reintenta la próxima vez")
            continue
        elegidos = [c for c in elegir(candidatos, modelo, version, anio) if verificar(c["id"])]
        buscados[f"{modelo}|{anio}"] = hoy
        if not elegidos:
            print(f"  🎬  {modelo} {anio}: sin pruebas en vídeo que cumplan los filtros")
            continue
        entrada = datos.setdefault(modelo, {"videos": []})
        existentes = {v["youtube"] for v in entrada["videos"]}
        for c in elegidos:
            if c["id"] in existentes:
                continue
            nuevo = {"youtube": c["id"], "titulo": titulo_corto(c["titulo"]), "medio": c["canal"], "auto": hoy}
            if anio:
                nuevo.update({"desde": anio - 1, "hasta": anio + 1})
            entrada["videos"].append(nuevo)
        informe.append(f"  • {modelo} ({anio}): {len(elegidos)} vídeo(s) — " + ", ".join(c["canal"] for c in elegidos))
        print(informe[-1])

    pruebas.PRUEBAS_PATH.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if informe and INFORME.exists():
        with INFORME.open("a", encoding="utf-8") as f:
            f.write("\n🎬 PRUEBAS EN VÍDEO AÑADIDAS AUTOMÁTICAMENTE\n" + "\n".join(informe) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
