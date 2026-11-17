"""Template-driven editable PowerPoint export."""

from __future__ import annotations

import math
import os
import re
import unicodedata
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import ImageFont
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Inches, Pt

from .models import ReportBatch, ReportDeck, ReportRow, ReportTable, SurvivalEstimate
from .summary_builder import SummaryItem, build_benchmark_summary


HEADER_FILL = RGBColor(198, 217, 241)
WHITE = RGBColor(255, 255, 255)
BLACK = RGBColor(0, 0, 0)
HOSPITAL_BLUE = RGBColor(0, 51, 204)
OBSERVATION_LABEL_BLUE = RGBColor(0, 0, 255)
ACCENT_RED = RGBColor(255, 0, 0)
LOCAL_HOSPITAL_BROWN = RGBColor(124, 75, 35)
PAGE_NUMBER_COLOR = RGBColor(0, 0, 0)
FONT_NAME = "微軟正黑體"
TITLE_FONT_NAME = "標楷體"
TABLE_LATIN_FONT = "+mj-lt"
FONT_FILE = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "msjh.ttc"
OVERVIEW_MAX_FONT_SIZE = 20
OVERVIEW_MIN_FONT_SIZE = 10

TITLE_GEOMETRY = (395536, 18288, 8229600, 530352)
TITLE_TABLE_GAP = 45720
PAGE_GEOMETRY = (6553200, 6356350, 2133600, 365125)
NOTES_GEOMETRY = (179512, 6165304, 7848872, 430887)
STANDARD_TABLE_GEOMETRY = (50800, 772160, 8964890, 5192131)

_CHINESE_NUMERALS = {
    1: "一",
    2: "二",
    3: "三",
    4: "四",
    5: "五",
    6: "六",
    7: "七",
    8: "八",
    9: "九",
    10: "十",
}


def _detail_key(cancer: str, staging_system: str) -> tuple[str, str]:
    cancer_key = re.sub(
        r"[\s_\-－—]+",
        "",
        unicodedata.normalize("NFKC", cancer).casefold(),
    )
    staging_key = re.sub(
        r"\s+",
        "",
        unicodedata.normalize("NFKC", staging_system).casefold(),
    )
    return cancer_key, staging_key


_FINALIZED_TITLE_LEFTS = {
    _detail_key("肺癌 非小細胞癌-鱗狀細胞癌", "AJCC"): 683568,
    _detail_key("肺癌 小細胞癌", "AJCC"): 683568,
}


@dataclass(frozen=True)
class _DetailLayout:
    left: int
    top: int
    width: int
    height: int
    column_widths: tuple[int, ...]
    first_header_height: int
    second_header_height: int


_FINALIZED_DETAIL_LAYOUTS = {
    _detail_key("大腸癌-all", "AJCC"): _DetailLayout(50800, 772160, 8964890, 5192131, (538842, 628460, 628460, 1792282, 1792282, 1792282, 1792282), 336970, 904486),
    _detail_key("大腸癌-結腸癌", "AJCC"): _DetailLayout(107502, 767437, 8928994, 5253852, (570350, 623434, 623434, 1777944, 1777944, 1777944, 1777944), 336970, 966207),
    _detail_key("大腸癌-直腸癌", "AJCC"): _DetailLayout(107502, 655509, 8928994, 5365775, (570350, 623434, 623434, 1777944, 1777944, 1777944, 1777944), 344148, 986791),
    _detail_key("子宮頸癌", "FIGO"): _DetailLayout(179512, 548681, 8784977, 5754404, (561151, 613379, 613379, 1749267, 1749267, 1749267, 1749267), 282928, 797191),
    _detail_key("子宮體癌", "FIGO"): _DetailLayout(251516, 767431, 8640960, 5541888, (551950, 603323, 603323, 1720591, 1720591, 1720591, 1720591), 355443, 1019178),
    _detail_key("卵巢癌", "FIGO"): _DetailLayout(179510, 767437, 8712973, 5469877, (556551, 608351, 608351, 1734930, 1734930, 1734930, 1734930), 350825, 1005935),
    _detail_key("女性乳癌", "AJCC"): _DetailLayout(179510, 767436, 8712973, 5397865, (556551, 608351, 608351, 1734930, 1734930, 1734930, 1734930), 348846, 1000260),
    _detail_key("肺癌 非小細胞癌-all", "AJCC"): _DetailLayout(323530, 767437, 8568952, 5532778, (547352, 598296, 598296, 1706252, 1706252, 1706252, 1706252), 243601, 698490),
    _detail_key("肺癌 非小細胞癌-腺癌", "AJCC"): _DetailLayout(323530, 767437, 8568952, 5541880, (547352, 598296, 598296, 1706252, 1706252, 1706252, 1706252), 243601, 698490),
    _detail_key("肺癌 非小細胞癌-鱗狀細胞癌", "AJCC"): _DetailLayout(323530, 767437, 8496944, 5613887, (542752, 593268, 593268, 1691914, 1691914, 1691914, 1691914), 246766, 707565),
    _detail_key("肺癌 小細胞癌", "AJCC"): _DetailLayout(323530, 767437, 8496944, 4328421, (542752, 593268, 593268, 1691914, 1691914, 1691914, 1691914), 276244, 792090),
    _detail_key("食道癌", "AJCC"): _DetailLayout(179510, 767437, 8784981, 5325863, (561151, 613379, 613379, 1749268, 1749268, 1749268, 1749268), 341588, 979450),
    _detail_key("肝癌", "BCLC"): _DetailLayout(179510, 767437, 8712969, 5541886, (556551, 608351, 608351, 1734929, 1734929, 1734929, 1734929), 355443, 1019177),
    _detail_key("胃癌", "AJCC"): _DetailLayout(179510, 767437, 8640964, 5397864, (551952, 603324, 603324, 1720591, 1720591, 1720591, 1720591), 346206, 992692),
    _detail_key("鼻咽癌", "AJCC"): _DetailLayout(251521, 620689, 8640963, 5688632, (551953, 603323, 603323, 1720591, 1720591, 1720591, 1720591), 279391, 801114),
    _detail_key("口腔癌", "AJCC"): _DetailLayout(251522, 548681, 8424932, 5832654, (538152, 588240, 588240, 1677575, 1677575, 1677575, 1677575), 286465, 821394),
    _detail_key("下咽癌", "AJCC"): _DetailLayout(323527, 548681, 8568952, 5760643, (507680, 554931, 554931, 1582585, 1582585, 1893120, 1893120), 282928, 811254),
    _detail_key("喉癌", "AJCC"): _DetailLayout(107503, 620689, 8856985, 5635018, (565751, 618407, 618407, 1763605, 1763605, 1763605, 1763605), 201016, 576381),
    _detail_key("口咽癌_p16+", "AJCC"): _DetailLayout(179512, 767438, 8784975, 5613889, (561149, 613379, 613379, 1749267, 1749267, 1749267, 1749267), 360061, 1032420),
    _detail_key("口咽癌_p16-", "AJCC"): _DetailLayout(179511, 620689, 8712969, 5760643, (556551, 608351, 608351, 1734929, 1734929, 1734929, 1734929), 282928, 811254),
    _detail_key("膀胱癌", "AJCC"): _DetailLayout(179510, 767437, 8568956, 5613890, (547352, 598296, 598296, 1706253, 1706253, 1706253, 1706253), 360062, 1032420),
    _detail_key("攝護腺癌", "AJCC"): _DetailLayout(179510, 767437, 8568956, 5469877, (547352, 598296, 598296, 1706253, 1706253, 1706253, 1706253), 350825, 1005935),
}

