import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import buscar_pruebas as bp  # noqa: E402


def cand(vid, titulo, canal="coches.net", dur=600):
    return {"id": vid, "titulo": titulo, "canal": canal, "segundos": dur}


class Elegir(unittest.TestCase):
    def test_acepta_pruebas_del_modelo_y_prioriza_medios_conocidos(self):
        c = [cand("AAAAAAAAAAA", "Nissan Qashqai 2019 prueba", canal="Canal Random"),
             cand("BBBBBBBBBBB", "Nissan Qashqai | Primera prueba / Review", canal="coches.net"),
             cand("CCCCCCCCCCC", "Nissan Qashqai 2019 review", canal="Motor.es")]
        elegidos = bp.elegir(c, "Nissan Qashqai", "DIG-T 160", 2019)
        self.assertEqual([e["id"] for e in elegidos], ["BBBBBBBBBBB", "CCCCCCCCCCC", "AAAAAAAAAAA"])

    def test_descarta_otro_modelo_shorts_y_sin_palabra_de_prueba(self):
        c = [cand("AAAAAAAAAAA", "Nissan Juke 2019 prueba"),              # otro modelo
             cand("BBBBBBBBBBB", "Nissan Qashqai prueba", dur=45),          # short
             cand("CCCCCCCCCCC", "Nissan Qashqai 2019 precios y ofertas"),  # no es prueba
             cand("DDDDDDDDDDD", "Nissan Qashqai 2024 prueba a fondo")]     # otra generación
        self.assertEqual(bp.elegir(c, "Nissan Qashqai", "DIG-T 160", 2019), [])

    def test_modelo_por_numero_de_version(self):
        c = [cand("AAAAAAAAAAA", "Abarth 595 | Prueba / Review en español")]
        self.assertEqual(len(bp.elegir(c, "Abarth 500", "1.4 16v T-Jet 595 121 kW (165 CV)", 2022)), 1)

    def test_descarta_generacion_nueva_por_titulo_o_publicacion(self):
        c = [dict(cand("AAAAAAAAAAA", "Renault Clio E-Tech 2026 prueba"), anio_publicacion=2025),
             dict(cand("BBBBBBBBBBB", "Nissan Qashqai prueba"), anio_publicacion=2021),
             dict(cand("CCCCCCCCCCC", "Nissan Qashqai prueba"), anio_publicacion=2018)]
        self.assertEqual(bp.elegir(c[:1], "Renault Clio", "E-Tech", 2025), [])
        self.assertEqual([e["id"] for e in bp.elegir(c[1:], "Nissan Qashqai", "DIG-T", 2019)], ["CCCCCCCCCCC"])

    def test_descarta_nuevo_del_mismo_anio_y_comparativas(self):
        c = [dict(cand("AAAAAAAAAAA", "¡Nuevo Renault Clio! Primera prueba"), anio_publicacion=2025),
             dict(cand("BBBBBBBBBBB", "Renault Clio o Mitsubishi Colt ¿Cuál es mejor? | Prueba"), anio_publicacion=2024),
             dict(cand("CCCCCCCCCCC", "Renault Clio E-Tech prueba"), anio_publicacion=2023)]
        self.assertEqual([e["id"] for e in bp.elegir(c, "Renault Clio", "E-Tech", 2025, hoy_anio=2026)], ["CCCCCCCCCCC"])
        # un coche del año en curso sí acepta "Nuevo …" de este año
        nuevo = [dict(cand("DDDDDDDDDDD", "Nuevo Renault Clio prueba"), anio_publicacion=2026)]
        self.assertEqual(len(bp.elegir(nuevo, "Renault Clio", "E-Tech", 2026, hoy_anio=2026)), 1)

    def test_anio_publicacion(self):
        from datetime import date
        hoy = date(2026, 9, 26)
        self.assertEqual(bp.anio_publicacion("hace 7 años", hoy), 2019)
        self.assertEqual(bp.anio_publicacion("hace 10 meses", hoy), 2025)
        self.assertEqual(bp.anio_publicacion("hace 3 semanas", hoy), 2026)
        self.assertEqual(bp.anio_publicacion("hace 7 a", hoy), 2019)
        self.assertEqual(bp.anio_publicacion("hace 10 m", hoy), 2025)
        self.assertEqual(bp.anio_publicacion("hace 2 sem", hoy), 2026)
        self.assertIsNone(bp.anio_publicacion("", hoy))

    def test_titulo_corto(self):
        self.assertEqual(bp.titulo_corto("Nissan QASHQAI SUV | Primera prueba / Test | coches.net"), "Nissan QASHQAI SUV")
        self.assertEqual(bp.titulo_corto("✅ Abarth 595 | Prueba"), "Abarth 595 · Prueba")

    def test_no_confunde_fiat_500_con_abarth_500(self):
        c = [cand("AAAAAAAAAAA", "Fiat 500 prueba 2022"), cand("BBBBBBBBBBB", "Abarth 500e prueba")]
        self.assertEqual(bp.elegir(c, "Abarth 500", "1.4 T-Jet", 2022), [])

    def test_maximo_tres(self):
        c = [cand(f"{i}AAAAAAAAAA", f"Renault Clio prueba {i}") for i in range(6)]
        self.assertEqual(len(bp.elegir(c, "Renault Clio", "E-Tech", 2025)), 3)


class Pendientes(unittest.TestCase):
    def test_solo_modelos_y_anios_sin_videos(self):
        datos = {"CUPRA Formentor": {"videos": [{"youtube": "AAAAAAAAAAA", "titulo": "x", "medio": "y", "hasta": 2023}]}}
        coches = [{"modelo": "CUPRA Formentor", "version": "1.5", "fecha": "06/2022", "estado": "Disponible"},
                  {"modelo": "CUPRA Formentor", "version": "1.5", "fecha": "06/2026", "estado": "Disponible"},
                  {"modelo": "Renault Clio", "version": "E-Tech", "fecha": "06/2025", "estado": "No disponible"},
                  {"modelo": "Renault Clio", "version": "E-Tech", "fecha": "06/2025", "estado": "Retirado"}]
        self.assertEqual(bp.pendientes(coches, datos, {}, "2026-09-26"),
                         [("CUPRA Formentor", "1.5", 2026), ("Renault Clio", "E-Tech", 2025)])

    def test_no_repite_busqueda_fallida_en_7_dias(self):
        coches = [{"modelo": "Renault Clio", "version": "E-Tech", "fecha": "06/2025", "estado": "Disponible"}]
        self.assertEqual(bp.pendientes(coches, {}, {"Renault Clio|2025": "2026-09-22"}, "2026-09-26"), [])
        self.assertEqual(len(bp.pendientes(coches, {}, {"Renault Clio|2025": "2026-09-10"}, "2026-09-26")), 1)


if __name__ == "__main__":
    unittest.main()
