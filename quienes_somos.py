"""
quienes_somos.py — página "Quiénes somos" (/quienes-somos/ y /alejandro/quienes-somos/).

Datos verificados (26/09/2026):
- Concesionario oficial SEAT en la provincia de Málaga desde 1995 (concesionarios.seat).
- Julio 2016: nuevas instalaciones en Vélez-Málaga, Av. Juan Carlos I, 500 m² de
  exposición y taller (posventa.info, 11/07/2016).
- Direcciones y fotos: fichas de Google Maps de cada sede. OJO: las fotos son de
  usuarios de Google Maps, no del propietario — sustituir por fotos propias
  cuando Andrés las tenga (mismos nombres en assets/sedes/).
"""
from __future__ import annotations

from html import escape as e

SEDES = [
    ("malaga-seat", "Málaga · SEAT y CUPRA", "Málaga · SEAT & CUPRA", "Av. de Velázquez, 105 · 29004 Málaga",
     "36.691265,-4.4558905"),
    ("malaga-ocasion", "Málaga · Das WeltAuto", "Málaga · Das WeltAuto", "Av. de Velázquez, 103 · 29004 Málaga",
     "36.6913379,-4.455824"),
    ("velez", "Vélez-Málaga", "Vélez-Málaga", "Av. del Rey Juan Carlos I · 29700 Vélez-Málaga",
     "36.7654266,-4.0984616"),
    ("antequera", "Antequera", "Antequera", "C. Papabellotas, 7 · Posventa: C. Torre del Hacho, 23 · 29200 Antequera",
     "37.030703,-4.5316571"),
]
TALLER = ("C. Esteban Salazar Chapela, 9 · Polígono Guadalhorce · 29004 Málaga", "36.6898769,-4.4708892")


def _maps(coords: str) -> str:
    return f"https://www.google.com/maps/dir/?api=1&destination={coords}"


