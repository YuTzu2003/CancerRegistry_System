import os
import io
import html
import zipfile
import base64
from PIL import Image, ImageStat
from bs4 import BeautifulSoup
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from playwright.sync_api import sync_playwright

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(
    PROJECT_ROOT, "tasks", "playwright-browsers"
)

def _split_tall_chart_at_blank_rows(image_bytes, max_height_ratio=0.62):
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    max_chunk_height = max(1, int(image.width * max_height_ratio))
    if image.height <= max_chunk_height:
        return [image_bytes]

    gray = image.convert("L")
    chunks = []
    top = 0
    while image.height - top > max_chunk_height:
        target = top + max_chunk_height
        search_radius = min(max(40, image.height // 100), max_chunk_height // 8)
        search_start = max(top + max_chunk_height // 2, target - search_radius)
        search_end = min(image.height - 1, target + search_radius)
        best_y = target
        best_score = None
        for y in range(search_start, search_end + 1):
            band = gray.crop((0, max(0, y - 3), gray.width, min(gray.height, y + 4)))
            score = 255 - ImageStat.Stat(band).mean[0]
            if best_score is None or score < best_score:
                best_y, best_score = y, score
        if best_y <= top:
            best_y = min(image.height, top + max_chunk_height)
        chunk = image.crop((0, top, image.width, best_y))
        buffer = io.BytesIO()
        chunk.save(buffer, format="PNG")
        chunks.append(buffer.getvalue())
        top = best_y

    if top < image.height:
        buffer = io.BytesIO()
        image.crop((0, top, image.width, image.height)).save(buffer, format="PNG")
        chunks.append(buffer.getvalue())
    return chunks

def _style_indicator_narrative_cell(cell):
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), "E9F5F0")
    tc_pr.append(shading)

    borders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        border = OxmlElement(f"w:{edge}")
        border.set(qn("w:val"), "single")
        border.set(qn("w:sz"), "6")
        border.set(qn("w:color"), "A3CFBB")
        borders.append(border)
    tc_pr.append(borders)

    margins = OxmlElement("w:tcMar")
    for edge in ("top", "left", "bottom", "right"):
        margin = OxmlElement(f"w:{edge}")
        margin.set(qn("w:w"), "130")
        margin.set(qn("w:type"), "dxa")
        margins.append(margin)
    tc_pr.append(margins)


def generate_export_files(format_pdf, format_word, charts_data, output_dir, export_language="zh-TW", filename_base="export_report"):
    os.makedirs(output_dir, exist_ok=True)
    insight_heading = "AI-generated narrative:" if export_language == "en" else "AI 分析敘述："
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body { font-family: sans-serif; margin: 0; }
            .chart-section { margin-bottom: 40px; page-break-after: always; }
            .annual-report-table { 
                border-collapse: collapse; width: 100%; font-size: 10px; margin-bottom: 20px;
            }
            .annual-report-table th, .annual-report-table td { 
                border: 1px solid #ccc; padding: 4px; text-align: center; vertical-align: middle;
            }
            .indicator-export-table { table-layout: fixed; }
            .indicator-export-table th:nth-child(1),
            .indicator-export-table td:nth-child(1) { width: 8%; white-space: nowrap; word-break: keep-all; }
            .indicator-export-table th:nth-child(2),
            .indicator-export-table td:nth-child(2) { width: 6%; white-space: nowrap; }
            .indicator-export-table th:nth-child(3),
            .indicator-export-table td:nth-child(3) { width: 17%; }
            .indicator-export-table th:nth-child(4),
            .indicator-export-table td:nth-child(4),
            .indicator-export-table th:nth-child(5),
            .indicator-export-table td:nth-child(5) { width: 22%; }
            .indicator-export-table th:nth-child(6),
            .indicator-export-table td:nth-child(6),
            .indicator-export-table th:nth-child(7),
            .indicator-export-table td:nth-child(7) { width: 7%; white-space: nowrap; }
            .indicator-export-table th:nth-child(8),
            .indicator-export-table td:nth-child(8) { width: 11%; white-space: nowrap; }
            /* Keep the histology table consistent in Chinese and English exports. */
            .annual-histology-table { table-layout: fixed; }
            .annual-histology-table .annual-histology-name-col,
            .annual-histology-table th:nth-child(1),
            .annual-histology-table td:nth-child(1) { width: 70%; }
            .annual-histology-table .annual-histology-count-col,
            .annual-histology-table th:nth-child(2),
            .annual-histology-table td:nth-child(2) { width: 15%; }
            .annual-histology-table .annual-histology-percent-col,
            .annual-histology-table th:nth-child(3),
            .annual-histology-table td:nth-child(3) { width: 15%; }
            .annual-histology-table td:nth-child(1) {
                text-align: left;
                overflow-wrap: anywhere;
                word-break: break-word;
            }
            .annual-report-table caption { font-weight: bold; font-size: 14px; margin-bottom: 10px; }
            .surgery-table-caption { text-align: center; }
            .annual-report-table:has(+ .annual-stage-report-note) { margin-bottom: 4px; }
            #annualHistologyTableNote { color: #dc3545 !important; font-size: 10px !important; margin-top: -14px !important; margin-bottom: 8px !important; }
            #annualAnalyzableConfirmedNote { margin-top: 6px !important; font-size: 10px !important; line-height: 1.45 !important; text-align: left !important; }
            #annualAnalyzableConfirmedNote .annual-analyzable-note-item { margin-left: 12px !important; }
            .annual-stage-report-note { margin-top: 0 !important; margin-bottom: 14px !important; padding-left: 8px !important; box-sizing: border-box; font-size: 10px !important; line-height: 1.45 !important; text-align: left !important; }
            .stage-export-chart-caption { margin-top: 4px; font-size: 12px; font-weight: bold; text-align: center; }
            .stage-export-chart-note { margin-top: 5px; margin-bottom: 12px; font-size: 10px; line-height: 1.45; text-align: left; }
            .chart-img { max-width: 100%; height: auto; margin-bottom: 15px; display: block; }
            .word-only-chart, .word-only-caption { display: none !important; }
            .indicator-export-chart-block {
                break-inside: avoid; page-break-inside: avoid;
            }
            .indicator-export-chart-heading { margin: 0 0 7px; text-align: center; }
            .indicator-export-chart-title { color: #111827; font-size: 15px; font-weight: 700; }
            .indicator-export-chart-source { color: #6b7280; font-size: 9px; margin-top: 3px; }
            .indicator-export-chart { display: grid; gap: 6px; margin: 6px 0 4px; }
            .indicator-export-chart-caption { color: #111827; font-size: 11px; font-weight: 700; margin-top: 7px; text-align: center; }
            .indicator-export-chart-caption-source { color: #6b7280; font-size: 8px; font-weight: 400; margin-top: 2px; }
            .indicator-export-card {
                border: 1px solid #d1d5db; border-top: 3px solid #64748b; border-radius: 7px;
                box-sizing: border-box; overflow: hidden; break-inside: avoid; page-break-inside: avoid;
            }
            .indicator-export-card.is-success { border-top-color: #45a9a6; }
            .indicator-export-card.is-warning { border-top-color: #b4232c; }
            .indicator-export-head {
                align-items: center; background: #f1f5f9; display: flex; gap: 12px;
                justify-content: space-between; min-height: 23px; padding: 3px 8px;
            }
            .indicator-export-card.is-success .indicator-export-head { background: #e8f6f5; }
            .indicator-export-card.is-warning .indicator-export-head { background: #fdebec; }
            .indicator-export-title { color: #1f2937; font-size: 10px; font-weight: 700; min-width: 0; }
            .indicator-export-meta {
                align-items: center; color: #374151; display: flex; flex: 0 0 auto;
                font-size: 8px; gap: 10px; white-space: nowrap;
            }
            .indicator-export-status { font-weight: 700; }
            .indicator-export-card.is-success .indicator-export-status { color: #15803d; }
            .indicator-export-card.is-warning .indicator-export-status { color: #b4232c; }
            .indicator-export-body { height: 36px; position: relative; }
            .indicator-export-track {
                background: #e5e7eb; height: 8px; left: 8px; overflow: hidden;
                position: absolute; right: 16px; top: 13px;
            }
            .indicator-export-fill { background: #64748b; display: block; height: 100%; }
            .indicator-export-card.is-success .indicator-export-fill { background: #45a9a6; }
            .indicator-export-card.is-warning .indicator-export-fill { background: #dc3545; }
            .indicator-export-threshold-line {
                background: #d89a18; height: 20px; position: absolute; top: 7px;
                transform: translateX(-1px); width: 2px;
            }
            .indicator-export-threshold-label {
                color: #8a6200; font-size: 7px; font-weight: 700; position: absolute;
                top: -1px; transform: translateX(-50%); white-space: nowrap;
            }
            .indicator-export-value {
                color: #374151; font-size: 8px; font-weight: 700; position: absolute;
                top: 23px; transform: translateX(-50%); white-space: nowrap;
            }
            .indicator-export-value.is-zero { left: 8px; top: 0; transform: none; }
            .indicator-export-value.is-full { right: 16px; top: 0; transform: none; }
            .indicator-export-axis { bottom: -1px; color: #6b7280; font-size: 7px; position: absolute; }
            .indicator-export-axis.is-left { left: 8px; }
            .indicator-export-axis.is-right { right: 16px; }
            .chart-img-wrapper.tall-chart { break-before: page; }
            .tall-chart .chart-img-page {
                height: 18cm;
                box-sizing: border-box;
                padding: 0.35cm 0;
                display: flex;
                align-items: center;
                justify-content: center;
                break-inside: avoid;
                break-after: page;
            }
            .tall-chart .chart-img-page:last-child { break-after: auto; }
            .tall-chart .chart-img {
                width: 100%;
                max-height: 17.3cm;
                object-fit: contain;
                margin: 0;
            }
            .llm-text {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                font-size: 12px;
                white-space: pre-wrap;
                margin-top: 15px;
                break-inside: avoid;
                page-break-inside: avoid;
            }
            .indicator-export-narrative {
                background: #e9f5f0; border: 1px solid #a3cfbb; border-radius: 7px;
                box-sizing: border-box; color: #111827; font-size: 11px; line-height: 1.7;
                margin-top: 12px; padding: 11px 14px;
            }
            .indicator-export-narrative-title { font-size: 11px; font-weight: 700; margin-bottom: 5px; }
            .indicator-export-narrative-text { white-space: pre-wrap; }
            .text-center { text-align: center !important; }
            .text-start { text-align: left !important; }
            .text-end { text-align: right !important; }
            .annual-report-table.text-start tbody td:first-child { text-align: left !important; }
            .annual-report-table.text-start tbody tr.table-secondary td:first-child { text-align: center !important; }
            .fw-bold { font-weight: bold !important; }
            .ps-4 { padding-left: 1.5rem !important; }
            .table-light { background-color: #f8f9fa !important; }
            .table-secondary { background-color: #e2e3e5 !important; }
            @page { size: A4 landscape; margin: 1cm; }
        </style>
    </head>
    <body>
    """
    
    image_bytes_map = {}
    
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
            chart_html = chart.get('chartHtml', '')
            b64_image = chart.get('chartImage', '')
            if b64_image and b64_image.startswith('data:image'):
                header, encoded = b64_image.split(",", 1)
                image_bytes = base64.b64decode(encoded)
                image_parts = (_split_tall_chart_at_blank_rows(image_bytes)
                               if chart.get("id") == "chartPane-DiagnosisHistology"
                               else [image_bytes])
                image_bytes_map[str(idx)] = image_parts
                wrapper_class = "chart-img-wrapper tall-chart" if len(image_parts) > 1 else "chart-img-wrapper"
                if chart_html:
                    html_content += chart_html
                    wrapper_class += " word-only-chart"
                html_content += f'<div class="{wrapper_class}">'
                for part_idx, part in enumerate(image_parts):
                    part_b64 = base64.b64encode(part).decode("ascii")
                    image_html = (f'<img src="data:image/png;base64,{part_b64}" '
                                  f'class="chart-img chart-img-part" data-idx="{idx}" data-part="{part_idx}" />')
                    html_content += (f'<div class="chart-img-page">{image_html}</div>'
                                     if len(image_parts) > 1 else image_html)
                html_content += '</div>'
                chart_caption = chart.get('chartCaption', '')
                chart_note = chart.get('chartNote', '')
                if chart_caption:
                    caption_class = "stage-export-chart-caption word-only-caption" if chart_html else "stage-export-chart-caption"
                    html_content += f'<div class="{caption_class}">{chart_caption}</div>'
                if chart_note:
                    html_content += f'<div class="stage-export-chart-note">{chart_note}</div>'
            elif chart_html:
                html_content += chart_html
                
        # LLM text
        if chart.get('includeAi', True):
            llm_text = chart.get('llmText', '')
            if llm_text:
                if chart.get('exportKind') == 'indicators':
                    narrative_heading = chart.get('narrativeHeading') or '語言模型敘述'
                    html_content += (
                        '<div class="llm-text indicator-export-narrative">'
                        f'<div class="indicator-export-narrative-title">{html.escape(str(narrative_heading))}</div>'
                        f'<div class="indicator-export-narrative-text">{html.escape(str(llm_text))}</div>'
                        '</div>'
                    )
                else:
                    html_content += f'<div class="llm-text"><strong>{insight_heading}</strong><br/>{llm_text}</div>'
        html_content += '</div>'    
    html_content += "</body></html>"
    
    pdf_bytes = None
    docx_bytes = None
    indicator_word_images = {}
    needs_indicator_word_images = format_word and any(
        chart.get("exportKind") == "indicators" and chart.get("includeChart", True) and chart.get("chartHtml")
        for chart in charts_data
    )
    
    # 1. Generate PDF and pixel-identical indicator charts for Word.
    if format_pdf or needs_indicator_word_images:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1600, "height": 1200}, device_scale_factor=1.5)
            page.set_content(html_content, wait_until="networkidle")
            page.emulate_media(media="print")
            if needs_indicator_word_images:
                word_chart_style = page.add_style_tag(content="""
                    .indicator-export-chart-heading { margin-bottom: 10px !important; }
                    .indicator-export-chart-title { font-size: 20px !important; }
                    .indicator-export-chart-source { font-size: 11px !important; margin-top: 4px !important; }
                    .indicator-export-chart { gap: 8px !important; margin-top: 8px !important; }
                    .indicator-export-head { min-height: 31px !important; padding: 5px 10px !important; }
                    .indicator-export-title { font-size: 13px !important; }
                    .indicator-export-meta { font-size: 11px !important; gap: 12px !important; }
                    .indicator-export-body { height: 50px !important; }
                    .indicator-export-track { height: 11px !important; top: 18px !important; }
                    .indicator-export-threshold-line { height: 28px !important; top: 9px !important; width: 3px !important; }
                    .indicator-export-threshold-label { font-size: 10px !important; top: -1px !important; }
                    .indicator-export-value { font-size: 11px !important; top: 32px !important; }
                    .indicator-export-value.is-zero,
                    .indicator-export-value.is-full { top: 0 !important; }
                    .indicator-export-axis { font-size: 9px !important; }
                    .indicator-export-chart-caption { font-size: 15px !important; margin-top: 10px !important; }
                    .indicator-export-chart-caption-source { font-size: 10px !important; margin-top: 3px !important; }
                """)
                for idx, chart in enumerate(charts_data):
                    if chart.get("exportKind") != "indicators" or not chart.get("includeChart", True):
                        continue
                    chart_block = page.locator(f"#section-{idx} .indicator-export-chart-block")
                    if chart_block.count():
                        indicator_word_images[str(idx)] = chart_block.screenshot(type="png")
                word_chart_style.evaluate("node => node.remove()")
            if format_pdf:
                pdf_bytes = page.pdf(format="A4", landscape=True, print_background=True)
            browser.close()
            
    # 2. Generate Word
    if format_word:
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
                
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
                chart_data = charts_data[sec_idx] if sec_idx < len(charts_data) else {}
                is_indicator_export = chart_data.get('exportKind') == 'indicators'
                if sec_idx > 0:
                    doc.add_page_break()
                    
                title = sec.find('h2')
                if title:
                    doc.add_heading(title.text.strip(), level=1)
                    
                table_node = sec.find('table', class_='annual-report-table')
                if table_node:
                    table_classes = table_node.get('class', [])
                    if isinstance(table_classes, str):
                        table_classes = table_classes.split()
                    is_histology_table = 'annual-histology-table' in table_classes
                    caption = table_node.find('caption')
                    if caption:
                        doc.add_paragraph(caption.get_text(separator='\n').strip())
                        
                    rows = table_node.find_all('tr')
                    if rows:
                        # Determine exact grid dimensions
                        grid = {}
                        max_cols = 0
                        for r_idx, row in enumerate(rows):
                            cells = row.find_all(['th', 'td'])
                            c_idx = 0
                            for cell in cells:
                                # Find first empty spot in this row
                                while (r_idx, c_idx) in grid:
                                    c_idx += 1
                                
                                rowspan = int(cell.get('rowspan', 1))
                                colspan = int(cell.get('colspan', 1))
                                
                                # parse classes and styles
                                cell_classes = cell.get('class', [])
                                if isinstance(cell_classes, str): cell_classes = cell_classes.split()
                                row_classes = row.get('class', [])
                                if isinstance(row_classes, str): row_classes = row_classes.split()
                                all_classes = table_classes + row_classes + cell_classes
                                
                                style_str = (cell.get('style', '') or '') + ';' + (row.get('style', '') or '')
                                is_bold = cell.name == 'th' or 'fw-bold' in all_classes or 'bold' in style_str or '900' in style_str
                                
                                alignment = WD_ALIGN_PARAGRAPH.CENTER
                                if 'text-start' in all_classes or 'ps-4' in cell_classes:
                                    alignment = WD_ALIGN_PARAGRAPH.LEFT
                                if 'text-center' in cell_classes:
                                    alignment = WD_ALIGN_PARAGRAPH.CENTER
                                elif 'text-end' in cell_classes:
                                    alignment = WD_ALIGN_PARAGRAPH.RIGHT
                                
                                font_color = None
                                import re
                                color_match = re.search(r'color:\s*([^;]+)', style_str)
                                if color_match:
                                    font_color = color_match.group(1).strip()
                                
                                # Mark the grid
                                for r in range(rowspan):
                                    for c in range(colspan):
                                        grid[(r_idx + r, c_idx + c)] = {
                                            'text': cell.text.strip(),
                                            'is_head': is_bold,
                                            'alignment': alignment,
                                            'font_color': font_color,
                                            'main_r': r_idx,
                                            'main_c': c_idx,
                                            'rowspan': rowspan,
                                            'colspan': colspan
                                        }
                                
                                c_idx += colspan
                                max_cols = max(max_cols, c_idx)
                                
                        if max_cols > 0:
                            w_table = doc.add_table(rows=len(rows), cols=max_cols)
                            w_table.style = 'Table Grid'
                            if is_histology_table and max_cols == 4:
                                # Match the fixed 20 / 50 / 13 / 17 percent layout used in the PDF.
                                w_table.autofit = False
                                histology_widths = [Inches(1.8), Inches(4.5), Inches(1.17), Inches(1.53)]
                                for row in w_table.rows:
                                    for col_idx, width in enumerate(histology_widths):
                                        row.cells[col_idx].width = width
                            
                            # Apply merges
                            merged_cells = set()
                            for (r, c), data in grid.items():
                                if (r, c) in merged_cells:
                                    continue
                                if data['rowspan'] > 1 or data['colspan'] > 1:
                                    main_cell = w_table.cell(data['main_r'], data['main_c'])
                                    target_cell = w_table.cell(data['main_r'] + data['rowspan'] - 1, data['main_c'] + data['colspan'] - 1)
                                    main_cell.merge(target_cell)
                                    for mr in range(data['rowspan']):
                                        for mc in range(data['colspan']):
                                            merged_cells.add((data['main_r'] + mr, data['main_c'] + mc))
                                    
                            # Write text and apply styles to the main cells
                            written = set()
                            for (r, c), data in grid.items():
                                mr, mc = data['main_r'], data['main_c']
                                if (mr, mc) not in written:
                                    w_cell = w_table.cell(mr, mc)
                                    w_cell.text = data['text']
                                    for paragraph in w_cell.paragraphs:
                                        paragraph.alignment = data['alignment']
                                        for run in paragraph.runs:
                                            run.font.size = Pt(8)
                                            if data['is_head']:
                                                run.font.bold = True
                                            if data['font_color']:
                                                if 'darkred' in data['font_color']: run.font.color.rgb = RGBColor(139, 0, 0)
                                                elif 'red' in data['font_color']: run.font.color.rgb = RGBColor(255, 0, 0)
                                    # Ensure minimal padding to prevent overlap
                                    written.add((mr, mc))

                    analyzable_note = table_node.find_next_sibling(id='annualAnalyzableConfirmedNote')
                    if analyzable_note:
                        note_lines = [line.strip() for line in analyzable_note.get_text(separator='\n').split('\n') if line.strip()]
                        for idx, note_line in enumerate(note_lines):
                            note_paragraph = doc.add_paragraph(note_line)
                            note_paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                            note_paragraph.paragraph_format.space_before = Pt(0)
                            note_paragraph.paragraph_format.space_after = Pt(0)
                            if idx > 0:
                                note_paragraph.paragraph_format.left_indent = Inches(0.12)
                            for run in note_paragraph.runs:
                                run.font.size = Pt(8)

                    histology_note = table_node.find_next_sibling(id='annualHistologyTableNote')
                    if histology_note:
                        note_text = histology_note.get_text(separator='\n').strip()
                        if note_text:
                            note_paragraph = doc.add_paragraph(note_text)
                            note_paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                            note_paragraph.paragraph_format.space_before = Pt(0)
                            note_paragraph.paragraph_format.space_after = Pt(0)
                            for run in note_paragraph.runs:
                                run.font.size = Pt(8)
                                run.font.color.rgb = RGBColor(220, 53, 69)

                    stage_note = table_node.find_next_sibling('div', class_='annual-stage-report-note')
                    if stage_note:
                        note_text = stage_note.get_text(separator='\n').strip()
                        if note_text:
                            note_paragraph = doc.add_paragraph(note_text)
                            note_paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                            note_paragraph.paragraph_format.space_before = Pt(0)
                            note_paragraph.paragraph_format.space_after = Pt(0)
                            for run in note_paragraph.runs:
                                run.font.size = Pt(8)
                                            
                indicator_word_image = indicator_word_images.get(str(sec_idx))
                img_nodes = sec.find_all('img', class_='chart-img')
                if indicator_word_image:
                    image_paragraph = doc.add_paragraph()
                    image_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    image_paragraph.paragraph_format.space_before = Pt(5)
                    image_paragraph.paragraph_format.space_after = Pt(5)
                    image_paragraph.add_run().add_picture(io.BytesIO(indicator_word_image), width=Inches(10.65))
                elif img_nodes:
                    idx_str = img_nodes[0].get('data-idx')
                    image_parts = image_bytes_map.get(idx_str, [])
                    for part_idx, image_part in enumerate(image_parts):
                        if part_idx > 0:
                            doc.add_page_break()
                        doc.add_paragraph()
                        doc.add_picture(io.BytesIO(image_part), width=Inches(9.0))

                chart_caption_node = sec.find('div', class_='stage-export-chart-caption')
                if chart_caption_node and not indicator_word_image:
                    caption_paragraph = doc.add_paragraph(chart_caption_node.get_text(separator=' ').strip())
                    caption_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    caption_paragraph.paragraph_format.space_before = Pt(2)
                    caption_paragraph.paragraph_format.space_after = Pt(2)
                    for run in caption_paragraph.runs:
                        run.font.size = Pt(9)
                        run.font.bold = True

                chart_note_node = sec.find('div', class_='stage-export-chart-note')
                if chart_note_node:
                    note_paragraph = doc.add_paragraph(chart_note_node.get_text(separator=' ').strip())
                    note_paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    note_paragraph.paragraph_format.space_before = Pt(0)
                    note_paragraph.paragraph_format.space_after = Pt(4)
                    for run in note_paragraph.runs:
                        run.font.size = Pt(8)
                        
                llm_node = sec.find('div', class_='llm-text')
                if llm_node:
                    if is_indicator_export:
                        doc.add_paragraph().paragraph_format.space_after = Pt(0)
                        narrative_table = doc.add_table(rows=1, cols=1)
                        narrative_table.autofit = True
                        narrative_cell = narrative_table.cell(0, 0)
                        _style_indicator_narrative_cell(narrative_cell)
                        title_text = chart_data.get('narrativeHeading') or '語言模型敘述'
                        title_paragraph = narrative_cell.paragraphs[0]
                        title_paragraph.paragraph_format.space_after = Pt(4)
                        title_run = title_paragraph.add_run(str(title_text))
                        title_run.bold = True
                        title_run.font.size = Pt(10)
                        narrative_text = str(chart_data.get('llmText') or '').strip()
                        text_paragraph = narrative_cell.add_paragraph(narrative_text)
                        text_paragraph.paragraph_format.space_before = Pt(0)
                        text_paragraph.paragraph_format.space_after = Pt(0)
                        text_paragraph.paragraph_format.line_spacing = 1.25
                        for run in text_paragraph.runs:
                            run.font.size = Pt(10)
                    else:
                        doc.add_paragraph()
                        # Split by newlines so Word formats paragraphs properly
                        lines = llm_node.text.strip().split('\n')
                        for line in lines:
                            if line.strip():
                                doc.add_paragraph(line.strip())
                    
            docx_buffer = io.BytesIO()
            doc.save(docx_buffer)
            docx_bytes = docx_buffer.getvalue()
        except Exception as e:
            print(f"Word export failed: {e}")
            
    # Return bytes in io.BytesIO
    if format_pdf and format_word:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            if pdf_bytes:
                zf.writestr(f"{filename_base}.pdf", pdf_bytes)
            if docx_bytes:
                zf.writestr(f"{filename_base}.docx", docx_bytes)
        zip_buffer.seek(0)
        return zip_buffer, "application/zip", f"{filename_base}.zip"
    elif format_pdf and pdf_bytes:
        return io.BytesIO(pdf_bytes), "application/pdf", f"{filename_base}.pdf"
    elif format_word and docx_bytes:
        return io.BytesIO(docx_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document", f"{filename_base}.docx"
    return None, None, None
