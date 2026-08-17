import re
from fpdf import FPDF

class LecturePDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(99, 102, 241)
        self.set_x(self.l_margin)
        self.cell(self.epw, 8, 'LectureDigest AI - Study Notes', border=0, align='L')
        self.ln(10)

    def footer(self):
        self.set_y(-12)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(140, 140, 140)
        self.cell(self.epw, 8, f'Page {self.page_no()}', border=0, align='C')

def sanitize_pdf_text(text: str) -> str:
    """Sanitizes text for standard Latin-1 PDF output."""
    replacements = {
        '\u2018': "'", '\u2019': "'",
        '\u201c': '"', '\u201d': '"',
        '\u2013': '-', '\u2014': '-',
        '\u2026': '...', '\u2022': '*',
        '•': '*', '–': '-', '—': '-',
        '’': "'", '‘': "'", '“': '"', '”': '"'
    }
    for orig, rep in replacements.items():
        text = text.replace(orig, rep)
    
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    
    return text.encode('latin-1', 'replace').decode('latin-1')

def create_pdf(markdown_text: str) -> bytes:
    """Renders notes into a downloadable PDF."""
    try:
        pdf = LecturePDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_margins(15, 15, 15)
        pdf.add_page()
        
        pdf.set_title("LectureDigest Study Notes")
        pdf.set_author("LectureDigest AI")

        clean_text = sanitize_pdf_text(markdown_text)

        for line in clean_text.split('\n'):
            line_str = line.strip()
            pdf.set_x(pdf.l_margin)
            
            if not line_str:
                pdf.ln(3)
                continue
            
            if line_str.startswith('# '):
                pdf.ln(2)
                pdf.set_font("Helvetica", 'B', 13)
                pdf.set_text_color(30, 41, 59)
                pdf.multi_cell(pdf.epw, 6, line_str.replace('# ', ''))
                pdf.ln(1)
            elif line_str.startswith('## '):
                pdf.ln(2)
                pdf.set_font("Helvetica", 'B', 11)
                pdf.set_text_color(79, 70, 229)
                pdf.multi_cell(pdf.epw, 5, line_str.replace('## ', ''))
                pdf.ln(1)
            elif line_str.startswith('### '):
                pdf.set_font("Helvetica", 'B', 10)
                pdf.set_text_color(51, 65, 85)
                pdf.multi_cell(pdf.epw, 5, line_str.replace('### ', ''))
            else:
                pdf.set_font("Helvetica", size=9.5)
                pdf.set_text_color(30, 30, 30)
                pdf.multi_cell(pdf.epw, 4.5, line_str)

        return bytes(pdf.output())

    except Exception:
        fallback_pdf = FPDF()
        fallback_pdf.add_page()
        fallback_pdf.set_font("Helvetica", size=10)
        fallback_pdf.multi_cell(fallback_pdf.epw, 5, sanitize_pdf_text(markdown_text))
        return bytes(fallback_pdf.output())
