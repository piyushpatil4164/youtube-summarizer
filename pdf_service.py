from fpdf import FPDF

class LectureNotesPDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 12)
        self.cell(self.epw, 10, 'Lecture Notes & Study Digest', border=False, align='C', new_x="LMARGIN", new_y="NEXT")
        self.line(10, 20, 200, 20)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(self.epw, 10, f'Page {self.page_no()}', align='C')

def create_pdf(text_content: str, title: str = "Video Notes") -> bytes:
    """Converts Markdown text to clean, downloadable PDF bytes."""
    pdf = LectureNotesPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Document Title
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(pdf.epw, 10, title[:60], align='L', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    
    # Clean standard Markdown formatting
    clean_text = text_content.replace('**', '').replace('###', '').replace('##', '').replace('#', '')
    
    pdf.set_font('Helvetica', size=10)
    for line in clean_text.split('\n'):
        safe_line = line.encode('latin-1', 'replace').decode('latin-1').strip()
        if not safe_line:
            pdf.ln(4)
        else:
            pdf.multi_cell(w=pdf.epw, h=6, text=safe_line, new_x="LMARGIN", new_y="NEXT")
            
    return bytes(pdf.output())