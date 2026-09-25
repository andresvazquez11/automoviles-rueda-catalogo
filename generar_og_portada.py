"""
generar_og_portada.py
=====================
Imagen de previsualización de la portada (la que muestran WhatsApp,
Facebook, etc. al compartir el enlace): assets/og-portada-{perfil}.jpg,
1200×630, una por asesor con su nombre y teléfono.

Se ejecuta a mano solo si cambia la foto de portada o los datos de un
asesor (`python3 generar_og_portada.py`). generar_web.py solo la enlaza.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from generar_web import PERFILES

BASE   = Path(__file__).parent
FUENTE = BASE / "assets" / "fonts"
W, H   = 1200, 630
ROJO   = (200, 35, 43)


def _centrado(d, y, texto, fuente, color, tracking=0):
    ancho = sum(d.textlength(c, font=fuente) + tracking for c in texto) - tracking
    x = (W - ancho) / 2
    for c in texto:
        d.text((x, y), c, font=fuente, fill=color)
        x += d.textlength(c, font=fuente) + tracking


def generar(perfil: dict) -> Path:
    foto = Image.open(BASE / "assets" / "hero-portada.jpg").convert("RGB")
    escala = max(W / foto.width, H / foto.height)
    foto = foto.resize((round(foto.width * escala), round(foto.height * escala)), Image.LANCZOS)
    x0 = (foto.width - W) // 2
    img = foto.crop((x0, 0, x0 + W, H))

    # Degradado oscuro de abajo hacia arriba para que el texto se lea
    capa = Image.new("L", (1, H))
    for y in range(H):
        capa.putpixel((0, y), int(238 * min(1, max(0, (y - H * 0.18) / (H * 0.55))) ** 0.9))
    negro = Image.new("RGB", (W, H), (20, 17, 15))
    img = Image.composite(negro, img, capa.resize((W, H)))

    d = ImageDraw.Draw(img)
    # Sombra suave del título: se dibuja en negro, se difumina y se pega debajo
    sombra = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sombra).rectangle((150, 330, W - 150, 440), fill=150)
    img = Image.composite(negro, img, sombra.filter(ImageFilter.GaussianBlur(40)))
    d = ImageDraw.Draw(img)
    titulo = ImageFont.truetype(str(FUENTE / "Oswald-SemiBold.ttf"), 92)
    lema   = ImageFont.truetype(str(FUENTE / "Oswald-Light.ttf"), 34)
    pie    = ImageFont.truetype(str(FUENTE / "Oswald-SemiBold.ttf"), 30)

    _centrado(d, 318, "AUTOMÓVILES RUEDA", titulo, (255, 255, 255), tracking=3)
    d.rectangle(((W - 120) / 2, 448, (W + 120) / 2, 453), fill=ROJO)
    _centrado(d, 470, "Coches seminuevos con garantía · SEAT · CUPRA · Volkswagen", lema, (235, 230, 222))
    _centrado(d, 540, f"{perfil['nombre']}  ·  {perfil['telefono']}", pie, (240, 194, 122), tracking=1)
    d.rectangle((0, H - 8, W, H), fill=ROJO)

    destino = BASE / "assets" / f"og-portada-{perfil['id']}.jpg"
    img.save(destino, "JPEG", quality=86, optimize=True, progressive=True)
    return destino


if __name__ == "__main__":
    for p in PERFILES:
        ruta = generar(p)
        print(f"  ✓ {ruta.name} ({ruta.stat().st_size // 1024} KB)")
