"""Level 1 data flow diagram, drawn as a two dimensional flow.

The earlier version arranged the seven processes in a single vertical chain,
which reads as a sequence of steps and therefore describes control flow rather
than data flow. This version places each process where its data actually comes
from and goes to: external entities sit on the left and right boundary, stores
sit beside the processes that read and write them, and several processes are
driven by the operator rather than by the process above them.

Drawn landscape. The Rotated wrapper turns it upright on a portrait page.
"""
import math

from reportlab.lib.colors import HexColor, white
from reportlab.platypus import Flowable

INK = HexColor("#111111")
LINE = HexColor("#333333")
SOFT = HexColor("#F2F2F2")
GREY = HexColor("#5A5A5A")


class Rotated(Flowable):
    """Draws a landscape figure sideways so it fits a portrait page."""

    def __init__(self, avail_w, avail_h, land_w, land_h, fn):
        Flowable.__init__(self)
        self.width = avail_w
        self.height = avail_h
        self.lw, self.lh = land_w, land_h
        self.fn = fn

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        c = self.canv
        scale = min(self.height / self.lw, self.width / self.lh)
        c.saveState()
        c.translate(self.width / 2 + (self.lh * scale) / 2,
                    self.height / 2 - (self.lw * scale) / 2)
        c.rotate(90)
        c.scale(scale, scale)
        self.fn(c, self.lw, self.lh)
        c.restoreState()


def _t(c, x, y, s, size=8.0, font="Helvetica", col=INK, anchor="middle"):
    c.setFont(font, size)
    c.setFillColor(col)
    if anchor == "middle":
        c.drawCentredString(x, y, s)
    elif anchor == "start":
        c.drawString(x, y, s)
    else:
        c.drawRightString(x, y, s)


def _lines(c, x, y, rows, size=7.2, lead=8.2, font="Helvetica"):
    yy = y + (len(rows) - 1) * lead / 2.0
    for r in rows:
        _t(c, x, yy - 2.5, r, size, font)
        yy -= lead


class Node:
    def __init__(self, kind, x, y, w=0, h=0, r=0):
        self.kind, self.x, self.y = kind, x, y
        self.w, self.h, self.r = w, h, r

    def edge(self, tx, ty, pad=3.0):
        """Where a line towards (tx, ty) leaves this shape."""
        dx, dy = tx - self.x, ty - self.y
        d = math.hypot(dx, dy) or 1.0
        if self.kind == "circle":
            k = (self.r + pad) / d
            return self.x + dx * k, self.y + dy * k
        hw, hh = self.w / 2 + pad, self.h / 2 + pad
        sx = hw / abs(dx) if dx else 1e9
        sy = hh / abs(dy) if dy else 1e9
        k = min(sx, sy)
        return self.x + dx * k, self.y + dy * k


def entity(c, n, rows):
    c.setStrokeColor(LINE)
    c.setFillColor(white)
    c.setLineWidth(1.0)
    c.rect(n.x - n.w / 2, n.y - n.h / 2, n.w, n.h, fill=1, stroke=1)
    _lines(c, n.x, n.y, rows, 8.4, 9.6)


def process(c, n, rows):
    c.setStrokeColor(LINE)
    c.setFillColor(white)
    c.setLineWidth(1.0)
    c.circle(n.x, n.y, n.r, fill=1, stroke=1)
    _lines(c, n.x, n.y, rows, 7.8, 8.8)


def store(c, n, tag, name):
    x0, y0 = n.x - n.w / 2, n.y - n.h / 2
    c.setFillColor(SOFT)
    c.rect(x0, y0, n.w, n.h, fill=1, stroke=0)
    c.setStrokeColor(LINE)
    c.setLineWidth(1.0)
    c.line(x0, y0, x0 + n.w, y0)
    c.line(x0, y0 + n.h, x0 + n.w, y0 + n.h)
    c.line(x0 + 19, y0, x0 + 19, y0 + n.h)
    _t(c, x0 + 9.5, n.y - 2.5, tag, 7.8, "Helvetica-Bold")
    _t(c, x0 + 19 + (n.w - 19) / 2, n.y - 2.5, name, 7.8)


