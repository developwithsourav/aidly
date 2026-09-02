"""Diagram flowables drawn directly on the reportlab canvas.

No external drawing tool is involved: every shape here is a canvas primitive,
which is what keeps the figures reproducible from source.
"""
import math

from reportlab.lib.colors import HexColor, white
from reportlab.platypus import Flowable

INK = HexColor("#111111")
LINE = HexColor("#333333")
SOFT = HexColor("#F2F2F2")
GREY = HexColor("#666666")


class Diagram(Flowable):
    """Wraps a draw function so it can sit in the story like any flowable."""

    def __init__(self, width, height, fn):
        Flowable.__init__(self)
        self.width = width
        self.height = height
        self.fn = fn

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        self.fn(self.canv, self.width, self.height)


# ---------------------------------------------------------------- helpers
def _text(c, x, y, s, size=7.4, font="Helvetica", col=INK, anchor="middle"):
    c.setFont(font, size)
    c.setFillColor(col)
    if anchor == "middle":
        c.drawCentredString(x, y, s)
    elif anchor == "start":
        c.drawString(x, y, s)
    else:
        c.drawRightString(x, y, s)


def _lines(c, x, y, rows, size=7.4, font="Helvetica", col=INK, lead=8.6):
    total = (len(rows) - 1) * lead
    yy = y + total / 2.0
    for r in rows:
        _text(c, x, yy - 2.5, r, size, font, col)
        yy -= lead


def box(c, cx, cy, w, h, rows, fill=white, size=7.4, font="Helvetica", rad=0):
    c.setStrokeColor(LINE)
    c.setFillColor(fill)
    c.setLineWidth(0.8)
    if rad:
        c.roundRect(cx - w / 2, cy - h / 2, w, h, rad, fill=1, stroke=1)
    else:
        c.rect(cx - w / 2, cy - h / 2, w, h, fill=1, stroke=1)
    _lines(c, cx, cy, rows, size, font)


def circle(c, cx, cy, r, rows, fill=white, size=7.4):
    c.setStrokeColor(LINE)
    c.setFillColor(fill)
    c.setLineWidth(0.8)
    c.circle(cx, cy, r, fill=1, stroke=1)
    _lines(c, cx, cy, rows, size, lead=8.2)


def store(c, cx, cy, w, h, tag, name, fill=SOFT):
    """Open ended store symbol: two horizontal rules with a tag cell."""
    x0, y0 = cx - w / 2, cy - h / 2
    c.setFillColor(fill)
    c.rect(x0, y0, w, h, fill=1, stroke=0)
    c.setStrokeColor(LINE)
    c.setLineWidth(0.8)
    c.line(x0, y0, x0 + w, y0)
    c.line(x0, y0 + h, x0 + w, y0 + h)
    c.line(x0 + 20, y0, x0 + 20, y0 + h)
    _text(c, x0 + 10, cy - 2.6, tag, 7.0, "Helvetica-Bold")
    _text(c, x0 + 20 + (w - 20) / 2, cy - 2.6, name, 7.0)


def arrow(c, x1, y1, x2, y2, label=None, lab_off=(0, 0), size=6.6, dash=False):
    c.setStrokeColor(LINE)
    c.setLineWidth(0.7)
    c.setDash(2, 2) if dash else c.setDash()
    c.line(x1, y1, x2, y2)
    c.setDash()
    ang = math.atan2(y2 - y1, x2 - x1)
    hl, hw = 5.2, 2.5
    bx, by = x2 - hl * math.cos(ang), y2 - hl * math.sin(ang)
    p = c.beginPath()
    p.moveTo(x2, y2)
    p.lineTo(bx - hw * math.sin(ang), by + hw * math.cos(ang))
    p.lineTo(bx + hw * math.sin(ang), by - hw * math.cos(ang))
    p.close()
    c.setFillColor(LINE)
    c.drawPath(p, fill=1, stroke=0)
    if label:
        mx, my = (x1 + x2) / 2 + lab_off[0], (y1 + y2) / 2 + lab_off[1]
        c.setFillColor(white)
        tw = c.stringWidth(label, "Helvetica", size)
        c.rect(mx - tw / 2 - 1.5, my - 2.2, tw + 3, 8, fill=1, stroke=0)
        _text(c, mx, my, label, size, col=GREY)


