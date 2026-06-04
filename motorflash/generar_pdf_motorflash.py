"""
Generador PDF — Comparativa DWA vs MotorFlash
Lee: comparacion.json + datos_motorflash.json + ../datos_coches.json
Genera: informe_motorflash.pdf
"""

import json
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
)
from reportlab.platypus import HRFlowable

BASE = Path(__file__).parent
COMP_JSON = BASE / "comparacion.json"
MF_JSON = BASE / "datos_motorflash.json"
DWA_JSON = BASE.parent / "datos_coches.json"
PDF_OUT = BASE / "informe_motorflash.pdf"

# Colores marca Rueda
ROJO = colors.HexColor("#C8232B")
AZUL_MARINO = colors.HexColor("#0d1b35")
GRIS_CLARO = colors.HexColor("#eef1f7")
NARANJA_KM0 = colors.HexColor("#E87722")
VERDE = colors.HexColor("#2E7D32")
GRIS_TEXTO = colors.HexColor("#555555")


def build_styles():
    styles = getSampleStyleSheet()
    custom = {
        "titulo_portada": ParagraphStyle("titulo_portada", fontSize=28, textColor=colors.white,
                                          alignment=TA_CENTER, fontName="Helvetica-Bold", spaceAfter=10),
        "subtitulo_portada": ParagraphStyle("subtitulo_portada", fontSize=14, textColor=colors.HexColor("#ccddff"),
                                             alignment=TA_CENTER, fontName="Helvetica", spaceAfter=6),
        "seccion": ParagraphStyle("seccion", fontSize=15, textColor=AZUL_MARINO,
                                   fontName="Helvetica-Bold", spaceBefore=16, spaceAfter=8,
                                   borderPad=4),
        "coche_titulo": ParagraphStyle("coche_titulo", fontSize=12, textColor=AZUL_MARINO,
                                        fontName="Helvetica-Bold", spaceAfter=2),
        "coche_version": ParagraphStyle("coche_version", fontSize=9, textColor=GRIS_TEXTO,
                                         fontName="Helvetica", spaceAfter=4),
        "equip": ParagraphStyle("equip", fontSize=8, textColor=GRIS_TEXTO,
                                 fontName="Helvetica", spaceAfter=2, leftIndent=10),
        "normal_small": ParagraphStyle("normal_small", fontSize=9, textColor=GRIS_TEXTO,
                                        fontName="Helvetica"),
        "badge_km0": ParagraphStyle("badge_km0", fontSize=8, textColor=colors.white,
                                     fontName="Helvetica-Bold", alignment=TA_CENTER),
        "badge_vo": ParagraphStyle("badge_vo", fontSize=8, textColor=colors.white,
                                    fontName="Helvetica-Bold", alignment=TA_CENTER),
    }
    return {**{k: styles[k] for k in styles.byName}, **custom}


def chip(texto, color_bg, color_text=colors.white, fontsize=8):
    """Crea una celda chip de color para badges."""
    style = ParagraphStyle("chip_s", fontSize=fontsize, textColor=color_text,
                            fontName="Helvetica-Bold", alignment=TA_CENTER)
    t = Table([[Paragraph(texto, style)]], colWidths=[2.5*cm], rowHeights=[0.5*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color_bg),
        ("ROUNDEDCORNERS", [4]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def tabla_resumen(resumen: dict, styles):
    data = [
        ["Plataforma", "Total coches"],
        ["Das WeltAuto (DWA)", str(resumen["total_dwa"])],
        ["MotorFlash.com", str(resumen["total_motorflash"])],
        ["En ambas plataformas", str(resumen["en_ambas_plataformas"])],
        ["Solo en DWA", str(resumen["solo_en_dwa"])],
        ["Solo en MotorFlash ★", str(resumen["solo_en_motorflash"])],
    ]
    t = Table(data, colWidths=[11*cm, 4*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL_MARINO),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, GRIS_CLARO]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#fff3cd")),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.HexColor("#856404")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    return t


def tabla_inventario(coches: list, fuente_label: str, styles, color_header=None):
    if color_header is None:
        color_header = AZUL_MARINO
    data = [["#", "Modelo", "Versión", "Km", "Año", "Combustible", "Precio"]]
    for c in coches:
        tipo_tag = f" [{c.get('tipo','VO')}]" if fuente_label == "MotorFlash" else ""
        data.append([
            str(c.get("n", "")),
            c.get("modelo", ""),
            c.get("version", "")[:35] + ("…" if len(c.get("version","")) > 35 else ""),
            c.get("km", ""),
            c.get("fecha", ""),
            c.get("combustible", ""),
            c.get("precio", "") + "€",
        ])

    col_widths = [0.8*cm, 3.5*cm, 5.5*cm, 2*cm, 1.5*cm, 2.2*cm, 2.2*cm]
    t = Table(data, colWidths=col_widths, repeatRows=1)
    row_colors = []
    for i in range(1, len(data)):
        bg = GRIS_CLARO if i % 2 == 0 else colors.white
        row_colors.append(("BACKGROUND", (0, i), (-1, i), bg))

    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), color_header),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (5, 0), (6, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#dddddd")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        *row_colors,
    ]))
    return t


