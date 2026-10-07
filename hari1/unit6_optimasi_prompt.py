# %% [markdown]
# # Unit 6 - Automatic Prompt Optimization
# Optimizer sederhana berbasis reflection: ukur prompt pada data dev, analisis kegagalan,
# tulis prompt baru, terima jika skor naik. Hasil akhirnya diuji pada data test.

# %%
# Langkah 1 - Data dev, data test, dan fungsi evaluasi
import pandas as pd

from common.data import load_hse
from common.llm import chat, parse_json, run_parallel, usage_summary

test, pool = load_hse()
dev = pool.groupby("incident_type", group_keys=False).head(5).reset_index(drop=True)
print(f"Data dev: {len(dev)} laporan (dari pool) | data test: {len(test)} laporan")

TYPES = ["Near Miss", "First Aid Case", "Medical Treatment Case", "Lost Time Injury",
         "Property Damage", "Environmental Spill"]
OUTPUT_SPEC = '\nKembalikan hanya JSON: {"incident_type": "<salah satu label>"}'


def evaluate(system_prompt: str, data: pd.DataFrame) -> tuple[float, pd.DataFrame]:
    """Accuracy incident_type dan tabel prediksi untuk analisis error."""
    def one(narasi: str) -> str:
        jawab = chat(f"<insiden>{narasi}</insiden>", system=system_prompt + OUTPUT_SPEC, json_mode=True)
        return parse_json(jawab).get("incident_type", "?")

    preds = [p if isinstance(p, str) else "ERROR" for p in run_parallel(one, data["narasi"], desc="Evaluasi")]
    tabel = data[["narasi", "incident_type"]].assign(pred=preds)
    return (tabel["pred"] == tabel["incident_type"]).mean(), tabel


# %% [markdown]
# ## Langkah 2 - Prompt awal (seed)

# %%
SEED = f"Klasifikasikan laporan insiden HSE ke dalam salah satu label: {TYPES}."
seed_acc, seed_tab = evaluate(SEED, dev)
print(f"Prompt awal: accuracy pada data dev {seed_acc:.1%}\n")
for r in seed_tab[seed_tab["pred"] != seed_tab["incident_type"]].itertuples():
    print(f"- prediksi: {r.pred} | acuan: {r.incident_type}\n  {r.narasi[:150]}")

# %% [markdown]
# ## Langkah 3 - Prompt untuk reflection

# %%
# TODO(U6.3): tulis REFLECT_SYSTEM yang meminta diagnosis pola kesalahan dan prompt pengganti dalam JSON
REFLECT_SYSTEM = None  # TODO: ganti dengan implementasi Anda


def reflect(prompt: str, acc: float, tabel: pd.DataFrame, n_err: int = 8) -> dict:
    """Kirim prompt, skor, dan contoh kesalahan ke LLM. Kembalikan diagnosis dan prompt baru."""
    err = tabel[tabel["pred"] != tabel["incident_type"]].head(n_err)
    contoh = "\n".join(f"- narasi: {r.narasi}\n  prediksi: {r.pred} | acuan: {r.incident_type}"
                       for r in err.itertuples())
    pesan = (f"<prompt_saat_ini>\n{prompt}\n</prompt_saat_ini>\nAccuracy: {acc:.0%}\n"
             f"<kesalahan>\n{contoh}\n</kesalahan>")
    # reflection memerlukan penalaran dan hanya dipanggil beberapa kali, sehingga mode reasoning diaktifkan
    return parse_json(chat(pesan, system=REFLECT_SYSTEM, json_mode=True, reasoning="high",
                           temperature=0.7, use_cache=False))


# %% [markdown]
# ## Langkah 4 - Loop optimasi

# %%
N_ITER = 3
best = {"prompt": SEED, "acc": seed_acc, "tabel": seed_tab}
riwayat = [{"iterasi": 0, "accuracy_dev": f"{seed_acc:.1%}", "diterima": "-", "diagnosis": "(prompt awal)"}]

for it in range(1, N_ITER + 1):
    if best["acc"] == 1:
        print("Accuracy pada data dev sudah 100%, optimasi dihentikan.")
        break
    usulan = reflect(best["prompt"], best["acc"], best["tabel"])
    cand_acc, cand_tab = evaluate(usulan["prompt_baru"], dev)
    # TODO(U6.4): terima kandidat jika accuracy pada data dev lebih tinggi, lalu perbarui `best`
    raise NotImplementedError("TODO(U6.4)")
    riwayat.append({"iterasi": it, "accuracy_dev": f"{cand_acc:.1%}", "diterima": "ya" if diterima else "tidak",
                    "diagnosis": usulan["diagnosis"]})

pd.set_option("display.max_colwidth", 60)
print(pd.DataFrame(riwayat).to_string(index=False))

# %% [markdown]
# ## Langkah 5 - Pengujian pada data test

# %%
HUMAN_PROMPT = """Anda adalah HSE analyst. Klasifikasikan laporan insiden sesuai pedoman berikut.
Pilih satu label dengan memeriksa secara berurutan dari nomor 1:
1. Environmental Spill: terdapat minyak atau air terproduksi yang keluar ke lingkungan.
2. Lost Time Injury: pekerja tidak dapat bekerja pada shift atau hari berikutnya.
3. Medical Treatment Case: cedera ditangani tenaga medis, tetapi pekerja tidak kehilangan hari kerja.
4. First Aid Case: cedera ringan yang cukup ditangani dengan P3K dan pekerja langsung kembali bekerja.
5. Property Damage: tidak ada cedera, tetapi terdapat aset yang rusak.
6. Near Miss: tidak ada cedera dan tidak ada kerusakan."""

hasil = []
for nama, prompt in (("Prompt awal", SEED), ("Prompt manusia", HUMAN_PROMPT), ("Prompt hasil optimasi", best["prompt"])):
    acc_dev, _ = evaluate(prompt, dev)
    acc_test, _ = evaluate(prompt, test)
    hasil.append({"prompt": nama, "accuracy_dev": f"{acc_dev:.1%}", "accuracy_test": f"{acc_test:.1%}",
                  "panjang_karakter": len(prompt)})
print(pd.DataFrame(hasil).to_string(index=False))

# %%
print("Prompt hasil optimasi:\n")
print(best["prompt"])

# %%
print(usage_summary())
