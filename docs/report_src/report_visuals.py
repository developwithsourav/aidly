"""Cover artwork, IDE style code panels and the analytical charts.

Everything is drawn with canvas primitives so it stays sharp at print size and
reproduces cleanly in black and white: contrast carries the meaning, never hue.
"""
import math
import random

from reportlab.lib.colors import HexColor, white, black
from reportlab.platypus import Flowable

BLACK = HexColor("#0B0E12")
INK = HexColor("#14181E")
MID = HexColor("#555C66")
SOFT = HexColor("#8A929C")
HAIR = HexColor("#C4CAD1")
PALE = HexColor("#EDEFF2")
PAPER = HexColor("#FAFBFC")
GUT = HexColor("#EEF0F3")


class Draw(Flowable):
    def __init__(self, width, height, fn, pad_bottom=0):
        Flowable.__init__(self)
        self.width = width
        self.height = height + pad_bottom
        self._h = height
        self.fn = fn

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        self.fn(self.canv, self.width, self._h)


def _t(c, x, y, s, size=8, font="Helvetica", col=INK, anchor="middle"):
    c.setFont(font, size)
    c.setFillColor(col)
    if anchor == "middle":
        c.drawCentredString(x, y, s)
    elif anchor == "end":
        c.drawRightString(x, y, s)
    else:
        c.drawString(x, y, s)


# ===================================================== cover artwork
def cover_art(c, W, H):
    """A distress signal rising out of a dense crowd, inside a shield.

    The subject of the project in one mark: many people, one call for help,
    one protected boundary around them.
    """
    c.saveState()
    c.setFillColor(BLACK)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # Everything after this is confined to the panel.
    clip = c.beginPath()
    clip.rect(0, 0, W, H)
    c.clipPath(clip, stroke=0, fill=0)

    cx, cy = W / 2, H * 0.560

    # Concentric signal rings, fading outward.
    for i in range(9):
        r = 24 + i * 21.0
        g = max(26, 214 - i * 24)
        c.setStrokeColor(HexColor("#%02x%02x%02x" % (g, g, g)))
        c.setLineWidth(1.3 if i < 2 else 0.55)
        c.circle(cx, cy, r, fill=0, stroke=1)

    # The crowd: many small figures, the ones nearest the signal lit.
    random.seed(23)
    rows = [(H * 0.300, 30, 8.0), (H * 0.232, 26, 9.6),
            (H * 0.158, 23, 11.4), (H * 0.078, 20, 13.4)]
    for ri, (ry, count, sc) in enumerate(rows):
        for i in range(count):
            x = (W / (count + 1)) * (i + 1) + random.uniform(-9, 9)
            lit = abs(x - cx) < sc * 2.2 and ri >= 1
            g = 248 if lit else random.randint(46, 84)
            col = HexColor("#%02x%02x%02x" % (g, g, g))
            c.setFillColor(col)
            c.setStrokeColor(col)
            c.setLineWidth(sc * 0.15)
            head = sc * 0.20
            top = ry + sc * 0.58
            c.circle(x, top, head, fill=1, stroke=0)
            hip = ry - sc * 0.10
            c.line(x, top - head, x, hip)                       # torso
            c.line(x - sc * 0.30, ry + sc * 0.30,
                   x + sc * 0.30, ry + sc * 0.30)               # arms
            c.line(x, hip, x - sc * 0.24, ry - sc * 0.62)       # legs
            c.line(x, hip, x + sc * 0.24, ry - sc * 0.62)

    # Shield outline around the signal.
    sw, sh = 104, 128
    p = c.beginPath()
    p.moveTo(cx, cy + sh * 0.52)
    p.lineTo(cx + sw * 0.5, cy + sh * 0.24)
    p.lineTo(cx + sw * 0.5, cy - sh * 0.10)
    p.curveTo(cx + sw * 0.5, cy - sh * 0.40, cx + sw * 0.22, cy - sh * 0.52,
              cx, cy - sh * 0.58)
    p.curveTo(cx - sw * 0.22, cy - sh * 0.52, cx - sw * 0.5, cy - sh * 0.40,
              cx - sw * 0.5, cy - sh * 0.10)
    p.lineTo(cx - sw * 0.5, cy + sh * 0.24)
    p.close()
    c.setStrokeColor(white)
    c.setLineWidth(2.4)
    c.setFillColor(BLACK)
    c.drawPath(p, fill=1, stroke=1)

    # The single raised alert inside the shield.
    c.setFillColor(white)
    c.setStrokeColor(white)
    c.setLineWidth(4.4)
    c.circle(cx, cy + 26, 4.6, fill=1, stroke=0)
    c.line(cx, cy + 16, cx, cy - 12)
    c.line(cx, cy + 8, cx - 15, cy - 6)
    c.line(cx, cy + 8, cx + 15, cy - 6)
    c.line(cx, cy - 12, cx - 12, cy - 34)
    c.line(cx, cy - 12, cx + 12, cy - 34)

    c.restoreState()


