import json
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import comparador  # noqa: E402


class Numeros(unittest.TestCase):
    def test_formatos(self):
        self.assertEqual(comparador._n("1.717 Kg"), 1717)
        self.assertEqual(comparador._n("7,9 s"), 7.9)
        self.assertEqual(comparador._n("204 CV (150 kW)"), 204)
        self.assertEqual(comparador._n("37.900"), 37900)
        self.assertIsNone(comparador._n(""))
        self.assertIsNone(comparador._n(None))
        self.assertIsNone(comparador._n("hasta 1.598 litros"))   # con asientos abatidos: no comparable


class Datos(unittest.TestCase):
    def setUp(self):
        self.ficha = json.loads((RAIZ / "fichas_tecnicas.json").read_text(encoding="utf-8"))["dwa-193600528"]
        self.car = {"modelo": "CUPRA Formentor", "version": "1.5 TSI e-Hybrid DSG 150 kW (204 CV)",
                    "precio": "37.900", "km": "50", "fecha": "06/2026", "combustible": "Híbrido",
                    "cambio": "Automático"}

    def test_con_ficha(self):
        d = comparador.datos(self.car, self.ficha)
        self.assertEqual(d["n"]["cv"], 204)
        self.assertEqual(d["n"]["maletero"], 345)
        self.assertEqual(d["n"]["largo"], 4451)
        self.assertEqual(d["n"]["precio"], 37900)
        self.assertEqual(d["v"]["dgt"], "CERO")
        self.assertEqual(d["v"]["garantia"], "33 meses")
        self.assertEqual(d["n"]["extras"], 28)
        self.assertTrue(len(d["eq"]) > 50)

    def test_sin_ficha(self):
        d = comparador.datos(self.car, None)
        self.assertEqual(d["n"]["precio"], 37900)
        self.assertEqual(d["n"]["km"], 50)
        self.assertNotIn("maletero", d["v"])
        self.assertEqual(d["eq"], [])


if __name__ == "__main__":
    unittest.main()
