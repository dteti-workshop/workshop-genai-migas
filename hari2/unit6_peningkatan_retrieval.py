# %% [markdown]
# # Unit 6 - Peningkatan Retrieval
# Contextual retrieval, query rewriting, HyDE, dan corrective RAG, masing-masing diukur dengan golden set.

# %%
# Langkah 1 - Nilai awal
import pandas as pd

import rag_pipeline as rp
from common import llm
from common.llm import chat, parse_json, usage_summary

gold = rp.load_golden()
retr = rp.load_retriever("markdown", 800)
parafrase = [g for g in gold if g["category"] == "paraphrase"]


def ukur(nama: str, cari, chunks=None) -> dict:
    """Metric tingkat dokumen dan tingkat chunk untuk satu fungsi pencarian cari(pertanyaan) -> daftar chunk."""
    m = rp.retrieval_metrics(cari, gold)
    c5, n = rp.chunk_hit(cari, gold, chunks or retr.chunks, k=5)
    p3 = rp.retrieval_metrics(cari, parafrase, k_list=(3,))["hit@3"]
    return {"metode": nama, "hit@1": m["hit@1"], "MRR": m["MRR"], "chunk hit@5": c5, "hit@3 parafrase": p3}


hasil = [ukur("Hybrid (nilai awal)", lambda q: retr.search(q, k=5, role="management"))]
print(pd.DataFrame(hasil).to_string(index=False))

# %% [markdown]
# ## Langkah 2 - Contextual retrieval

# %%
panggilan0 = llm.USAGE.calls + llm.USAGE.cache_hits
retr_ctx = rp.load_retriever("markdown", 800, contextual=True)
print(f"Pemanggilan LLM untuk menulis konteks: {llm.USAGE.calls + llm.USAGE.cache_hits - panggilan0}\n")
c = next(c for c in retr_ctx.chunks if c.metadata["section"].startswith("4. Tingkat Alarm") and c.metadata["revision"] == "3")
print("Konteks yang ditambahkan:\n ", c.metadata["context"], "\n")
hasil.append(ukur("Contextual retrieval", lambda q: retr_ctx.search(q, k=5, role="management"), retr_ctx.chunks))
print(pd.DataFrame(hasil).to_string(index=False))

# %% [markdown]
# ## Langkah 3 - Query rewriting dan HyDE

# %%
# TODO(U6.3): tulis REWRITE_SYSTEM yang meminta tiga query alternatif dengan istilah teknis baku dalam JSON
REWRITE_SYSTEM = None  # TODO: ganti dengan implementasi Anda


def tulis_ulang(pertanyaan: str) -> list[str]:
    """Pertanyaan asli ditambah query hasil rewriting."""
    try:
        return [pertanyaan] + parse_json(chat(pertanyaan, system=REWRITE_SYSTEM, json_mode=True))["queries"][:3]
    except (ValueError, KeyError):
        return [pertanyaan]


def cari_multi(pertanyaan: str, k: int = 5) -> list:
    """Cari dengan setiap query, lalu gabungkan peringkatnya dengan RRF."""
    # TODO(U6.3): kumpulkan daftar chunk_id untuk setiap query (4k kandidat), gabungkan dengan rp.rrf_fuse
    raise NotImplementedError("TODO(U6.3)")


contoh = parafrase[0]["question"]
print("Pertanyaan:", contoh)
for q in tulis_ulang(contoh)[1:]:
    print("  ->", q)
print()
hasil.append(ukur("Query rewriting", cari_multi))
hasil.append(ukur("Query rewriting + HyDE", lambda q: rp.multi_query_search(retr, q, k=5, hyde=True, role="management")))
print(pd.DataFrame(hasil).to_string(index=False))

# %% [markdown]
# ## Langkah 4 - Corrective RAG

# %%
UJI = ["Pada konsentrasi H2S berapa pekerja wajib menghentikan pekerjaan dan evakuasi?",
       "Pompa angguk saya masih naik-turun tapi tidak ada minyak yang keluar sama sekali, apa penyebabnya?",
       "Bagaimana prosedur start-up gas compressor K-ML1-201?"]
for q in UJI:
    for corrective in (False, True):
        panggilan0 = llm.USAGE.calls + llm.USAGE.cache_hits
        # TODO(U6.4): panggil rp.answer dengan parameter corrective, role management, dan log=False
        h = None  # TODO: ganti dengan implementasi Anda
        langkah = [(s["langkah"], "cukup" if s["cukup"] else "tidak cukup") for s in h["corrective_steps"]]
        print(f"corrective={corrective!s:5} | pemanggilan LLM {llm.USAGE.calls + llm.USAGE.cache_hits - panggilan0} | {langkah}\n"
              f"  {' '.join(h['answer'].split())[:170]}")
    print()

# %%
print(usage_summary())
