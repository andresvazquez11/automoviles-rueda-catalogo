import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import confianza_dwa  # noqa: E402


def i18n(es, en, cls=""):
    return es


class GarantiaCorta(unittest.TestCase):
    def test_fabrica(self):
        self.assertEqual(confianza_dwa.garantia_corta("33 meses (de fábrica)"), "33 meses de garantía")

    def test_con_extension(self):
        self.assertEqual(confianza_dwa.garantia_corta("21 meses (de fábrica) + 24 meses de extensión"),
                         "21 meses de garantía + 24 de extensión")

    def test_das_weltauto(self):
        self.assertEqual(confianza_dwa.garantia_corta("12 meses desde la compra (Das WeltAuto)"),
                         "12 meses de garantía")

    def test_vacio(self):
        self.assertEqual(confianza_dwa.garantia_corta(""), "")
        self.assertEqual(confianza_dwa.garantia_corta(None), "")


class Pastillas(unittest.TestCase):
    def test_tarjeta_con_ficha(self):
        html = confianza_dwa.pastilla_tarjeta_html({"gen": {"garantia": "33 meses (de fábrica)"}}, i18n)
        self.assertIn("33 meses de garantía", html)
        self.assertIn("126 puntos", html)

    def test_tarjeta_sin_ficha(self):
        html = confianza_dwa.pastilla_tarjeta_html(None, i18n)
        self.assertIn("Garantía oficial", html)

    def test_ficha_no_publica_lo_descartado(self):
        html = confianza_dwa.tarjeta_ficha_html({"gen": {"garantia": "33 meses (de fábrica)",
                                                         "garantia_bateria": "Junio 2034"}}, i18n)
        self.assertIn("33 meses de garantía", html)
        for prohibido in ("2034", "15 días", "1.000 km", "24 meses de garantía"):
            self.assertNotIn(prohibido, html)

    def test_banners(self):
        html = confianza_dwa.banners_template_html(i18n, "/quienes-somos/")
        self.assertEqual(html.count('<aside class="rd-banner'), 5)
        self.assertIn("/quienes-somos/", html)


if __name__ == "__main__":
    unittest.main()
