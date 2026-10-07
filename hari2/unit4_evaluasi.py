# %% [markdown]
# # Unit 4 - Evaluasi RAG
# Retrieval dan generation diukur secara terpisah dengan golden set.

# %%
# Langkah 1 - Memuat golden set
import pandas as pd

import rag_pipeline as rp
from common.llm import chat, parse_json, run_parallel, usage_summary

gold = rp.load_golden()
ada_jawaban = [g for g in gold if g["expected_doc_ids"]]
print(f"Jumlah pertanyaan: {len(gold)} | memiliki jawaban pada dokumen: {len(ada_jawaban)}\n")
print(pd.Series([g["category"] for g in gold]).value_counts().to_string())
print("\nContoh:", gold[0])

retr = rp.load_retriever("markdown", 800)

# %% [markdown]
# ## Langkah 2 - Metric retrieval pada tingkat dokumen

# %%
def eval_retrieval(mode: str, k_list=(1, 3, 5)) -> dict:
    """hit@k dan MRR: apakah dokumen sumber berada pada k chunk teratas."""
    hits, rr = {k: 0 for k in k_list}, 0.0
    for g in ada_jawaban:
        hasil = retr.search(g["question"], k=max(k_list), mode=mode, role="management")
        ids = [d.metadata["doc_id"] for d in hasil]
        # TODO(U4.2): tentukan peringkat dokumen sumber, lalu perbarui hits dan rr
        raise NotImplementedError("TODO(U4.2)")
    n = len(ada_jawaban)
    return {"mode": mode} | {f"hit@{k}": round(hits[k] / n, 3) for k in k_list} | {"MRR": round(rr / n, 3)}


print(pd.DataFrame([eval_retrieval(m) for m in ("dense", "sparse", "hybrid")]).to_string(index=False))

# %% [markdown]
# ## Langkah 3 - Pengaruh strategi dan ukuran chunk

# %%
baris = []
for strategi in ("fixed", "markdown"):
    for ukuran in (300, 800, 1500):
        r = rp.load_retriever(strategi, ukuran)
        m = rp.retrieval_metrics(lambda q, r=r: r.search(q, k=5, role="management"), gold)
        baris.append({"strategi": strategi, "ukuran": ukuran, "jumlah_chunk": len(r.chunks)} | m)
print(pd.DataFrame(baris).to_string(index=False))

# %% [markdown]
# ## Langkah 4 - Metric retrieval pada tingkat chunk

# %%
baris = []
for mode in ("dense", "sparse", "hybrid"):
    row = {"mode": mode}
    for k in (3, 5, 10):
        nilai, n = rp.chunk_hit(lambda q, m=mode, k=k: retr.search(q, k=k, mode=m, role="management"), gold, retr.chunks, k)
        row[f"chunk hit@{k}"] = nilai
    baris.append(row)
print(f"Dihitung pada {n} pertanyaan yang butir jawabannya tertulis persis pada dokumen\n")
print(pd.DataFrame(baris).to_string(index=False))

# %% [markdown]
# ## Langkah 5 - Evaluasi jawaban dengan LLM sebagai penilai

# %%
# TODO(U4.5): tulis JUDGE_SYSTEM yang menilai jumlah butir jawaban yang tercakup dan penolakan
JUDGE_SYSTEM = None  # TODO: ganti dengan implementasi Anda
TANPA_RAG = ("Anda adalah asisten operasi lapangan migas PT Hulu Energi Nusantara. Jawab pertanyaan berikut "
             "secara singkat. Jika tidak mengetahui jawabannya, katakan tidak tahu.")


def nilai(pasangan: tuple[dict, str]) -> dict:
    """Minta LLM menilai satu jawaban terhadap butir jawaban kunci."""
    g, jawaban = pasangan
    v = parse_json(chat(f"Pertanyaan: {g['question']}\nKeypoint: {g['answer_keypoints']}\nJawaban sistem: {jawaban}",
                        system=JUDGE_SYSTEM, json_mode=True))
    return {"id": g["id"], "kategori": g["category"], "n": len(g["answer_keypoints"]),
            "tercakup": min(int(v.get("keypoints_covered", 0)), len(g["answer_keypoints"])),
            "menolak": bool(v.get("refused"))}


def evaluasi(nama: str, fungsi_jawab) -> pd.DataFrame:
    """Jalankan fungsi_jawab pada seluruh golden set, nilai hasilnya, dan tampilkan ringkasannya."""
    jawaban = [j if isinstance(j, str) else "ERROR" for j in run_parallel(fungsi_jawab, gold, desc="Jawab")]
    skor = pd.DataFrame([s for s in run_parallel(nilai, list(zip(gold, jawaban)), desc="Penilai") if isinstance(s, dict)])
    a, u = skor[skor["kategori"] != "unanswerable"], skor[skor["kategori"] == "unanswerable"]
    print(f"{nama:22s} | keypoint coverage {a['tercakup'].sum() / a['n'].sum():.1%} | jawaban lengkap "
          f"{(a['tercakup'] == a['n']).sum()} dari {len(a)} | menolak padahal ada jawaban {a['menolak'].sum()} | "
          f"menolak dengan benar {u['menolak'].sum()} dari {len(u)}")
    return skor.assign(jawaban=jawaban)


s_tanpa = evaluasi("Tanpa RAG", lambda g: chat(g["question"], system=TANPA_RAG))
s_rag = evaluasi("RAG, top-5 chunk", lambda g: rp.answer(g["question"], retr, role="management", k=5, log=False)["answer"])

# %% [markdown]
# ## Langkah 6 - Analisis kegagalan

# %%
gagal = s_rag[(s_rag["kategori"] != "unanswerable") & s_rag["menolak"]]
print(f"Pertanyaan yang dijawab tidak ditemukan padahal jawabannya tersedia: {len(gagal)}\n")
for row in gagal.itertuples():
    g = next(x for x in gold if x["id"] == row.id)
    top = retr.search(g["question"], k=20, role="management")
    # TODO(U4.6): tentukan peringkat dokumen sumber dan peringkat chunk yang memuat seluruh butir jawaban
    p_dok = None  # TODO: ganti dengan implementasi Anda
    p_chunk = None  # TODO: ganti dengan implementasi Anda
    print(f"{row.id} {g['question'][:74]}\n     peringkat dokumen sumber: {p_dok} | peringkat chunk pemuat jawaban: {p_chunk}")

# %% [markdown]
# ## Langkah 7 - Perbaikan dan pengukuran ulang

# %%
s_rag10 = evaluasi("RAG, top-10 chunk", lambda g: rp.answer(g["question"], retr, role="management", k=10, log=False)["answer"])
masih = s_rag10[(s_rag10["kategori"] != "unanswerable") & s_rag10["menolak"]]["id"].tolist()
print("Masih dijawab tidak ditemukan:", masih or "tidak ada")

tok = lambda k: sum(len(d.page_content) for g in ada_jawaban for d in retr.search(g["question"], k=k, role="management")) / len(ada_jawaban)
print(f"Rata-rata panjang context: top-5 = {tok(5):,.0f} karakter | top-10 = {tok(10):,.0f} karakter")

# %%
print(usage_summary())
