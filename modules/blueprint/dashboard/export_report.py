import os
import uuid
import zipfile
import base64
from bs4 import BeautifulSoup
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.section import WD_ORIENT
from playwright.sync_api import sync_playwright

def generate_export_files(format_pdf, format_word, charts_data, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    session_id = str(uuid.uuid4())
    
    # Generate temporary HTML structure for Playwright and BeautifulSoup to parse
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body { font-family: sans-serif; }
            .chart-section { margin-bottom: 40px; page-break-after: always; }
            .annual-report-table { 
                border-collapse: collapse; width: 100%; font-size: 10px; table-layout: fixed; margin-bottom: 20px;
            }
            .annual-report-table th, .annual-report-table td { 
                border: 1px solid #ccc; padding: 4px; white-space: normal; word-wrap: break-word; text-align: center;
            }
            .annual-report-table caption { font-weight: bold; font-size: 14px; margin-bottom: 10px; }
            .chart-img { max-width: 100%; height: auto; margin-bottom: 10px; }
            .llm-text { background: #f8f9fa; padding: 10px; border-radius: 5px; font-size: 12px; }
            @page { size: A4 landscape; margin: 1cm; }
        </style>
    </head>
    <body>
    """
    
    image_paths = []
    
    for idx, chart in enumerate(charts_data):
        html_content += f'<div class="chart-section" id="section-{idx}">'
        html_content += f'<h2>{chart.get("title", "")}</h2>'
        
        # Table
        if chart.get('includeTable', True):
            table_html = chart.get('tableHtml', '')
            if table_html:
                html_content += table_html
                
        # Image
        if chart.get('includeChart', True):
            b64_image = chart.get('chartImage', '')
            img_path = ""
            if b64_image and b64_image.startswith('data:image'):
                # Extract base64
                header, encoded = b64_image.split(",", 1)
                img_data = base64.b64decode(encoded)
                img_path = os.path.join(output_dir, f"chart_{session_id}_{idx}.png")
                with open(img_path, "wb") as f:
                    f.write(img_data)
                image_paths.append(img_path)
                html_content += f'<div class="chart-img-wrapper"><img src="file://{img_path.replace(chr(92), "/")}" class="chart-img" /></div>'
                
        # LLM text
        if chart.get('includeAi', True):
            llm_text = chart.get('llmText', '')
            if llm_text:
                html_content += f'<div class="llm-text"><strong>AI 分析敘述:</strong><br/>{llm_text}</div>'
            
        html_content += '</div>'
        
    html_content += "</body></html>"
    
    temp_html_path = os.path.join(output_dir, f"temp_{session_id}.html")
    with open(temp_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    pdf_path = os.path.join(output_dir, f"export_{session_id}.pdf")
    docx_path = os.path.join(output_dir, f"export_{session_id}.docx")
    
    # 1. Generate PDF
    if format_pdf:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("file://" + os.path.abspath(temp_html_path).replace("\\", "/"), wait_until="networkidle")
            page.emulate_media(media="print")
            page.pdf(path=pdf_path, format="A4", landscape=True, print_background=True)
            browser.close()
            
    # 2. Generate Word
    if format_word:
        try:
            with open(temp_html_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f, 'html.parser')
                
            doc = Document()
            section = doc.sections[0]
            section.orientation = WD_ORIENT.LANDSCAPE
            section.page_width = Inches(11.69)
            section.page_height = Inches(8.27)
            section.left_margin = Inches(0.5)
            section.right_margin = Inches(0.5)
            section.top_margin = Inches(0.5)
            section.bottom_margin = Inches(0.5)
            
            sections = soup.find_all('div', class_='chart-section')
            for sec_idx, sec in enumerate(sections):
                if sec_idx > 0:
                    doc.add_page_break()
                    
                title = sec.find('h2')
                if title:
                    doc.add_heading(title.text.strip(), level=1)
                    
                table_node = sec.find('table', class_='annual-report-table')
                if table_node:
                    caption = table_node.find('caption')
                    if caption:
                        doc.add_paragraph(caption.text.strip())
                        
                    rows = table_node.find_all('tr')
                    if rows:
                        num_cols = max(len(row.find_all(['th', 'td'])) for row in rows)
                        w_table = doc.add_table(rows=len(rows), cols=num_cols)
                        w_table.style = 'Table Grid'
                        
                        for r_idx, row in enumerate(rows):
                            cells = row.find_all(['th', 'td'])
                            for c_idx, cell in enumerate(cells):
                                if c_idx >= num_cols:
                                    break
                                w_cell = w_table.cell(r_idx, c_idx)
                                w_cell.text = cell.text.strip()
                                for paragraph in w_cell.paragraphs:
                                    for run in paragraph.runs:
                                        run.font.size = Pt(8)
                                        if cell.name == 'th' or 'fw-bold' in cell.get('class', []):
                                            run.font.bold = True
                                            
                img_node = sec.find('img', class_='chart-img')
                if img_node and img_node.get('src'):
                    src = img_node.get('src').replace('file://', '')
                    if os.path.exists(src):
                        doc.add_picture(src, width=Inches(9.5))
                        
                llm_node = sec.find('div', class_='llm-text')
                if llm_node:
                    doc.add_paragraph(llm_node.text.strip())
                    
            doc.save(docx_path)
        except Exception as e:
            print(f"Word export failed: {e}")
            
    # Cleanup temps
    try:
        os.remove(temp_html_path)
        for p in image_paths:
            if os.path.exists(p):
                os.remove(p)
    except:
        pass
        
    # Return paths
    if format_pdf and format_word:
        zip_path = os.path.join(output_dir, f"export_{session_id}.zip")
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.write(pdf_path, "export_report.pdf")
            zf.write(docx_path, "export_report.docx")
        if os.path.exists(pdf_path): os.remove(pdf_path)
        if os.path.exists(docx_path): os.remove(docx_path)
        return zip_path, "application/zip", "export_report.zip"
    elif format_pdf:
        return pdf_path, "application/pdf", "export_report.pdf"
    elif format_word:
        return docx_path, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "export_report.docx"
    return None, None, None
