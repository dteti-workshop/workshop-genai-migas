"""Render dokumen sumber Markdown sederhana di scripts/pdf_src/ menjadi PDF di data/docs/manual/.

Metadata (frontmatter) disimpan sebagai file pendamping <nama>.meta.json, karena
PDF di dunia nyata biasanya tidak membawa metadata yang rapi.

Jalankan: python scripts/build_pdfs.py   (butuh: pip install fpdf2)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "scripts" / "pdf_src"
OUT = ROOT / "data" / "docs" / "manual"


def split_frontmatter(text: str) -> tuple[dict, str]:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        meta[k.strip()] = v.strip().strip('"')
    return meta, text[m.end():]


class Doc(FPDF):
    title_text = ""

    def header(self):
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 6, self.title_text, align="R", new_x="LMARGIN", new_y="NEXT")

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 6, f"Halaman {self.page_no()}  |  Dokumen fiktif untuk pelatihan", align="C")


def render(md_path: Path) -> None:
    meta, body = split_frontmatter(md_path.read_text(encoding="utf-8"))
    pdf = Doc(format="A4")
    pdf.title_text = f"{meta.get('doc_id', '')} Rev. {meta.get('revision', '')}"
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()
    lines = body.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if line.startswith("|"):  # tabel markdown
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip("|").split("|")]
                if not set("".join(cells)) <= set("-: "):
                    rows.append(cells)
                i += 1
            pdf.set_font("Helvetica", size=7.5)
            with pdf.table(col_widths=(10, 22, 40, 48, 18), line_height=4) as table:
                for r in rows:
                    row = table.row()
                    for c in r:
                        row.cell(c)
            pdf.ln(3)
            continue
        if line.startswith("# "):
            pdf.set_font("Helvetica", "B", 15)
            pdf.multi_cell(0, 8, line[2:], new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
        elif line.startswith("## "):
            pdf.set_font("Helvetica", "B", 12)
            pdf.ln(2)
            pdf.multi_cell(0, 7, line[3:], new_x="LMARGIN", new_y="NEXT")
        elif line.strip():
            pdf.set_font("Helvetica", size=10)
            pdf.multi_cell(0, 5, line, new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.ln(2)
        i += 1
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{md_path.stem}.pdf"
    pdf.output(str(out))
    (OUT / f"{md_path.stem}.meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  tulis {out.relative_to(ROOT)} ({pdf.page_no()} halaman)")


if __name__ == "__main__":
    for p in sorted(SRC.glob("*.md")):
        render(p)
