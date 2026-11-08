"""Tests du registre des hypothèses. Depuis la racine : venv/bin/python tests/test_registry.py"""

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import registry


def row(**changes):
    base = {"id": "H99", "inscrite_le": "2026-11-08", "titre": "t", "famille": "heuristique", "hypothese": "h", "source": "s",
            "inspiree_de_resultats_vus": "non", "donnees": "d", "conception": "2018-2021", "validation": "2022-2024",
            "variantes_max": "2", "statut": "proposee", "protocole": "", "resultat": "", "rapport": "", "liee_a": ""}
    return {**base, **changes}


class Registry(unittest.TestCase):
    def test_the_real_registry_is_valid(self):
        self.assertEqual(registry.check(registry.load()), [])

    def test_detected_problems(self):
        table = pd.DataFrame([row(), row(), row(id="H98", famille="magie", statut="fini", variantes_max="0"),
                              row(id="H97", statut="echec", protocole="p.md"), row(id="H96", inspiree_de_resultats_vus="oui", validation="2018-2024"),
                              row(id="H95", liee_a="H99 H00")])
        problems = " | ".join(registry.check(table))
        for expected in ("en double", "famille inconnue", "statut inconnu", "variantes_max", "résultat manquant", "doit se valider ailleurs", "hypothèses inconnues"):
            self.assertIn(expected, problems)

    def test_require_only_lets_a_frozen_protocol_run(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "r.csv"
            pd.DataFrame([row(), row(id="H98", statut="protocole_fige", protocole="p.md")]).to_csv(path, index=False)
            self.assertEqual(registry.require("H98", path)["id"], "H98")
            with self.assertRaises(RuntimeError):
                registry.require("H99", path)          # seulement proposée
            with self.assertRaises(RuntimeError):
                registry.require("H01", path)          # pas inscrite


if __name__ == "__main__":
    unittest.main()
