"""Tests du contrôle des chiffres dans les communiqués. Depuis la racine : venv/bin/python tests/test_exhibit_check.py"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from exhibit_check import locate_figure


class Locate(unittest.TestCase):
    def test_sentence_with_the_current_figure(self):
        text = "The company reported net income of $10.6 million or $0.37 per diluted share, compared to $12.6 million or $0.44 in the fourth quarter of 2019."
        self.assertEqual(locate_figure(text, 0.37)[0], "current")
        self.assertEqual(locate_figure(text, 0.44)[0], "historical_only")

    def test_table_first_column_only(self):
        text = "Diluted earnings per share | $ | 0.11 | | $ | 0.23 |\nNet income | 3.2 | 6.8 |"
        self.assertEqual(locate_figure(text, 0.11)[0], "current")
        self.assertEqual(locate_figure(text, 0.23)[0], "historical_only")

    def test_absent_and_partial_numbers(self):
        text = "Diluted EPS of $10.23 for the quarter, and 1.230 thousand units."
        self.assertEqual(locate_figure(text, 0.23)[0], "absent")
        self.assertEqual(locate_figure(text, 1.23)[0], "current")

    def test_zeros_and_losses(self):
        self.assertEqual(locate_figure("Loss per share of $(.60) for the quarter", -0.6)[0], "current")
        self.assertEqual(locate_figure("Net loss per diluted share | $ | (1.50) |", -1.5)[0], "current")
        self.assertEqual(locate_figure("Earnings per share of $2.00 for the quarter", 2.0)[0], "current")

    def test_figure_without_per_share_context_is_not_current(self):
        self.assertNotEqual(locate_figure("Total assets rose 0.37 percent in a year of expansion and new contracts, with no other change reported anywhere in this very long sentence about balance sheet items and more text that goes on for a while to escape the window.", 0.37)[0], "current")

    def test_basis_around_the_figure(self):
        self.assertEqual(locate_figure("Adjusted earnings per share of $1.10 for the quarter", 1.10)[1], "adjusted")
        self.assertEqual(locate_figure("Diluted earnings per share of $1.10 for the quarter", 1.10)[1], "plain")


if __name__ == "__main__":
    unittest.main()
