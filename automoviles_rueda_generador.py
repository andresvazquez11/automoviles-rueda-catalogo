"""
Generador de catálogo - Automóviles Rueda / Das WeltAuto
Genera: PDF (1 coche/página) con enlaces clickables a DWA o MotorFlash

Lee datos de datos_coches.json — ejecutar tras actualizar_catalogo.py
"""

import json
import sys
from pathlib import Path
from io import BytesIO

# ── Instalación automática de dependencias ─────────────────────────────────
def instalar_si_falta(paquete):
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", paquete, "-q"])

for pkg in ["fpdf2", "pillow"]:
    try:
        __import__(pkg.replace("-", "_").replace("2", ""))
    except ImportError:
        print(f"Instalando {pkg}...")
        instalar_si_falta(pkg)

from fpdf import FPDF
from PIL import Image

# ── Configuración ──────────────────────────────────────────────────────────
DASWELTAUTO = "https://www.dasweltauto.es"
BASE_DIR    = Path(__file__).parent
JSON_PATH   = BASE_DIR / "datos_coches.json"
WEB_FOTOS   = BASE_DIR / "web_fotos"
FOTOS_DIR   = BASE_DIR / "fotos"
PDF_PATH    = BASE_DIR / "catalogo_automoviles_rueda.pdf"

# ── Colores de marca ───────────────────────────────────────────────────────
def color_marca(modelo):
    m = modelo.upper()
    if "CUPRA" in m:
        return (40, 30, 15), (198, 151, 71)    # fondo oscuro, dorado CUPRA
    elif "SEAT" in m:
        return (15, 25, 50), (255, 80, 0)       # azul oscuro, naranja SEAT
    else:
        return (10, 10, 10), (0, 160, 220)      # negro, azul VW/otro

# ── Buscar foto local ──────────────────────────────────────────────────────
def buscar_foto(car, idx):
    """Devuelve Path a la primera foto disponible para este coche."""
    # 1) fotos[] del JSON (rutas absolutas descargadas por el scraper)
    for p in car.get("fotos", []):
        fp = Path(p)
        if fp.exists() and fp.stat().st_size > 1000:
            return fp

    # 2) web_fotos/{idx:02d}/ (copia creada por generar_web.py)
    carpeta = WEB_FOTOS / f"{idx:02d}"
    if carpeta.exists():
        candidatos = sorted(carpeta.glob("foto_*.jpg"))
        if candidatos:
            return candidatos[0]
        candidatos = sorted(carpeta.glob("*.jpg"))
        if candidatos:
            return candidatos[0]

    return None

# ── Crear URL pública del coche ────────────────────────────────────────────
def url_coche(car):
    if car.get("fuente") == "motorflash":
        return car.get("url_motorflash", ""), "MotorFlash"
    url = car.get("url", "")
    return (DASWELTAUTO + url if url else ""), "Das WeltAuto"

