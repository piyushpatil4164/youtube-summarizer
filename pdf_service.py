from fpdf import FPDF
import re

class SecurePDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 12)
        self.set_text_color(99, 102, 241)
        self.cell(0, 10, 'LectureDigest AI - Study Notes', border=False, align='L')
        self.ln(12)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f'Page {self.page_no()}', border=False, align='C')

def sanitize_text_for_pdf(text: str) -> str:
    """Encodes text to standard Latin-1 compatible characters to prevent PDF export errors."""
    replacements = {
        '\u2018': "'", '\u2019': "'",
        '\u201c': '"', '\u201d': '"',
        '\u2013': '-', '\u2014': '-',
        '\u2026': '...', '\u2022': '*',
    }
    for orig, rep in replacements.items():
        text = text.replace(orig, rep)
    
    # Strip non-latin1 characters
    return text.encode('latin-1', 'ignore').decode('latin-1')

def create_pdf(markdown_text: str) -> bytes:
    """Generates an in-memory PDF without storing files on disk or exposing server paths."""
    pdf = SecurePDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Clean PDF Metadata (Removes local creator/OS info)
    pdf.set_title("Study Notes")
    pdf.set_author("LectureDigest AI")
    pdf.set_creator("LectureDigest AI Engine")
    
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(40, 40, 40)

    clean_content = sanitize_text_for_pdf(markdown_text)

    for line in clean_content.split('\n'):
        line_clean = line.strip()
        if not line_clean:
            pdf.ln(4)
            continue
        
        # Headers
        if line_clean.startswith('# '):
            pdf.ln(3)
            pdf.set_font("Helvetica", 'B', 14)
            pdf.set_text_color(30, 41, 59)
            pdf.multi_cell(0, 7, line_clean.replace('# ', ''))
            pdf.set_font("Helvetica", size=10)
            pdf.set_text_color(40, 40, 40)
        elif line_clean.startswith('## '):
            pdf.ln(2)
            pdf.set_font("Helvetica", 'B', 12)
            pdf.set_text_color(79, 70, 229)
            pdf.multi_cell(0, 6, line_clean.replace('## ', ''))
            pdf.set_font("Helvetica", size=10)
            pdf.set_text_color(40, 40, 40)
        elif line_clean.startswith('### '):
            pdf.set_font("Helvetica", 'B', 10)
            pdf.multi_cell(0, 5, line_clean.replace('### ', ''))
            pdf.set_font("Helvetica", size=10)
        else:
            # Strip bold formatting markers for plain PDF rendering
            stripped_line = re.sub(r'\*\*(.*?)\*\*', r'\1', line_clean)
            pdf.multi_cell(0, 5, stripped_line)

    return bytes(pdf.output())
