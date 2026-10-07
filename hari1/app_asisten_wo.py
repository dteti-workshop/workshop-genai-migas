"""Unit 8 - Aplikasi Assistant Analisis Work Order (Streamlit).

Jalankan dari folder repository:
    streamlit run hari1/app_asisten_wo.py

Fitur:
- Chat dengan lampiran file (CSV work order, laporan TXT/MD/PDF) langsung dari kotak chat
- Router: setiap pesan diarahkan ke intent wo_baru, tanya_dokumen, atau tanya_data
- Tabel data terstruktur dan dashboard (Pareto downtime, tren, bad actor)
"""
from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from common import config
from common.config import DATA, OUTPUTS
from common.llm import chat, chat_stream, parse_json, run_parallel, usage_summary
from wo_extractor import extract_one, max_failures_in_window

st.set_page_config(page_title="Assistant Analisis Work Order", layout="wide")
st.title("Assistant Analisis Work Order")
st.caption(f"Model: `{config.get_profile().model}`. Seluruh data adalah data sintetis.")

MAX_DOC_CHARS = 60_000  # batas teks dokumen yang dikirim ke LLM
ss = st.session_state
ss.setdefault("msgs", [])  # riwayat percakapan [{"role", "content"}]
ss.setdefault("docs", {})  # dokumen yang di-upload pada sesi ini {nama: teks}

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.subheader("Data work order")
    n_maks = st.slider("Jumlah work order maksimum per file", 10, 400, 40, step=10)
    if st.button("Muat hasil extraction Unit 4", type="primary"):
        ss.muat_unit4 = True
    st.divider()
    st.caption("Dokumen pada sesi ini: " + (", ".join(ss.docs) or "-"))
    st.caption(usage_summary())