# ── Creación del PDF ───────────────────────────────────────────────────────
def crear_pdf(cars_data):
    total = len(cars_data)
    pdf = FPDF(orientation="L", unit="mm", format="A4")   # A4 apaisado 297×210
    pdf.set_auto_page_break(False)

    tmp_files = []

    for idx, car in enumerate(cars_data, start=1):
        pdf.add_page()

        foto_path = buscar_foto(car, idx)
        fondo_hex, acento_hex = color_marca(car["modelo"])

        # ── Fondo completo ─────────────────────────────────────────────────
        pdf.set_fill_color(*fondo_hex)
        pdf.rect(0, 0, 297, 210, "F")

        # ── Foto (columna izquierda) ───────────────────────────────────────
        if foto_path:
            try:
                img_pil = Image.open(foto_path).convert("RGB")
                img_buf = BytesIO()
                img_pil.save(img_buf, format="JPEG", quality=85)
                img_buf.seek(0)
                tmp = WEB_FOTOS / f"_tmp_{idx:02d}.jpg"
                tmp.write_bytes(img_buf.read())
                tmp_files.append(tmp)
                pdf.image(str(tmp), x=5, y=10, w=155, h=115)
            except Exception as e:
                print(f"  ⚠️  Foto [{idx}] {car['modelo']}: {e}")

        # ── Barra de acento vertical ───────────────────────────────────────
        pdf.set_fill_color(*acento_hex)
        pdf.rect(162, 0, 4, 210, "F")

        # ── Columna derecha ────────────────────────────────────────────────
        x = 170

        # Modelo
        pdf.set_text_color(*acento_hex)
        pdf.set_font("Helvetica", "B", 20)
        pdf.set_xy(x, 8)
        pdf.cell(122, 10, car["modelo"].encode("latin-1", "replace").decode("latin-1"), ln=True)

        # Versión
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_xy(x, 20)
        ver = car.get("version", "")[:72].encode("latin-1", "replace").decode("latin-1")
        pdf.cell(122, 6, ver, ln=True)

        # Línea separadora
        pdf.set_draw_color(*acento_hex)
        pdf.set_line_width(0.8)
        pdf.line(x, 28, 292, 28)

        # Precio
        pdf.set_text_color(*acento_hex)
        pdf.set_font("Helvetica", "B", 28)
        pdf.set_xy(x, 31)
        pdf.cell(122, 14, f"{car['precio']} EUR", ln=True)

        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(200, 200, 200)
        pdf.set_xy(x, 46)
        pdf.cell(122, 5, "IVA incluido", ln=True)

        # Especificaciones
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_xy(x, 54)
        pdf.cell(122, 6, "ESPECIFICACIONES", ln=True)

        specs = [
            ("Combustible",  car.get("combustible", "")),
            ("Kilometraje",  f"{car.get('km', '')} km"),
            ("Matriculacion", car.get("fecha", "")),
            ("Cambio",       car.get("cambio", "")),
            ("Color",        car.get("color", "")),
            ("Ubicacion",    car.get("ubicacion", "")),
        ]
        pdf.set_font("Helvetica", "", 9)
        y = 62
        for label, value in specs:
            pdf.set_text_color(180, 180, 180)
            pdf.set_xy(x, y)
            pdf.cell(36, 5, label.encode("latin-1", "replace").decode("latin-1"))
            pdf.set_text_color(255, 255, 255)
            pdf.cell(84, 5, value.encode("latin-1", "replace").decode("latin-1"), ln=True)
            y += 6

        # Equipamiento
        equip = car.get("equipamiento", [])
        if equip:
            pdf.set_xy(x, y + 3)
            pdf.set_text_color(*acento_hex)
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(122, 6, "EQUIPAMIENTO DESTACADO", ln=True)
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(220, 220, 220)
            y_eq = y + 12
            for item in equip[:8]:
                safe = ("• " + item[:55]).encode("latin-1", "replace").decode("latin-1")
                pdf.set_xy(x, y_eq)
                pdf.cell(122, 5, safe, ln=True)
                y_eq += 5
                if y_eq > 172:
                    break

        # ── Enlace clickable ───────────────────────────────────────────────
        car_url, fuente_label = url_coche(car)
        if car_url:
            pdf.set_xy(x, 182)
            pdf.set_fill_color(*acento_hex)
            pdf.rect(x, 181, 120, 9, "F")
            pdf.set_text_color(*fondo_hex)
            pdf.set_font("Helvetica", "B", 8)
            link_text = f"  Ver ficha en {fuente_label}  ↗".encode("latin-1", "replace").decode("latin-1")
            pdf.cell(120, 9, link_text, link=car_url)

        # ── Parte inferior izquierda: concesionario ────────────────────────
        pdf.set_fill_color(0, 0, 0)
        pdf.rect(0, 130, 162, 80, "F")

        pdf.set_text_color(*acento_hex)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_xy(5, 134)
        pdf.cell(152, 8, "AUTOMOVILES RUEDA", ln=True)

        pdf.set_text_color(200, 200, 200)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_xy(5, 143)
        pdf.cell(152, 5, "Concesionario Oficial SEAT & CUPRA | Velez-Malaga", ln=True)
        pdf.set_xy(5, 150)
        pdf.cell(152, 5, "Das WeltAuto | Vehiculos de ocasion garantizados", ln=True)

        # Estado
        if car["estado"] == "Disponible":
            pdf.set_fill_color(0, 140, 60)
            pdf.rect(5, 158, 55, 12, "F")
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_xy(6, 161)
            pdf.cell(53, 6, "DISPONIBLE - RESERVAR YA")
        else:
            pdf.set_fill_color(180, 0, 0)
            pdf.rect(5, 158, 55, 12, "F")
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_xy(6, 161)
            pdf.cell(53, 6, "RESERVADO / NO DISPONIBLE")

        # Fuente (DWA / MF) en esquina inferior derecha de foto
        fuente_tag = "MF" if car.get("fuente") == "motorflash" else "DWA"
        pdf.set_fill_color(30, 30, 30)
        pdf.rect(130, 118, 30, 8, "F")
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_xy(131, 119)
        pdf.cell(28, 6, f"Fuente: {fuente_tag}")

        # Número de página
        pdf.set_text_color(100, 100, 100)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_xy(272, 204)
        pdf.cell(20, 5, f"{idx}/{total}")

    pdf.output(str(PDF_PATH))

    # Limpiar temporales
    for tmp in tmp_files:
        try:
            tmp.unlink()
        except Exception:
            pass

    print(f"\n✅  PDF generado: {PDF_PATH}")
    print(f"    {total} coches · {total} páginas")


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    if not JSON_PATH.exists():
        print(f"❌  No se encontró {JSON_PATH}")
        sys.exit(1)

    todos = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    # Excluir "Retirado": ya no están publicados en DWA
    cars_data = [c for c in todos if c.get("estado") != "Retirado"]

    dwa_n = sum(1 for c in cars_data if c.get("fuente") != "motorflash")
    mf_n  = sum(1 for c in cars_data if c.get("fuente") == "motorflash")

    print("=" * 60)
    print("  AUTOMÓVILES RUEDA - Generador de Catálogo PDF")
    print("=" * 60)
    print(f"\n  Total JSON:          {len(todos)}")
    print(f"  Retirado (excl.):    {len(todos) - len(cars_data)}")
    print(f"  Coches en PDF:       {len(cars_data)}")
    print(f"    DWA:               {dwa_n}")
    print(f"    MotorFlash:        {mf_n}")
    print()

    print("  Generando PDF...")
    crear_pdf(cars_data)

    print(f"\n{'='*60}")
    print(f"  ¡Listo! → {PDF_PATH}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