# ===================================================== IDE code panel
KW = {"def", "class", "return", "if", "not", "is", "None", "True", "False",
      "import", "from", "try", "except", "raise", "for", "in", "with", "as",
      "and", "or", "else", "elif", "async", "await", "lambda", "pass", "self"}


class CodePanel(Flowable):
    """A code listing drawn to look like an editor pane: title bar, line number
    gutter, and weight based highlighting that survives a monochrome printer."""

    def __init__(self, width, filename, src, fs=7.6, lead=10.2, caption=None):
        Flowable.__init__(self)
        self.width = width
        self.filename = filename
        self.lines = src.strip("\n").split("\n")
        self.fs = fs
        self.lead = lead
        self.bar = 17.0
        self.pad = 6.0
        self.gut = 24.0
        self.caption = caption
        # The caption belongs to the panel, so a page break can never leave
        # it stranded on a page of its own.
        self.cap_h = 18.0 if caption else 0.0
        self.panel_h = self.bar + self.pad * 2 + self.lead * len(self.lines)
        self.height = self.panel_h + self.cap_h

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        c = self.canv
        W = self.width
        H = self.panel_h
        r = 3.4
        if self.caption:
            c.translate(0, self.cap_h)
            _t(c, W / 2, -12.5, self.caption, 9.0, "Helvetica-Oblique", MID)

        c.setFillColor(PAPER)
        c.setStrokeColor(HAIR)
        c.setLineWidth(0.7)
        c.roundRect(0, 0, W, H, r, fill=1, stroke=1)

        # Title bar
        c.saveState()
        pth = c.beginPath()
        pth.moveTo(0, H - self.bar)
        pth.lineTo(0, H - r)
        pth.curveTo(0, H, 0, H, r, H)
        pth.lineTo(W - r, H)
        pth.curveTo(W, H, W, H, W, H - r)
        pth.lineTo(W, H - self.bar)
        pth.close()
        c.setFillColor(INK)
        c.drawPath(pth, fill=1, stroke=0)
        c.restoreState()

        for i, g in enumerate(("#6E7681", "#8A929C", "#A7AEB6")):
            c.setFillColor(HexColor(g))
            c.circle(9 + i * 8, H - self.bar / 2, 2.5, fill=1, stroke=0)
        _t(c, 34, H - self.bar / 2 - 2.6, self.filename, 7.4, "Courier-Bold",
           white, "start")

        # Gutter
        gx = self.gut
        c.setFillColor(GUT)
        c.rect(0.7, self.pad * 0.2, gx, H - self.bar - self.pad * 0.4,
               fill=1, stroke=0)
        c.setStrokeColor(HAIR)
        c.setLineWidth(0.5)
        c.line(gx, 0.7, gx, H - self.bar)

        y = H - self.bar - self.pad - self.fs
        for n, ln in enumerate(self.lines, 1):
            _t(c, gx - 4, y, str(n), self.fs * 0.86, "Courier", SOFT, "end")
            self._line(c, gx + 6, y, ln)
            y -= self.lead

    def _line(self, c, x, y, ln):
        stripped = ln.strip()
        if stripped.startswith("#"):
            _t(c, x, y, ln, self.fs, "Courier-Oblique", MID, "start")
            return
        if stripped.startswith(('"""', "'''")):
            _t(c, x, y, ln, self.fs, "Courier-Oblique", MID, "start")
            return
        # Word level: keywords bold, everything else regular.
        cur = x
        tok = ""
        for ch in ln:
            if ch.isalnum() or ch == "_":
                tok += ch
            else:
                cur = self._tok(c, cur, y, tok)
                tok = ""
                _t(c, cur, y, ch, self.fs, "Courier", INK, "start")
                cur += c.stringWidth(ch, "Courier", self.fs)
        self._tok(c, cur, y, tok)

    def _tok(self, c, x, y, tok):
        if not tok:
            return x
        font = "Courier-Bold" if tok in KW else "Courier"
        _t(c, x, y, tok, self.fs, font, INK, "start")
        return x + c.stringWidth(tok, font, self.fs)


