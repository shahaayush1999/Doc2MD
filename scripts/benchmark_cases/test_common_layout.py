from __future__ import annotations

import unittest

from reportlab.pdfbase import pdfmetrics

from benchmark_cases.common import wrap_lines


class CommonLayoutTest(unittest.TestCase):
    def test_wrap_lines_splits_long_word_after_an_existing_word(self) -> None:
        width = 28
        lines = wrap_lines("Residual requirement", width, "DocSans-Bold", 5.5)

        self.assertGreater(len(lines), 2)
        self.assertEqual("".join(lines), "Residualrequirement")
        self.assertTrue(all(pdfmetrics.stringWidth(line, "DocSans-Bold", 5.5) <= width for line in lines))


if __name__ == "__main__":
    unittest.main()