def actor(c, cx, cy, name):
    """Stick figure for the use case diagram."""
    c.setStrokeColor(LINE)
    c.setLineWidth(0.9)
    c.setFillColor(white)
    c.circle(cx, cy + 15, 5, fill=1, stroke=1)
    c.line(cx, cy + 10, cx, cy - 3)
    c.line(cx - 8, cy + 5, cx + 8, cy + 5)
    c.line(cx, cy - 3, cx - 6, cy - 14)
    c.line(cx, cy - 3, cx + 6, cy - 14)
    for i, part in enumerate(name.split("|")):
        _text(c, cx, cy - 24 - i * 8, part, 7.0)


def oval(c, cx, cy, w, h, rows, size=7.0):
    c.setStrokeColor(LINE)
    c.setFillColor(white)
    c.setLineWidth(0.8)
    c.ellipse(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, fill=1, stroke=1)
    _lines(c, cx, cy, rows, size, lead=7.8)


# The level 0 and level 1 diagrams live in dfd_l1.py. They were removed from
# this module so each figure has exactly one definition.

# ---------------------------------------------------------------- use case
def use_case(c, W, H):
    bx0, by0 = 108, 26
    bw, bh = W - 216, H - 52
    c.setStrokeColor(LINE)
    c.setFillColor(white)
    c.setLineWidth(0.9)
    c.rect(bx0, by0, bw, bh, fill=1, stroke=1)
    _text(c, bx0 + bw / 2, by0 + bh - 15, "Venue Operations System", 8.2,
          "Helvetica-Bold")

    cxm = bx0 + bw / 2
    ow, oh = 138, 27
    # Grouped by actor so the association lines do not cross. The UC number
    # on each oval gives the examiner the mapping to Table 5.2 directly.
    cases = [
        ["UC 01  Submit", "emergency report"],
        ["UC 04  Submit discreet", "safety report"],
        ["UC 05  Attach photo", "evidence"],
        ["UC 06  Triage and", "verify incident"],
        ["UC 02  Dispatch", "responder"],
        ["UC 07  Acknowledge", "and resolve"],
        ["UC 03  Authenticate", "control room operator"],
        ["UC 08  Escalate to", "ERSS 112"],
        ["UC 09  Broadcast", "exit guidance"],
        ["UC 10  Manage venue", "and responders"],
    ]
    topy = by0 + bh - 44
    step = (topy - (by0 + 26)) / (len(cases) - 1)
    ys = [topy - i * step for i in range(len(cases))]
    for rows, y in zip(cases, ys):
        oval(c, cxm, y, ow, oh, rows)

    la, ra = 50, W - 50

    def link(x, y, tx, ty):
        c.setStrokeColor(LINE)
        c.setLineWidth(0.6)
        c.line(x, y, tx, ty)

    # Reporter owns the three reporting cases, which sit together at the top.
    ry = ys[1]
    actor(c, la, ry + 4, "Reporter")
    for y in (ys[0], ys[1], ys[2]):
        link(la + 12, ry, cxm - ow / 2, y)

    # Responder owns one case only. No link to evidence capture: a responder
    # receives evidence, the reporter supplies it.
    actor(c, la, ys[5] + 4, "Responder")
    link(la + 12, ys[5], cxm - ow / 2, ys[5])

    oy = ys[4]
    actor(c, ra, oy + 4, "Control Room|Operator")
    for y in (ys[3], ys[4], ys[6], ys[7], ys[8]):
        link(ra - 12, oy, cxm + ow / 2, y)

    # ERSS 112 receives the escalation; the operator initiates it.
    actor(c, ra, ys[7] - 32, "ERSS 112")
    link(ra - 12, ys[7] - 36, cxm + ow / 2, ys[7])

    actor(c, ra, ys[9] + 4, "Venue|Administrator")
    link(ra - 12, ys[9], cxm + ow / 2, ys[9])

    _text(c, W / 2, 4, "Figure 5.1  Use case diagram", 7.6,
          "Helvetica-Oblique", GREY)
