# %% [markdown]
# # Unit 4 - Extraction Work Order
# Pipeline: teks work order -> LLM (extraction dan validasi schema) -> tabel -> pandas -> insight.
# Prinsip: LLM membaca dan menstrukturkan teks, kode menghitung.

# %%
# Langkah 1 - Memuat data
import re
import time
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field, ValidationError, field_validator

from common import llm
from common.config import DATA, OUTPUTS
from common.llm import chat, parse_json, run_parallel, usage_summary

wo = pd.read_csv(DATA / "raw" / "work_orders.csv")
truth = pd.read_csv(DATA / "eval" / "work_orders_truth.csv")
print(f"Jumlah work order: {len(wo)} | kolom: {list(wo.columns)}\n")
for r in wo.sample(4, random_state=1).itertuples():
    print(f"{r.wo_id} | {r.area} | {r.deskripsi}")

# %% [markdown]
# ## Langkah 2 - Baseline dengan aturan kata kunci

# %%
def rule_based(desc: str) -> dict:
    """Baseline tanpa LLM: kategori dari kata kunci, downtime dari pola '<angka> jam'."""
    d = desc.lower()
    if "pm " in d or d.startswith("pm"):
        cat = "Preventive Maintenance"
    elif any(k in d for k in ["bocor", "leak", "rembes"]):
        cat = "Leak/Corrosion"
    elif any(k in d for k in ["kabel", "motor", "megger"]):
        cat = "Electrical"
    elif any(k in d for k in ["pasir", "wax", "parafin", "buntu"]):
        cat = "Flow Assurance"
    elif any(k in d for k in ["underload", "ul ", "suction"]):
        cat = "Process/Trip"
    elif any(k in d for k in ["level", "scanner", "vsd"]):
        cat = "Instrumentation/Control"
    else:
        cat = "Mechanical"
    m = re.search(r"(\d+[.,]?\d*)\s*jam", d)
    dt = float(m.group(1).replace(",", ".")) if m else None
    return {"failure_category": cat, "downtime_hours": dt}


base = pd.concat([wo[["wo_id", "deskripsi"]], wo["deskripsi"].apply(rule_based).apply(pd.Series)], axis=1)
base = base.merge(truth, on="wo_id", suffixes=("_pred", ""))
acc_cat = (base["failure_category_pred"] == base["failure_category"]).mean()
acc_dt = (base["downtime_hours_pred"].sub(base["downtime_hours"]).abs() <= 0.5).mean()
print(f"Baseline pada {len(base)} work order")
print(f"  failure_category sesuai : {acc_cat:.1%}")
print(f"  downtime_hours sesuai   : {acc_dt:.1%} (toleransi 0,5 jam)\n")
salah = base[base["failure_category_pred"] != base["failure_category"]]
for r in salah.head(3).itertuples():
    print(f"{r.wo_id}: {r.deskripsi}\n  baseline: {r.failure_category_pred} | acuan: {r.failure_category}")

# %% [markdown]
# ## Langkah 3 - Schema output dengan Pydantic

# %%
EquipmentType = Literal["ESP", "SRP", "PCP", "Steam Generator", "Flowline", "Separator",
                        "Gas Compressor", "Water Injection Pump"]
FailureCategory = Literal["Electrical", "Mechanical", "Leak/Corrosion", "Flow Assurance",
                          "Instrumentation/Control", "Process/Trip", "Preventive Maintenance"]
ActionCategory = Literal["Replace", "Repair", "Clean/Flush", "Adjust/Reset", "Workover"]


# TODO(U4.3): lengkapi field schema WOExtract sesuai tabel pada labsheet
class WOExtract(BaseModel):
    pass  # TODO: definisikan field



print(list(WOExtract.model_json_schema()["properties"]))

# %% [markdown]
# ## Langkah 4 - Prompt extraction

# %%
# TODO(U4.4): tulis SYSTEM_V1 berisi definisi failure_category, aturan downtime, safety_flag, dan format JSON
SYSTEM_V1 = None  # TODO: ganti dengan implementasi Anda

contoh = wo.iloc[3]
print(contoh["deskripsi"])
print(chat(f"<wo>{contoh['deskripsi']}</wo>", system=SYSTEM_V1, json_mode=True))

# %% [markdown]
# ## Langkah 5 - Extraction dengan validasi dan self-repair

