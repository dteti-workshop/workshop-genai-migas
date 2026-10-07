# %% [markdown]
# # Unit 5 - Klasifikasi Laporan Insiden HSE
# Prompt diperlakukan seperti model: terdapat data uji berlabel, metric, dan perbaikan bertahap.

# %%
# Langkah 1 - Memuat data dan memisahkan data uji
import pandas as pd

from common import llm
from common.data import load_hse
from common.llm import chat, parse_json, run_parallel, usage_summary

uji, pool = load_hse()
print(f"Data uji: {len(uji)} laporan | pool: {len(pool)} laporan\n")
print(pd.DataFrame({"uji": uji["incident_type"].value_counts(), "pool": pool["incident_type"].value_counts()}))
print(f"\nContoh laporan:\n{uji['narasi'].iloc[0]}")

TYPES = ["Near Miss", "First Aid Case", "Medical Treatment Case", "Lost Time Injury",
         "Property Damage", "Environmental Spill"]
HAZARDS = ["H2S/Gas", "Hot Work/Fire", "Working at Height", "Dropped Object", "Vehicle/Driving",
           "Steam/Hot Surface", "Electrical", "Manual Handling", "Pinch Point", "Spill/Release"]
SINGKAT = {"Near Miss": "NM", "First Aid Case": "FAC", "Medical Treatment Case": "MTC",
           "Lost Time Injury": "LTI", "Property Damage": "PD", "Environmental Spill": "SPILL"}
HASIL: dict[str, dict] = {}


def classify_all(system: str, data: pd.DataFrame, few_shot: list[dict] | None = None,
                 temperature: float = 0.0) -> pd.DataFrame:
    """Klasifikasikan setiap laporan pada `data`. Kembalikan data beserta kolom prediksi."""
    def one(narasi: str) -> dict:
        pesan = (few_shot or []) + [{"role": "user", "content": f"<insiden>{narasi}</insiden>"}]
        out = parse_json(chat(pesan, system=system, json_mode=True, temperature=temperature,
                              use_cache=temperature == 0))
        return {"incident_type_pred": out.get("incident_type"), "hazard_pred": out.get("hazard")}

    res = run_parallel(one, data["narasi"], desc="Klasifikasi")
    res = [r if isinstance(r, dict) else {"incident_type_pred": "ERROR", "hazard_pred": "ERROR"} for r in res]
    return pd.concat([data.reset_index(drop=True), pd.DataFrame(res)], axis=1)


def report(nama: str, system: str, few_shot: list[dict] | None = None) -> pd.DataFrame:
    """Jalankan satu versi prompt pada data uji, tampilkan accuracy dan confusion matrix."""
    tok0 = llm.USAGE.prompt_tokens
    r = classify_all(system, uji, few_shot)
    acc = (r["incident_type_pred"] == r["incident_type"]).mean()
    HASIL[nama] = {"incident_type": f"{acc:.1%}", "hazard": f"{(r['hazard_pred'] == r['hazard']).mean():.1%}",
                   "input_tokens": llm.USAGE.prompt_tokens - tok0}
    print(f"{nama}: incident_type sesuai {acc:.1%} | hazard sesuai {HASIL[nama]['hazard']}\n")
    cm = pd.crosstab(r["incident_type"], r["incident_type_pred"].map(SINGKAT).fillna("lain"),
                     rownames=["label acuan"], colnames=["prediksi"])
    print(cm.reindex(index=TYPES, columns=[*SINGKAT.values(), "lain"], fill_value=0).loc[:, lambda d: d.sum() > 0])
    return r


# %% [markdown]
# ## Langkah 2 - Zero-shot dengan nama label

# %%
SYSTEM_ZERO = f"""Klasifikasikan laporan insiden HSE.
incident_type adalah salah satu dari: {TYPES}
hazard adalah salah satu dari: {HAZARDS}
Kembalikan hanya JSON: {{"incident_type": "...", "hazard": "..."}}"""
r_zero = report("Zero-shot", SYSTEM_ZERO)

# %% [markdown]
# ## Langkah 3 - Definisi operasional

