import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pruebas  # noqa: E402


def i18n(es, en, cls=""):
    return es


DATOS = {"CUPRA Formentor": {"videos": [
    {"youtube": "AAAAAAAAAAA", "titulo": "Vieja", "medio": "km77.com", "hasta": 2023},
    {"youtube": "BBBBBBBBBBB", "titulo": "Nueva 1", "medio": "Diariomotor", "desde": 2024},
    {"youtube": "CCCCCCCCCCC", "titulo": "Nueva 2", "medio": "coches.net", "desde": 2024},
    {"youtube": "DDDDDDDDDDD", "titulo": "Nueva 3", "medio": "Motor.es", "desde": 2024},
    {"youtube": "EEEEEEEEEEE", "titulo": "Nueva 4", "medio": "Motor.es", "desde": 2024},
    {"youtube": "FFFFFFFFFFF", "titulo": "Solo VZ", "medio": "Motor.es", "version_contiene": "VZ"},
]}}


class Bloque(unittest.TestCase):
    def test_modelo_sin_videos(self):
        self.assertEqual(pruebas.bloque_html({"modelo": "Renault Clio", "fecha": "2025"}, DATOS, i18n), "")

    def test_filtra_por_anio_y_maximo_tres(self):
        car = {"modelo": "CUPRA Formentor", "version": "1.5 eTSI", "fecha": "05/2026"}
        html = pruebas.bloque_html(car, DATOS, i18n)
        self.assertNotIn("AAAAAAAAAAA", html)
        self.assertNotIn("FFFFFFFFFFF", html)
        self.assertIn("img.youtube.com/vi/BBBBBBBBBBB/hqdefault.jpg", html)
        self.assertIn("https://www.youtube.com/watch?v=BBBBBBBBBBB", html)
        self.assertNotIn("EEEEEEEEEEE", html)   # máximo 3

    def test_generacion_anterior(self):
        car = {"modelo": "Cupra Formentor", "version": "1.5 TSI", "fecha": "06/2022"}
        html = pruebas.bloque_html(car, DATOS, i18n)
        self.assertIn("AAAAAAAAAAA", html)
        self.assertNotIn("BBBBBBBBBBB", html)

    def test_json_real_carga(self):
        datos = pruebas.cargar()
        self.assertIn("CUPRA Formentor", datos)
        for modelo, d in datos.items():
            if modelo.startswith("_"):
                continue
            for v in d["videos"]:
                self.assertRegex(v["youtube"], r"^[\w-]{11}$")


if __name__ == "__main__":
    unittest.main()