_FINALIZED_NOTES_POSITIONS = {
    _detail_key("大腸癌-all", "AJCC"): (179512, 6165304),
    _detail_key("大腸癌-結腸癌", "AJCC"): (179512, 6165304),
    _detail_key("大腸癌-直腸癌", "AJCC"): (179512, 6165304),
    _detail_key("子宮頸癌", "FIGO"): (179512, 6427113),
    _detail_key("子宮體癌", "FIGO"): (251520, 6427113),
    _detail_key("卵巢癌", "FIGO"): (251520, 6309320),
    _detail_key("女性乳癌", "AJCC"): (179512, 6309320),
    _detail_key("肺癌 非小細胞癌-all", "AJCC"): (0, 6427113),
    _detail_key("肺癌 非小細胞癌-腺癌", "AJCC"): (0, 6427113),
    _detail_key("肺癌 非小細胞癌-鱗狀細胞癌", "AJCC"): (0, 6427113),
    _detail_key("肺癌 小細胞癌", "AJCC"): (323528, 5301208),
    _detail_key("食道癌", "AJCC"): (251520, 6309320),
    _detail_key("肝癌", "BCLC"): (179512, 6309320),
    _detail_key("胃癌", "AJCC"): (179512, 6309320),
    _detail_key("鼻咽癌", "AJCC"): (0, 6427113),
    _detail_key("口腔癌", "AJCC"): (0, 6427113),
    _detail_key("下咽癌", "AJCC"): (0, 6427113),
    _detail_key("喉癌", "AJCC"): (0, 6427113),
    _detail_key("口咽癌_p16+", "AJCC"): (0, 6427113),
    _detail_key("口咽癌_p16-", "AJCC"): (0, 6427113),
    _detail_key("膀胱癌", "AJCC"): (0, 6427113),
    _detail_key("攝護腺癌", "AJCC"): (0, 6427113),
}

MIN_NOTES_GAP = 45720
NOTES_GAP_OVERRIDES = {
    _detail_key("喉癌", "AJCC"): 137160,
}


def _remove_slide(presentation: Presentation, index: int) -> None:
    slide_id = presentation.slides._sldIdLst[index]
    presentation.part.drop_rel(slide_id.rId)
    del presentation.slides._sldIdLst[index]


def _set_border(cell, color: str = "000000", width: str = "12700") -> None:
    properties = cell._tc.get_or_add_tcPr()
    for edge_index, edge in enumerate(("a:lnL", "a:lnR", "a:lnT", "a:lnB")):
        existing = properties.find(qn(edge))
        if existing is not None:
            properties.remove(existing)
        line = OxmlElement(edge)
        line.set("w", width)
        line.set("cap", "flat")
        line.set("cmpd", "sng")
        line.set("algn", "ctr")
        solid = OxmlElement("a:solidFill")
        rgb = OxmlElement("a:srgbClr")
        rgb.set("val", color)
        solid.append(rgb)
        line.append(solid)
        dash = OxmlElement("a:prstDash")
        dash.set("val", "solid")
        line.append(dash)
        line.append(OxmlElement("a:round"))
        for end_name in ("a:headEnd", "a:tailEnd"):
            end = OxmlElement(end_name)
            end.set("type", "none")
            end.set("w", "med")
            end.set("len", "med")
            line.append(end)
        # DrawingML requires border elements before the cell fill. PowerPoint
        # ignores otherwise-valid lines when they are appended after solidFill.
        properties.insert(edge_index, line)


def _set_border_no_fill(cell, edge: str) -> None:
    properties = cell._tc.get_or_add_tcPr()
    existing = properties.find(qn(edge))
    if existing is not None:
        properties.remove(existing)
    line = OxmlElement(edge)
    line.append(OxmlElement("a:noFill"))
    edge_order = ("a:lnL", "a:lnR", "a:lnT", "a:lnB")
    properties.insert(edge_order.index(edge), line)


def _set_table_run_typefaces(run, text: str) -> None:
    """Match the finalized deck's theme Latin and East Asian table fonts."""
    properties = run._r.get_or_add_rPr()
    latin = properties.find(qn("a:latin"))
    if latin is None:
        latin = OxmlElement("a:latin")
        properties.append(latin)
    latin.set("typeface", TABLE_LATIN_FONT)
    has_east_asian_text = any(
        "\u3400" <= character <= "\u9fff"
        for character in text
    )
    east_asian = properties.find(qn("a:ea"))
    if has_east_asian_text:
        if east_asian is None:
            east_asian = OxmlElement("a:ea")
            properties.append(east_asian)
        east_asian.set("typeface", FONT_NAME)
    elif east_asian is not None:
        properties.remove(east_asian)


