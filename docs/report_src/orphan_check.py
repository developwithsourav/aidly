"""Fails if any page ends with a heading and nothing under it."""
import os
import re
import sys
from pypdf import PdfReader

SP = os.path.dirname(os.path.abspath(__file__))
# report_src sits inside docs/, so the outputs go to its parent. Derived
# rather than hardcoded, so renaming the project folder cannot break it.
DOCS = os.path.dirname(SP)

PDF = os.path.join(DOCS, "Aidly_SE_Report.pdf")
HEAD = re.compile(r"^\d+\.\d+\s+[A-Z]")
bad = []
for i, page in enumerate(PdfReader(PDF).pages, 1):
    lines = [l.strip() for l in (page.extract_text() or "").split("\n") if l.strip()]
    # drop the footer, which is always the running head and the page number
    body = [l for l in lines if "P a g e" not in l]
    if body and HEAD.match(body[-1]):
        bad.append((i, body[-1][:60]))
print("orphaned headings:", len(bad))
for pg, h in bad:
    print(f"  p{pg}: {h}")
sys.exit(1 if bad else 0)
