import io
import re
from fpdf import FPDF

class StudyNotesPDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 13)
        self.set_text_color(79, 70, 229)
        # Using standard ASCII hyphen to prevent character encoding errors
        self.cell(0, 10, 'AI Lecture Digest - Study Notes', border=False, align='C', new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(226, 232, 240)
        self.line(10, 20, 200, 20)
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, f'Page {self.page_no()}', border=False, align='C')

def sanitize_for_pdf(text: str) -> str:
    """Replaces Unicode punctuation and non-ASCII characters with safe ASCII equivalents."""
    replacements = {
        "—": " - ",   # em-dash
        "–": "-",     # en-dash
        "“": '"',     # left double quotation mark
        "”": '"',     # right double quotation mark
        "‘": "'",     # left single quotation mark
        "’": "'",     # right single quotation mark
        "•": "-",     # bullet point
        "…": "...",   # ellipsis
        "\u00a0": " ",# non-breaking space
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return re.sub(r'[^\x00-\x7F]+', ' ', text)

def create_pdf(markdown_text: str) -> bytes:
    pdf = StudyNotesPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    clean_text = sanitize_for_pdf(markdown_text)
    
    for raw_line in clean_text.split('\n'):
        line = raw_line.strip()
        if not line:
            pdf.ln(2)
            continue
            
        if line.startswith('## '):
            pdf.ln(3)
            pdf.set_font('Helvetica', 'B', 11)
            pdf.set_text_color(30, 27, 75)
            pdf.multi_cell(0, 6, line.replace('## ', ''))
            pdf.ln(1)
        elif line.startswith('### '):
            pdf.ln(2)
            pdf.set_font('Helvetica', 'B', 10)
            pdf.set_text_color(79, 70, 229)
            pdf.multi_cell(0, 5, line.replace('### ', ''))
            pdf.ln(1)
        elif line.startswith(('- ', '* ')):
            pdf.set_font('Helvetica', '', 9.5)
            pdf.set_text_color(15, 23, 42)
            bullet_line = "  - " + line[2:]
            pdf.multi_cell(0, 4.5, bullet_line)
        else:
            pdf.set_font('Helvetica', '', 9.5)
            pdf.set_text_color(15, 23, 42)
            pdf.multi_cell(0, 4.5, line)

    buffer = io.BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer.getvalue()