def _set_cell(
    cell,
    text: str,
    *,
    size: float = 10,
    bold: bool = False,
    color: RGBColor = BLACK,
    fill: RGBColor = WHITE,
) -> None:
    cell.fill.solid()
    cell.fill.fore_color.rgb = fill
    cell.margin_left = 9525
    cell.margin_right = 9525
    cell.margin_top = 9525
    cell.margin_bottom = 0
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    frame = cell.text_frame
    frame.clear()
    frame.word_wrap = True
    paragraph = frame.paragraphs[0]
    paragraph.alignment = PP_ALIGN.CENTER
    run = paragraph.add_run()
    run.text = text
    _set_table_run_typefaces(run, text)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    _set_border(cell)


def _format_number(value: int | None) -> str:
    return "-" if value is None else str(value)


def _format_rate(value: SurvivalEstimate) -> str:
    return "-" if value.rate is None else f"{value.rate:.2f}"


def _format_ci(value: SurvivalEstimate) -> str:
    if value.ci_low is None or value.ci_high is None:
        return "-"
    return f"( {value.ci_low:.2f} , {value.ci_high:.2f} )"


def _format_stage_label(value: str) -> tuple[str, float]:
    if value.strip().startswith("不分期別"):
        return "不分期別\n(含不詳)", 10
    return value, 12


def _set_textbox(
    shape,
    text: str,
    size: float,
    bold: bool = False,
    font_name: str = FONT_NAME,
) -> None:
    frame = shape.text_frame
    frame.clear()
    frame.auto_size = None
    frame.word_wrap = False
    frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    paragraph = frame.paragraphs[0]
    paragraph.alignment = PP_ALIGN.CENTER
    run = paragraph.add_run()
    run.text = text
    run.font.name = font_name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = BLACK


def _set_page_number(shape, page_number: int) -> None:
    frame = shape.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    paragraph = frame.paragraphs[0]
    paragraph.alignment = PP_ALIGN.RIGHT
    run = paragraph.add_run()
    run.text = str(page_number)
    run.font.name = FONT_NAME
    run.font.size = Pt(12)
    run.font.bold = False
    run.font.color.rgb = PAGE_NUMBER_COLOR


def _set_summary_textbox(
    shape,
    text: str,
    *,
    size: float,
    bold: bool = False,
    alignment: PP_ALIGN = PP_ALIGN.CENTER,
) -> None:
    frame = shape.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    paragraph = frame.paragraphs[0]
    paragraph.alignment = alignment
    run = paragraph.add_run()
    run.text = text
    run.font.name = FONT_NAME
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = BLACK


def _set_summary_cell(
    cell,
    text: str,
    *,
    header: bool = False,
    shaded: bool = False,
) -> None:
    fill = HEADER_FILL if header else (RGBColor(242, 245, 249) if shaded else WHITE)
    _set_cell(cell, text, size=12.5, bold=header, fill=fill)
    cell.margin_left = Inches(0.08)
    cell.margin_right = Inches(0.06)
    cell.text_frame.paragraphs[0].alignment = PP_ALIGN.LEFT


def _add_summary_table(slide, items: tuple[SummaryItem, ...], left: int):
    row_count = max(2, len(items) + 1)
    height = Inches(4.95)
    shape = slide.shapes.add_table(
        row_count,
        2,
        left,
        Inches(1.25),
        Inches(4.56),
        height,
    )
    table = shape.table
    table.columns[0].width = Inches(1.20)
    table.columns[1].width = Inches(3.36)
    table.rows[0].height = Inches(0.52)
    body_height = (height - table.rows[0].height) // (row_count - 1)
    for index in range(1, row_count):
        table.rows[index].height = body_height
    _set_summary_cell(table.cell(0, 0), "癌別", header=True)
    _set_summary_cell(table.cell(0, 1), "優於醫學中心之分期", header=True)
    for index in range(1, row_count):
        item = items[index - 1] if index - 1 < len(items) else None
        _set_summary_cell(
            table.cell(index, 0),
            item.cancer if item else "",
            shaded=index % 2 == 0,
        )
        table.cell(index, 0).text_frame.paragraphs[0].runs[0].font.bold = True
        _set_summary_cell(
            table.cell(index, 1),
            item.stages if item else "",
            shaded=index % 2 == 0,
        )
    return shape


def _add_summary_slide(
    presentation: Presentation,
    tables: tuple[ReportTable, ...],
    logo: tuple[bytes, int, int, int, int] | None,
) -> None:
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])
    if logo:
        blob, left, top, width, height = logo
        slide.shapes.add_picture(BytesIO(blob), left, top, width, height)

    first = tables[0]
    hospital_name = first.hospital_name or "本院"
    title_name = "本院" if any(item.is_local for item in first.hospitals) else hospital_name
    title_width = Inches(7.0)
    title = slide.shapes.add_textbox(
        (presentation.slide_width - title_width) // 2,
        Inches(0.20),
        title_width,
        Inches(0.52),
    )
    _set_summary_textbox(
        title,
        f"{first.period_start}–{first.period_end} {title_name}癌症全死因存活率",
        size=27,
        bold=False,
    )
    subtitle_width = Inches(6.3)
    subtitle = slide.shapes.add_textbox(
        (presentation.slide_width - subtitle_width) // 2,
        Inches(0.70),
        subtitle_width,
        Inches(0.38),
    )
    _set_summary_textbox(
        subtitle,
        "優於醫學中心之癌別與分期（部分採 AJCC 第八版）",
        size=16,
    )

    items = build_benchmark_summary(tables)
    split_at = (len(items) + 1) // 2
    summary_tables = (
        _add_summary_table(slide, items[:split_at], Inches(0.34)),
        _add_summary_table(slide, items[split_at:], Inches(5.10)),
    )

    note_top = max(shape.top + shape.height for shape in summary_tables) + MIN_NOTES_GAP
    note = slide.shapes.add_textbox(
        summary_tables[0].left,
        note_top,
        Inches(6.5),
        Inches(0.32),
    )
    _set_summary_textbox(
        note,
        "說明：  * 代表該分期採用觀察存活率",
        size=12,
        alignment=PP_ALIGN.LEFT,
    )
    note.text_frame.margin_left = 0
    page = slide.shapes.add_textbox(*PAGE_GEOMETRY)
    _set_page_number(page, 3)