# %%
def extract_one(desc: str, system: str, max_repair: int = 2) -> dict:
    """Extraction satu work order. Output divalidasi; jika tidak valid, model diminta memperbaiki."""
    messages = [{"role": "user", "content": f"<wo>{desc}</wo>"}]
    # TODO(U4.5): panggil chat, validasi dengan WOExtract, kirim pesan error ke model jika tidak valid
    raise NotImplementedError("TODO(U4.5)")


print(wo.iloc[10]["deskripsi"])
print(extract_one(wo.iloc[10]["deskripsi"], SYSTEM_V1))

# %% [markdown]
# ## Langkah 6 - Extraction pada 60 work order dan evaluasi

# %%
FIELDS = ["asset_id", "equipment_type", "failure_category", "action_category", "safety_flag"]


def run_extraction(rows: pd.DataFrame, system: str, desc: str) -> pd.DataFrame:
    """Jalankan extract_one secara paralel, kembalikan DataFrame hasil yang valid beserta wo_id."""
    hasil = run_parallel(lambda d: extract_one(d, system), rows["deskripsi"], desc=desc)
    valid = [isinstance(h, dict) for h in hasil]
    pred = pd.DataFrame([h for h in hasil if isinstance(h, dict)])
    pred.insert(0, "wo_id", rows.loc[valid, "wo_id"].values)
    print(f"Valid: {sum(valid)} dari {len(valid)} | memerlukan self-repair: {(pred['_repairs'] > 0).sum()}")
    return pred


def evaluate(pred: pd.DataFrame) -> pd.DataFrame:
    """Kesesuaian setiap field terhadap label acuan."""
    m = pred.merge(truth, on="wo_id", suffixes=("_pred", ""))
    rows = [{"field": c, "sesuai": (m[f"{c}_pred"].astype(str).str.upper() == m[c].astype(str).str.upper()).mean()}
            for c in FIELDS]
    selisih = (m["downtime_hours_pred"] - m["downtime_hours"]).abs()
    rows.append({"field": "downtime_hours (toleransi 0,5 jam)", "sesuai": (selisih <= 0.5).mean()})
    return pd.DataFrame(rows).assign(sesuai=lambda d: (d["sesuai"] * 100).round(1))


sample = wo.sample(60, random_state=42).reset_index(drop=True)
t0 = time.perf_counter()
pred_v1 = run_extraction(sample, SYSTEM_V1, "Prompt versi 1")
print(f"Waktu: {time.perf_counter() - t0:.0f} detik\n")
print(evaluate(pred_v1).to_string(index=False))

# %% [markdown]
# ## Langkah 7 - Analisis error dan perbaikan prompt

# %%
m = pred_v1.merge(truth, on="wo_id", suffixes=("_pred", "")).merge(wo[["wo_id", "deskripsi"]], on="wo_id")
for kolom in ("asset_id", "equipment_type", "action_category"):
    beda = m[m[f"{kolom}_pred"].astype(str).str.upper() != m[kolom].astype(str).str.upper()]
    print(f"{kolom}: {len(beda)} tidak sesuai")
    for r in beda.drop_duplicates([f"{kolom}_pred", kolom]).head(3).itertuples():
        print(f"  LLM: {getattr(r, kolom + '_pred')} | acuan: {getattr(r, kolom)} | {r.deskripsi[:75]}")

# %%
# TODO(U4.7): tulis TAMBAHAN_V2 berisi nilai yang diperbolehkan, konvensi kode aset, dan aturan action_category
TAMBAHAN_V2 = None  # TODO: ganti dengan implementasi Anda
SYSTEM_V2 = None  # TODO: ganti dengan implementasi Anda

pred_v2 = run_extraction(sample, SYSTEM_V2, "Prompt versi 2")
banding = evaluate(pred_v1).merge(evaluate(pred_v2), on="field", suffixes=("_v1", "_v2"))
print(banding.to_string(index=False))
print(f"\nSelf-repair: versi 1 = {(pred_v1['_repairs'] > 0).sum()} | versi 2 = {(pred_v2['_repairs'] > 0).sum()}")

# %% [markdown]
# ## Langkah 8 - Pengaruh format output dan mode reasoning

