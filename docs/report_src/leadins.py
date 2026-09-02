"""Adds a lead in sentence to every section that opened straight into a table.

Two reasons. A section should not begin with a bare table, and with
keepWithNext on the headings a short sentence is what lets the heading move
cheaply while the table itself still splits across pages.
"""
import re

P = "report_body.py"
L = open(P, encoding="utf-8").read().split("\n")

LEAD = {
    "1.5  Stakeholders":
        "Six parties have an interest in the system, and their interests differ "
        "enough that a design decision which suits one can work against another.",
    "1.6  Scope of the System":
        "The boundary is stated in both directions, because what a system will "
        "not do is as much a decision as what it will.",
    "2.7  Functional Requirements":
        "Eighteen functional requirements follow. Each is traceable either to a "
        "finding recorded above or to the analysis that followed the prototype.",
    "2.8  Nonfunctional Requirements":
        "The requirements below constrain how the system must behave rather than "
        "what it must do.",
    "3.3  Comparison of the Candidates":
        "Each candidate is judged against the five characteristics above.",
    "3.7  The Increment Plan":
        "The requirement set is partitioned into five increments, ordered so that "
        "the riskiest work is proven first.",
    "Flows crossing the boundary":
        "These eleven flows are the complete interface between the system and "
        "everything outside it.",
    "4.7  Data Dictionary: Data Stores":
        "Each store named in the two diagrams is defined below, in the same "
        "notation.",
    "4.8  Data Dictionary: Data Elements":
        "The elements below appear inside several of the flows and stores already "
        "defined, so they are given once here rather than repeated.",
    "5.1  Actors":
        "Five actors interact with the system. Four are people and one is an "
        "external service.",
    "5.3  Use Case Inventory":
        "The ten use cases below are the complete inventory for the system.",
    "6.1  UC 01: Submit Emergency Report":
        "This is the path that begins every incident, and the only one open to "
        "someone who is not authenticated.",
    "6.2  UC 02: Dispatch Responder":
        "This is the operator path that turns a verified incident into a "
        "responder on the ground.",
    "6.3  UC 03: Authenticate Control Room Operator":
        "This case guards every operational screen. It is implemented and "
        "demonstrated in Chapter 7.",
    "7.11  Sequence of One Authentication":
        "The sequence below traces one successful sign in from the operator "
        "through to the database and back.",
    "Documentation and websites consulted":
        "The sources below were consulted during design and implementation.",
}

out = []
added = 0
for i, line in enumerate(L):
    out.append(line)
    m = re.search(r'h[23]\("([^"]+)"\)', line)
    if not m:
        continue
    lead = LEAD.get(m.group(1))
    if not lead:
        continue
    prefix = "_blk" if line.strip().startswith("_blk") else "S"
    # wrap the sentence so the source stays readable
    words, cur, rows = lead.split(), "", []
    for w in words:
        if len(cur) + len(w) + 1 > 62:
            rows.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    rows.append(cur)
    body = ('\n        '.join('"%s "' % r for r in rows[:-1] + [rows[-1]]))
    body = body.rstrip()
    if body.endswith('" '):
        body = body[:-2] + '"'
    out.append(f'{prefix} += [P({body})]')
    added += 1

open(P, "w", encoding="utf-8").write("\n".join(out))
print("lead in sentences added:", added, "of", len(LEAD))
