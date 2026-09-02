"""Builds the Aidly software engineering report.

Everything is produced from this script: no word processor, no design tool.
Diagrams are drawn as canvas primitives in report_diagrams.py.
"""
import os
import sys

from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, KeepTogether, NextPageTemplate, PageBreak,
    PageTemplate, Paragraph, Spacer, Table, TableStyle,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from report_diagrams import Diagram, use_case  # noqa: E402
from dfd_l1 import Rotated, dfd_level0, dfd_level1  # noqa: E402
from report_visuals import (  # noqa: E402
    Draw, CodePanel, cover_art, increment_chart, login_sequence, dispatch_flow,
    notation_legend, module_architecture)

SP = os.path.dirname(os.path.abspath(__file__))
# report_src sits inside docs/, so the outputs go to its parent. Derived
# rather than hardcoded, so renaming the project folder cannot break it.
DOCS = os.path.dirname(SP)
OUT = os.path.join(DOCS, "Aidly_SE_Report.pdf")

INK = HexColor("#111111")
SOFT = HexColor("#444444")
GREY = HexColor("#6B6B6B")
RULE = HexColor("#BFBFBF")
BAND = HexColor("#EEEEEE")
CODEBG = HexColor("#F6F6F6")

F = r"C:\Windows\Fonts"
for nm, fn in [("T", "times.ttf"), ("TB", "timesbd.ttf"), ("TI", "timesi.ttf"),
               ("TBI", "timesbi.ttf"), ("M", "consola.ttf"), ("MB", "consolab.ttf"),
               ("H", "arial.ttf"), ("HB", "arialbd.ttf")]:
    pdfmetrics.registerFont(TTFont(nm, os.path.join(F, fn)))
pdfmetrics.registerFontFamily("T", normal="T", bold="TB", italic="TI", boldItalic="TBI")

PW, PH = A4
LM, RM, TM, BM = 28 * mm, 22 * mm, 24 * mm, 22 * mm
CW = PW - LM - RM

# ------------------------------------------------------------------ styles
def st(name, **k):
    k.setdefault("fontName", "T")
    k.setdefault("fontSize", 11.5)
    k.setdefault("leading", 16.4)
    k.setdefault("textColor", INK)
    return ParagraphStyle(name, **k)

BODY = st("body", alignment=TA_JUSTIFY, spaceAfter=8)
BODY_T = st("bodyt", alignment=TA_JUSTIFY, spaceAfter=8, firstLineIndent=0)
H1N = st("h1n", fontName="TB", fontSize=40, leading=44, textColor=HexColor("#C9C9C9"))
H1 = st("h1", fontName="TB", fontSize=22, leading=26, spaceAfter=14)
# keepWithNext stops a heading being left alone at the foot of a page. This is
# set on the style, so it applies to every heading rather than the ones anybody
# happened to notice.
H2 = st("h2", fontName="TB", fontSize=14, leading=18, spaceBefore=13,
        spaceAfter=6, keepWithNext=1)
H3 = st("h3", fontName="TB", fontSize=12, leading=16, spaceBefore=9,
        spaceAfter=4, keepWithNext=1)
LI = st("li", alignment=TA_JUSTIFY, leftIndent=16, bulletIndent=4, spaceAfter=5,
        bulletFontName="T", bulletFontSize=11)
LIN = st("lin", alignment=TA_JUSTIFY, leftIndent=20, bulletIndent=2, spaceAfter=5,
         bulletFontName="T", bulletFontSize=11)
CAP = st("cap", fontSize=9.5, leading=13, alignment=TA_CENTER, textColor=GREY,
         spaceBefore=5, spaceAfter=10, fontName="TI")
CODE = st("code", fontName="M", fontSize=7.9, leading=10.4, textColor=INK)
CODEC = st("codec", fontName="M", fontSize=7.4, leading=9.8, textColor=SOFT)
TH = st("th", fontName="TB", fontSize=9.3, leading=11.7)
TD = st("td", fontSize=9.3, leading=11.7)
TDM = st("tdm", fontName="M", fontSize=7.9, leading=11.4)
TOC1 = st("toc1", fontName="TB", fontSize=11.5, leading=17)
TOC2 = st("toc2", fontSize=11, leading=15.6)
CAP_T = st("capt", fontSize=9.5, leading=13, alignment=TA_CENTER,
           textColor=GREY, fontName="TI")
