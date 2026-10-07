# Workshop Implementasi Agentic AI untuk Oil & Gas Industry

Kode hands-on untuk topik LLM & Prompt Engineering (`hari1/`) dan RAG & Enterprise Knowledge Management (`hari2/`).
Pusat Kajian LKFT, Fakultas Teknik, Universitas Gadjah Mada.

> Semua data di repo ini **fiktif** (lapangan "Blok Sungai Jernih", perusahaan "PT Hulu Energi Nusantara").
> SOP dan manual dibuat untuk keperluan pelatihan dan **bukan** prosedur resmi perusahaan mana pun.

## Panduan penggunaan

```bash
git clone https://github.com/dteti-workshop/workshop-genai-migas.git
cd workshop-genai-migas
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env      # macOS/Linux: cp .env.example .env  -> lalu isi API key
python setup_check.py
```

Panduan lengkap setiap unit, termasuk instalasi dan daftar error yang mungkin muncul, terdapat pada labsheet yang dibagikan instruktur.

## Struktur

```
common/            helper bersama: config (.env), llm.py (chat, retry, cache, biaya), embeddings.py
data/
  raw/             work_orders.csv (400 WO teks bebas), hse_incidents.csv (120 narasi), daily_reports/
  docs/            korpus RAG: sop/, manual/ (PDF), laporan/, investigasi/ (rahasia), glosarium/
  eval/            ground truth & golden set (untuk mengukur akurasi)
  contoh_upload/   file contoh untuk latihan upload (SOP baru, revisi SOP, laporan shift)
hari1/             satu file per unit (unit2 sampai unit7), app_asisten_wo.py (Unit 8: chat + upload file)
hari2/             rag_pipeline.py (pustaka RAG), satu file per unit (unit1 sampai unit6), app_doc_qa.py (Unit 7: chat + lampiran session + upload knowledge)
scripts/           reset_knowledge.py (mengembalikan knowledge base ke kondisi awal)
setup_check.py     cek kesiapan laptop
```

## Cara mengerjakan unit

- Buka file `hari1/unit*.py` atau `hari2/unit*.py` di VS Code (urutan unit mengikuti labsheet; Unit 1 pada `hari1/` adalah instalasi dan setup). Setiap blok `# %%` adalah satu sel. Klik **Run Cell** atau tekan
  `Shift+Enter` (butuh ekstensi Python + Jupyter).
- Cari komentar `# TODO(Ux.y)` dan lengkapi kodenya sesuai labsheet.
- Pada `hari2/`, file `rag_pipeline.py` adalah pustaka yang sudah lengkap. Bagian TODO berada pada file setiap unit.
- Aplikasi Streamlit dijalankan dari **root repo**:
  `streamlit run hari1/app_asisten_wo.py` dan `streamlit run hari2/app_doc_qa.py`.

## Aturan pemakaian API key bersama

- Satu API key dipakai seluruh peserta. Isi `PARTICIPANT_ID` di `.env` agar pemakaian bisa dipantau.
- Jangan menaikkan `LLM_MAX_CONCURRENCY` (default 4).
- Panggilan dengan `temperature=0` otomatis di-cache di `.cache/`, jadi menjalankan ulang sel tidak menambah biaya.
- Jangan commit file `.env`, jangan tempel API key di chat/forum.

## Profil model online vs lokal

`LLM_PROFILE=online` memakai OpenRouter (default DeepSeek V4 Flash). Mode reasoning diatur lewat `LLM_REASONING_EFFORT` (default `none`) atau parameter `chat(..., reasoning="high")`. `LLM_PROFILE=local` memakai server lokal yang
kompatibel dengan API OpenAI (Ollama/vLLM). Semua kode memakai antarmuka yang sama, jadi cukup mengganti `.env`.

## Catatan

- Folder `hari1/` dan `hari2/` berisi kode awal (starter) dengan bagian TODO yang dilengkapi peserta.
- Kembalikan knowledge base ke kondisi awal setelah latihan upload: `python scripts/reset_knowledge.py`.
- Versi yang diuji (Okt 2026, Python 3.11): openai 3.22, langchain-core 1.6, langchain-openai 1.6, langchain-chroma 1.1,
  chromadb 1.5, fastembed 0.8, streamlit 1.64, pandas 3.0, pydantic 2.13.