def ficha_coche_mf(c: dict, styles, idx: int):
    """Bloque visual para un coche exclusivo de MotorFlash."""
    elementos = []

    tipo = c.get("tipo", "VO")
    color_tipo = NARANJA_KM0 if tipo == "KM0" else ROJO

    # Cabecera: modelo + badge tipo + precio
    precio_fmt = c.get("precio", "")
    header_data = [[
        Paragraph(f"{c.get('modelo', '')} <font color='#{AZUL_MARINO.hexval()[2:]}'>#{idx}</font>", styles["coche_titulo"]),
        chip(tipo, color_tipo),
        Paragraph(f"<b><font color='#C8232B'>{precio_fmt}€</font></b>", ParagraphStyle(
            "precio_s", fontSize=14, textColor=ROJO, fontName="Helvetica-Bold", alignment=TA_CENTER)),
    ]]
    header_t = Table(header_data, colWidths=[9*cm, 2.5*cm, 4*cm])
    header_t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, -1), 8),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ("RIGHTPADDING", (2, 0), (2, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("BACKGROUND", (0, 0), (-1, -1), GRIS_CLARO),
        ("LINEBELOW", (0, 0), (-1, -1), 1.5, color_tipo),
    ]))
    elementos.append(header_t)

    # Versión
    version = c.get("version", "")
    if version:
        elementos.append(Paragraph(version, styles["coche_version"]))

    # Datos clave en una fila
    datos_data = [[
        Paragraph(f"<b>Km:</b> {c.get('km','-')}", styles["normal_small"]),
        Paragraph(f"<b>Año:</b> {c.get('fecha','-')}", styles["normal_small"]),
        Paragraph(f"<b>Cambio:</b> {c.get('cambio','-')}", styles["normal_small"]),
        Paragraph(f"<b>Combustible:</b> {c.get('combustible','-')}", styles["normal_small"]),
    ]]
    datos_t = Table(datos_data, colWidths=[3.8*cm, 3.8*cm, 3.8*cm, 4.3*cm])
    datos_t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elementos.append(datos_t)

    # Foto + equipamiento
    foto_path = c.get("fotos", [None])[0] if c.get("fotos") else None
    equip = c.get("equipamiento", [])[:8]
    equip_textos = [Paragraph(f"• {e}", styles["equip"]) for e in equip]

    if foto_path and Path(foto_path).exists():
        try:
            img = Image(foto_path, width=5*cm, height=3.5*cm)
            img.hAlign = "LEFT"
            col_foto = [img]
            col_equip = equip_textos or [Paragraph("Sin equipamiento detallado", styles["equip"])]
            contenido_data = [[col_foto, col_equip]]
            contenido_t = Table(contenido_data, colWidths=[5.5*cm, 10.2*cm])
            contenido_t.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]))
            elementos.append(contenido_t)
        except Exception:
            for e in equip_textos:
                elementos.append(e)
    else:
        for e in equip_textos:
            elementos.append(e)

    # URL
    url = c.get("url_motorflash", "")
    if url:
        elementos.append(Paragraph(
            f'<link href="{url}"><font color="#1565C0" size="8">Ver en MotorFlash →</font></link>',
            styles["normal_small"]))

    elementos.append(Spacer(1, 0.3*cm))
    return elementos


