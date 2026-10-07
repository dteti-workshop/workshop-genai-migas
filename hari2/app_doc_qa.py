"""Unit 7 - Aplikasi Document Q&A berbasis RAG (Streamlit).

Jalankan dari folder repository:
    streamlit run hari2/app_doc_qa.py

Fitur:
- Tab Tanya Dokumen   : chat dengan sitasi, filter role dan status dokumen, lampiran file untuk session sendiri
- Tab Knowledge Base  : upload dokumen ke knowledge base bersama dengan quality gate dan penanganan revisi
- Tab Audit           : audit log tanya jawab
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

import rag_pipeline as rp
from common import config
from common.config import OUTPUTS

st.set_page_config(page_title="Document Q&A", layout="wide")


@st.cache_resource(show_spinner="Menyiapkan index dokumen ...")
def get_retriever() -> rp.HybridRetriever:
    """Satu retriever dipakai bersama oleh seluruh session, sehingga upload ke knowledge base terlihat semua pengguna."""
    return rp.load_retriever("markdown", 800)


ss = st.session_state
ss.setdefault("history", [])
ss.setdefault("session_index", rp.SessionIndex())  # dokumen lampiran, hanya untuk session ini

with st.sidebar:
    st.header("Pengaturan")
    role = st.selectbox("Role pengguna", list(rp.ROLE_GROUPS), index=0)
    mode = st.radio("Mode retrieval", ["hybrid", "dense", "sparse"], horizontal=True)
    k = st.slider("Jumlah chunk (top-k)", 1, 10, 5)
    active_only = st.toggle("Hanya dokumen berstatus active", value=True)
    corrective = st.toggle("Corrective RAG", value=False)
    st.caption(f"Model: `{config.get_profile().model}`")
    n_sesi = len({c.metadata["title"] for c in ss.session_index.chunks})
    st.caption(f"Dokumen pada session ini: {n_sesi} file, {len(ss.session_index.chunks)} chunk")

retr = get_retriever()
st.title("Document Q&A")
tab_chat, tab_kb, tab_audit = st.tabs(["Tanya Dokumen", "Knowledge Base", "Audit"])

# ====================================================================== tanya dokumen
with tab_chat:
    for turn in ss.history:
        st.chat_message(turn["role"]).markdown(turn["content"])

    msg = st.chat_input("Tulis pertanyaan, atau lampirkan file .md, .txt, atau .pdf untuk session ini",
                        accept_file="multiple", file_type=["md", "txt", "pdf"])
    if msg:
        q, files = (msg.text or "").strip(), msg.files
        label = q + "".join(f"\n\n`lampiran: {f.name}`" for f in files)
        st.chat_message("user").markdown(label)
        ss.history.append({"role": "user", "content": label})
        with st.chat_message("assistant"):
            for f in files:
                # TODO(U7.1): ambil teks file, tambahkan ke ss.session_index, dan susun pesan `note`
                raise NotImplementedError("TODO(U7.1)")
                st.markdown(note)
                ss.history.append({"role": "assistant", "content": note})
            if q:
                with st.spinner("Mencari dokumen dan menyusun jawaban ..."):
                    # TODO(U7.2): panggil rp.answer dengan pengaturan pada sidebar dan session_index
                    res = None  # TODO: ganti dengan implementasi Anda
                st.markdown(res["answer"])
                if res["invalid_citations"]:
                    st.warning(f"Sitasi tidak terdapat pada chunk yang diambil: {res['invalid_citations']}")
                with st.expander(f"Sumber ({len(res['sources'])} chunk)", expanded=True):
                    # TODO(U7.3): tampilkan doc_id, revisi, bagian, dan status setiap chunk sumber
                    raise NotImplementedError("TODO(U7.3)")
                st.caption(f"role: {role} | filter: {rp.chroma_filter(role, active_only)} | {res['latency_s']} detik")
                ss.history.append({"role": "assistant", "content": res["answer"]})

# ====================================================================== knowledge base
with tab_kb:
    st.subheader("Tambah dokumen ke knowledge base")
    st.caption(f"Hanya role {sorted(rp.UPLOAD_ROLES)} yang dapat menambah dokumen. Role saat ini: **{role}**.")
    with st.form("upload_kb"):
        up = st.file_uploader("File dokumen", type=["md", "txt", "pdf"])
        c1, c2, c3 = st.columns(3)
        doc_id = c1.text_input("doc_id", placeholder="SOP-OPS-030")
        revision = c2.text_input("revision", placeholder="1")
        doc_type = c3.selectbox("doc_type", ["SOP", "Manual", "Laporan", "Lessons Learned", "Investigasi", "Glosarium"])
        title = st.text_input("title", placeholder="Pengoperasian Gas Compressor")
        c4, c5, c6 = st.columns(3)
        owner = c4.text_input("owner", placeholder="Departemen Production Operations")
        status = c5.selectbox("status", ["active", "draft", "superseded"])
        access_group = c6.selectbox("access_group", ["all", "hse", "management"])
        kirim = st.form_submit_button("Tambahkan ke knowledge base", type="primary")
    if kirim:
        if up is None:
            st.error("File belum dipilih.")
        else:
            meta = {"doc_id": doc_id, "title": title, "doc_type": doc_type, "revision": revision, "status": status,
                    "owner": owner, "access_group": access_group}
            with st.spinner("Quality gate, chunking, dan indexing ..."):
                # TODO(U7.4): panggil rp.ingest_document dengan file, metadata, dan role pengunggah
                lap = None  # TODO: ganti dengan implementasi Anda
            if lap["ok"]:
                st.success(lap["pesan"])
                if lap["superseded_revisions"]:
                    st.info(f"Revisi lama {doc_id} Rev. {', '.join(lap['superseded_revisions'])} ditandai superseded.")
            else:
                st.error(f"Ditolak oleh quality gate: {lap['pesan']}")

    st.subheader("Isi knowledge base")
    kb = (pd.DataFrame([c.metadata for c in retr.chunks])
          .groupby(["doc_id", "revision", "title", "doc_type", "status", "access_group"], dropna=False)
          .size().rename("jumlah_chunk").reset_index().sort_values(["doc_id", "revision"]))
    st.dataframe(kb, width="stretch", hide_index=True)

# ====================================================================== audit
with tab_audit:
    st.subheader("Audit log tanya jawab")
    path = OUTPUTS / "rag_audit_log.jsonl"
    if path.exists():
        log = pd.read_json(path, lines=True).tail(50).iloc[::-1]
        st.dataframe(log[["ts", "role", "question", "chunk_ids", "cited", "invalid_citations"]], width="stretch",
                     hide_index=True)
    else:
        st.caption("Belum ada data.")
