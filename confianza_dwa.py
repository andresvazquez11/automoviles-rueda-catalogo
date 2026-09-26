"""
confianza_dwa.py — piezas de "confianza" Das WeltAuto y Automóviles Rueda.

- Sello "Das WeltAuto · Concesionario oficial" y botones Coches / Quiénes somos del encabezado.
- Pastilla de garantía de cada tarjeta del catálogo.
- Banners horizontales entre las filas de coches (los coloca assets/confianza.js).
- Tarjeta "Comprando este coche en Das WeltAuto" al final de la ficha.

La garantía SIEMPRE es la real del coche (fichas_tecnicas.json → gen.garantia).
Acordado con Andrés (26/09/2026): NO publicar "hasta 24 meses", "15 días / 1.000 km"
ni la garantía de la batería — solo garantía real, 126 puntos, km certificados y
asistencia 24 h en Europa (+ taller propio y financiación, que son de Rueda).
"""
from __future__ import annotations

import re

LOGO_DWA = "/assets/dasweltauto-logo.svg"
URL_DWA_RUEDA = "https://www.dasweltauto.es/esp/concesionario-seat-automoviles-rueda"

_SVG = {
    "escudo": '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
    "llave": '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.4-.6-.6-2.4z"/>',
    "cuentakm": '<path d="M4 17a8 8 0 1 1 16 0"/><path d="M12 17l4-5"/><circle cx="12" cy="17" r="1.3"/>',
    "telefono": ('<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 '
                 '2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 '
                 '2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z"/>'),
    "taller": ('<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M2 12h3M19 12h3'
               'M4.9 19.1L7 17M17 7l2.1-2.1"/>'),
    "euro": '<path d="M17 6.5A7 7 0 1 0 17 17.5"/><path d="M4 10h9M4 14h9"/>',
}


def _icono(nombre: str) -> str:
    return f'<svg viewBox="0 0 24 24" aria-hidden="true">{_SVG[nombre]}</svg>'


def garantia_corta(texto: "str | None") -> str:
    """'21 meses (de fábrica) + 24 meses de extensión' → '21 meses de garantía + 24 de extensión'."""
    if not texto:
        return ""
    m = re.search(r"(\d+)\s*meses", texto)
    if not m:
        return ""
    corta = f"{m.group(1)} meses de garantía"
    ext = re.search(r"\+\s*(\d+)\s*meses de extensi[oó]n", texto)
    if ext:
        corta += f" + {ext.group(1)} de extensión"
    return corta


def _garantia_en(corta: str) -> str:
    m = re.match(r"(\d+) meses de garantía(?: \+ (\d+) de extensión)?", corta)
    if not m:
        return corta
    return f"{m.group(1)}-month warranty" + (f" + {m.group(2)}-month extension" if m.group(2) else "")


def _garantia_de(ficha: "dict | None") -> str:
    return garantia_corta(((ficha or {}).get("gen") or {}).get("garantia"))


# ── Encabezado ───────────────────────────────────────────────────────────────

def sello_html(i18n_span) -> str:
    return (f'<a class="rd-dwa-sello" href="{URL_DWA_RUEDA}" target="_blank" rel="noopener" '
            f'aria-label="Das WeltAuto — concesionario oficial">'
            f'<img src="{LOGO_DWA}" alt="Das WeltAuto" width="120" height="34">'
            f'<span>{i18n_span("Concesionario oficial", "Official dealer")}</span></a>')


def nav_html(i18n_span, base: str, activo: str) -> str:
    """base = '' (Andrés, raíz) o '/alejandro'. activo ∈ {'coches', 'quienes', ''}."""
    def boton(clave, href, es, en):
        cls = "rd-nav-btn activo" if activo == clave else "rd-nav-btn"
        return f'<a class="{cls}" href="{href}">{i18n_span(es, en)}</a>'
    return ('<nav class="rd-nav">'
            + boton("coches", f"{base}/", "Coches", "Cars")
            + boton("quienes", f"{base}/quienes-somos/", "Quiénes somos", "About us")
            + '</nav>')


# ── Catálogo ─────────────────────────────────────────────────────────────────

def pastilla_tarjeta_html(ficha: "dict | None", i18n_span) -> str:
    g = _garantia_de(ficha)
    es = f"{g or 'Garantía oficial'} · Revisado 126 puntos"
    en = f"{_garantia_en(g) if g else 'Official warranty'} · 126-point inspection"
    return f'<span class="rd-card-dwa">🛡 {i18n_span(es, en)}</span>'