# %%
pola_sulit = r"s/d|kemarin|\d{2}\.\d{2}-\d{2}|hari|menit|DT \d"
hard = wo[wo["deskripsi"].str.contains(pola_sulit, regex=True)]
hard = hard.sample(min(30, len(hard)), random_state=3).merge(truth[["wo_id", "downtime_hours"]], on="wo_id")
print(f"{len(hard)} work order dengan penulisan waktu yang sulit. Contoh:\n  {hard['deskripsi'].iloc[0]}\n")

DT_RULES = ("Hitung downtime dalam jam desimal dari catatan work order. '1 hari' = 24, '1,5 hari' = 36, "
            "'45 menit' = 0.75, rentang '07.30 s/d 15.00' = 7.5, rentang yang melewati tengah malam "
            "dihitung lintas hari, contoh '22.00 kemarin sampai 04.00' = 6.")
# TODO(U4.8): lengkapi prompt varian B dengan field "langkah" sebelum field "downtime_hours"
PROMPTS = None  # TODO: ganti dengan implementasi Anda


def run_variant(name: str) -> dict:
    """Jalankan satu varian pada seluruh work order sulit, kembalikan akurasi, token, dan waktu."""
    effort = "high" if name.startswith("C") else "none"
    out0, rt0, t0 = llm.USAGE.completion_tokens, llm.USAGE.reasoning_tokens, time.perf_counter()

    def one(desc: str) -> float:
        jawab = chat(f"<wo>{desc}</wo>", system=PROMPTS[name], json_mode=True, reasoning=effort,
                     use_cache=False)  # tanpa cache agar token dan waktu terukur
        return float(parse_json(jawab)["downtime_hours"])

    preds = run_parallel(one, hard["deskripsi"], desc=name)
    benar = sum(isinstance(p, float) and abs(p - t) <= 0.25 for p, t in zip(preds, hard["downtime_hours"]))
    return {"varian": name, "benar": f"{benar} dari {len(hard)}",
            "output_tokens": llm.USAGE.completion_tokens - out0,
            "reasoning_tokens": llm.USAGE.reasoning_tokens - rt0,
            "detik": round(time.perf_counter() - t0, 1)}


riset = pd.DataFrame([run_variant(v) for v in PROMPTS])
print(riset.to_string(index=False))

# %% [markdown]
# ## Langkah 9 - Extraction pada seluruh work order

# %%
t0 = time.perf_counter()
calls0, cost0 = llm.USAGE.calls, llm.USAGE.cost_usd
pred_all = run_extraction(wo, SYSTEM_V2, "Extraction 400 work order")
print(f"Waktu: {time.perf_counter() - t0:.0f} detik | pemanggilan baru: {llm.USAGE.calls - calls0} | "
      f"biaya: USD {llm.USAGE.cost_usd - cost0:.4f}\n")
print(evaluate(pred_all).to_string(index=False))
print(f"\nPembanding (baseline aturan kata kunci): failure_category {acc_cat:.1%}, downtime_hours {acc_dt:.1%}")
m = pred_all.merge(truth, on="wo_id", suffixes=("_pred", "")).merge(wo[["wo_id", "deskripsi"]], on="wo_id")
print("\nWork order dengan downtime_hours tidak sesuai:")
for r in m[(m["downtime_hours_pred"] - m["downtime_hours"]).abs() > 0.5].itertuples():
    print(f"  {r.wo_id} | LLM: {r.downtime_hours_pred} | acuan: {r.downtime_hours} | {r.deskripsi}")

# %% [markdown]
# ## Langkah 10 - Analisis dengan pandas

# %%
full = wo.merge(pred_all, on="wo_id")
full["tanggal"] = pd.to_datetime(full["tanggal"])
failures = full[full["failure_category"] != "Preventive Maintenance"]

# (a) Pareto downtime per failure_category
pareto = failures.groupby("failure_category")["downtime_hours"].agg(jumlah="count", downtime_jam="sum")
pareto = pareto.sort_values("downtime_jam", ascending=False)
pareto["kumulatif_%"] = (pareto["downtime_jam"].cumsum() / pareto["downtime_jam"].sum() * 100).round(1)
print(pareto.to_string(), "\n")


# (b) Bad actor: aset dengan 3 kegagalan atau lebih dalam 90 hari
def max_failures_in_window(dates: pd.Series, days: int = 90) -> int:
    """Jumlah kegagalan terbanyak dalam satu jendela waktu sepanjang `days` hari."""
    # TODO(U4.10): urutkan tanggal, lalu untuk setiap tanggal hitung kegagalan dalam `days` hari berikutnya
    raise NotImplementedError("TODO(U4.10)")