SHOTLAB = st("shotlab", fontName="H", fontSize=7.6, leading=10,
            alignment=TA_CENTER, textColor=GREY)

CHAPTERS = {}


def P(t, s=BODY):
    return Paragraph(t, s)


def bullets(items, style=LI, mark="\u2022"):
    return [Paragraph(t, style, bulletText=mark) for t in items]


def numbered(items, style=LIN):
    return [Paragraph(t, style, bulletText=f"{i}.") for i, t in enumerate(items, 1)]


def h1(num, title):
    CHAPTERS[num] = title
    p = Paragraph(title, H1)
    p._tocKey = str(num)
    p._chapTitle = title
    return [Paragraph(str(num), H1N), p,
            Table([[""]], colWidths=[CW], rowHeights=[1.6],
                  style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), INK)])),
            Spacer(1, 14)]


H2_FREE = st("h2f", fontName="TB", fontSize=14, leading=18, spaceBefore=13,
             spaceAfter=6)


def h2(t, keep=True):
    """keep=False for a heading that introduces a full page figure. Holding the
    heading to a figure that needs a page of its own would strand both and
    leave the previous page nearly empty."""
    p = Paragraph(t, H2 if keep else H2_FREE)
    p._tocKey = t.split()[0]
    return p


def h3(t):
    return Paragraph(t, H3)


def table(rows, widths, align=None, head=True, fs=None, caption=None,
          nosplit=False):
    """A caption is rendered as a final spanning row of the same table, so it
    can never be orphaned onto the next page away from its own table."""
    ncol = len(widths)
    data = []
    for i, r in enumerate(rows):
        style = TH if (i == 0 and head) else TD
        row = []
        for j, cell in enumerate(r):
            if isinstance(cell, str):
                s = style
                if align and align[j] == "m" and not (i == 0 and head):
                    s = TDM
                row.append(Paragraph(cell, s))
            else:
                row.append(cell)
        data.append(row)

    last = len(data) - 1
    if caption:
        data.append([Paragraph(caption, CAP_T)] + [""] * (ncol - 1))

    t = Table(data, colWidths=widths, repeatRows=1 if head else 0, hAlign="LEFT")
    cmd = [("VALIGN", (0, 0), (-1, last), "TOP"),
           ("GRID", (0, 0), (-1, last), 0.5, RULE),
           ("LEFTPADDING", (0, 0), (-1, -1), 6),
           ("RIGHTPADDING", (0, 0), (-1, -1), 6),
           ("TOPPADDING", (0, 0), (-1, last), 3.4),
           ("BOTTOMPADDING", (0, 0), (-1, last), 3.4)]
    if head:
        cmd.append(("BACKGROUND", (0, 0), (-1, 0), BAND))
    if caption:
        cmd += [("SPAN", (0, last + 1), (-1, last + 1)),
                ("TOPPADDING", (0, last + 1), (-1, last + 1), 5),
                ("BOTTOMPADDING", (0, last + 1), (-1, last + 1), 9),
                ("LEFTPADDING", (0, last + 1), (-1, last + 1), 0),
                ("RIGHTPADDING", (0, last + 1), (-1, last + 1), 0)]
    t.setStyle(TableStyle(cmd))
    # Tables split by default, because holding one back leaves the previous
    # page half empty. nosplit is for the few where a split would strand the
    # repeated header and the caption on a page by themselves.
    if nosplit:
        return KeepTogether([t])
    return t


def code_block(src, caption=None, cw=CW, comment_prefix=("#", '"""', "'''")):
    lines = src.strip("\n").split("\n")
    rows = []
    for ln in lines:
        s = ln.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        s = s.replace(" ", "&nbsp;")
        style = CODEC if ln.strip().startswith(comment_prefix) else CODE
        rows.append([Paragraph(s or "&nbsp;", style)])
    t = Table(rows, colWidths=[cw], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CODEBG),
        ("BOX", (0, 0), (-1, -1), 0.5, RULE),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 0.6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0.6),
    ]))
    out = [t]
    if caption:
        out.append(Paragraph(caption, CAP))
    return out