_BANNERS = [
    ("escudo", "Garantía oficial en cada coche", "Official warranty on every car",
     "Todos nuestros seminuevos tienen garantía. En la ficha de cada coche ves los meses exactos que le quedan.",
     "All our cars come with a warranty. Each car's page shows exactly how many months are left."),
    ("llave", "Revisado en 126 puntos", "126-point inspection",
     "Antes de entregártelo, los mecánicos del servicio oficial revisan el coche punto por punto.",
     "Before handover, official service mechanics check the car point by point."),
    ("cuentakm", "Kilómetros certificados", "Certified mileage",
     "Historial verificado: sabes exactamente lo que compras.",
     "Verified history: you know exactly what you are buying."),
    ("telefono", "Asistencia 24 h en toda Europa", "24/7 roadside assistance across Europe",
     "Ayuda en carretera y traslado al taller oficial más cercano, estés donde estés.",
     "Roadside help and towing to the nearest official workshop, wherever you are."),
]


def banners_template_html(i18n_span, href_quienes: str) -> str:
    """<template> con los banners; assets/confianza.js los reparte entre las filas visibles."""
    items = []
    for ico, t_es, t_en, p_es, p_en in _BANNERS:
        items.append(
            f'<aside class="rd-banner"><div class="rd-banner-ico">{_icono(ico)}</div>'
            f'<div class="rd-banner-txt"><strong>{i18n_span(t_es, t_en)}</strong><p>{i18n_span(p_es, p_en)}</p></div>'
            f'<img class="rd-banner-logo" src="{LOGO_DWA}" alt="Das WeltAuto" loading="lazy"></aside>')
    items.append(
        f'<aside class="rd-banner rd-banner-rueda"><div class="rd-banner-ico">{_icono("taller")}</div>'
        f'<div class="rd-banner-txt"><strong>{i18n_span("Taller oficial propio", "Our own official workshop")}</strong>'
        f'<p>{i18n_span("Te seguimos atendiendo después de la compra en Málaga, Antequera y Vélez-Málaga.", "We keep looking after you after the sale in Málaga, Antequera and Vélez-Málaga.")}</p></div>'
        f'<a class="rd-banner-cta" href="{href_quienes}">{i18n_span("Conócenos →", "About us →")}</a></aside>')
    return '<template id="rd-banners">' + "".join(items) + '</template>'


# ── Ficha de coche ───────────────────────────────────────────────────────────

def tarjeta_ficha_html(ficha: "dict | None", i18n_span) -> str:
    g = _garantia_de(ficha)
    chips = [
        ("escudo", g or "Garantía oficial", _garantia_en(g) if g else "Official warranty",
         "Garantía de esta unidad", "Warranty on this car", True),
        ("llave", "Revisado en 126 puntos", "126-point inspection", "por el servicio oficial", "by the official service", False),
        ("cuentakm", "Kilómetros certificados", "Certified mileage", "historial verificado", "verified history", False),
        ("telefono", "Asistencia 24 h", "24/7 assistance", "en toda Europa", "across Europe", False),
        ("taller", "Taller oficial Rueda", "Rueda official workshop", "Málaga, Antequera y Vélez-Málaga",
         "Málaga, Antequera and Vélez-Málaga", False),
        ("euro", "Financiación a medida", "Tailored financing", "calcula tu cuota arriba", "work out your payment above", False),
    ]
    html = "".join(
        f'<div class="rd-dwa-chip{" destacada" if dest else ""}"><div class="rd-dwa-chip-ico">{_icono(ico)}</div>'
        f'<div><b>{i18n_span(b_es, b_en)}</b><small>{i18n_span(s_es, s_en)}</small></div></div>'
        for ico, b_es, b_en, s_es, s_en, dest in chips)
    return (f'<section class="rd-dwa-ficha"><div class="rd-dwa-ficha-top">'
            f'<h3>{i18n_span("Comprando este coche en Das WeltAuto", "Buying this car from Das WeltAuto")}</h3>'
            f'<img src="{LOGO_DWA}" alt="Das WeltAuto" loading="lazy"></div>'
            f'<div class="rd-dwa-chips">{html}</div></section>')
