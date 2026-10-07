# %% [markdown]
# # Unit 2 - Indexing dan Retrieval
# Embedding, vector store, dense retrieval, sparse retrieval (BM25), dan hybrid retrieval dengan RRF.

# %%
# Langkah 1 - Embedding dan cosine similarity
import numpy as np
import pandas as pd
from rank_bm25 import BM25Okapi

import rag_pipeline as rp
from common.embeddings import get_embeddings

emb = get_embeddings()
kalimat = [
    "Rangkaian rod pada pompa angguk putus",
    "Sucker rod pump mengalami rod part",
    "Detektor menunjukkan adanya gas hidrogen sulfida",
    "Gas H2S terdeteksi di area wellhead",
    "Harga minyak dunia naik pada pekan ini",
]
# TODO(U2.1): ubah kalimat menjadi vektor, normalisasi panjangnya, lalu hitung matriks cosine similarity
V = None  # TODO: ganti dengan implementasi Anda
V = None  # TODO: ganti dengan implementasi Anda
sim = None  # TODO: ganti dengan implementasi Anda
print(f"Ukuran matriks vektor: {V.shape}\n")
print(pd.DataFrame(sim, index=[f"{i + 1}. {k[:38]}" for i, k in enumerate(kalimat)],
                   columns=range(1, len(kalimat) + 1)).round(2).to_string())

# %% [markdown]
# ## Langkah 2 - Membangun index dan dense retrieval

# %%
docs = rp.load_documents()
chunks = rp.chunk_documents(docs, "markdown", 800, 100)
store = rp.build_index(chunks, "sop_markdown_800")


def dense(query: str, k: int = 5) -> list:
    """Chunk dengan vektor terdekat terhadap vektor query."""
    return store.similarity_search(query, k=k)


for q in ("Berapa jarak minimum muster point saat evakuasi H2S?", "Apa arti kode F12?"):
    print(f"\nQuery: {q}")
    for doc, jarak in store.similarity_search_with_score(q, k=3):
        print(f"  similarity {1 - jarak:.2f} | {doc.metadata['doc_id']:14s} | {doc.metadata['section'][:45]}")

# %% [markdown]
# ## Langkah 3 - Sparse retrieval dengan BM25

# %%
# TODO(U2.3): bangun index BM25 dari token setiap chunk, lalu lengkapi fungsi sparse
bm25 = None  # TODO: ganti dengan implementasi Anda
def sparse(query: str, k: int = 5) -> list:
    raise NotImplementedError("TODO(U2.3)")



UJI = {  # query -> doc_id yang memuat jawabannya
    "Apa arti kode F12?": "MAN-VSD-FD500",
    "Kejadian di sumur SR-027": "INV-2026-011",
    "Pompa angguk masih naik-turun tetapi tidak ada minyak yang keluar": "SOP-OPS-015",
    "Boleh mulai menggerinda jika alat ukur masih mendeteksi sedikit gas?": "SOP-HSE-004",
}


def peringkat(hasil: list, doc_id: str):
    """Peringkat pertama dokumen `doc_id` pada hasil pencarian, atau '-' jika tidak ada."""
    return next((i + 1 for i, c in enumerate(hasil) if c.metadata["doc_id"] == doc_id), "-")


for q, target in UJI.items():
    print(f"{q[:62]:62s} | dense: {peringkat(dense(q, 20), target):>2} | sparse: {peringkat(sparse(q, 20), target):>2}")

# %% [markdown]
# ## Langkah 4 - Hybrid retrieval dengan Reciprocal Rank Fusion

# %%
def rrf(daftar_peringkat: list[list[str]], k: int = 60) -> list[str]:
    """Gabungkan beberapa daftar id. Skor setiap id = jumlah 1 / (k + peringkat) pada setiap daftar."""
    # TODO(U2.4): hitung skor RRF setiap id, lalu kembalikan id terurut dari skor tertinggi
    raise NotImplementedError("TODO(U2.4)")


print("Contoh RRF:", rrf([["a", "b", "c"], ["c", "a", "d"]]))

per_id = {c.metadata["chunk_id"]: c for c in chunks}


def hybrid(query: str, k: int = 5) -> list:
    """Gabungkan 4k kandidat dense dan 4k kandidat sparse dengan RRF."""
    d = [c.metadata["chunk_id"] for c in dense(query, 4 * k)]
    s = [c.metadata["chunk_id"] for c in sparse(query, 4 * k)]
    return [per_id[i] for i in rrf([d, s])[:k]]


print()
for q, target in UJI.items():
    print(f"{q[:62]:62s} | dense: {peringkat(dense(q, 20), target):>2} | sparse: {peringkat(sparse(q, 20), target):>2} "
          f"| hybrid: {peringkat(hybrid(q, 20), target):>2}")

# %%
# Fungsi yang sama tersedia pada pustaka: HybridRetriever.search(query, k, mode)
retr = rp.HybridRetriever(store, chunks)
q = "Berapa jarak minimum muster point saat evakuasi H2S?"
for mode in ("dense", "sparse", "hybrid"):
    print(f"{mode:7s}:", [c.metadata["section"][:30] for c in retr.search(q, k=3, mode=mode, role="operator")])
