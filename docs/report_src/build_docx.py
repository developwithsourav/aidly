"""Builds the editable Word version from the same content file as the PDF.

report_body.py is executed against a different set of helpers, so the text is
never duplicated between the two outputs. Diagrams and code panels are drawn
once with reportlab and embedded as images; everything else stays editable.
"""
import html
import os
import re
import sys

import docx
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

SP = os.path.dirname(os.path.abspath(__file__))
# report_src sits inside docs/, so the outputs go to its parent. Derived
# rather than hardcoded, so renaming the project folder cannot break it.
DOCS = os.path.dirname(SP)
sys.path.insert(0, SP)
OUT = os.path.join(DOCS, "Aidly_SE_Report.docx")
IMGDIR = os.path.join(SP, "docximg")
os.makedirs(IMGDIR, exist_ok=True)

from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import SimpleDocTemplate  # noqa: E402

F = r"C:\Windows\Fonts"
for nm, fn in [("T", "times.ttf"), ("TB", "timesbd.ttf"), ("TI", "timesi.ttf"),
               ("TBI", "timesbi.ttf"), ("M", "consola.ttf"),
               ("MB", "consolab.ttf"), ("H", "arial.ttf"), ("HB", "arialbd.ttf")]:
    pdfmetrics.registerFont(TTFont(nm, os.path.join(F, fn)))

from report_visuals import (Draw as RLDraw, CodePanel, cover_art,  # noqa: E402
                            increment_chart, login_sequence, dispatch_flow,
                            notation_legend, module_architecture)
from report_diagrams import Diagram as RLDiagram, use_case  # noqa: E402
from dfd_l1 import Rotated as RLRotated, dfd_level0, dfd_level1  # noqa: E402

PW, PH = A4
CW = PW - 50 * mm

# ------------------------------------------------------------- rasterising
_cache = {}


def _raster(flowable, w_pt, h_pt, key):
    """Renders one flowable to a PNG and returns the path."""
    if key in _cache:
        return _cache[key]
    import pypdfium2 as pdfium
    pdf = os.path.join(IMGDIR, key + ".pdf")
    png = os.path.join(IMGDIR, key + ".png")
    d = SimpleDocTemplate(pdf, pagesize=(w_pt + 90, h_pt + 90),
                          leftMargin=24, rightMargin=24, topMargin=24,
                          bottomMargin=24)
    d.build([flowable])
    doc = pdfium.PdfDocument(pdf)
    doc[0].render(scale=3.2).to_pil().save(png)
    _cache[key] = png
    return png


# ------------------------------------------------------------------- text
TAG = re.compile(r"<(/?)(b|i|br\s*/?)>", re.I)


def _runs(par, text, base_size=10.5, font="Times New Roman"):
    """Writes text into a paragraph, honouring b, i and br markup."""
    text = text.replace("<br/>", "\n").replace("<br>", "\n")
    bold = italic = False
    pos = 0
    for m in re.finditer(r"</?[bi]>", text, re.I):
        chunk = text[pos:m.start()]
        if chunk:
            _emit(par, chunk, bold, italic, base_size, font)
        tag = m.group(0).lower()
        if tag == "<b>":
            bold = True
        elif tag == "</b>":
            bold = False
        elif tag == "<i>":
            italic = True
        elif tag == "</i>":
            italic = False
        pos = m.end()
    if text[pos:]:
        _emit(par, text[pos:], bold, italic, base_size, font)


def _emit(par, chunk, bold, italic, size, font):
    chunk = html.unescape(chunk)
    parts = chunk.split("\n")
    for k, part in enumerate(parts):
        if k:
            par.add_run().add_break()
        if not part:
            continue
        r = par.add_run(part)
        r.bold = bold
        r.italic = italic
        r.font.size = Pt(size)
        r.font.name = font


def _shade(cell, hexcolor):
    el = OxmlElement("w:shd")
    el.set(qn("w:val"), "clear")
    el.set(qn("w:fill"), hexcolor)
    cell._tc.get_or_add_tcPr().append(el)


# ------------------------------------------------------------ the document
D = docx.Document()
sec = D.sections[0]
sec.page_height = Inches(11.69)
sec.page_width = Inches(8.27)
sec.left_margin = Inches(1.1)
sec.right_margin = Inches(0.87)
sec.top_margin = Inches(0.95)
sec.bottom_margin = Inches(0.87)

