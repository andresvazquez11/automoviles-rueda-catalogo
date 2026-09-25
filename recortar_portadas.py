"""
recortar_portadas.py
====================
Recorta el coche de la foto de portada (quita el fondo del concesionario)
para el efecto "el coche sale de la tarjeta" al pasar el ratón en el
catálogo.

- Guarda web_fotos/recortes/{id}.webp (id = ID estable del anuncio, nunca
  "n") y un registro en recortes.json con el hash de la portada usada: solo
  se vuelve a recortar si la portada cambia. Los recortes de coches que ya no
  están en la lista se borran.
- Necesita `rembg` (pip install "rembg[cpu]"). Si no está instalado, no hace
  nada: la web se genera igual, sin el efecto en esos coches.
"""
from __future__ import annotations

import hashlib, json, sys
from pathlib import Path

BASE_DIR      = Path(__file__).parent
DATOS_PATH    = BASE_DIR / "datos_coches.json"
RECORTES_DIR  = BASE_DIR / "web_fotos" / "recortes"
REGISTRO_PATH = BASE_DIR / "recortes.json"
ANCHO_MAX     = 1100   # px — suficiente para verse grande sin pesar demasiado


def clave(car: dict) -> str:
    """Igual que generar_web.id_estable_coche."""
    if car.get("motorflash_id"):
        return f"mf-{car['motorflash_id']}"
    listing_id = (car.get("url") or "").rstrip("/").split("/")[-1]
    return f"dwa-{listing_id}" if listing_id.isdigit() else ""


def portada(car: dict) -> Path | None:
    """La misma foto que la tarjeta muestra primero (ver generar_web.copiar_fotos)."""
    if car.get("fuente") == "motorflash":
        return BASE_DIR / car["fotos"][0] if car.get("fotos") else None
    return BASE_DIR / "web_fotos" / f"{car['n']:02d}" / "foto_01.jpg"


def cargar_registro() -> dict:
    try:
        return json.loads(REGISTRO_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main():
    coches = [c for c in json.loads(DATOS_PATH.read_text(encoding="utf-8"))
              if c.get("estado") != "Retirado" and clave(c)]
    registro = cargar_registro()
    vigentes = {clave(c) for c in coches}

    pendientes = []
    for c in coches:
        foto = portada(c)
        if not foto or not foto.exists():
            continue
        h = hashlib.sha1(foto.read_bytes()).hexdigest()[:16]
        destino = RECORTES_DIR / f"{clave(c)}.webp"
        if registro.get(clave(c), {}).get("hash") != h or not destino.exists():
            pendientes.append((c, foto, h, destino))

    print(f"\n  ✂️  Recortes de portada: {len(registro)} guardados, {len(pendientes)} por hacer")
    if pendientes:
        try:
            from rembg import remove, new_session
            from PIL import Image
        except ImportError:
            print("  ⚠️  rembg no está instalado — se omiten los recortes nuevos")
            pendientes = []
        else:
            sesion = new_session("u2net")
            RECORTES_DIR.mkdir(parents=True, exist_ok=True)
            for c, foto, h, destino in pendientes:
                try:
                    img = Image.open(foto).convert("RGB")
                    img.thumbnail((2000, 2000))
                    recorte = remove(img, session=sesion, post_process_mask=True)
                    caja = recorte.getchannel("A").point(lambda a: 255 if a > 20 else 0).getbbox()
                    if not caja:
                        raise ValueError("no se detectó el coche")
                    recorte = recorte.crop(caja)
                    # Un recorte que ocupa casi toda la foto = no separó el coche del fondo
                    if recorte.width * recorte.height > 0.9 * img.width * img.height:
                        raise ValueError("el recorte ocupa toda la foto")
                    recorte.thumbnail((ANCHO_MAX, ANCHO_MAX))
                    recorte.save(destino, "WEBP", quality=82, method=6)
                    registro[clave(c)] = {"hash": h, "archivo": f"web_fotos/recortes/{destino.name}",
                                          "proporcion": round(recorte.width / recorte.height, 3)}
                    print(f"  ✓ [{c['n']:02d}] {c['modelo']}")
                except Exception as e:
                    registro.pop(clave(c), None)
                    print(f"  ⚠️  [{c['n']:02d}] {c['modelo']}: {e}")

    # Limpiar recortes de coches que ya no están
    for k in list(registro):
        if k not in vigentes:
            (BASE_DIR / registro[k]["archivo"]).unlink(missing_ok=True)
            del registro[k]
    REGISTRO_PATH.write_text(json.dumps(registro, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  ✓ recortes.json: {len(registro)} coches")


if __name__ == "__main__":
    main()
    sys.stdout.flush()
    # onnxruntime (rembg) a veces aborta al cerrarse ("recursive_mutex lock
    # failed") DESPUÉS de haber guardado todo: salir sin pasar por su cierre.
    import os
    os._exit(0)
