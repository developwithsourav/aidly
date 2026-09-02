# Cover page and contents. Executed once per pass so the second pass can print
# the page numbers recorded during the first.

S += [Spacer(1, 20 * mm)]

# The team logo, used as supplied. Small, as asked.
S += [shot("aidly_logo.png", 64)]
S += [Spacer(1, 10 * mm)]

S += [P("AIDLY", st("cvt", fontName="HB", fontSize=64, alignment=TA_CENTER,
                    leading=70, spaceAfter=14, textColor=INK))]
S += [Table([[""]], colWidths=[30 * mm], rowHeights=[2.2], hAlign="CENTER",
            style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), INK)]))]
S += [Spacer(1, 8 * mm)]
S += [P("A Venue Operations Layer for Crowd Emergencies",
        st("cvs", fontName="T", fontSize=16, alignment=TA_CENTER, leading=21,
           textColor=INK, spaceAfter=4))]
S += [P("Software Engineering Project Report",
        st("cvs2", fontName="HB", fontSize=12, alignment=TA_CENTER, leading=17,
           textColor=GREY))]

S += [Spacer(1, 18 * mm)]

_NAME = st("tname", fontName="T", fontSize=13.5, leading=19, textColor=INK)
_ROLL = st("troll", fontName="M", fontSize=13, leading=19, textColor=INK)
_LBL = st("tlbl", fontName="HB", fontSize=8.5, alignment=TA_CENTER, leading=12,
          textColor=GREY)
# The cell alignment does not reach inside a paragraph, so the footer entries
# need a centred style of their own.
_CNAME = st("tcname", fontName="T", fontSize=13.5, alignment=TA_CENTER,
            leading=19, textColor=INK)

_team = Table(
    [[Paragraph("SUBMITTED BY", _LBL), ""],
     ["", ""],
     [Paragraph("Sourav Kumar", _NAME), Paragraph("24/48044", _ROLL)],
     [Paragraph("Janvi Monga", _NAME), Paragraph("24/48092", _ROLL)],
     [Paragraph("Avijit Sakkarwal", _NAME), Paragraph("24/48079", _ROLL)]],
    colWidths=[58 * mm, 34 * mm], hAlign="CENTER")
_team.setStyle(TableStyle([
    ("SPAN", (0, 0), (1, 0)),
    ("LINEBELOW", (0, 0), (1, 0), 0.8, RULE),
    ("LINEBELOW", (0, 2), (1, 3), 0.4, HexColor("#E2E5E9")),
    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("TOPPADDING", (0, 0), (-1, -1), 6),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
]))
S += [_team]

S += [Spacer(1, 20 * mm)]
_foot = Table(
    [[Paragraph("Submitted to", _LBL), ""],
     [Paragraph("Uma Ma'am", _CNAME), ""],
     ["", ""],
     [Paragraph("Subject", _LBL), ""],
     [Paragraph("Software Engineering", _CNAME), ""]],
    colWidths=[92 * mm, 0.1 * mm], hAlign="CENTER")
_foot.setStyle(TableStyle([
    ("SPAN", (0, 0), (1, 0)), ("SPAN", (0, 1), (1, 1)),
    ("SPAN", (0, 3), (1, 3)), ("SPAN", (0, 4), (1, 4)),
    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ("TOPPADDING", (0, 0), (-1, -1), 1.5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
]))
for _r in (1, 4):
    _foot.setStyle(TableStyle([("ALIGN", (0, _r), (0, _r), "CENTER")]))
S += [_foot]

S += [NextPageTemplate("main"), PageBreak()]

# ------------------------------------------------------------------ contents
S += [P("Contents", st("toch", fontName="TB", fontSize=21, leading=27,
                       spaceAfter=4))]
S += [Table([[""]], colWidths=[CW], rowHeights=[1.4],
            style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), INK)]))]
S += [Spacer(1, 12)]

_TOC = [
    ("1", "Problem Statement"),
    ("1.1", "Overview"),
    ("1.2", "Why the Present Method Fails"),
    ("1.3", "Challenges in the Current System"),
    ("1.4", "The Proposed Solution"),
    ("1.5", "Stakeholders"),
    ("1.6", "Scope of the System"),
    ("2", "Requirements Identification"),
    ("2.1", "Method of Elicitation"),
    ("2.2", "The Prototype"),
    ("2.3", "Walkthrough of the Reporting Path"),
    ("2.4", "Specification of the Reporting Inputs"),
    ("2.5", "The Control Surfaces"),
    ("2.6", "Findings Carried into the Requirements"),
    ("2.7", "Functional Requirements"),
    ("2.8", "Nonfunctional Requirements"),
    ("2.9", "Requirements Traceability"),
    ("3", "Process Model"),
    ("3.1", "Candidate Models"),
    ("3.2", "Characteristics of This Project"),
    ("3.3", "Comparison of the Candidates"),
    ("3.4", "The Selected Model"),
    ("3.5", "Reasons for the Selection"),
    ("3.6", "Why Each Alternative Was Rejected"),
    ("3.7", "The Increment Plan"),
    ("4", "Data Flow Diagrams and Data Dictionary"),
    ("4.1", "Notation"),
    ("4.2", "Level 0: Context Diagram"),
    ("4.3", "Level 1 Data Flow Diagram"),
    ("4.4", "Reading the Level 1 Diagram"),
    ("4.5", "Process Specifications"),
    ("4.6", "Data Dictionary: Data Flows"),
    ("4.7", "Data Dictionary: Data Stores"),
    ("4.8", "Data Dictionary: Data Elements"),
    ("5", "Use Case Diagram"),
    ("5.1", "Actors"),
    ("5.2", "The Diagram"),
    ("5.3", "Use Case Inventory"),
    ("6", "Use Case Templates"),
    ("6.1", "UC 01: Submit Emergency Report"),
    ("6.2", "UC 02: Dispatch Responder"),
    ("6.3", "UC 03: Authenticate Control Room Operator"),
    ("6.4", "Incident State Transitions"),
    ("7", "Login Module Connection with Database"),
    ("7.1", "What Was Built"),
    ("7.2", "Structure of the Module"),
    ("7.3", "The Users Table"),
    ("7.4", "The Connection Layer"),
    ("7.5", "Password Hashing"),
    ("7.6", "Access Tokens"),
    ("7.7", "The Authentication Service"),
    ("7.8", "The Endpoints"),
    ("7.9", "The Interface Offered by the Module"),
    ("7.10", "The Sign In Screen"),
    ("7.11", "Sequence of One Authentication"),
    ("7.12", "Execution Against the Database"),
    ("7.13", "Verification"),
    ("8", "References"),
]

_rows = []
for _num, _title in _TOC:
    _top = "." not in _num
    _s = TOC1 if _top else TOC2
    _ind = "" if _top else "&nbsp;&nbsp;&nbsp;&nbsp;"
    _pg = HEAD_PAGES.get(_num, "")
    _rows.append([Paragraph(f"{_ind}{_num}", _s),
                  Paragraph(_title, _s),
                  Paragraph(str(_pg), _s)])

_tt = Table(_rows, colWidths=[20 * mm, CW - 32 * mm, 12 * mm], hAlign="LEFT")
_tt.setStyle(TableStyle([
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("ALIGN", (2, 0), (2, -1), "RIGHT"),
    ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ("TOPPADDING", (0, 0), (-1, -1), 1.9),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 1.9),
]))
S += [_tt, PageBreak()]