def structure_work_orders(raw: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Extraction work order dari file CSV. Kembalikan (tabel terstruktur, jumlah yang gagal)."""
    raw = raw.head(n_maks).reset_index(drop=True)
    hasil = run_parallel(extract_one, raw["deskripsi"])
    valid = [isinstance(h, dict) for h in hasil]
    df = pd.concat([raw[valid].reset_index(drop=True), pd.DataFrame([h for h in hasil if isinstance(h, dict)])], axis=1)
    return df, valid.count(False)


if ss.pop("muat_unit4", False):
    berkas = OUTPUTS / "work_orders_structured.csv"
    if berkas.exists():
        ss.df = pd.read_csv(berkas)
    else:  # Unit 4 belum dijalankan: gunakan label acuan agar aplikasi tetap dapat dicoba
        ss.df = pd.read_csv(DATA / "raw" / "work_orders.csv").merge(
            pd.read_csv(DATA / "eval" / "work_orders_truth.csv"), on="wo_id")


# ---------------------------------------------------------------- context dan router
def build_context(d: pd.DataFrame) -> str:
    """Ringkasan statistik yang dikirim ke LLM sebagai pengganti data mentah."""
    # TODO(U8.2): susun ringkasan agregat yang cukup untuk menjawab pertanyaan umum mengenai data
    raise NotImplementedError("TODO(U8.2)")


ROUTER_SYSTEM = """Klasifikasikan pesan pengguna aplikasi analisis work order ke dalam satu intent:
- "wo_baru": pesan berisi catatan kerusakan atau pekerjaan pada satu aset yang perlu dianalisis.
- "tanya_dokumen": pertanyaan mengenai isi dokumen atau laporan yang di-upload pengguna.
- "tanya_data": pertanyaan mengenai statistik, tren, atau aset pada data work order.
Kembalikan hanya JSON: {"intent": "..."}"""


def route(text: str) -> str:
    """Tentukan intent pesan dengan LLM. Jika gagal, gunakan intent default tanya_data."""
    # TODO(U8.3): kirim informasi dokumen yang tersedia dan pesan pengguna ke LLM, kembalikan intent
    raise NotImplementedError("TODO(U8.3)")


# ---------------------------------------------------------------- penanganan file
def read_text(file) -> str:
    if file.name.lower().endswith(".pdf"):
        from pypdf import PdfReader

        return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(file.getvalue())).pages)
    return file.getvalue().decode("utf-8", errors="replace")


def handle_file(file) -> str:
    """Proses satu lampiran. Kembalikan pesan Markdown untuk ditampilkan pada chat."""
    name = file.name
    if name.lower().endswith(".csv"):
        raw = pd.read_csv(file)
        kurang = {"wo_id", "tanggal", "deskripsi"} - set(raw.columns)
        if kurang:
            return f"**{name}**: kolom wajib tidak tersedia: {sorted(kurang)}"
        with st.spinner(f"Extraction {min(n_maks, len(raw))} work order dari {name} ..."):
            ss.df, gagal = structure_work_orders(raw)
        return (f"**{name}**: {len(ss.df)} work order berhasil distrukturkan, {gagal} gagal. "
                "Hasil tersedia pada tab Data Terstruktur dan Dashboard.")
    text = read_text(file)
    if not text.strip():
        return f"**{name}**: teks tidak terbaca. File PDF hasil scan memerlukan OCR."
    ss.docs[name] = text[:MAX_DOC_CHARS]
    # TODO(U8.4): buat ringkasan otomatis dokumen untuk Manajer Area, paling banyak 100 kata
    ringkasan = None  # TODO: ganti dengan implementasi Anda
    potong = " (dipotong)" if len(text) > MAX_DOC_CHARS else ""
    return f"**{name}** dimuat ({len(text):,} karakter{potong}). Ringkasan:\n\n{ringkasan}"


# ---------------------------------------------------------------- jawaban untuk setiap intent
def answer_wo(text: str) -> str:
    """Intent wo_baru: extraction, pencarian riwayat aset dengan pandas, lalu rekomendasi."""
    info = extract_one(text)
    riwayat = pd.DataFrame()
    if "df" in ss:
        riwayat = ss.df[ss.df["asset_id"] == info["asset_id"]].sort_values("tanggal")
    tabel = riwayat[["tanggal", "failure_category", "component"]].to_csv(index=False) if len(riwayat) else "tidak ada"
    saran = chat(
        f"Work order baru (terstruktur): {info}\nRiwayat aset:\n{tabel}\n"
        "Berikan: (1) apakah masalah ini berulang, (2) tiga langkah tindakan berikutnya, "
        "(3) pihak yang perlu diinformasikan. Paling banyak 120 kata.",
        system="Anda adalah production engineer senior. Gunakan hanya data yang diberikan.",
    )
    return (f"**Hasil extraction:** `{info}`\n\n**Riwayat aset {info['asset_id']}:** "
            f"{len(riwayat)} work order\n\n{saran}")


def stream_answer(text: str, intent: str):
    """Intent tanya_dokumen dan tanya_data: susun context, lalu kembalikan jawaban secara streaming."""
    if intent == "tanya_dokumen" and ss.docs:
        ctx = "\n\n".join(f'<dokumen nama="{k}">\n{v}\n</dokumen>' for k, v in ss.docs.items())
        system = ("Jawab hanya berdasarkan dokumen berikut dan sebutkan nama dokumen sumbernya. "
                  "Jika informasi tidak tercantum, jawab bahwa informasi tidak ditemukan.\n" + ctx)
    elif "df" in ss:
        system = ("Anda adalah reliability analyst. Jawab berdasarkan bagian <data>. Gunakan hanya angka yang "
                  "tercantum pada <data> dan jangan menghitung angka baru. Jika data tidak cukup, sebutkan "
                  "analisis yang diperlukan.\n<data>\n" + build_context(ss.df) + "\n</data>")
    else:
        return iter(["Data belum tersedia. Klik **Muat hasil extraction Unit 4** pada sidebar atau "
                     "lampirkan file CSV atau dokumen pada kotak chat."])
    # TODO(U8.5): kirim enam pesan terakhir sebagai riwayat, lalu kembalikan generator dari chat_stream
    raise NotImplementedError("TODO(U8.5)")


# ---------------------------------------------------------------- antarmuka
tab_chat, tab_data, tab_dash = st.tabs(["Assistant", "Data Terstruktur", "Dashboard"])

with tab_chat:
    for m in ss.msgs:
        st.chat_message(m["role"]).markdown(m["content"])

    prompt = st.chat_input("Tulis pertanyaan, tempel catatan work order, atau lampirkan file CSV/TXT/MD/PDF",
                           accept_file="multiple", file_type=["csv", "txt", "md", "pdf"])
    if prompt:
        text, files = (prompt.text or "").strip(), prompt.files
        label = text + ("".join(f"\n\n`lampiran: {f.name}`" for f in files))
        st.chat_message("user").markdown(label)
        with st.chat_message("assistant"):
            jawaban = []
            for f in files:
                jawaban.append(handle_file(f))
                st.markdown(jawaban[-1])
            if text:
                intent = route(text)
                st.caption(f"intent: {intent}")
                if intent == "wo_baru":
                    with st.spinner("Menganalisis work order ..."):
                        jawaban.append(answer_wo(text))
                    st.markdown(jawaban[-1])
                else:
                    jawaban.append(st.write_stream(stream_answer(text, intent)))
        ss.msgs.append({"role": "user", "content": label})
        ss.msgs += [{"role": "assistant", "content": j} for j in jawaban]

with tab_data:
    if "df" in ss:
        st.dataframe(ss.df, width="stretch", hide_index=True)
        st.download_button("Unduh CSV", ss.df.to_csv(index=False), "work_orders_terstruktur.csv")
    else:
        st.info("Data belum tersedia.")

with tab_dash:
    if "df" not in ss:
        st.info("Data belum tersedia.")
    else:
        df = ss.df.assign(tanggal=pd.to_datetime(ss.df["tanggal"]))
        fail = df[df["failure_category"] != "Preventive Maintenance"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Jumlah kegagalan", len(fail))
        c2.metric("Total downtime (jam)", f"{fail['downtime_hours'].sum():,.0f}")
        c3.metric("Work order dengan safety flag", int(df["safety_flag"].astype(str).str.lower().eq("true").sum()))
        kiri, kanan = st.columns(2)
        kiri.subheader("Downtime per failure category")
        kiri.bar_chart(fail.groupby("failure_category")["downtime_hours"].sum().sort_values(ascending=False))
        kanan.subheader("Jumlah kegagalan per bulan")
        kanan.line_chart(fail.assign(bulan=fail["tanggal"].dt.strftime("%Y-%m"))
                         .pivot_table(index="bulan", columns="equipment_type", values="wo_id",
                                      aggfunc="count", fill_value=0))
        st.subheader("Bad actor (3 kegagalan atau lebih dalam 90 hari)")
        bad = fail.groupby("asset_id")["tanggal"].apply(max_failures_in_window).rename("kegagalan_90_hari")
        st.dataframe(bad[bad >= 3].sort_values(ascending=False).to_frame(), width="stretch")
