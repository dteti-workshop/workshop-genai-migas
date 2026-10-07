# %% [markdown]
# # Unit 3 - Struktur Prompt dan Output JSON
# Kasus: ringkasan mingguan laporan harian operasi GS-SR1 (14 sampai 20 Juli 2026).

# %%
# Langkah 1 - Memuat data
import json
import re

import pandas as pd

from common.config import DATA
from common.llm import chat, parse_json, usage_summary

laporan = (DATA / "raw" / "daily_reports" / "GS-SR1_2026-07.md").read_text(encoding="utf-8")
awal, akhir = laporan.index("## Selasa, 14 Juli 2026"), laporan.index("## Selasa, 21 Juli 2026")
minggu = laporan[awal:akhir]

acuan = pd.read_csv(DATA / "eval" / "daily_gs_sr1_2026-07.csv")
acuan = acuan[acuan["tanggal"].between("2026-07-14", "2026-07-20")].reset_index(drop=True)

print(minggu[:560], "...")
print(f"\nPanjang laporan satu minggu: {len(minggu):,} karakter")
print(acuan[["tanggal", "oil_bopd", "wells_on", "deferred_bbl"]].to_string(index=False))

# %% [markdown]
# ## Langkah 2 - Prompt tanpa struktur

# %%
ringkasan_a = chat(f"Rangkum laporan ini:\n{minggu}")
print(ringkasan_a)
print(f"\n({len(ringkasan_a.split())} kata)")

# %% [markdown]
# ## Langkah 3 - Prompt terstruktur untuk Manajer Area

# %%
def build_prompt(role: str, context: str, task: str, output_format: str, data: str):
    """Susun system message dan user message dari lima komponen prompt."""
    system = f"{role}\n{context}"
    user = f"{task}\n\nFormat output:\n{output_format}\n\n<laporan>\n{data}\n</laporan>"
    return system, user


# TODO(U3.3): isi empat komponen prompt untuk pembaca Manajer Area
ROLE_MGR = None  # TODO: ganti dengan implementasi Anda
CONTEXT_MGR = None  # TODO: ganti dengan implementasi Anda
TASK_MGR = None  # TODO: ganti dengan implementasi Anda
FORMAT_MGR = None  # TODO: ganti dengan implementasi Anda
system, user = build_prompt(ROLE_MGR, CONTEXT_MGR, TASK_MGR, FORMAT_MGR, minggu)
ringkasan_b = chat(user, system=system)
print(ringkasan_b)
print(f"\n({len(ringkasan_b.split())} kata)")

# %% [markdown]
# ## Langkah 4 - Mengganti pembaca

# %%
# TODO(U3.4): isi komponen prompt untuk pembaca Shift Supervisor yang menerima serah terima shift
ROLE_SPV = None  # TODO: ganti dengan implementasi Anda
CONTEXT_SPV = None  # TODO: ganti dengan implementasi Anda
TASK_SPV = None  # TODO: ganti dengan implementasi Anda
FORMAT_SPV = None  # TODO: ganti dengan implementasi Anda
system, user = build_prompt(ROLE_SPV, CONTEXT_SPV, TASK_SPV, FORMAT_SPV, minggu)
ringkasan_c = chat(user, system=system)
print(ringkasan_c)

# %% [markdown]
# ## Langkah 5 - Memeriksa angka pada ringkasan dengan kode

# %%
ANGKA = re.compile(r"\d+(?:[.,]\d+)*")


def kumpulan_angka(teks: str) -> set[str]:
    """Seluruh angka pada teks. Nomor urut daftar diabaikan, titik pemisah ribuan dihapus."""
    teks = re.sub(r"(?m)^\s*\d+\.\s+", "", teks)  # nomor urut daftar, contoh "2. "
    return {re.sub(r"\.(?=\d{3}(?!\d))", "", a) for a in ANGKA.findall(teks)}


def angka_tanpa_sumber(ringkasan: str, sumber: str) -> list[str]:
    """Angka pada ringkasan yang tidak tercantum pada teks sumber."""
    # TODO(U3.5): kembalikan daftar terurut berisi angka pada ringkasan yang tidak ada pada sumber
    raise NotImplementedError("TODO(U3.5)")


for nama, teks in (("Tanpa struktur", ringkasan_a), ("Manajer Area", ringkasan_b), ("Shift Supervisor", ringkasan_c)):
    print(f"{nama:17s}: {angka_tanpa_sumber(teks, minggu)}")

print("\nNilai acuan (dihitung dengan pandas):")
print("  Rata-rata produksi minyak :", round(acuan["oil_bopd"].mean()), "bopd")
print("  Produksi minyak terendah  :", acuan["oil_bopd"].min(), "bopd pada", acuan.loc[acuan["oil_bopd"].idxmin(), "tanggal"])
print("  Total deferred production :", acuan["deferred_bbl"].sum(), "bbl")

# %% [markdown]
# ## Langkah 6 - Output JSON dan perhitungan dengan pandas

# %%
# TODO(U3.6): tulis PROMPT_JSON yang meminta satu objek per hari sesuai schema pada labsheet
PROMPT_JSON = None  # TODO: ganti dengan implementasi Anda
data = parse_json(chat(PROMPT_JSON, json_mode=True))
harian = pd.DataFrame(data["hari"])
print(harian.to_string(index=False))

# %%
# Membandingkan hasil extraction dengan data acuan, lalu menghitung dengan pandas
gabung = harian.merge(acuan, on="tanggal", suffixes=("_llm", ""))
for kolom in ("oil_bopd", "wells_on", "deferred_bbl"):
    sesuai = int((gabung[f"{kolom}_llm"] == gabung[kolom]).sum())
    print(f"{kolom:13s}: {sesuai} dari {len(acuan)} hari sesuai dengan data acuan")

terendah = harian.loc[harian["oil_bopd"].idxmin()]
statistik = {
    "periode": "14 sampai 20 Juli 2026",
    "rata_rata_oil_bopd": round(harian["oil_bopd"].mean()),
    "oil_terendah_bopd": int(terendah["oil_bopd"]),
    "tanggal_oil_terendah": terendah["tanggal"],
    "total_deferred_bbl": int(harian["deferred_bbl"].sum()),
    "kejadian": harian.loc[harian["deferred_bbl"] > 0, ["tanggal", "aset", "kejadian", "deferred_bbl"]].to_dict("records"),
}
print(json.dumps(statistik, indent=2, ensure_ascii=False))

# %% [markdown]
# ## Langkah 7 - Ringkasan dari angka hasil perhitungan

# %%
# TODO(U3.7): susun TASK_STAT yang meminta ringkasan hanya berdasarkan statistik pada bagian <laporan>
TASK_STAT = None  # TODO: ganti dengan implementasi Anda
system, user = build_prompt(ROLE_MGR, CONTEXT_MGR, TASK_STAT, FORMAT_MGR, json.dumps(statistik, indent=2, ensure_ascii=False))
ringkasan_d = chat(user, system=system)
print(ringkasan_d)
print("\nAngka tanpa sumber:", angka_tanpa_sumber(ringkasan_d, json.dumps(statistik, ensure_ascii=False)))

# %%
print(usage_summary())
