import json
import base64
import io
import re
from http.server import BaseHTTPRequestHandler
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

HEADING_COLOR = RGBColor(0x1F, 0x49, 0x7D)
PLACEHOLDER_COLOR = RGBColor(0xC0, 0x39, 0x2B)


def add_formatted_runs(paragraph, text):
    """Parser inline **bold** og legger til riktig formaterte runs."""
    parts = re.split(r'(\*\*[^*]+?\*\*)', text)
    for part in parts:
        if not part:
            continue
        if part.startswith('**') and part.endswith('**'):
            run = paragraph.add_run(part[2:-2])
            run.bold = True
        else:
            run = paragraph.add_run(part)
        if '[FYLL INN' in part:
            run.font.color.rgb = PLACEHOLDER_COLOR
            run.bold = True


def build_docx(text):
    doc = Document()

    for section in doc.sections:
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin = Cm(3)
        section.right_margin = Cm(2.5)

    doc.styles['Normal'].font.name = 'Calibri'
    doc.styles['Normal'].font.size = Pt(11)

    for level, size in [(1, 14), (2, 13), (3, 12)]:
        style = doc.styles[f'Heading {level}']
        style.font.name = 'Calibri'
        style.font.size = Pt(size)
        style.font.color.rgb = HEADING_COLOR
        style.font.bold = True

    table_rows = []
    in_table = False
    on_title_page = True  # Første seksjon (før første ---) er forsiden

    def flush_table():
        if not table_rows:
            return
        max_cols = max(len(r) for r in table_rows)
        tbl = doc.add_table(rows=len(table_rows), cols=max_cols)
        tbl.style = 'Table Grid'
        for r_i, row in enumerate(table_rows):
            for c_i in range(max_cols):
                cell_text = row[c_i] if c_i < len(row) else ''
                cell = tbl.cell(r_i, c_i)
                cell.text = cell_text
                if r_i == 0:
                    for para in cell.paragraphs:
                        for run in para.runs:
                            run.bold = True
        table_rows.clear()

    for line in text.split('\n'):
        s = line.strip()

        if s.startswith('|'):
            cells = [c.strip() for c in s.split('|')[1:-1]]
            is_separator = all(set(c) <= set('-: ') for c in cells)
            if not is_separator:
                in_table = True
                table_rows.append(cells)
            continue

        if in_table:
            flush_table()
            in_table = False

        if not s:
            continue

        if s == '---':
            on_title_page = False
            doc.add_page_break()
            continue

        if s.startswith('# '):
            doc.add_heading(s[2:], level=1)
        elif s.startswith('## '):
            doc.add_heading(s[3:], level=2)
        elif s.startswith('### '):
            doc.add_heading(s[4:], level=3)
        elif s.startswith('- '):
            p = doc.add_paragraph(style='List Bullet')
            add_formatted_runs(p, s[2:])
        elif on_title_page:
            # Forsidetekst: sentrert og stor
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            clean = s.replace('**', '')
            run = p.add_run(clean)
            run.bold = True
            run.font.size = Pt(16)
            run.font.color.rgb = HEADING_COLOR
        else:
            p = doc.add_paragraph()
            add_formatted_runs(p, s)

    if in_table:
        flush_table()

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))

            docx_bytes = build_docx(body.get("document", ""))
            docx_b64 = base64.b64encode(docx_bytes).decode('utf-8')

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"docx": docx_b64}).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
