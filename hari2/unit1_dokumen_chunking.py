# %% [markdown]
# # Unit 1 - Pemrosesan Dokumen dan Chunking
# Jalankan cell satu per satu dengan Shift+Enter atau tombol "Run Cell".
# Urutan langkah mengikuti labsheet.

# %%
# Langkah 1 - Memuat dokumen dan metadata
import pandas as pd
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

import rag_pipeline as rp

docs = rp.load_documents()
meta = pd.DataFrame([d.metadata | {"karakter": len(d.page_content)} for d in docs])
print(f"Jumlah dokumen: {len(docs)}\n")
print(meta[["doc_id", "revision", "status", "doc_type", "access_group", "file_type", "karakter"]].to_string(index=False))

# %% [markdown]
# ## Langkah 2 - Memeriksa hasil parsing

# %%
sop = next(d for d in docs if d.metadata["doc_id"] == "SOP-HSE-001" and d.metadata["revision"] == "3")
i = sop.page_content.find("| Level")
print("=== SOP (Markdown): tabel tingkat alarm\n" + sop.page_content[i : i + 420])

manual = next(d for d in docs if d.metadata["file_type"] == "pdf")
j = manual.page_content.find("F11")
print("\n=== Manual (PDF): tabel kode alarm setelah parsing\n" + manual.page_content[j : j + 420])

# %% [markdown]
# ## Langkah 3 - Chunking fixed size

# %%
def potong_fixed(teks: str, ukuran: int = 500, overlap: int = 50) -> list[str]:
    """Potong teks setiap `ukuran` karakter. Setiap potongan mengulang `overlap` karakter terakhir."""
    # TODO(U1.3): kembalikan daftar potongan teks[i : i + ukuran] dengan langkah (ukuran - overlap)
    raise NotImplementedError("TODO(U1.3)")


def tampilkan(potongan: list[str], kata: str) -> None:
    """Tampilkan potongan pertama yang memuat `kata`."""
    k = next(i for i, c in enumerate(potongan) if kata in c)
    print(f"Jumlah chunk: {len(potongan)} | chunk ke-{k + 1} ({len(potongan[k])} karakter):\n")
    print(potongan[k])


fixed = potong_fixed(sop.page_content)
tampilkan(fixed, "Alarm 2 (merah)")

# %% [markdown]
# ## Langkah 4 - Chunking berbasis struktur dengan identitas dokumen

# %%
def potong_struktur(doc: Document, ukuran: int = 800) -> list[Document]:
    """Potong dokumen Markdown per bagian (heading ##). Setiap chunk diawali identitas dokumen."""
    per_bagian = MarkdownHeaderTextSplitter([("#", "judul"), ("##", "section")], strip_headers=False)
    pemecah = RecursiveCharacterTextSplitter(chunk_size=ukuran, chunk_overlap=ukuran // 8)
    m, hasil = doc.metadata, []
    for bagian in per_bagian.split_text(doc.page_content):
        section = bagian.metadata.get("section", "Pendahuluan")
        for teks in pemecah.split_text(bagian.page_content):
            # TODO(U1.4): susun baris identitas, lalu tambahkan chunk beserta metadata dokumen dan section
            raise NotImplementedError("TODO(U1.4)")
    return hasil


struktur = potong_struktur(sop)
tampilkan([c.page_content for c in struktur], "Alarm 2 (merah)")
print("\nMetadata chunk:", {k: struktur[4].metadata[k] for k in ("doc_id", "revision", "status", "access_group", "section")})

# %% [markdown]
# ## Langkah 5 - Statistik chunk pada seluruh dokumen

# %%
baris = []
for strategi in ("fixed", "recursive", "markdown"):
    for ukuran in (300, 800, 1500):
        ch = rp.chunk_documents(docs, strategi, ukuran, ukuran // 8)
        panjang = pd.Series([len(c.page_content) for c in ch])
        utuh = sum("Alarm 1" in c.page_content and "Alarm 2" in c.page_content and "Darurat" in c.page_content
                   for c in ch if c.metadata["doc_id"] == "SOP-HSE-001" and c.metadata["revision"] == "3")
        baris.append({"strategi": strategi, "ukuran": ukuran, "jumlah_chunk": len(ch),
                      "median_karakter": int(panjang.median()), "tabel_alarm_utuh": "ya" if utuh else "tidak"})
print(pd.DataFrame(baris).to_string(index=False))

# %%
# Pustaka rag_pipeline memakai strategi "markdown", yaitu pemotongan berbasis struktur seperti pada Langkah 4
chunks = rp.chunk_documents(docs, "markdown", 800, 100)
print(f"Jumlah chunk: {len(chunks)}\n")
for c in chunks[46:48]:
    print(c.metadata["chunk_id"], "|", c.metadata["section"], "\n" + c.page_content[:230], "\n")