# ===================================================== charts
def increment_chart(c, W, H):
    """Increment plan as a staged bar chart."""
    rows = [("I", "Database, schema, authentication", 0, 2, True),
            ("II", "Report intake and zone resolution", 2, 2, False),
            ("III", "Triage, merge, control room view", 4, 2, False),
            ("IV", "Dispatch, acknowledgement, escalation", 6, 2, False),
            ("V", "Broadcast, discreet path, audit record", 8, 2, False)]
    left, right = 96, W - 14
    span = right - left
    unit = span / 10.0
    top = H - 26
    bh = 17
    gap = 9

    for i in range(6):
        x = left + i * 2 * unit
        c.setStrokeColor(PALE)
        c.setLineWidth(0.6)
        c.line(x, top + 6, x, top - len(rows) * (bh + gap) - 2)
        _t(c, x, top + 11, f"W{i * 2}", 6.6, "Helvetica", SOFT)

    y = top - bh
    for tag, label, st, ln, done in rows:
        x0 = left + st * unit
        w = ln * unit
        c.setFillColor(INK if done else PALE)
        c.setStrokeColor(INK)
        c.setLineWidth(0.8)
        c.rect(x0, y, w, bh, fill=1, stroke=1)
        _t(c, left - 6, y + bh / 2 - 2.4, "Increment " + tag, 7.2,
           "Helvetica-Bold", INK, "end")
        _t(c, x0 + w / 2, y + bh / 2 - 2.4, label, 6.5, "Helvetica",
           white if done else INK)
        y -= bh + gap

    _t(c, W / 2, 4, "Figure 3.1  Increment plan. The filled bar is delivered.",
       7.4, "Helvetica-Oblique", MID)


def login_sequence(c, W, H):
    """Sequence of one successful authentication."""
    cols = ["Operator", "Login screen", "Endpoint", "Service", "PostgreSQL"]
    n = len(cols)
    m = 54
    step = (W - 2 * m) / (n - 1)
    xs = [m + i * step for i in range(n)]
    top = H - 34
    bot = 34

    for x, name in zip(xs, cols):
        c.setFillColor(white)
        c.setStrokeColor(INK)
        c.setLineWidth(0.9)
        c.rect(x - 40, top, 80, 19, fill=1, stroke=1)
        _t(c, x, top + 6.2, name, 7.0, "Helvetica-Bold")
        c.setStrokeColor(HAIR)
        c.setLineWidth(0.6)
        c.setDash(2, 2)
        c.line(x, top, x, bot)
        c.setDash()

    msgs = [
        (0, 1, "enters email and password"),
        (1, 2, "POST /api/auth/login"),
        (2, 3, "authenticate(email, password)"),
        (3, 4, "SELECT on indexed email"),
        (4, 3, "row, or nothing"),
        (3, 3, "verify hash, dummy hash if absent"),
        (3, 2, "user, or None"),
        (2, 1, "200 with token, or 401"),
        (1, 0, "signed in, or one generic error"),
    ]
    y = top - 20
    for a, b, label in msgs:
        if a == b:
            x = xs[a]
            c.setStrokeColor(INK)
            c.setLineWidth(0.7)
            c.line(x, y, x + 26, y)
            c.line(x + 26, y, x + 26, y - 9)
            c.line(x + 26, y - 9, x + 3, y - 9)
            c.setFillColor(INK)
            p = c.beginPath()
            p.moveTo(x, y - 9)
            p.lineTo(x + 5.4, y - 6.8)
            p.lineTo(x + 5.4, y - 11.2)
            p.close()
            c.drawPath(p, fill=1, stroke=0)
            _t(c, x + 32, y - 3, label, 6.4, "Helvetica", MID, "start")
            y -= 26
            continue
        x1, x2 = xs[a], xs[b]
        c.setStrokeColor(INK)
        c.setLineWidth(0.7)
        c.line(x1, y, x2, y)
        d = 1 if x2 > x1 else -1
        c.setFillColor(INK)
        p = c.beginPath()
        p.moveTo(x2, y)
        p.lineTo(x2 - 5.6 * d, y + 2.4)
        p.lineTo(x2 - 5.6 * d, y - 2.4)
        p.close()
        c.drawPath(p, fill=1, stroke=0)
        _t(c, (x1 + x2) / 2, y + 4.4, label, 6.4, "Helvetica", MID)
        y -= 22

    _t(c, W / 2, 4, "Figure 7.2  One authentication, end to end", 7.4,
       "Helvetica-Oblique", MID)