bad = failures.groupby("asset_id").agg(
    kegagalan_90_hari=("tanggal", max_failures_in_window), downtime_jam=("downtime_hours", "sum"))
bad = bad[bad["kegagalan_90_hari"] >= 3].sort_values("downtime_jam", ascending=False)
print(f"Jumlah bad actor: {len(bad)}. Lima teratas menurut downtime:")
print(bad.head(5).to_string(), "\n")

# (c) Tren bulanan kejadian rod part pada sumur SRP
rod = failures[failures["component"].str.contains("rod", case=False)]
rod_bulanan = rod.groupby(rod["tanggal"].dt.month).size().reindex(range(1, 10), fill_value=0)
print("Kejadian rod part per bulan (Januari sampai September):", rod_bulanan.tolist())

# %%
# Perbandingan dengan analisis yang sama pada label acuan
ref = wo.merge(truth, on="wo_id")
ref["tanggal"] = pd.to_datetime(ref["tanggal"])
ref = ref[ref["failure_category"] != "Preventive Maintenance"]
ref_bad = ref.groupby("asset_id")["tanggal"].apply(max_failures_in_window)
ref_bad = set(ref_bad[ref_bad >= 3].index)
print(f"Bad actor menurut label acuan: {len(ref_bad)} aset | sama dengan hasil LLM: {len(ref_bad & set(bad.index))}")
ref_dt = ref.groupby("failure_category")["downtime_hours"].sum()
banding = pd.DataFrame({"LLM": pareto["downtime_jam"], "acuan": ref_dt}).sort_values("acuan", ascending=False)
banding["selisih_%"] = ((banding["LLM"] - banding["acuan"]) / banding["acuan"] * 100).round(1)
print(banding.to_string())

# %% [markdown]
# ## Langkah 11 - Insight dari angka hasil perhitungan

# %%
# TODO(U4.11): susun konteks dari pareto, bad, dan rod_bulanan, lalu minta insight dan rekomendasi
konteks = None  # TODO: ganti dengan implementasi Anda
insight = None  # TODO: ganti dengan implementasi Anda
print(insight)

# Pembanding untuk memeriksa angka turunan yang ditulis model
total = pareto["downtime_jam"].sum()
print(f"\nHasil pandas: total downtime {total:,.2f} jam | lima bad actor teratas "
      f"{bad.head(5)['downtime_jam'].sum():,.2f} jam ({bad.head(5)['downtime_jam'].sum() / total:.1%})")

# %%
OUTPUTS.mkdir(exist_ok=True)
full.to_csv(OUTPUTS / "work_orders_structured.csv", index=False)
print("Hasil extraction disimpan pada outputs/work_orders_structured.csv")
print(usage_summary())

# %% [markdown]
# ## Langkah tambahan (opsional) - Batch prompting
# Beberapa work order dikirim dalam satu request. Bandingkan waktu, jumlah request, dan akurasinya.

# %%
def extract_batch(rows: pd.DataFrame) -> list[dict]:
    """Extraction beberapa work order dalam satu request."""
    payload = "\n".join(f'<wo id="{r.wo_id}">{r.deskripsi}</wo>' for r in rows.itertuples())
    tambahan = ('\n\nTerdapat beberapa work order. Kembalikan {"items": [{"wo_id": "...", ...}]} '
                "dengan urutan yang sama seperti input.")
    out = []
    for item in parse_json(chat(payload, system=SYSTEM_V2 + tambahan, json_mode=True))["items"]:
        try:
            out.append({"wo_id": item["wo_id"]} | WOExtract.model_validate(item).model_dump())
        except (ValidationError, KeyError):
            pass
    return out


chunks = [sample.iloc[i : i + 10] for i in range(0, len(sample), 10)]
t0 = time.perf_counter()
hasil_batch = run_parallel(extract_batch, chunks, desc="Batch")
pred_batch = pd.DataFrame([x for h in hasil_batch if isinstance(h, list) for x in h])
print(f"Batch: {time.perf_counter() - t0:.0f} detik, {len(chunks)} request, {len(pred_batch)} item valid")
print(evaluate(pred_batch).to_string(index=False))