style = D.styles["Normal"]
style.font.name = "Times New Roman"
style.font.size = Pt(10.5)
style.paragraph_format.space_after = Pt(7)
style.paragraph_format.line_spacing = 1.15

USABLE_IN = 8.27 - 1.1 - 0.87


# ---------------------------------------------------------------- helpers
class _Noop:
    def __init__(self, *a, **k):
        pass


def P(t, s=None):
    p = D.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    _runs(p, t)
    return p


def h1(num, title):
    D.add_page_break() if len(D.paragraphs) > 1 else None
    p = D.add_paragraph()
    r = p.add_run(str(num))
    r.font.size = Pt(30)
    r.bold = True
    r.font.color.rgb = RGBColor(0xC0, 0xC0, 0xC0)
    p2 = D.add_paragraph()
    r2 = p2.add_run(title)
    r2.font.size = Pt(19)
    r2.bold = True
    p2.paragraph_format.space_after = Pt(10)
    pr = p2._p.get_or_add_pPr()
    bd = OxmlElement("w:pBdr")
    bt = OxmlElement("w:bottom")
    bt.set(qn("w:val"), "single")
    bt.set(qn("w:sz"), "12")
    bt.set(qn("w:color"), "111111")
    bd.append(bt)
    pr.append(bd)
    return []


def h2(t, keep=True):
    p = D.add_paragraph()
    r = p.add_run(t)
    r.bold = True
    r.font.size = Pt(13)
    p.paragraph_format.space_before = Pt(11)
    p.paragraph_format.space_after = Pt(4)
    return p


def h3(t):
    p = D.add_paragraph()
    r = p.add_run(t)
    r.bold = True
    r.font.size = Pt(11.5)
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(3)
    return p


def fig(caption):
    p = D.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _runs(p, "<i>" + caption + "</i>", 9)
    p.paragraph_format.space_after = Pt(10)
    return p


def bullets(items, style=None, mark=None):
    for t in items:
        p = D.add_paragraph(style="List Bullet")
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        _runs(p, t)
    return []


def numbered(items, style=None):
    for t in items:
        p = D.add_paragraph(style="List Number")
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        _runs(p, t)
    return []


def table(rows, widths, align=None, head=True, fs=None, caption=None,
          nosplit=False):
    total = float(sum(widths))
    t = D.add_table(rows=0, cols=len(widths))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, r in enumerate(rows):
        cells = t.add_row().cells
        for j, val in enumerate(r):
            cells[j].text = ""
            par = cells[j].paragraphs[0]
            par.paragraph_format.space_after = Pt(1)
            if isinstance(val, str):
                _runs(par, ("<b>" + val + "</b>") if (i == 0 and head) else val,
                      9)
            if i == 0 and head:
                _shade(cells[j], "EEEEEE")
    for j, w in enumerate(widths):
        share = (w / total) * USABLE_IN
        for row in t.rows:
            row.cells[j].width = Inches(share)
    if caption:
        fig(caption)
    return []


def uc_table(rows):
    t = D.add_table(rows=0, cols=2)
    t.style = "Table Grid"
    for k, v in rows:
        cells = t.add_row().cells
        cells[0].text = ""
        _runs(cells[0].paragraphs[0], "<b>" + k + "</b>", 9)
        _shade(cells[0], "EEEEEE")
        cells[1].text = ""
        _runs(cells[1].paragraphs[0], v, 9)
        cells[0].width = Inches(1.55)
        cells[1].width = Inches(USABLE_IN - 1.55)
    D.add_paragraph().paragraph_format.space_after = Pt(6)
    return []


def code(filename, src, caption=None, fs=7.6):
    hdr = D.add_paragraph()
    _shade_par(hdr, "1A1A1A")
    r = hdr.add_run("  " + filename)
    r.font.name = "Consolas"
    r.font.size = Pt(8.5)
    r.bold = True
    r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    hdr.paragraph_format.space_after = Pt(0)

    body = D.add_paragraph()
    _shade_par(body, "F5F5F5")
    body.paragraph_format.space_before = Pt(0)
    body.paragraph_format.space_after = Pt(4)
    body.paragraph_format.line_spacing = 1.0
    lines = src.strip("\n").split("\n")
    for i, ln in enumerate(lines):
        if i:
            body.add_run().add_break()
        r = body.add_run(("%3d  " % (i + 1)) + ln)
        r.font.name = "Consolas"
        r.font.size = Pt(7.6)
    if caption:
        fig(caption)
    return []