def dispatch_flow(c, W, H):
    """Decision flow for matching a responder."""
    cx = W / 2

    def node(y, w, h, txt, shape="rect"):
        c.setFillColor(white)
        c.setStrokeColor(INK)
        c.setLineWidth(0.9)
        if shape == "dia":
            p = c.beginPath()
            p.moveTo(cx, y + h / 2)
            p.lineTo(cx + w / 2, y)
            p.lineTo(cx, y - h / 2)
            p.lineTo(cx - w / 2, y)
            p.close()
            c.drawPath(p, fill=1, stroke=1)
        elif shape == "round":
            c.roundRect(cx - w / 2, y - h / 2, w, h, h / 2, fill=1, stroke=1)
        else:
            c.rect(cx - w / 2, y - h / 2, w, h, fill=1, stroke=1)
        for i, part in enumerate(txt.split("|")):
            _t(c, cx, y + (len(txt.split("|")) - 1) * 4 - i * 8 - 2.4, part, 6.9)

    def link(y1, y2, label=None, off=0):
        c.setStrokeColor(INK)
        c.setLineWidth(0.7)
        c.line(cx + off, y1, cx + off, y2)
        c.setFillColor(INK)
        p = c.beginPath()
        p.moveTo(cx + off, y2)
        p.lineTo(cx + off - 2.6, y2 + 5.6)
        p.lineTo(cx + off + 2.6, y2 + 5.6)
        p.close()
        c.drawPath(p, fill=1, stroke=0)
        if label:
            _t(c, cx + off + 5, (y1 + y2) / 2 - 2, label, 6.3, "Helvetica",
               MID, "start")

    # Reserve room for the caption and the closing note, then space the six
    # nodes inside what is left, so nothing can overrun the frame.
    cap, note = 16.0, 30.0
    top = H - 14
    step = (top - cap - note - 18) / 5.0
    ys = [top - i * step for i in range(6)]
    node(ys[0], 150, 18, "Incident verified", "round")
    link(ys[0] - 9, ys[1] + 15)
    node(ys[1], 168, 30, "Required role from|the incident category", "rect")
    link(ys[1] - 15, ys[2] + 17)
    node(ys[2], 186, 34, "Attribute needed?|harassment or escort", "dia")
    link(ys[2] - 17, ys[3] + 15, "yes and no")
    node(ys[3], 200, 30, "Query available responders,|nearest first", "rect")
    link(ys[3] - 15, ys[4] + 17)
    node(ys[4], 176, 34, "Any match?", "dia")
    link(ys[4] - 17, ys[5] + 9, "yes")
    node(ys[5], 150, 18, "Assign and notify", "round")

    # Fallback branch on the right.
    bx = cx + 118
    c.setStrokeColor(INK)
    c.setLineWidth(0.7)
    c.line(cx + 88, ys[4], bx, ys[4])
    c.line(bx, ys[4], bx, ys[5] - 26)
    c.line(bx, ys[5] - 26, cx, ys[5] - 26)
    c.setFillColor(INK)
    p = c.beginPath()
    p.moveTo(cx, ys[5] - 26)
    p.lineTo(cx + 5.6, ys[5] - 23.6)
    p.lineTo(cx + 5.6, ys[5] - 28.4)
    p.close()
    c.drawPath(p, fill=1, stroke=0)
    _t(c, bx + 4, ys[4] + 5, "no", 6.3, "Helvetica", MID, "start")
    c.setFillColor(PALE)
    c.setStrokeColor(INK)
    c.rect(bx - 52, ys[4] - 62, 104, 30, fill=1, stroke=1)
    _t(c, bx, ys[4] - 42, "Widen search, flag", 6.6)
    _t(c, bx, ys[4] - 51, "as fallback, raise", 6.6)
    _t(c, cx, ys[5] - 36, "Never silent: no responder is still an outcome",
       6.4, "Helvetica-Oblique", MID)

    _t(c, W / 2, 4, "Figure 6.1  Responder matching decision flow", 7.4,
       "Helvetica-Oblique", MID)


