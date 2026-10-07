"""Buat kode starter peserta dari kode solusi.

Blok di kode solusi yang ditandai:
    # >>> TODO(T2.4): petunjuk singkat
    ... kode solusi ...
    # <<<
diganti menjadi komentar TODO + kerangka minimal (lihat fungsi `placeholder`):
- assignment     -> `NAMA = None`
- def / class    -> signature dipertahankan, isi diganti raise NotImplementedError / pass
- lainnya        -> raise NotImplementedError("TODO(...)")

Placeholder kustom (mis. agar modul tetap bisa di-import) ditulis di baris pembuka:
    # >>> TODO(L3.1): petunjuk || placeholder: RAG_SYSTEM = "Jawab berdasarkan konteks."

Jalankan:  python scripts/make_starter.py
Output  :  hari1/ dan hari2/ (ditimpa). Folder solutions/ tidak berubah.

Untuk distribusi GitHub disarankan: branch `main` berisi starter (tanpa folder solutions/),
branch `solutions` berisi semuanya. Lihat README bagian "Untuk instruktur".
"""
from __future__ import annotations

import ast
import re
import shutil
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPEN = re.compile(r"^(?P<ind>\s*)# >>> (?P<tag>TODO\([^)]*\)):?\s*(?P<hint>.*)$")
CLOSE = re.compile(r"^\s*# <<<\s*$")


def placeholder(body: list[str], ind: str, tag: str) -> list[str]:
    """Kerangka pengganti blok solusi.

    - Blok berisi hanya assignment/def/class: pertahankan nama variabel (= None), signature fungsi
      (isi diganti raise NotImplementedError), dan header class (isi diganti pass).
    - Selain itu: satu baris raise NotImplementedError.
    """
    raise_line = [f'{ind}raise NotImplementedError("{tag}")']
    code = textwrap.dedent("\n".join(body))
    try:
        tree = ast.parse(code)
    except SyntaxError:  # mis. blok berisi 'return' di dalam fungsi
        return raise_line
    if not tree.body or not all(isinstance(n, (ast.Assign, ast.AnnAssign, ast.FunctionDef, ast.ClassDef)) for n in tree.body):
        return raise_line
    src = code.splitlines()
    out: list[str] = []
    for n in tree.body:
        if isinstance(n, (ast.Assign, ast.AnnAssign)):
            targets = n.targets if isinstance(n, ast.Assign) else [n.target]
            for t in targets:
                for nm in ([t] if isinstance(t, ast.Name) else getattr(t, "elts", [])):
                    if isinstance(nm, ast.Name):
                        out.append(f"{ind}{nm.id} = None  # TODO: ganti dengan implementasi Anda")
        else:
            header = src[n.lineno - 1 : n.body[0].lineno - 1]
            out += [ind + h for h in header]
            if isinstance(n, ast.FunctionDef):
                out.append(f'{ind}    raise NotImplementedError("{tag}")')
            else:
                out.append(f"{ind}    pass  # TODO: definisikan field")
            out.append("")
    return out


def transform(src: str) -> tuple[str, int]:
    out: list[str] = []
    lines = src.splitlines()
    i, n_blocks = 0, 0
    while i < len(lines):
        m = OPEN.match(lines[i])
        if not m:
            out.append(lines[i])
            i += 1
            continue
        ind, tag, hint = m.group("ind"), m.group("tag"), m.group("hint")
        j = i + 1
        while j < len(lines) and not CLOSE.match(lines[j]):
            j += 1
        hint, _, custom = hint.partition(" || placeholder: ")
        out.append(f"{ind}# {tag}: {hint}")
        out += [f"{ind}{custom}  # TODO: ganti dengan implementasi Anda"] if custom else placeholder(lines[i + 1 : j], ind, tag)
        n_blocks += 1
        i = j + 1
    return "\n".join(out) + "\n", n_blocks


def main() -> None:
    for day in ("hari1", "hari2"):
        src_dir, dst_dir = ROOT / "solutions" / day, ROOT / day
        if dst_dir.exists():
            shutil.rmtree(dst_dir)
        dst_dir.mkdir()
        for p in sorted(src_dir.glob("*.py")):
            text, n = transform(p.read_text(encoding="utf-8"))
            (dst_dir / p.name).write_text(text, encoding="utf-8")
            print(f"  {day}/{p.name}: {n} blok TODO")


if __name__ == "__main__":
    main()
