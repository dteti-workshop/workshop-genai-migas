# %% [markdown]
# # Unit 7 - Analisis Dokumen Panjang
# Laporan harian 31 hari dimasukkan seluruhnya ke dalam prompt, kemudian diuji dengan pertanyaan fakta
# dan pertanyaan agregasi. Setelah itu agregasi dikerjakan dengan pembagian tugas antara LLM dan kode.

# %%
# Langkah 1 - Memuat dokumen dan mengukur ukurannya
import re

import pandas as pd

from common.config import DATA
from common.llm import chat, chat_detail, parse_json, run_parallel, usage_summary

laporan = (DATA / "raw" / "daily_reports" / "GS-SR1_2026-07.md").read_text(encoding="utf-8")
acuan = pd.read_csv(DATA / "eval" / "daily_gs_sr1_2026-07.csv")

SYSTEM_QA = ("Jawab pertanyaan hanya berdasarkan laporan pada bagian <laporan>. Jika informasi tidak "
             "tercantum, jawab bahwa informasi tidak ditemukan. Jawab singkat.")


def ask(pertanyaan: str, reasoning: str = "none"):
    """Kirim seluruh laporan beserta satu pertanyaan. Kembalikan ChatResult."""
    return chat_detail(f"<laporan>\n{laporan}\n</laporan>\n\nPertanyaan: {pertanyaan}",
                       system=SYSTEM_QA, reasoning=reasoning)


def ringkas(teks: str, n: int = 110) -> str:
    return " ".join(teks.split())[:n]


r = ask("Laporan ini mencakup periode apa?")
print(f"Panjang laporan : {len(laporan):,} karakter, {laporan.count('## ')} hari")
print(f"Input tokens    : {r.prompt_tokens:,} untuk satu pertanyaan")
print(f"Jawaban         : {ringkas(r.text)}")

# %% [markdown]
# ## Langkah 2 - Pertanyaan fakta

# %%
FAKTA = {  # pertanyaan -> jawaban menurut laporan
    "Pada tanggal berapa terdeteksi H2S dan berapa konsentrasinya?": "22 Juli, 12 ppm",
    "Siapa supervisor shift pada 14 Juli 2026?": "Hendra Saputra",
    "Apa temuan audit internal HSE pada bulan ini?": "2 fire extinguisher kedaluwarsa",
    "Berapa tekanan discharge pompa transfer pada 5 Juli?": "(tidak tercantum pada laporan)",
}
for pertanyaan, kunci in FAKTA.items():
    print(f"Pertanyaan: {pertanyaan}\n  LLM  : {ringkas(ask(pertanyaan).text)}\n  Kunci: {kunci}")

# %% [markdown]
# ## Langkah 3 - Pertanyaan agregasi

# %%
terendah = acuan.loc[acuan["oil_bopd"].idxmin()]
AGREGASI = {  # pertanyaan -> kunci yang dihitung dengan pandas dari data acuan
    "Berapa total deferred production selama Juli 2026 dalam barel?": int(acuan["deferred_bbl"].sum()),
    "Berapa rata-rata produksi minyak harian selama Juli 2026 dalam bopd? Bulatkan.": round(acuan["oil_bopd"].mean()),
    "Berapa hari jumlah sumur aktif kurang dari 54?": int((acuan["wells_on"] < 54).sum()),
    "Berapa hari yang memiliki deferred production?": int((acuan["deferred_bbl"] > 0).sum()),
}


def angka_jawaban(teks: str) -> float | None:
    """Angka pertama pada jawaban, dengan titik pemisah ribuan dihapus."""
    m = re.search(r"\d+(?:[.,]\d+)*", teks.replace("**", ""))
    return float(re.sub(r"\.(?=\d{3}(?!\d))", "", m.group()).replace(",", ".")) if m else None


baris = []
for pertanyaan, kunci in AGREGASI.items():
    # TODO(U7.3): panggil ask() dengan reasoning "none" dan "high", simpan pada variabel a dan b
    a = None  # TODO: ganti dengan implementasi Anda
    b = None  # TODO: ganti dengan implementasi Anda
    baris.append({"pertanyaan": pertanyaan[:45], "kunci": kunci,
                  "tanpa_reasoning": angka_jawaban(a.text), "reasoning_high": angka_jawaban(b.text),
                  "detik": f"{a.latency_s:.0f} / {b.latency_s:.0f}",
                  "reasoning_tokens": b.reasoning_tokens})
tabel = pd.DataFrame(baris)
print(tabel.to_string(index=False))
print(f"\nBenar tanpa reasoning: {(tabel['tanpa_reasoning'] == tabel['kunci']).sum()} dari {len(tabel)} | "
      f"dengan reasoning: {(tabel['reasoning_high'] == tabel['kunci']).sum()} dari {len(tabel)}")

# %% [markdown]
# ## Langkah 4 - Extraction per bagian dan perhitungan dengan pandas

# %%
hari = re.split(r"\n(?=## )", laporan)[1:]
bagian = ["\n".join(hari[i : i + 7]) for i in range(0, len(hari), 7)]
print(f"{len(hari)} hari dibagi menjadi {len(bagian)} bagian, masing-masing paling banyak 7 hari")

# TODO(U7.4): tulis prompt EXTRACT_HARIAN dan fungsi extract_bagian yang mengembalikan list of dict
EXTRACT_HARIAN = None  # TODO: ganti dengan implementasi Anda
BENTUK_LAIN = None  # TODO: ganti dengan implementasi Anda
def extract_bagian(teks: str) -> list[dict]:
    raise NotImplementedError("TODO(U7.4)")



hasil = run_parallel(extract_bagian, bagian, desc="Extraction")
harian = pd.DataFrame([d for h in hasil if isinstance(h, list) for d in h]).sort_values("tanggal")
print(f"Hasil extraction: {len(harian)} dari {len(hari)} hari | "
      f"bagian dengan bentuk JSON berbeda dari yang diminta: {len(BENTUK_LAIN)}")
assert len(harian) == len(hari), "Jumlah hari tidak lengkap, periksa hasil extraction sebelum menghitung"
gabung = harian.merge(acuan, on="tanggal", suffixes=("_llm", ""))
for kolom in ("oil_bopd", "water_bwpd", "wells_on", "deferred_bbl"):
    print(f"{kolom:13s}: {(gabung[f'{kolom}_llm'] == gabung[kolom]).sum()} dari {len(acuan)} hari sesuai")

print("\nJawaban dari hasil extraction, dihitung dengan pandas:")
print("  Total deferred production :", harian["deferred_bbl"].sum(), "bbl")
print("  Rata-rata produksi minyak :", round(harian["oil_bopd"].mean()), "bopd")
print("  Hari dengan sumur aktif kurang dari 54 :", int((harian["wells_on"] < 54).sum()))
print("  Hari dengan deferred production :", int((harian["deferred_bbl"] > 0).sum()))

# %% [markdown]
# ## Langkah 5 - Biaya pengiriman dokumen pada setiap pertanyaan

# %%
r = ask("Siapa supervisor shift pada 14 Juli 2026?")
print(f"Satu pertanyaan dengan seluruh laporan: {r.prompt_tokens:,} input tokens, USD {r.cost_usd:.6f}")
# TODO(U7.5): hitung input tokens dan biaya untuk 100 pertanyaan pada 1, 12, dan 120 laporan bulanan
raise NotImplementedError("TODO(U7.5)")

# %%
print(usage_summary())
