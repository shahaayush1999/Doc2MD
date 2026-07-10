from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import tempfile
import unittest

import pdfplumber
from pypdf import PdfReader
from reportlab.lib.pagesizes import A4, LETTER, landscape
from reportlab.pdfgen.canvas import Canvas

from scripts.benchmark_cases.rasterize import ScanProfile, rasterize_pdf_pages


class RasterizePdfPagesTest(unittest.TestCase):
    def _make_source(self, path: Path) -> None:
        canvas = Canvas(str(path), pagesize=LETTER, invariant=1, pageCompression=1)
        canvas.setTitle("Controlled mixed-modality packet")
        canvas.setAuthor("Document Control")
        canvas.setSubject("Rasterization helper verification")
        canvas.setKeywords("controlled, test")
        # Intentionally expose a library in the source metadata.  The helper
        # must not carry these implementation values into its output.
        canvas.setCreator("ReportLab source fixture")
        canvas.setProducer("ReportLab PDF Library")
        canvas.setDateFormatter(lambda *_: "D:20260710121500+05'30'")

        page_sizes = (LETTER, landscape(LETTER), A4)
        labels = ("NATIVE PAGE ONE", "PAGE TWO BECOMES A SCAN", "NATIVE PAGE THREE")
        for index, (page_size, label) in enumerate(zip(page_sizes, labels), start=1):
            if index > 1:
                canvas.showPage()
            canvas.setPageSize(page_size)
            width, height = page_size
            canvas.setFont("Helvetica-Bold", 20)
            canvas.drawString(48, height - 72, label)
            canvas.setFont("Helvetica", 11)
            canvas.drawString(48, height - 100, f"ORDER TOKEN {index:02d}")
            canvas.setStrokeColorRGB(0.15, 0.35, 0.6)
            canvas.rect(48, 72, width - 96, height - 210, fill=0, stroke=1)
        canvas.save()

    def test_selected_pages_are_deterministic_full_page_scans(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            source = root / "source.pdf"
            output_a = root / "mixed-a.pdf"
            output_b = root / "mixed-b.pdf"
            in_place = root / "in-place.pdf"
            self._make_source(source)

            profiles = {
                2: ScanProfile(
                    seed=20_260_710,
                    color_mode="color",
                    dpi=144,
                    skew_degrees=-0.19,
                    noise_level=1.6,
                    blur_radius=0.20,
                    jpeg_quality=87,
                )
            }
            metadata = {
                "Creator": "Archive scan station 04",
                "Producer": "Enterprise Document Services",
            }
            rasterize_pdf_pages(source, output_a, profiles, metadata=metadata)
            rasterize_pdf_pages(source, output_b, profiles, metadata=metadata)
            in_place.write_bytes(source.read_bytes())
            rasterize_pdf_pages(in_place, in_place, profiles, metadata=metadata)

            self.assertEqual(sha256(output_a.read_bytes()).digest(), sha256(output_b.read_bytes()).digest())
            self.assertEqual(sha256(output_a.read_bytes()).digest(), sha256(in_place.read_bytes()).digest())
            self.assertFalse(any(path.name.endswith(".tmp") for path in root.iterdir()))
            self.assertFalse(any(".render-" in path.name for path in root.iterdir()))

            source_reader = PdfReader(str(source))
            output_reader = PdfReader(str(output_a))
            self.assertEqual(len(output_reader.pages), len(source_reader.pages))
            for source_page, output_page in zip(source_reader.pages, output_reader.pages):
                self.assertAlmostEqual(float(output_page.mediabox.width), float(source_page.mediabox.width), places=4)
                self.assertAlmostEqual(float(output_page.mediabox.height), float(source_page.mediabox.height), places=4)

            self.assertIn("NATIVE PAGE ONE", output_reader.pages[0].extract_text())
            self.assertEqual(output_reader.pages[1].extract_text().strip(), "")
            self.assertIn("NATIVE PAGE THREE", output_reader.pages[2].extract_text())

            with pdfplumber.open(output_a) as document:
                selected = document.pages[1]
                self.assertEqual(len(selected.images), 1)
                image = selected.images[0]
                image_area = (float(image["x1"]) - float(image["x0"])) * (
                    float(image["y1"]) - float(image["y0"])
                )
                self.assertGreaterEqual(image_area / (selected.width * selected.height), 0.90)
                pixel_width, pixel_height = image["srcsize"]
                effective_dpi = min(
                    float(pixel_width) * 72 / (float(image["x1"]) - float(image["x0"])),
                    float(pixel_height) * 72 / (float(image["y1"]) - float(image["y0"])),
                )
                self.assertGreaterEqual(effective_dpi, 120)

            output_metadata = output_reader.metadata
            self.assertEqual(output_metadata["/Title"], "Controlled mixed-modality packet")
            self.assertEqual(output_metadata["/Author"], "Document Control")
            self.assertEqual(output_metadata["/Subject"], "Rasterization helper verification")
            self.assertEqual(output_metadata["/Keywords"], "controlled, test")
            self.assertEqual(output_metadata["/Creator"], "Archive scan station 04")
            self.assertEqual(output_metadata["/Producer"], "Enterprise Document Services")
            self.assertEqual(output_metadata["/CreationDate"], "D:20260710121500+05'30'")
            self.assertEqual(output_metadata["/ModDate"], "D:20260710121500+05'30'")

            output_bytes = output_a.read_bytes().lower()
            for marker in (b"reportlab", b"pypdf", b"pillow", b"poppler"):
                self.assertNotIn(marker, output_bytes)


if __name__ == "__main__":
    unittest.main()