# %%
# TODO(U5.3): tulis SYSTEM_GUIDE berisi definisi operasional setiap incident_type dan urutan pemeriksaannya
SYSTEM_GUIDE = None  # TODO: ganti dengan implementasi Anda
r_guide = report("Definisi operasional", SYSTEM_GUIDE)

# %% [markdown]
# ## Langkah 4 - Few-shot

# %%
# TODO(U5.4): susun FEW_SHOT berisi satu contoh untuk setiap incident_type, diambil dari pool
raise NotImplementedError("TODO(U5.4)")
r_few = report("Definisi operasional + few-shot", SYSTEM_GUIDE, FEW_SHOT)

print("\nPerbandingan ketiga versi prompt:")
print(pd.DataFrame(HASIL).T.to_string())

# %% [markdown]
# ## Langkah 5 - Recall pada label kritis dan severity dengan kode

# %%
for nama, r in (("Zero-shot", r_zero), ("Definisi operasional", r_guide)):
    for label in ("Lost Time Injury", "Environmental Spill"):
        sub = r[r["incident_type"] == label]
        print(f"{nama:21s} recall {label:19s}: {(sub['incident_type_pred'] == label).sum()} dari {len(sub)}")

# TODO(U5.5): buat mapping SEVERITY, lalu hitung kolom severity_pred dari incident_type_pred
SEVERITY = None  # TODO: ganti dengan implementasi Anda
print(f"\nSeverity sesuai: {(r_guide['severity_pred'] == r_guide['severity']).mean():.1%}")

# %% [markdown]
# ## Langkah 6 - Self-consistency sebagai sinyal review

# %%
def self_consistency(nama: str, system: str, n: int = 3) -> pd.DataFrame:
    """Jalankan prompt n kali pada temperature 0,7, lalu bandingkan jawaban setiap laporan."""
    runs = [classify_all(system, uji, temperature=0.7)["incident_type_pred"] for _ in range(n)]
    votes = pd.concat(runs, axis=1, keys=[f"run{i + 1}" for i in range(n)])
    # TODO(U5.6): hitung kolom mayoritas (jawaban terbanyak) dan sepakat (True jika semua jawaban sama)
    votes["acuan"] = uji["incident_type"].values
    votes["benar"] = votes["mayoritas"] == votes["acuan"]
    ya, tidak = votes[votes["sepakat"]], votes[~votes["sepakat"]]
    print(f"{nama}")
    print(f"  jawaban sepakat       : {len(ya):2d} laporan, mayoritas benar {ya['benar'].sum()}")
    print(f"  jawaban tidak sepakat : {len(tidak):2d} laporan, mayoritas benar {tidak['benar'].sum()}")
    return votes


v_zero = self_consistency("Zero-shot", SYSTEM_ZERO)
v_guide = self_consistency("Definisi operasional", SYSTEM_GUIDE)
print("\nLaporan dengan jawaban tidak sepakat pada zero-shot:")
print(v_zero[~v_zero["sepakat"]].drop(columns=["mayoritas", "sepakat", "benar"]).replace(SINGKAT).to_string())

# %% [markdown]
# ## Langkah 7 - Sensitivitas terhadap format prompt

# %%
# TODO(U5.7): buat tiga variasi format SYSTEM_GUIDE dengan isi yang sama
VARIAN = None  # TODO: ganti dengan implementasi Anda
for nama, prompt in VARIAN.items():
    r = classify_all(prompt, uji)
    persis = (r["incident_type_pred"] == r["incident_type"]).mean()
    makna = (r["incident_type_pred"].str.upper() == r["incident_type"].str.upper()).mean()
    print(f"{nama:16s}: label benar {makna:.1%} | penulisan label sama persis {persis:.1%} | "
          f"contoh output: {r['incident_type_pred'].iloc[0]}")

print("\nOutput mentah varian huruf kapital:")
print(chat(f"<insiden>{uji['narasi'].iloc[0]}</insiden>", system=VARIAN["huruf kapital"], json_mode=True))

# %%
print(usage_summary())