def _set_run_typeface(element, font_name: str) -> None:
    properties = element.find(qn("a:rPr"))
    if properties is None:
        properties = OxmlElement("a:rPr")
        element.insert(0, properties)
    for tag in ("a:latin", "a:ea"):
        typeface = properties.find(qn(tag))
        if typeface is None:
            typeface = OxmlElement(tag)
            properties.append(typeface)
        typeface.set("typeface", font_name)


def _set_table_typeface(table, font_name: str) -> None:
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.text_frame.paragraphs:
                for run in paragraph.runs:
                    if run.text:
                        _set_run_typeface(run._r, font_name)


def _normalize_non_table_shape_font(shape, font_name: str = TITLE_FONT_NAME) -> None:
    if getattr(shape, "has_table", False):
        return
    child_shapes = getattr(shape, "shapes", None)
    if child_shapes is not None:
        for child in child_shapes:
            _normalize_non_table_shape_font(child, font_name)
        return
    for tag in (qn("a:r"), qn("a:fld")):
        for element in shape.element.iter(tag):
            text = element.find(qn("a:t"))
            if text is not None and text.text:
                _set_run_typeface(element, font_name)


def _normalize_non_table_fonts(presentation: Presentation) -> None:
    for slide in presentation.slides:
        for shape in slide.shapes:
            _normalize_non_table_shape_font(shape)
    cover_text_shapes = tuple(
        shape for shape in presentation.slides[0].shapes
        if not getattr(shape, "has_table", False)
        and getattr(shape, "has_text_frame", False)
        and shape.text.strip()
    )
    if cover_text_shapes:
        cover_motto = max(cover_text_shapes, key=lambda shape: shape.top)
        _normalize_non_table_shape_font(cover_motto, FONT_NAME)
    for slide in presentation.slides:
        for shape in slide.shapes:
            if (
                not getattr(shape, "has_table", False)
                and getattr(shape, "has_text_frame", False)
                and shape.text.startswith("(1)")
            ):
                _normalize_non_table_shape_font(shape, FONT_NAME)


def _set_rich_cell(
    cell,
    parts: tuple[tuple[str, RGBColor], ...],
    *,
    size: float = 12,
    fill: RGBColor = HEADER_FILL,
) -> None:
    cell.fill.solid()
    cell.fill.fore_color.rgb = fill
    cell.margin_left = 9525
    cell.margin_right = 9525
    cell.margin_top = 9525
    cell.margin_bottom = 0
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    frame = cell.text_frame
    frame.clear()
    frame.word_wrap = True
    paragraph = frame.paragraphs[0]
    paragraph.alignment = PP_ALIGN.CENTER
    for text, color in parts:
        run = paragraph.add_run()
        run.text = text
        _set_table_run_typefaces(run, text)
        run.font.size = Pt(size)
        run.font.bold = True
        run.font.color.rgb = color
    _set_border(cell)


def _set_comparison_banner(cell, table_data: ReportTable) -> None:
    target_years = _CHINESE_NUMERALS.get(table_data.target_years, str(table_data.target_years))
    has_local = any(hospital.is_local for hospital in table_data.hospitals)
    scope_parts = (
        (("台大雲林", LOCAL_HOSPITAL_BROWN), ("與全國", BLACK))
        if has_local
        else (("全國", BLACK),)
    )
    _set_rich_cell(
        cell,
        (
            (f"{table_data.period_start}-{table_data.period_end}", ACCENT_RED),
            (" 存活率：", BLACK),
            *scope_parts,
            (target_years, ACCENT_RED),
            ("年存活率比較（百分比）", BLACK),
        ),
    )


def _set_hospital_header(cell, hospital_name: str, size: float) -> None:
    cell.fill.solid()
    cell.fill.fore_color.rgb = HEADER_FILL
    cell.margin_left = 9525
    cell.margin_right = 9525
    cell.margin_top = 9525
    cell.margin_bottom = 0
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    frame = cell.text_frame
    frame.clear()
    frame.word_wrap = True
    lines = (
        ((hospital_name, BLACK),),
        (("年齡調整", BLACK), ("(觀察)", OBSERVATION_LABEL_BLUE)),
        (("存活率%", BLACK),),
        (("95% CI", BLACK),),
    )
    for line_index, parts in enumerate(lines):
        paragraph = frame.paragraphs[0] if line_index == 0 else frame.add_paragraph()
        paragraph.alignment = PP_ALIGN.CENTER
        paragraph.space_before = Pt(0)
        paragraph.space_after = Pt(0)
        for text, color in parts:
            run = paragraph.add_run()
            run.text = text
            _set_table_run_typefaces(run, text)
            run.font.size = Pt(size)
            run.font.bold = True
            run.font.color.rgb = color
    _set_border(cell)


def _table_geometry(row_count: int) -> tuple[int, int, int, int, int, int, int]:
    """Return the template geometry and row heights for the table density."""
    if row_count <= 10:
        left, top, width, height = STANDARD_TABLE_GEOMETRY
        return left, top, width, height, 397813, 1140666, NOTES_GEOMETRY[1]
    if row_count <= 14:
        return 179510, 767436, 8784979, 5515658, 324314, 929921, 6427113
    return 323530, 767437, 8496942, 5625771, 276244, 792090, 6427113