def uc_table(rows):
    data = [[Paragraph(a, TH), Paragraph(b, TD)] for a, b in rows]
    t = Table(data, colWidths=[38 * mm, CW - 38 * mm], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, RULE),
        ("BACKGROUND", (0, 0), (0, -1), BAND),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3.4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.4),
    ]))
    return t


def shot(path, w_mm):
    from PIL import Image as PILImage
    p = os.path.join(SP, path)
    iw, ih = PILImage.open(p).size
    w = w_mm * mm
    return Image(p, width=w, height=w * ih / iw)


def fig(caption):
    return Paragraph(caption, CAP)


def code(filename, src, caption=None, fs=7.6):
    return [CodePanel(CW, filename, src, fs=fs, caption=caption)]


def shots_row(items, w_mm, caption):
    """items: list of (file, label). Renders a row of screenshots."""
    cells, labs = [], []
    for f, lab in items:
        cells.append(shot(f, w_mm))
        labs.append(Paragraph(lab, SHOTLAB))
    n = len(items)
    cap_row = [Paragraph(caption, CAP_T)] + [""] * (n - 1)
    t = Table([cells, labs, cap_row], colWidths=[CW / n] * n, hAlign="CENTER")
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, 1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 1), (-1, 1), 4),
        ("SPAN", (0, 2), (-1, 2)),
        ("TOPPADDING", (0, 2), (-1, 2), 6),
        ("BOTTOMPADDING", (0, 2), (-1, 2), 10),
    ]))
    # A figure must not split between its images, its labels and its caption,
    # so the whole block moves to the next page together.
    return [KeepTogether([t])]


# --------------------------------------------------------------- page deco
HEAD_PAGES = {}      # "4.2" -> page number
CHAP_ON_PAGE = {}    # page number -> chapter title, filled on pass one


def on_cover(canvas, doc):
    pass


def on_page(canvas, doc):
    canvas.saveState()
    n = canvas.getPageNumber()
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(LM, BM - 7 * mm, PW - RM, BM - 7 * mm)
    canvas.setFont("T", 9)
    canvas.setFillColor(GREY)
    label = CHAP_ON_PAGE.get(n, "")
    if label:
        canvas.drawString(LM, BM - 12 * mm, label)
    canvas.drawRightString(PW - RM, BM - 12 * mm, f"{n} | P a g e")
    canvas.restoreState()


class Doc(BaseDocTemplate):
    """Records where each heading landed so pass two can print real page
    numbers in the contents and the right chapter name in the footer."""

    def afterFlowable(self, flowable):
        key = getattr(flowable, "_tocKey", None)
        if key is not None:
            HEAD_PAGES[key] = self.page
            title = getattr(flowable, "_chapTitle", None)
            if title:
                CHAP_ON_PAGE[self.page] = title


# ------------------------------------------------------------------ build
FRONT_SRC = open(os.path.join(SP, "report_front.py"), encoding="utf-8").read()
BODY_SRC = open(os.path.join(SP, "report_body.py"), encoding="utf-8").read()

TMP = os.path.join(SP, "_pass1.pdf")

for _pass, _target in ((1, TMP), (2, OUT)):
    S = []
    globals()["S"] = S
    exec(FRONT_SRC, globals())
    exec(BODY_SRC, globals())
    S = globals()["S"]

    doc = Doc(_target, pagesize=A4, leftMargin=LM, rightMargin=RM,
              topMargin=TM, bottomMargin=BM,
              title="Aidly: Software Engineering Report, First Draft",
              author="Janvi Monga, Sourav Kumar, Avijit Sakkarwal")
    frame = Frame(LM, BM, CW, PH - TM - BM, id="f",
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[frame], onPage=on_cover),
        PageTemplate(id="main", frames=[frame], onPage=on_page),
    ])
    doc.build(S)

    if _pass == 1:
        # Forward fill the chapter label so every page of a chapter carries it.
        _last = ""
        for _n in range(1, doc.page + 1):
            if _n in CHAP_ON_PAGE:
                _last = CHAP_ON_PAGE[_n]
            elif _last:
                CHAP_ON_PAGE[_n] = _last

os.remove(TMP)
print("written:", OUT, os.path.getsize(OUT), "bytes")
