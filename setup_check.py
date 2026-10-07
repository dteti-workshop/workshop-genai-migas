"""Cek kesiapan laptop peserta. Jalankan dari root repo:

    python setup_check.py            # cek lengkap (termasuk panggilan API & unduh model embedding)
    python setup_check.py --offline  # lewati cek yang butuh internet
"""
from __future__ import annotations

import importlib
import sys
import time
from pathlib import Path

OFFLINE = "--offline" in sys.argv
ROOT = Path(__file__).resolve().parent
ok_all = True


def check(name: str, fn, hint: str = "") -> None:
    global ok_all
    t0 = time.perf_counter()
    try:
        info = fn() or ""
        print(f"  [OK]   {name} {info} ({time.perf_counter() - t0:.1f}s)")
    except Exception as e:  # noqa: BLE001
        ok_all = False
        print(f"  [GAGAL] {name}: {type(e).__name__}: {str(e)[:200]}")
        if hint:
            print(f"          -> {hint}")


print("\n== 1. Python dan paket")


def _py():
    v = sys.version_info
    if v < (3, 10):
        raise RuntimeError(f"Python {v.major}.{v.minor} terlalu lama")
    return f"Python {v.major}.{v.minor}.{v.micro} di {sys.executable}"


check("Versi Python >= 3.10", _py, "Pasang Python 3.11 atau 3.12 (Unit 1 Langkah 1)")
for pkg in ["openai", "dotenv", "pydantic", "pandas", "matplotlib", "streamlit", "langchain_core", "langchain_openai",
            "langchain_community", "langchain_text_splitters", "langchain_chroma", "chromadb", "fastembed", "rank_bm25",
            "pypdf", "yaml", "common"]:
    check(f"import {pkg}", lambda p=pkg: getattr(importlib.import_module(p), "__version__", ""),
          "Aktifkan virtual environment, kemudian jalankan: pip install -r requirements.txt")

print("\n== 2. Konfigurasi .env")


def _env():
    if not (ROOT / ".env").exists():
        raise FileNotFoundError(".env belum ada")
    from common import config

    p = config.get_profile()
    if not p.api_key or "isi-dengan" in p.api_key:
        raise ValueError(f"{p.name.upper()}_API_KEY belum diisi")
    return f"profil={p.name}, model={p.model}, API key terisi"


check("File .env dan API key", _env, "Salin .env.example menjadi .env, kemudian isi API key (Unit 1 Langkah 5)")


def _data():
    need = ["data/raw/work_orders.csv", "data/raw/hse_incidents.csv", "data/docs/sop/SOP-HSE-001_rev3_H2S.md",
            "data/docs/manual/MAN-VSD-FD500.pdf", "data/eval/rag_golden_set.jsonl"]
    missing = [n for n in need if not (ROOT / n).exists()]
    if missing:
        raise FileNotFoundError(missing)
    return "data lengkap"


check("Data workshop", _data, "Lakukan clone ulang repository")

if not OFFLINE:
    print("\n== 3. Koneksi (memerlukan internet)")

    def _llm():
        from common.llm import chat

        out = chat("Balas hanya dengan kata: SIAP", max_tokens=5, use_cache=False)
        return f"jawaban model: {out.strip()!r}"

    check("Pemanggilan LLM", _llm, "Periksa API key dan koneksi internet (Lampiran A pada labsheet)")

    def _emb():
        from common.embeddings import get_embeddings

        v = get_embeddings().embed_query("uji embedding")
        return f"dimensi {len(v)}"

    check("Model embedding (unduhan pertama sekitar 220 MB)", _emb,
          "Salin folder models/ dari instruktur ke folder repository (Lampiran A pada labsheet)")

print("\n" + ("Seluruh pemeriksaan berhasil. Environment siap digunakan." if ok_all
               else "Terdapat pemeriksaan yang GAGAL. Ikuti petunjuk pada baris tersebut atau lihat Lampiran A pada labsheet."))
sys.exit(0 if ok_all else 1)