def cuerpo_html(i18n_span, total_coches: int, whatsapp_url: str, asesor: str, telefono: str) -> str:
    sedes = "".join(
        f'<article class="qs-sede"><div class="qs-foto" style="background-image:url(/assets/sedes/{foto}.jpg)"></div>'
        f'<div class="qs-sede-txt"><h3>{i18n_span(es, en)}</h3><p>{e(dire)}</p>'
        f'<a href="{_maps(coords)}" target="_blank" rel="noopener">📍 {i18n_span("Cómo llegar", "Directions")}</a></div></article>'
        for foto, es, en, dire, coords in SEDES)
    taller_items = "".join(f"<li>{i18n_span(es, en)}</li>" for es, en in [
        ("Servicio oficial SEAT y CUPRA", "Official SEAT & CUPRA service"),
        ("Mantenimiento y reparación", "Maintenance and repair"),
        ("Recambios y accesorios originales", "Genuine parts and accessories"),
        ("Cita previa online", "Online booking"),
    ])
    hitos = "".join(
        f'<div><b>{i18n_span(t_es, t_en)}</b><p>{i18n_span(p_es, p_en)}</p></div>'
        for t_es, t_en, p_es, p_en in [
            ("1995", "1995", "Concesionario oficial SEAT en Málaga", "Official SEAT dealer in Málaga"),
            ("Antequera", "Antequera", "Venta y taller oficial en el norte de la provincia", "Sales and official workshop in the north of the province"),
            ("2016", "2016", "Nuevas instalaciones en Vélez-Málaga (500 m²)", "New premises in Vélez-Málaga (500 m²)"),
            ("Hoy", "Today", "SEAT · CUPRA · Das WeltAuto y taller propio", "SEAT · CUPRA · Das WeltAuto and our own workshop"),
        ])
    return f'''<section class="qs-hero"><div class="qs-hero-txt">
  <div class="qs-eyebrow">{i18n_span("Quiénes somos", "About us")}</div>
  <h1>{i18n_span("Más de 30 años vendiendo confianza", "Over 30 years of trust")}</h1>
  <p>{i18n_span("Concesionario oficial SEAT, CUPRA y Das WeltAuto en la provincia de Málaga desde 1995.", "Official SEAT, CUPRA and Das WeltAuto dealer in the province of Málaga since 1995.")}</p>
</div></section>

<div class="qs-cifras">
  <div><b>1995</b><span>{i18n_span("Concesionario oficial SEAT", "Official SEAT dealer")}</span></div>
  <div><b>3</b><span>{i18n_span("Ciudades: Málaga, Antequera y Vélez-Málaga", "Towns: Málaga, Antequera and Vélez-Málaga")}</span></div>
  <div><b>3</b><span>{i18n_span("Marcas: SEAT · CUPRA · Das WeltAuto", "Brands: SEAT · CUPRA · Das WeltAuto")}</span></div>
  <div><b>{total_coches}</b><span>{i18n_span("Seminuevos disponibles hoy", "Cars available today")}</span></div>
</div>

<div class="qs-wrap">
  <div class="qs-hist">
    <div>
      <h2>{i18n_span("Una empresa malagueña", "A Málaga company")}</h2>
      <p>{i18n_span("Automóviles Rueda nació en Málaga y desde 1995 es concesionario y servicio oficial SEAT. Con los años sumamos CUPRA y el programa de seminuevos Das WeltAuto, y crecimos hasta Antequera y la Axarquía.", "Automóviles Rueda was born in Málaga and has been an official SEAT dealer and service centre since 1995. Over the years we added CUPRA and the Das WeltAuto used-car programme, and grew to Antequera and the Axarquía.")}</p>
      <p>{i18n_span("En 2016 abrimos las instalaciones de Vélez-Málaga, en la avenida Juan Carlos I: exposición, venta y taller oficial en el mismo sitio. Detrás de cada coche que vendemos hay un taller oficial que lo revisa y que te sigue atendiendo después.", "In 2016 we opened our Vélez-Málaga premises on Avenida Juan Carlos I: showroom, sales and official workshop in one place. Behind every car we sell there is an official workshop that checks it and keeps looking after you afterwards.")}</p>
    </div>
    <div class="qs-foto qs-foto-hist" style="background-image:url(/assets/sedes/velez.jpg)"></div>
  </div>

  <div class="qs-linea">{hitos}</div>

  <h2 class="qs-h2">{i18n_span("Nuestras sedes", "Our dealerships")}</h2>
  <div class="qs-sedes">{sedes}</div>

  <section class="qs-taller">
    <div class="qs-foto" style="background-image:url(/assets/sedes/taller.jpg)"></div>
    <div class="qs-taller-txt">
      <div class="qs-eyebrow">{i18n_span("Taller propio", "Our own workshop")}</div>
      <h2>{i18n_span("Tu coche, en manos del servicio oficial", "Your car, in the hands of the official service")}</h2>
      <p>{i18n_span("En el Polígono Guadalhorce tenemos nuestro propio taller oficial SEAT y CUPRA. Es donde revisamos los coches antes de entregarlos y donde te seguimos atendiendo después de la compra.", "Our own official SEAT and CUPRA workshop is in the Guadalhorce industrial estate. It is where we check cars before handover and where we keep looking after you after the sale.")}</p>
      <ul>{taller_items}</ul>
      <a class="qs-taller-dir" href="{_maps(TALLER[1])}" target="_blank" rel="noopener">📍 {e(TALLER[0])}</a>
    </div>
  </section>

  <h2 class="qs-h2 qs-centro">{i18n_span("Marcas oficiales", "Official brands")}</h2>
  <div class="qs-marcas"><span>SEAT</span><span>CUPRA</span><span><img src="/assets/dasweltauto-logo.svg" alt="Das WeltAuto"></span></div>

  <div class="qs-cta">
    <div><h3>{i18n_span("¿Hablamos de tu próximo coche?", "Shall we talk about your next car?")}</h3>
      <p>{e(asesor)} · {i18n_span("asesor comercial", "sales advisor")} · {e(telefono)}</p></div>
    <a href="{e(whatsapp_url)}" target="_blank" rel="noopener">{i18n_span("Escríbeme por WhatsApp", "Message me on WhatsApp")}</a>
  </div>
</div>'''