def _shade_par(par, color):
    pr = par._p.get_or_add_pPr()
    el = OxmlElement("w:shd")
    el.set(qn("w:val"), "clear")
    el.set(qn("w:fill"), color)
    pr.append(el)


def shot(path, w_mm):
    return ("IMG", os.path.join(SP, path), w_mm)


def shots_row(items, w_mm, caption):
    t = D.add_table(rows=2, cols=len(items))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, (f, lab) in enumerate(items):
        cell = t.cell(0, j)
        cell.text = ""
        run = cell.paragraphs[0].add_run()
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        run.add_picture(os.path.join(SP, f), width=Inches(w_mm / 25.4))
        c2 = t.cell(1, j)
        c2.text = ""
        c2.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        _runs(c2.paragraphs[0], lab, 8.5)
    fig(caption)
    return []


def Draw(w, h, fn, pad_bottom=0):
    png = _raster(RLDraw(CW, h, fn), CW, h, "v_" + fn.__name__)
    p = D.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(png, width=Inches(USABLE_IN * 0.97))
    return []



def Rotated(avail_w, avail_h, land_w, land_h, fn):
    """The landscape figure is inserted upright in Word, scaled to the text
    width. Word readers can zoom, so there is no need to turn the page."""
    png = _raster(RLDraw(land_w, land_h, fn), land_w, land_h, "r_" + fn.__name__)
    p = D.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(png, width=Inches(USABLE_IN))
    return []


def Diagram(w, h, fn):
    png = _raster(RLDiagram(CW, h, fn), CW, h, "d_" + fn.__name__)
    p = D.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(png, width=Inches(USABLE_IN * 0.97))
    return []


def Spacer(a, b):
    return []


def PageBreak():
    return ("PB",)


def KeepTogether(x):
    return []


def Paragraph(t, s=None):
    name = getattr(s, "name", "")
    if name in ("cap", "capt"):
        return fig(t)
    return P(t)


class _S(list):
    def __iadd__(self, other):
        for item in other if isinstance(other, list) else [other]:
            if isinstance(item, tuple) and item and item[0] == "PB":
                D.add_page_break()
        return self


# --------------------------------------------------------------- cover page
def _centre(text, size, bold=False, mono=False, grey=False, before=0, after=0):
    par = D.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.paragraph_format.space_before = Pt(before)
    par.paragraph_format.space_after = Pt(after)
    run = par.add_run(text)
    run.font.size = Pt(size)
    run.bold = bold
    run.font.name = "Consolas" if mono else ("Arial" if bold else "Times New Roman")
    if grey:
        run.font.color.rgb = RGBColor(0x6B, 0x6B, 0x6B)
    return par


_badge = D.add_paragraph()
_badge.alignment = WD_ALIGN_PARAGRAPH.CENTER
_badge.paragraph_format.space_before = Pt(54)
_badge.add_run().add_picture(os.path.join(SP, "aidly_logo.png"),
                             width=Inches(2.5))

_centre("AIDLY", 56, bold=True, before=12, after=6)
_centre("A Venue Operations Layer for Crowd Emergencies", 16, after=2)
_centre("Software Engineering Project Report", 12, bold=True, grey=True,
        after=34)

_centre("SUBMITTED BY", 8.5, bold=True, grey=True, after=6)
_team = D.add_table(rows=0, cols=2)
_team.alignment = WD_TABLE_ALIGNMENT.CENTER
for _nm, _roll in (("Sourav Kumar", "24/48044"),
                   ("Janvi Monga", "24/48092"),
                   ("Avijit Sakkarwal", "24/48079")):
    cs = _team.add_row().cells
    cs[0].text = ""
    _runs(cs[0].paragraphs[0], _nm, 13.5)
    cs[1].text = ""
    _runs(cs[1].paragraphs[0], _roll, 13, "Consolas")
    cs[0].width = Inches(2.3)
    cs[1].width = Inches(1.4)

_centre("Submitted to", 8.5, bold=True, grey=True, before=42, after=2)
_centre("Uma Ma'am", 13.5, after=14)
_centre("Subject", 8.5, bold=True, grey=True, after=2)
_centre("Software Engineering", 13.5)

# ------------------------------------------------------------------ body
S = _S()
BODY = open(os.path.join(SP, "report_body.py"), encoding="utf-8").read()
g = dict(globals())
g["S"] = S
exec(BODY, g)

D.save(OUT)
print("written:", OUT, os.path.getsize(OUT), "bytes")
