"""Kembalikan knowledge base ke kondisi awal workshop.

Memindahkan (bukan menghapus) data/docs/uploads/ dan chroma_db/ ke .backup_reset/<waktu>/.
Index akan dibangun ulang otomatis saat lab/aplikasi dijalankan berikutnya.

Jalankan: python scripts/reset_knowledge.py
"""
import shutil
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
targets = [ROOT / "data" / "docs" / "uploads", ROOT / "chroma_db"]
existing = [t for t in targets if t.exists()]
if not existing:
    print("Tidak ada yang perlu di-reset.")
else:
    print("Akan dipindahkan:", *[f"  {t.relative_to(ROOT)}" for t in existing], sep="\n")
    if input("Lanjutkan? (y/N) ").strip().lower() == "y":
        dest = ROOT / ".backup_reset" / time.strftime("%Y%m%d-%H%M%S")
        dest.mkdir(parents=True)
        for t in existing:
            shutil.move(str(t), str(dest / t.name))
        print(f"Selesai. Cadangan di {dest.relative_to(ROOT)}. Hentikan & jalankan ulang Streamlit bila sedang berjalan.")
