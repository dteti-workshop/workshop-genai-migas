# %% [markdown]
# # Unit 3 - Generation dengan Sitasi
# Menyusun prompt RAG, memverifikasi sitasi, menangani revisi dokumen, dan pertanyaan tanpa jawaban.

# %%
# Langkah 1 - Retrieval dan penyusunan context
import re

import rag_pipeline as rp
from common.llm import chat, usage_summary

retr = rp.load_retriever("markdown", 800)
Q = "Berapa jarak minimum muster point saat evakuasi H2S?"
docs = retr.search(Q, k=2)
print(rp.format_context(docs)[:900], "...")

# %% [markdown]
# ## Langkah 2 - Prompt RAG

# %%
# TODO(U3.2): tulis SYSTEM_RAG berisi enam aturan pada labsheet
SYSTEM_RAG = None  # TODO: ganti dengan implementasi Anda


def jawab(pertanyaan: str, k: int = 5, active_only: bool = True) -> dict:
    """Retrieval, penyusunan prompt, dan generation. Kembalikan jawaban beserta chunk sumbernya."""
    sumber = retr.search(pertanyaan, k=k, active_only=active_only)
    # TODO(U3.2): susun user message berisi context di dalam tag <konteks> dan pertanyaan, lalu panggil chat()
    user = None  # TODO: ganti dengan implementasi Anda
    teks = None  # TODO: ganti dengan implementasi Anda
    return {"pertanyaan": pertanyaan, "jawaban": teks, "sumber": sumber}


hasil = jawab(Q)
print(hasil["jawaban"])

# %% [markdown]
# ## Langkah 3 - Verifikasi sitasi dengan kode

# %%
KURUNG = re.compile(r"\[([^\[\]]+)\]")  # isi setiap kurung siku
DOC_ID = re.compile(r"\b[A-Z]{2,4}(?:-[A-Z0-9]+)+\b")  # contoh: SOP-HSE-001, MAN-VSD-FD500


def periksa_sitasi(hasil: dict) -> dict:
    """Bandingkan doc_id pada sitasi dengan doc_id chunk yang diambil retriever."""
    # TODO(U3.3): ambil doc_id pada setiap kurung siku, lalu pisahkan yang tidak ada pada chunk sumber
    raise NotImplementedError("TODO(U3.3)")


print(periksa_sitasi(hasil))

palsu = dict(hasil, jawaban="Jarak minimum muster point adalah 50 m [SOP-HSE-099 §6. Prosedur Evakuasi].")
print(periksa_sitasi(palsu))

# %%
for q in ("Berapa kali ESP boleh di-restart setelah trip overload dalam 24 jam?",
          "Jelaskan langkah LOTO sebelum memperbaiki panel VSD.",
          "VSD menampilkan kode F12, apa yang harus dilakukan?"):
    h = jawab(q)
    print(f"Pertanyaan: {q}\n{h['jawaban']}\nSitasi: {periksa_sitasi(h)}\n" + "-" * 90)

# %% [markdown]
# ## Langkah 4 - Revisi dokumen

# %%
Q_REV = "Seberapa sering personal H2S detector harus di-bump test?"
for active_only in (False, True):
    h = jawab(Q_REV, k=3, active_only=active_only)
    revisi = [(d.metadata["doc_id"], "Rev." + d.metadata["revision"], d.metadata["status"]) for d in h["sumber"]]
    print(f"active_only={active_only}\n  chunk: {revisi}\n  jawaban: {' '.join(h['jawaban'].split())[:330]}\n")

# %% [markdown]
# ## Langkah 5 - Pertanyaan tanpa jawaban pada dokumen

# %%
for q in ("Berapa harga minyak Brent hari ini?", "Bagaimana prosedur start-up gas compressor K-ML1-201?"):
    h = jawab(q)
    print(f"Pertanyaan: {q}\n  dokumen yang diambil: {periksa_sitasi(h)['diambil']}\n  jawaban: {' '.join(h['jawaban'].split())[:300]}\n")

# %%
print(usage_summary())