def flow(c, a, b, label=None, off=0.0, lab_at=0.5, lab_dy=3.6):
    """An arrow from node a to node b, labelled with the data in motion."""
    x1, y1 = a.edge(b.x, b.y)
    x2, y2 = b.edge(a.x, a.y)
    if off:
        dx, dy = x2 - x1, y2 - y1
        d = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / d * off, dx / d * off
        x1, y1, x2, y2 = x1 + nx, y1 + ny, x2 + nx, y2 + ny
    c.setStrokeColor(LINE)
    c.setLineWidth(0.7)
    c.line(x1, y1, x2, y2)
    ang = math.atan2(y2 - y1, x2 - x1)
    hl, hw = 5.4, 2.6
    bx, by = x2 - hl * math.cos(ang), y2 - hl * math.sin(ang)
    p = c.beginPath()
    p.moveTo(x2, y2)
    p.lineTo(bx - hw * math.sin(ang), by + hw * math.cos(ang))
    p.lineTo(bx + hw * math.sin(ang), by - hw * math.cos(ang))
    p.close()
    c.setFillColor(LINE)
    c.drawPath(p, fill=1, stroke=0)
    if label:
        mx = x1 + (x2 - x1) * lab_at
        my = y1 + (y2 - y1) * lab_at + lab_dy
        c.setFillColor(white)
        w = c.stringWidth(label, "Helvetica", 7.0)
        c.rect(mx - w / 2 - 1.4, my - 2.0, w + 2.8, 7.6, fill=1, stroke=0)
        _t(c, mx, my, label, 7.0, "Helvetica", GREY)



def routed(c, a, b, waypoints, label=None, lab_i=0, lab_dy=4.0):
    """A flow that follows waypoints, used where a straight line would cross
    other symbols. The arrowhead lands on b."""
    pts = [a.edge(*waypoints[0])] + list(waypoints) + [b.edge(*waypoints[-1])]
    c.setStrokeColor(LINE)
    c.setLineWidth(0.7)
    for i in range(len(pts) - 1):
        c.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])
    (x1, y1), (x2, y2) = pts[-2], pts[-1]
    ang = math.atan2(y2 - y1, x2 - x1)
    hl, hw = 5.4, 2.6
    bx, by = x2 - hl * math.cos(ang), y2 - hl * math.sin(ang)
    pth = c.beginPath()
    pth.moveTo(x2, y2)
    pth.lineTo(bx - hw * math.sin(ang), by + hw * math.cos(ang))
    pth.lineTo(bx + hw * math.sin(ang), by - hw * math.cos(ang))
    pth.close()
    c.setFillColor(LINE)
    c.drawPath(pth, fill=1, stroke=0)
    if label:
        (ax, ay), (bx2, by2) = pts[lab_i], pts[lab_i + 1]
        mx, my = (ax + bx2) / 2, (ay + by2) / 2 + lab_dy
        c.setFillColor(white)
        w = c.stringWidth(label, "Helvetica", 7.0)
        c.rect(mx - w / 2 - 1.4, my - 2.0, w + 2.8, 7.6, fill=1, stroke=0)
        _t(c, mx, my, label, 7.0, "Helvetica", GREY)