def _apply_column_widths(
    table,
    table_width: int,
    hospital_count: int,
    finalized_widths: tuple[int, ...] | None = None,
) -> None:
    flexible_count = hospital_count + 3
    if finalized_widths is not None and hospital_count == 1:
        widths = finalized_widths
    elif finalized_widths is not None:
        fixed_widths = finalized_widths[:3]
        remaining = table_width - sum(fixed_widths)
        flexible_width = remaining // flexible_count
        flexible_widths = [flexible_width] * flexible_count
        flexible_widths[-1] += remaining - (flexible_width * flexible_count)
        widths = (*fixed_widths, *flexible_widths)
    elif flexible_count == 4 and table_width == STANDARD_TABLE_GEOMETRY[2]:
        widths = (556551, 608351, 608351, 1734929, 1734929, 1734929, 1734929)
    else:
        fixed_total = min(1773253, table_width // 3)
        fixed_widths = (
            fixed_total * 556551 // 1773253,
            fixed_total * 608351 // 1773253,
        )
        third_fixed = fixed_total - sum(fixed_widths)
        flexible_width = (table_width - fixed_total) // flexible_count
        flexible_widths = [flexible_width] * flexible_count
        flexible_widths[-1] += table_width - fixed_total - (flexible_width * flexible_count)
        widths = (*fixed_widths, third_fixed, *flexible_widths)
    for column, width in zip(table.columns, widths):
        column.width = width


def _set_overview_runs(
    cell,
    parts: tuple[tuple[str, RGBColor], ...],
    *,
    alignment: PP_ALIGN = PP_ALIGN.CENTER,
    size: float = OVERVIEW_MAX_FONT_SIZE,
) -> None:
    """Replace body-cell text while preserving the template cell and bullet styling."""
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    frame = cell.text_frame
    frame.word_wrap = True
    frame.auto_size = None
    paragraph = frame.paragraphs[0]
    paragraph.clear()
    paragraph.alignment = alignment
    for text, color in parts:
        run = paragraph.add_run()
        run.text = text
        _set_table_run_typefaces(run, text)
        run.font.size = Pt(size)
        run.font.bold = False
        run.font.color.rgb = color


def _overview_cancer_font_size(cell, column_width: int, row_height: int, text: str) -> int:
    paragraph = cell.text_frame.paragraphs[0]
    properties = paragraph._p.get_or_add_pPr()
    left_indent = int(properties.get("marL", "0"))
    right_indent = int(properties.get("marR", "0"))
    width_points = (
        column_width
        - cell.margin_left
        - cell.margin_right
        - left_indent
        - right_indent
    ) / 12700
    height_points = (row_height - cell.margin_top - cell.margin_bottom) / 12700

    for size in range(OVERVIEW_MAX_FONT_SIZE, OVERVIEW_MIN_FONT_SIZE - 1, -1):
        if FONT_FILE.exists():
            font = ImageFont.truetype(str(FONT_FILE), size * 4)
            line_count = 1
            line_width = 0.0
            for character in text:
                if character == "\n":
                    line_count += 1
                    line_width = 0.0
                    continue
                character_width = font.getlength(character) / 4
                if line_width and line_width + character_width > width_points:
                    line_count += 1
                    line_width = character_width
                else:
                    line_width += character_width
            ascent, descent = font.getmetrics()
            required_height = line_count * ((ascent + descent) / 4)
        else:
            weighted_length = sum(1 if ord(character) > 127 else 0.55 for character in text)
            characters_per_line = max(1, width_points / size)
            line_count = math.ceil(weighted_length / characters_per_line)
            required_height = line_count * size * 1.35
        if required_height <= height_points:
            return size
    return OVERVIEW_MIN_FONT_SIZE


_OVERVIEW_CANCER_ORDER = (
    "大腸癌",
    "乳癌",
    "胃癌",
    "口腔癌",
    "口咽癌",
    "下咽癌",
    "鼻咽癌",
    "喉癌",
    "膀胱癌",
    "攝護腺癌",
    "肺癌",
    "食道癌",
    "子宮頸癌",
    "子宮體癌",
    "卵巢癌",
)


def _overview_cancer_name(table: ReportTable) -> str | None:
    cancer = re.sub(r"\s+", "", unicodedata.normalize("NFKC", table.cancer)).casefold()
    if "大腸癌" in cancer or "結腸直腸癌" in cancer:
        return "大腸癌"
    if "乳癌" in cancer:
        return "乳癌"
    if "胃癌" in cancer:
        return "胃癌"
    if "口腔癌" in cancer:
        return "口腔癌"
    if "口咽癌" in cancer:
        return "口咽癌"
    if "下咽癌" in cancer:
        return "下咽癌"
    if "鼻咽癌" in cancer:
        return "鼻咽癌"
    if cancer == "喉癌" or cancer.endswith("-喉癌"):
        return "喉癌"
    if "膀胱癌" in cancer:
        return "膀胱癌"
    if "攝護腺癌" in cancer or "前列腺癌" in cancer:
        return "攝護腺癌"
    if "肺癌" in cancer:
        return "肺癌"
    if "食道癌" in cancer:
        return "食道癌"
    if "子宮頸癌" in cancer:
        return "子宮頸癌"
    if "子宮體癌" in cancer:
        return "子宮體癌"
    if "卵巢癌" in cancer:
        return "卵巢癌"
    if "肝癌" in cancer:
        return None
    return table.cancer.strip()


def _overview_cancer_label(name: str, tables: tuple[ReportTable, ...]) -> str:
    label = name
    if name in {"子宮頸癌", "子宮體癌", "卵巢癌"}:
        systems: set[str] = set()
        for table in tables:
            source = f"{table.cancer} {table.staging_system}".upper()
            if "AJCC" in source:
                systems.add("AJCC")
            if "FIGO" in source:
                systems.add("FIGO")
        if systems == {"AJCC", "FIGO"}:
            label += "AJCC&FIGO"
        elif "FIGO" in systems:
            label += "FIGO"
        elif "AJCC" in systems:
            label += "AJCC"
    rows = tuple(row for table in tables for row in table.rows)
    if rows and all(
        not table.hospital_value(row, table.primary_hospital_key).estimate.available
        for table in tables
        for row in table.rows
    ):
        label += "(個案數太少，無可採用數據)"
    return label


def _overview_groups(
    tables: tuple[ReportTable, ...],
) -> tuple[tuple[int, int, int, str], ...]:
    grouped: dict[tuple[int, int, int], dict[str, list[ReportTable]]] = {}
    for table in tables:
        key = (table.period_start, table.period_end, table.target_years)
        name = _overview_cancer_name(table)
        if not name:
            continue
        grouped.setdefault(key, {}).setdefault(name, []).append(table)
    result: list[tuple[int, int, int, str]] = []
    for start, end, years in sorted(grouped):
        cancer_tables = grouped[(start, end, years)]
        ordered_names = sorted(
            cancer_tables,
            key=lambda name: (
                _OVERVIEW_CANCER_ORDER.index(name)
                if name in _OVERVIEW_CANCER_ORDER
                else len(_OVERVIEW_CANCER_ORDER),
                name,
            ),
        )
        labels = tuple(
            _overview_cancer_label(name, tuple(cancer_tables[name]))
            for name in ordered_names
        )
        result.append((start, end, years, "、".join(labels)))
    return tuple(result)


def _add_data_slide(
    presentation: Presentation,
    table_data: ReportTable,
    logo: tuple[bytes, int, int, int, int] | None,
    page_number: int,
) -> None:
    slide = presentation.slides.add_slide(presentation.slide_layouts[1])
    title = slide.shapes.title
    for placeholder in tuple(slide.placeholders):
        if placeholder.placeholder_format.idx != title.placeholder_format.idx:
            placeholder._element.getparent().remove(placeholder._element)
    title_left = _FINALIZED_TITLE_LEFTS.get(
        _detail_key(table_data.cancer, table_data.staging_system),
        TITLE_GEOMETRY[0],
    )
    title.left, title.top, title.width, title.height = (
        title_left,
        TITLE_GEOMETRY[1],
        TITLE_GEOMETRY[2],
        TITLE_GEOMETRY[3],
    )
    _set_textbox(
        title,
        table_data.display_title,
        32,
        False,
        TITLE_FONT_NAME,
    )

    if logo:
        blob, left, top, width, height = logo
        slide.shapes.add_picture(BytesIO(blob), left, top, width, height)

    page = slide.shapes.add_textbox(*PAGE_GEOMETRY)
    _set_page_number(page, page_number)

    row_count = 2 + (2 * len(table_data.rows))
    hospital_count = len(table_data.hospitals)
    column_count = 3 + hospital_count + 3
    finalized_layout = _FINALIZED_DETAIL_LAYOUTS.get(
        _detail_key(table_data.cancer, table_data.staging_system)
    )
    if finalized_layout is not None:
        table_left = finalized_layout.left
        table_top = finalized_layout.top
        table_width = finalized_layout.width
        table_height = finalized_layout.height
        first_header_height = finalized_layout.first_header_height
        second_header_height = finalized_layout.second_header_height
        notes_left, notes_top = _FINALIZED_NOTES_POSITIONS.get(
            _detail_key(table_data.cancer, table_data.staging_system),
            (NOTES_GEOMETRY[0], NOTES_GEOMETRY[1]),
        )
    else:
        (
            table_left,
            table_top,
            table_width,
            table_height,
            first_header_height,
            second_header_height,
            notes_top,
        ) = _table_geometry(row_count)
        notes_left = NOTES_GEOMETRY[0]
    title.top = max(
        TITLE_GEOMETRY[1],
        table_top - title.height - TITLE_TABLE_GAP,
    )
    notes_gap = NOTES_GAP_OVERRIDES.get(
        _detail_key(table_data.cancer, table_data.staging_system),
        MIN_NOTES_GAP,
    )
    required_notes_top = table_top + table_height + notes_gap
    maximum_notes_top = presentation.slide_height - NOTES_GEOMETRY[3]
    if required_notes_top > maximum_notes_top:
        table_height -= required_notes_top - maximum_notes_top
        required_notes_top = maximum_notes_top
    notes_top = required_notes_top
    notes_left = table_left
    table_shape = slide.shapes.add_table(
        row_count,
        column_count,
        table_left,
        table_top,
        table_width,
        table_height,
    )
    table = table_shape.table
    _apply_column_widths(
        table,
        table_width,
        hospital_count,
        finalized_layout.column_widths if finalized_layout is not None else None,
    )
    table.rows[0].height = first_header_height
    table.rows[1].height = second_header_height
    body_row_count = max(1, row_count - 2)
    remaining_height = table_height - first_header_height - second_header_height
    body_height = remaining_height // body_row_count
    for row_index, row in enumerate(list(table.rows)[2:]):
        row.height = body_height + (remaining_height - (body_height * body_row_count) if row_index == body_row_count - 1 else 0)

    table.cell(0, 0).merge(table.cell(1, 0))
    table.cell(0, 1).merge(table.cell(0, column_count - 1))
    staging_label = table_data.staging_system.strip().upper()
    stage_header = f"{staging_label}\n期別" if staging_label else "期別"
    _set_cell(table.cell(0, 0), stage_header, size=12, bold=True, fill=HEADER_FILL)
    _set_comparison_banner(table.cell(0, 1), table_data)
    headers = (
        "期別人數",
        "死亡人數",
        "全國\n年齡調整存活率%\n95% CI",
        "醫學中心\n年齡調整存活率%\n95% CI",
        "非醫學中心\n年齡調整存活率%\n95% CI",
    )
    header_size = max(8.0, 12 - max(0, column_count - 7) * 0.7)
    _set_cell(table.cell(1, 1), headers[0], size=header_size, bold=True, fill=HEADER_FILL)
    _set_cell(table.cell(1, 2), headers[1], size=header_size, bold=True, fill=HEADER_FILL)
    for hospital_index, hospital in enumerate(table_data.hospitals, start=3):
        hospital_size = min(header_size, 9.5) if len(hospital.display_name) > 12 else header_size
        _set_hospital_header(table.cell(1, hospital_index), hospital.display_name, hospital_size)
    for offset, text in enumerate(headers[2:], start=3 + hospital_count):
        _set_cell(table.cell(1, offset), text, size=header_size, bold=True, fill=HEADER_FILL)

    for index, row_data in enumerate(table_data.rows):
        rate_row = 2 + (index * 2)
        ci_row = rate_row + 1
        for column_index in range(3):
            table.cell(rate_row, column_index).merge(table.cell(ci_row, column_index))
        stage_label, stage_size = _format_stage_label(row_data.stage)
        _set_cell(table.cell(rate_row, 0), stage_label, size=stage_size, bold=True)
        _set_cell(table.cell(rate_row, 1), _format_number(row_data.stage_count), size=12)
        _set_cell(table.cell(rate_row, 2), _format_number(row_data.death_count), size=12)
        hospital_values = tuple(
            table_data.hospital_value(row_data, hospital.key)
            for hospital in table_data.hospitals
        )
        values = (
            *((value.estimate, value.value_type) for value in hospital_values),
            (row_data.nationwide, None),
            (row_data.medical_center, None),
            (row_data.non_medical_center, None),
        )
        for column_index, (estimate, value_type) in enumerate(values, start=3):
            hospital_index = column_index - 3
            is_primary = (
                hospital_index < hospital_count
                and table_data.hospitals[hospital_index].key == table_data.primary_hospital_key
            )
            use_observation_blue = is_primary and value_type == "observed"
            _set_cell(
                table.cell(rate_row, column_index),
                _format_rate(estimate),
                size=12,
                bold=is_primary,
                color=HOSPITAL_BLUE if use_observation_blue else BLACK,
            )
            _set_cell(
                table.cell(ci_row, column_index),
                _format_ci(estimate),
                size=12,
                bold=is_primary,
                color=HOSPITAL_BLUE if use_observation_blue else BLACK,
            )
            _set_border_no_fill(table.cell(rate_row, column_index), "a:lnB")
            _set_border_no_fill(table.cell(ci_row, column_index), "a:lnT")

    notes = slide.shapes.add_textbox(
        notes_left,
        notes_top,
        NOTES_GEOMETRY[2],
        NOTES_GEOMETRY[3],
    )
    frame = notes.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.margin_left = 0
    note_lines = (
        "(1) 藍字：代表年齡層未滿 10 人，無法進行年齡標準化調整，故呈現觀察存活率及 95% CI。",
        "(2) 存活率顯示「-」代表無足夠個案可追蹤至目標年，或所有個案於目標年前死亡，無法計算。",
    )
    for index, text in enumerate(note_lines):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        run = paragraph.add_run()
        run.text = text
        run.font.name = FONT_NAME
        run.font.size = Pt(11)
        run.font.color.rgb = BLACK


def _comparison_stage_key(value: str) -> str:
    return re.sub(
        r"[\s()（）]+",
        "",
        unicodedata.normalize("NFKC", value).casefold(),
    )


def _local_hospital_key(table_data: ReportTable | None) -> str:
    if table_data is None:
        return ""
    local = next(
        (hospital.key for hospital in table_data.hospitals if hospital.is_local),
        None,
    )
    return local or table_data.primary_hospital_key


def _comparison_value_text(
    table_data: ReportTable | None,
    row_data: ReportRow | None,
) -> str:
    if table_data is None or row_data is None:
        return "-"
    estimate = table_data.hospital_value(
        row_data,
        _local_hospital_key(table_data),
    ).estimate
    if not estimate.available:
        return "-"
    ci = _format_ci(estimate)
    return _format_rate(estimate) if ci == "-" else f"{_format_rate(estimate)}\n{ci}"


def _benchmark_comparison_text(estimate: SurvivalEstimate | None) -> str:
    if estimate is None or not estimate.available:
        return "-"
    ci = _format_ci(estimate)
    return _format_rate(estimate) if ci == "-" else f"{_format_rate(estimate)}\n{ci}"


def _comparison_rows(
    base_table: ReportTable | None,
    comparison_table: ReportTable | None,
) -> tuple[tuple[str, ReportRow | None, ReportRow | None], ...]:
    base_rows = base_table.rows if base_table is not None else ()
    comparison_rows = comparison_table.rows if comparison_table is not None else ()
    comparison_by_stage = {
        _comparison_stage_key(row.stage): row for row in comparison_rows
    }
    result: list[tuple[str, ReportRow | None, ReportRow | None]] = []
    used: set[str] = set()
    for row in base_rows:
        key = _comparison_stage_key(row.stage)
        used.add(key)
        result.append((row.stage, row, comparison_by_stage.get(key)))
    for row in comparison_rows:
        key = _comparison_stage_key(row.stage)
        if key not in used:
            result.append((row.stage, None, row))
    return tuple(result)


def _add_period_comparison_table(
    slide,
    source_table: ReportTable,
    table_data: ReportTable | None,
    rows: tuple[tuple[str, ReportRow | None, ReportRow | None], ...],
    row_position: int,
    period_label: str,
    top: int,
    height: int,
):
    shape = slide.shapes.add_table(
        2 + len(rows),
        7,
        Inches(0.25),
        top,
        Inches(9.50),
        height,
    )
    table = shape.table
    widths = (
        Inches(0.75),
        Inches(0.65),
        Inches(0.65),
        Inches(1.75),
        Inches(1.85),
        Inches(1.90),
        Inches(1.95),
    )
    for column, width in zip(table.columns, widths):
        column.width = width
    table.rows[0].height = Inches(0.32)
    table.rows[1].height = Inches(0.62)
    body_height = (
        height - table.rows[0].height - table.rows[1].height
    ) // max(1, len(rows))
    for body_row in list(table.rows)[2:]:
        body_row.height = body_height

    table.cell(0, 0).merge(table.cell(0, 6))
    _set_cell(
        table.cell(0, 0),
        period_label,
        size=12,
        bold=True,
        fill=HEADER_FILL,
    )
    staging = source_table.staging_system.strip().upper()
    headers = (
        f"{staging}\n期別" if staging else "期別",
        "期別人數",
        "死亡人數",
        "本院存活率%\n95% CI",
        "全國\n年齡調整存活率%\n95% CI",
        "醫學中心\n年齡調整存活率%\n95% CI",
        "非醫學中心\n年齡調整存活率%\n95% CI",
    )
    for column_index, text in enumerate(headers):
        _set_cell(
            table.cell(1, column_index),
            text,
            size=8,
            bold=True,
            fill=HEADER_FILL,
        )

    body_size = 9 if len(rows) <= 6 else 7.5
    for table_row, comparison_row in enumerate(rows, start=2):
        stage, base_row, other_row = comparison_row
        row_data = base_row if row_position == 1 else other_row
        stage_label, _ = _format_stage_label(stage)
        values = (
            stage_label,
            _format_number(row_data.stage_count) if row_data is not None else "-",
            _format_number(row_data.death_count) if row_data is not None else "-",
            _comparison_value_text(table_data, row_data),
            _benchmark_comparison_text(row_data.nationwide if row_data else None),
            _benchmark_comparison_text(row_data.medical_center if row_data else None),
            _benchmark_comparison_text(row_data.non_medical_center if row_data else None),
        )
        for column_index, text in enumerate(values):
            is_local_value = column_index == 3
            _set_cell(
                table.cell(table_row, column_index),
                text,
                size=body_size,
                bold=column_index == 0 or is_local_value,
                color=HOSPITAL_BLUE if is_local_value else BLACK,
            )
    return shape


def _add_year_comparison_slide(
    presentation: Presentation,
    base_table: ReportTable | None,
    comparison_table: ReportTable | None,
    base_deck: ReportDeck,
    comparison_deck: ReportDeck,
    logo: tuple[bytes, int, int, int, int] | None,
    page_number: int,
) -> None:
    source_table = base_table or comparison_table
    if source_table is None:
        return
    slide = presentation.slides.add_slide(presentation.slide_layouts[1])
    title = slide.shapes.title
    for placeholder in tuple(slide.placeholders):
        if placeholder.placeholder_format.idx != title.placeholder_format.idx:
            placeholder._element.getparent().remove(placeholder._element)
    title_left = _FINALIZED_TITLE_LEFTS.get(
        _detail_key(source_table.cancer, source_table.staging_system),
        TITLE_GEOMETRY[0],
    )
    title.left, title.top, title.width, title.height = (
        title_left,
        TITLE_GEOMETRY[1],
        TITLE_GEOMETRY[2],
        TITLE_GEOMETRY[3],
    )
    _set_textbox(
        title,
        source_table.display_title,
        32,
        False,
        TITLE_FONT_NAME,
    )
    if logo:
        blob, left, top, width, height = logo
        slide.shapes.add_picture(BytesIO(blob), left, top, width, height)

    rows = _comparison_rows(base_table, comparison_table)
    table_top = Inches(0.92)
    table_area_height = Inches(5.75)
    table_gap = Inches(0.12)
    table_height = (table_area_height - table_gap) // 2
    title.top = max(
        TITLE_GEOMETRY[1],
        table_top - title.height - TITLE_TABLE_GAP,
    )
    _add_period_comparison_table(
        slide,
        source_table,
        base_table,
        rows,
        1,
        f"{base_deck.period_start}-{base_deck.period_end}",
        table_top,
        table_height,
    )
    _add_period_comparison_table(
        slide,
        source_table,
        comparison_table,
        rows,
        2,
        f"{comparison_deck.period_start}-{comparison_deck.period_end}",
        table_top + table_height + table_gap,
        table_height,
    )

    page = slide.shapes.add_textbox(*PAGE_GEOMETRY)
    _set_page_number(page, page_number)


def _update_overview(presentation: Presentation, tables: tuple[ReportTable, ...]) -> None:
    if len(presentation.slides) < 2:
        return
    slide = list(presentation.slides)[1]
    overview_shape = next((shape for shape in slide.shapes if shape.has_table), None)
    if overview_shape is None:
        return
    overview_table = overview_shape.table
    groups = _overview_groups(tables)
    body_rows = len(overview_table.rows) - 1
    for offset in range(body_rows):
        row_index = offset + 1
        if offset >= len(groups):
            for column_index in range(3):
                overview_table.cell(row_index, column_index).text_frame.paragraphs[0].clear()
            continue
        start, end, target_years, cancers = groups[offset]
        years_text = _CHINESE_NUMERALS.get(target_years, str(target_years)) + "年"
        _set_overview_runs(
            overview_table.cell(row_index, 0),
            ((str(start), RGBColor(0, 0, 255)), (f"-{end}", BLACK)),
        )
        _set_overview_runs(
            overview_table.cell(row_index, 1),
            ((years_text, ACCENT_RED),),
        )
        cancer_cell = overview_table.cell(row_index, 2)
        cancer_font_size = _overview_cancer_font_size(
            cancer_cell,
            overview_table.columns[2].width,
            overview_table.rows[row_index].height,
            cancers,
        )
        _set_overview_runs(
            cancer_cell,
            ((cancers, BLACK),),
            alignment=PP_ALIGN.LEFT,
            size=cancer_font_size,
        )
    _set_table_typeface(overview_table, FONT_NAME)
    tracking_note = next(
        (
            shape for shape in slide.shapes
            if "死亡檔最後追蹤日期" in getattr(shape, "text", "")
        ),
        None,
    )
    if tracking_note is not None:
        tracking_note.left = overview_shape.left
        tracking_note.top = overview_shape.top + overview_shape.height + MIN_NOTES_GAP
        tracking_note.text_frame.margin_left = 0


def build_presentation(
    source: ReportDeck | ReportBatch,
    template_path: Path,
    *,
    comparison_deck: ReportDeck | None = None,
) -> BytesIO:
    """Build a presentation while retaining the approved template package/theme."""
    selected = source.ordered_tables if isinstance(source, ReportDeck) else source.selected_tables
    if not selected:
        raise ValueError("沒有可匯出的報表。")
    presentation = Presentation(template_path)
    logo = None
    for sample_slide in list(presentation.slides)[2:]:
        picture = next(
            (
                shape for shape in sample_slide.shapes
                if getattr(shape, "image", None) and shape.width < Inches(2.5)
            ),
            None,
        )
        if picture is not None:
            logo = (picture.image.blob, picture.left, picture.top, picture.width, picture.height)
            break
    for index in range(len(presentation.slides) - 1, 1, -1):
        _remove_slide(presentation, index)
    _update_overview(presentation, selected)
    _add_summary_slide(presentation, selected, logo)
    detail_tables = tuple(table for table in selected if table.detail_visible)
    page_number = 4
    comparison_by_key = {
        _detail_key(table.cancer, table.staging_system): table
        for table in (comparison_deck.ordered_tables if comparison_deck else ())
        if table.detail_visible
    }
    used_comparison_keys: set[tuple[str, str]] = set()
    for table in detail_tables:
        _add_data_slide(presentation, table, logo, page_number)
        page_number += 1
        if comparison_deck is not None:
            key = _detail_key(table.cancer, table.staging_system)
            comparison_table = comparison_by_key.get(key)
            if comparison_table is not None:
                used_comparison_keys.add(key)
            _add_year_comparison_slide(
                presentation,
                table,
                comparison_table,
                source,
                comparison_deck,
                logo,
                page_number,
            )
            page_number += 1
    if comparison_deck is not None:
        for key, comparison_table in comparison_by_key.items():
            if key in used_comparison_keys:
                continue
            _add_year_comparison_slide(
                presentation,
                None,
                comparison_table,
                source,
                comparison_deck,
                logo,
                page_number,
            )
            page_number += 1
    _normalize_non_table_fonts(presentation)
    output = BytesIO()
    presentation.save(output)
    output.seek(0)
    return output