def notation_legend(c, W, H):
    y = H - 30
    items = [("circle", "Process", "A transformation of data, numbered"),
             ("rect", "External entity", "A source or sink outside the boundary"),
             ("store", "Data store", "Persisted data, tagged D1 to D7"),
             ("arrow", "Data flow", "Named for the data, not the action")]
    for kind, name, desc in items:
        x = 42
        if kind == "circle":
            c.setStrokeColor(INK)
            c.setFillColor(white)
            c.setLineWidth(0.9)
            c.circle(x, y, 13, fill=1, stroke=1)
            _t(c, x, y - 2.4, "n.0", 6.6)
        elif kind == "rect":
            c.setStrokeColor(INK)
            c.setFillColor(white)
            c.rect(x - 20, y - 10, 40, 20, fill=1, stroke=1)
        elif kind == "store":
            c.setFillColor(PALE)
            c.rect(x - 22, y - 8, 44, 16, fill=1, stroke=0)
            c.setStrokeColor(INK)
            c.setLineWidth(0.9)
            c.line(x - 22, y - 8, x + 22, y - 8)
            c.line(x - 22, y + 8, x + 22, y + 8)
            c.line(x - 12, y - 8, x - 12, y + 8)
            _t(c, x - 17, y - 2.4, "D1", 6.4, "Helvetica-Bold")
        else:
            c.setStrokeColor(INK)
            c.setLineWidth(0.9)
            c.line(x - 20, y, x + 16, y)
            c.setFillColor(INK)
            p = c.beginPath()
            p.moveTo(x + 21, y)
            p.lineTo(x + 15, y + 2.6)
            p.lineTo(x + 15, y - 2.6)
            p.close()
            c.drawPath(p, fill=1, stroke=0)
        _t(c, 82, y + 1.5, name, 8.4, "Helvetica-Bold", INK, "start")
        _t(c, 190, y + 1.5, desc, 8.0, "Helvetica", MID, "start")
        y -= 38

    _t(c, W / 2, 4, "Figure 4.1  Notation used in the data flow diagrams", 7.4,
       "Helvetica-Oblique", MID)


def module_architecture(c, W, H):
    """The four files of the login module and what crosses between them."""
    titles = [
        ("Browser", "Sign in screen"),
        ("app/routers/auth.py", "HTTP layer, no security logic"),
        ("app/services/auth.py", "The authentication decision"),
        ("app/core/security.py", "Hashing and token handling"),
        ("app/db.py", "Engine, session per request"),
        ("PostgreSQL", "users table, indexed email"),
    ]
    bh = 34
    cap = 20                      # room reserved for the figure caption
    top = H - 6
    step = (top - cap - bh) / (len(titles) - 1)
    boxes = [(t, sub, top - i * step) for i, (t, sub) in enumerate(titles)]
    bw = W * 0.62
    cx = W / 2
    for i, (title, sub, y) in enumerate(boxes):
        fill = INK if i in (0, 5) else white
        c.setFillColor(fill)
        c.setStrokeColor(INK)
        c.setLineWidth(1.0)
        c.rect(cx - bw / 2, y - bh, bw, bh, fill=1, stroke=1)
        _t(c, cx, y - 14, title, 8.4,
           "Courier-Bold" if "/" in title else "Helvetica-Bold",
           white if i in (0, 5) else INK)
        _t(c, cx, y - 25, sub, 6.9, "Helvetica",
           HexColor("#C9CFD6") if i in (0, 5) else MID)
        if i:
            py = boxes[i - 1][2] - bh
            c.setStrokeColor(INK)
            c.setLineWidth(0.8)
            c.line(cx, py, cx, y + 5)
            c.setFillColor(INK)
            p = c.beginPath()
            p.moveTo(cx, y)
            p.lineTo(cx - 3, y + 6)
            p.lineTo(cx + 3, y + 6)
            p.close()
            c.drawPath(p, fill=1, stroke=0)

    labels = ["credentials over HTTPS", "validated request object",
              "session and email", "hash comparison", "parameterised query"]
    for i, lb in enumerate(labels):
        py = boxes[i][2] - bh
        ny = boxes[i + 1][2]
        _t(c, cx + bw / 2 + 6, (py + ny) / 2 - 2, lb, 6.5, "Helvetica",
           MID, "start")

    _t(c, W / 2, 4, "Figure 7.1  Structure of the login module", 7.4,
       "Helvetica-Oblique", MID)