def dfd_level1(c, W, H):
    EW, EH = 92, 28
    R = 31
    SW, SH = 116, 18

    # Boundary. These are exactly the entities shown in the context diagram.
    reporter = Node("rect", 56, 386, EW, EH)
    admin = Node("rect", 56, 96, EW, EH + 8)
    operator = Node("rect", W - 56, 386, EW, EH + 8)
    responder = Node("rect", W - 56, 226, EW, EH)
    erss = Node("rect", W - 56, 96, EW, EH)

    # Processes, placed by where their data comes from and goes to.
    p1 = Node("circle", 186, 386, r=R)
    p2 = Node("circle", 318, 386, r=R)
    p3 = Node("circle", 450, 386, r=R)
    p8 = Node("circle", 186, 226, r=R)
    p6 = Node("circle", 318, 226, r=R)
    p4 = Node("circle", 450, 226, r=R)
    p7 = Node("circle", 318, 96, r=R)
    p5 = Node("circle", 450, 96, r=R)

    # Stores, beside the process that reads or writes them.
    d1 = Node("rect", 186, 452, SW, SH)
    d5 = Node("rect", 318, 452, SW, SH)
    d4 = Node("rect", 108, 306, SW, SH)
    d2 = Node("rect", W - 134, 262, SW, SH)
    d3 = Node("rect", W - 130, 160, SW, SH)
    d7 = Node("rect", 318, 158, SW, SH)
    d6 = Node("rect", 318, 30, SW, SH)

    for n, rows in ((reporter, ["Reporter"]),
                    (admin, ["Venue", "Administrator"]),
                    (operator, ["Control Room", "Operator"]),
                    (responder, ["Responder"]), (erss, ["ERSS 112"])):
        entity(c, n, rows)

    process(c, p1, ["1.0", "Report", "Intake"])
    process(c, p2, ["2.0", "Triage"])
    process(c, p3, ["3.0", "Merge and", "Corroborate"])
    process(c, p4, ["4.0", "Dispatch"])
    process(c, p5, ["5.0", "Escalation"])
    process(c, p6, ["6.0", "Broadcast"])
    process(c, p7, ["7.0", "Audit and", "Evidence"])
    process(c, p8, ["8.0", "Venue", "Configuration"])

    store(c, d1, "D1", "Reports")
    store(c, d5, "D5", "Protocols")
    store(c, d4, "D4", "Venues and Zones")
    store(c, d2, "D2", "Incidents")
    store(c, d3, "D3", "Responders")
    store(c, d7, "D7", "Broadcasts")
    store(c, d6, "D6", "Audit Log")

    # --- intake ------------------------------------------------------
    flow(c, reporter, p1, "emergency report")
    flow(c, d4, p1, "zone list")
    flow(c, p1, d1, "report record")
    flow(c, p1, reporter, "acknowledgement", off=-9, lab_at=0.55)
    flow(c, p1, p2, "new report")

    # --- triage and merge --------------------------------------------
    flow(c, d5, p2, "protocol match")
    flow(c, p2, p3, "categorised report")
    flow(c, d2, p3, "open incidents", off=8)
    flow(c, p3, d2, "incident record", off=-8)
    flow(c, p3, operator, "live incident feed")

    # --- dispatch, driven by the operator, not by 3.0 -----------------
    flow(c, operator, p4, "dispatch order")
    flow(c, d3, p4, "available units", lab_at=0.34)
    flow(c, p4, d2, "assignment record", lab_at=0.72)
    flow(c, p4, responder, "assignment", off=8)
    flow(c, responder, p4, "status update", off=8)

    # --- escalation, driven by a timer over the incident store --------
    flow(c, d2, p5, "unacknowledged incident", lab_at=0.62)
    flow(c, p5, erss, "escalation handoff")

    # --- broadcast, also operator driven ------------------------------
    flow(c, operator, p6, "advisory text", lab_at=0.30)
    flow(c, p6, d7, "broadcast record")
    flow(c, p6, reporter, "exit guidance", lab_at=0.60)

    # --- venue configuration, the administrator's input ---------------
    flow(c, admin, p8, "venue configuration")
    flow(c, p8, d4, "zone definitions")
    routed(c, p8, d3, [(186, 62), (W - 134, 62)], "responder roster",
           lab_i=1)

    # --- audit, fed by the processes that change state ----------------
    flow(c, p4, p7, "state changes", lab_at=0.42)
    flow(c, p5, p7, "escalation event")
    flow(c, p7, d6, "audit record")
    flow(c, p7, admin, "audit report", lab_at=0.55)

    _t(c, W / 2, 10, "Figure 4.3  Data flow diagram, level 1", 8.0,
       "Helvetica-Oblique", GREY)


def dfd_level0(c, W, H):
    """Context diagram.

    One process, no data stores, and exactly the flows that cross the system
    boundary in figure 4.2. Keeping the two in step is what balancing means.
    """
    EW, EH = 104, 30
    cx, cy = W / 2, H / 2 - 4

    core = Node("circle", cx, cy, r=64)
    reporter = Node("rect", 62, H - 52, EW, EH)
    operator = Node("rect", W - 62, H - 52, EW, EH + 8)
    responder = Node("rect", W - 62, cy - 6, EW, EH)
    erss = Node("rect", W - 62, 48, EW, EH)
    admin = Node("rect", 62, 48, EW, EH + 8)

    c.setStrokeColor(LINE)
    c.setFillColor(white)
    c.setLineWidth(1.1)
    c.circle(cx, cy, core.r, fill=1, stroke=1)
    _lines(c, cx, cy, ["0", "Aidly", "Venue Operations", "System"], 8.0, 9.6)

    entity(c, reporter, ["Reporter"])
    entity(c, operator, ["Control Room", "Operator"])
    entity(c, responder, ["Responder"])
    entity(c, erss, ["ERSS 112"])
    entity(c, admin, ["Venue", "Administrator"])

    flow(c, reporter, core, "emergency report", off=9, lab_at=0.30)
    flow(c, core, reporter, "acknowledgement", off=9, lab_at=0.80)
    flow(c, core, reporter, "exit guidance", off=-18, lab_at=0.32)

    flow(c, operator, core, "dispatch order", off=9, lab_at=0.30)
    flow(c, operator, core, "advisory text", off=22, lab_at=0.56)
    flow(c, core, operator, "live incident feed", off=9, lab_at=0.78)

    flow(c, core, responder, "assignment", off=8, lab_at=0.5)
    flow(c, responder, core, "status update", off=8, lab_at=0.5)

    flow(c, admin, core, "venue configuration", off=9, lab_at=0.44)
    flow(c, core, admin, "audit report", off=9, lab_at=0.56)

    flow(c, core, erss, "escalation handoff", lab_at=0.55)

    _t(c, W / 2, 10, "Figure 4.2  Context diagram, level 0", 8.0,
       "Helvetica-Oblique", GREY)
