import io
import os
import re
from pathlib import Path

from fpdf import FPDF


def _find_unicode_font():
    """Find a bundled or configured TrueType font for Unicode PDF output."""
    candidates = [
        os.getenv("PDF_UNICODE_FONT", ""),
        "fonts/NotoSans-Regular.ttf",
        "fonts/NotoSansDevanagari-Regular.ttf",
        "fonts/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]

    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate))

    return None


def _ascii_fallback(text: str) -> str:
    replacements = {
        "\u2014": "-",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "-",
        "\u2026": "...",
        "\u00a0": " ",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return re.sub(r"[^\x00-\x7F]+", " ", text)


class StudyNotesPDF(FPDF):
    def __init__(self, unicode_font=None):
        super().__init__()
        self.unicode_font = unicode_font

        if unicode_font:
            self.add_font(
                family="StudyFont",
                style="",
                fname=unicode_font,
            )
            self.font_family = "StudyFont"
        else:
            self.font_family = "Helvetica"

    def header(self):
        self.set_font(self.font_family, size=13)
        self.set_text_color(79, 70, 229)
        self.cell(
            0,
            10,
            "AI Lecture Digest - Study Notes",
            border=False,
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )

        self.set_draw_color(226, 232, 240)
        self.line(10, 20, 200, 20)
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", size=8)
        self.set_text_color(148, 163, 184)
        self.cell(
            0,
            10,
            f"Page {self.page_no()}",
            border=False,
            align="C",
        )


def create_pdf(markdown_text: str) -> bytes:
    if not markdown_text or not markdown_text.strip():
        raise ValueError("There is no study-note content to export.")

    unicode_font = _find_unicode_font()
    pdf = StudyNotesPDF(unicode_font=unicode_font)

    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()

        if not line:
            pdf.ln(2)
            continue

        if not unicode_font:
            line = _ascii_fallback(line)

        if not line:
            continue

        if line.startswith("### "):
            pdf.ln(2)
            pdf.set_font(pdf.font_family, size=11)
            pdf.multi_cell(0, 7, line[4:])

        elif line.startswith("## "):
            pdf.ln(3)
            pdf.set_font(pdf.font_family, size=12)
            pdf.multi_cell(0, 8, line[3:])

        elif line.startswith("# "):
            pdf.ln(3)
            pdf.set_font(pdf.font_family, size=14)
            pdf.multi_cell(0, 9, line[2:])

        elif line.startswith(("- ", "* ")):
            pdf.set_font(pdf.font_family, size=9.5)
            pdf.set_x(14)
            pdf.multi_cell(0, 6, "- " + line[2:])

        else:
            pdf.set_font(pdf.font_family, size=9.5)
            pdf.multi_cell(0, 6, line)

    buffer = io.BytesIO()
    pdf.output(buffer)
    buffer.seek(0)

    return buffer.getvalue()