def _norm_precio(p):
    import re
    s = re.sub(r"[^\d]", "", str(p))
    return int(s) if s else 0

def _norm_km(k):
    import re
    s = re.sub(r"[^\d]", "", str(k))
    return int(s) if s else 0

def _clave(c):
    return (_norm_precio(c.get("precio", "0")), round(_norm_km(c.get("km", "0")), -1))

def _comparar_live(dwa_coches, mf_coches):
    """Calcula comparación en vivo — nunca usa comparacion.json obsoleto."""
    from collections import defaultdict
    def agrupar(lst):
        g = defaultdict(list)
        for c in lst:
            g[_clave(c)].append(c)
        return g

    dwa_g = agrupar(dwa_coches)
    mf_g  = agrupar(mf_coches)
    claves = set(dwa_g) | set(mf_g)

    en_ambos, solo_dwa, solo_mf = [], [], []
    for k in sorted(claves):
        ld, lm = dwa_g.get(k, []), mf_g.get(k, [])
        n = min(len(ld), len(lm))
        en_ambos.extend(ld[:n]); solo_dwa.extend(ld[n:]); solo_mf.extend(lm[n:])

    return en_ambos, solo_dwa, solo_mf

def main():
    mf_coches  = json.loads(MF_JSON.read_text())  if MF_JSON.exists()  else []
    todos_dwa  = json.loads(DWA_JSON.read_text()) if DWA_JSON.exists() else []

    # Separar: los que son de DWA puro vs los que ya son de MF (integrados en datos_coches.json)
    dwa_coches = [c for c in todos_dwa if c.get("fuente","dwa") != "motorflash"]

    en_ambos, solo_dwa, solo_mf = _comparar_live(dwa_coches, mf_coches)

    resumen = {
        "total_dwa":            len(dwa_coches),
        "total_motorflash":     len(mf_coches),
        "en_ambas_plataformas": len(en_ambos),
        "solo_en_dwa":          len(solo_dwa),
        "solo_en_motorflash":   len(solo_mf),
    }
    print(f"  PDF: DWA={resumen['total_dwa']} | MF={resumen['total_motorflash']} | "
          f"Ambos={resumen['en_ambas_plataformas']} | Solo MF={resumen['solo_en_motorflash']}")

    styles = build_styles()
    doc = SimpleDocTemplate(
        str(PDF_OUT),
        pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm
    )

    story = []

    # ── PORTADA ──
    portada_data = [[
        Paragraph("AUTOMÓVILES RUEDA", styles["titulo_portada"]),
    ]]
    portada_t = Table([[
        Paragraph("AUTOMÓVILES RUEDA", styles["titulo_portada"]),
        Paragraph("Comparativa de Inventario", styles["subtitulo_portada"]),
        Paragraph(f"Das WeltAuto  vs  MotorFlash.com", styles["subtitulo_portada"]),
        Paragraph(f"Generado el {date.today().strftime('%d/%m/%Y')}", styles["subtitulo_portada"]),
    ]], colWidths=[17*cm])
    portada_wrap = Table([[portada_t]], colWidths=[17*cm])
    portada_wrap.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), AZUL_MARINO),
        ("TOPPADDING", (0, 0), (-1, -1), 24),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 24),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
    ]))
    story.append(portada_wrap)
    story.append(Spacer(1, 0.5*cm))

    # Línea roja decorativa
    story.append(HRFlowable(width="100%", thickness=3, color=ROJO))
    story.append(Spacer(1, 0.8*cm))

    # ── SECCIÓN 1: RESUMEN EJECUTIVO ──
    story.append(Paragraph("1. Resumen Ejecutivo", styles["seccion"]))
    story.append(tabla_resumen(resumen, styles))
    story.append(Spacer(1, 0.5*cm))

    nota = (
        "<b>★ Coches exclusivos de MotorFlash</b>: son vehículos publicados en MotorFlash.com "
        "que no están en el catálogo de Das WeltAuto. Incluyen principalmente coches <b>KM0</b> "
        "y algunos modelos CUPRA de ocasión que no tienen certificación DWA."
    )
    story.append(Paragraph(nota, ParagraphStyle("nota", fontSize=9, textColor=GRIS_TEXTO,
                                                  fontName="Helvetica-Oblique",
                                                  borderPad=8, borderWidth=1,
                                                  borderColor=colors.HexColor("#ffe082"),
                                                  backColor=colors.HexColor("#fff8e1"),
                                                  leftIndent=8, rightIndent=8,
                                                  spaceAfter=12)))
    story.append(PageBreak())

    # ── SECCIÓN 2: INVENTARIO DAS WELLAUTO ──
    story.append(Paragraph(f"2. Inventario Das WeltAuto  ({resumen['total_dwa']} coches)", styles["seccion"]))
    story.append(Paragraph(
        "Coches del catálogo oficial DWA scrapeados desde dasweltauto.es. "
        "Esta es la fuente actual de nuestra web de clientes.",
        ParagraphStyle("desc", fontSize=9, textColor=GRIS_TEXTO, fontName="Helvetica", spaceAfter=8)
    ))
    if dwa_coches:
        story.append(tabla_inventario(dwa_coches, "DWA", styles, AZUL_MARINO))
    story.append(PageBreak())

    # ── SECCIÓN 3: INVENTARIO MOTORFLASH ──
    story.append(Paragraph(f"3. Inventario MotorFlash.com  ({resumen['total_motorflash']} coches)", styles["seccion"]))
    story.append(Paragraph(
        "Todos los coches publicados en MotorFlash. Incluye tanto ocasión (VO) como nuevos kilómetro cero (KM0).",
        ParagraphStyle("desc", fontSize=9, textColor=GRIS_TEXTO, fontName="Helvetica", spaceAfter=8)
    ))
    if mf_coches:
        story.append(tabla_inventario(mf_coches, "MotorFlash", styles, colors.HexColor("#1565C0")))
    story.append(PageBreak())

    # ── SECCIÓN 4: EXCLUSIVOS MOTORFLASH ──
    story.append(Paragraph(
        f"4. Coches EXCLUSIVOS de MotorFlash  ({resumen['solo_en_motorflash']} coches)",
        styles["seccion"]
    ))
    story.append(Paragraph(
        "Estos coches están publicados en MotorFlash pero NO en Das WeltAuto. "
        "Son los candidatos para añadir a nuestra web de clientes.",
        ParagraphStyle("desc", fontSize=9, textColor=GRIS_TEXTO, fontName="Helvetica", spaceAfter=12)
    ))

    if solo_mf:
        for idx, c in enumerate(solo_mf, 1):
            for elem in ficha_coche_mf(c, styles, idx):
                story.append(elem)
    else:
        story.append(Paragraph(
            "✓ Todos los coches de MotorFlash ya están en Das WeltAuto.",
            ParagraphStyle("ok", fontSize=11, textColor=VERDE, fontName="Helvetica-Bold")
        ))

    # ── SECCIÓN 5: EN AMBAS PLATAFORMAS ──
    if en_ambos:
        story.append(PageBreak())
        story.append(Paragraph(
            f"5. Coches en AMBAS plataformas  ({resumen['en_ambas_plataformas']} coches)",
            styles["seccion"]
        ))
        story.append(Paragraph(
            "Estos coches coinciden en DWA y MotorFlash (mismo modelo + precio + km).",
            ParagraphStyle("desc", fontSize=9, textColor=GRIS_TEXTO, fontName="Helvetica", spaceAfter=8)
        ))
        story.append(tabla_inventario(en_ambos, "Ambos", styles, VERDE))

    # Build
    doc.build(story)
    print(f"✓ PDF generado: {PDF_OUT}")


if __name__ == "__main__":
    main()
