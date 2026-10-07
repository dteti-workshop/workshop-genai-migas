# %% [markdown]
# # Unit 2 - Pemanggilan LLM melalui API
# Jalankan cell satu per satu dengan Shift+Enter atau tombol "Run Cell".
# Urutan langkah mengikuti labsheet.

# %%
# Langkah 1 - Memeriksa konfigurasi
import re
from collections import Counter
from datetime import datetime

from common import config
from common.llm import chat, chat_detail, extra_body, get_client, usage_summary

p = config.get_profile()
print(f"Profil aktif : {p.name}")
print(f"Model        : {p.model}")
print(f"Endpoint     : {p.base_url}")
print(f"Penyedia     : {', '.join(config.PROVIDERS) or 'routing default'}")

# %% [markdown]
# ## Langkah 2 - Request dan response

# %%
client = get_client()
EXTRA = extra_body()  # parameter khusus OpenRouter: penyedia model, mode reasoning, pencatatan biaya
SYSTEM = "Anda adalah production engineer. Jawab dalam bahasa Indonesia formal."
messages = [
    {"role": "system", "content": SYSTEM},
    {"role": "user", "content": "Jelaskan fungsi Electric Submersible Pump dalam dua kalimat."},
]
# TODO(U2.2): panggil client.chat.completions.create dengan model, messages, temperature=0, extra_body=EXTRA
resp = None  # TODO: ganti dengan implementasi Anda
print("Jawaban       :", resp.choices[0].message.content)
print("finish_reason :", resp.choices[0].finish_reason)
print("Input tokens  :", resp.usage.prompt_tokens)
print("Output tokens :", resp.usage.completion_tokens)
print("Penyedia      :", getattr(resp, "provider", "-"))

# %%
# Request yang sama dengan batas output 15 token
pendek = client.chat.completions.create(
    model=p.model, messages=messages, temperature=0, max_tokens=15, extra_body=EXTRA
)
print("Jawaban       :", pendek.choices[0].message.content)
print("finish_reason :", pendek.choices[0].finish_reason)
print("Output tokens :", pendek.usage.completion_tokens)

# %% [markdown]
# ## Langkah 3 - Mengukur jumlah token

# %%
def count_prompt_tokens(text: str) -> int:
    """Jumlah input tokens untuk `text` menurut server. max_tokens=1 agar biaya output minimal."""
    # TODO(U2.3): kirim `text` sebagai satu message user dengan max_tokens=1, kembalikan usage.prompt_tokens
    raise NotImplementedError("TODO(U2.3)")


# Special token dari chat template ikut terhitung. Teks "a" terdiri atas 1 token, sisanya overhead.
overhead = count_prompt_tokens("a") - 1
print(f"Overhead chat template: {overhead} token\n")

kalimat = {
    "Indonesia": "Tekanan discharge pompa menurun secara bertahap selama tiga hari terakhir.",
    "Inggris": "The pump discharge pressure has decreased gradually over the last three days.",
    "Singkatan": "Press. disch. pompa turun bertahap 3 hr terakhir.",
}
for nama, teks in kalimat.items():
    token, kata = count_prompt_tokens(teks) - overhead, len(teks.split())
    print(f"{nama:10s} {kata:2d} kata | {token:2d} token | {token / kata:.2f} token per kata")

# %% [markdown]
# ## Langkah 4 - Temperature

# %%
PROMPT_SLOGAN = ("Tulis satu kalimat pengingat keselamatan kerja untuk operator gathering station, "
                 "maksimum 12 kata.")


def sampel(temperature: float, n: int = 6) -> list[str]:
    """Jalankan PROMPT_SLOGAN sebanyak n kali pada temperature tertentu."""
    # TODO(U2.4): panggil chat() sebanyak n kali dengan temperature tersebut dan use_cache=False
    raise NotImplementedError("TODO(U2.4)")


for t in (0.0, 1.0):
    hasil = sampel(t)
    print(f"temperature = {t}: {len(set(hasil))} jawaban berbeda dari {len(hasil)} pemanggilan")
    for teks, jumlah in Counter(hasil).most_common():
        print(f"  {jumlah}x  {teks}")

# %% [markdown]
# ## Langkah 5 - Mode reasoning

# %%
KEJADIAN = [  # (sumur, waktu berhenti, waktu kembali berproduksi, laju produksi bopd)
    ("SR-041", "2026-07-19 14:30", "2026-07-21 09:15", 96),
    ("SR-014", "2026-07-20 22:45", "2026-07-21 03:10", 132),
    ("SR-027", "2026-07-21 06:20", "2026-07-21 11:50", 84),
]
SOAL = "Data sumur yang berhenti berproduksi:\n" + "\n".join(
    f"- {s}: berhenti {a[8:10]} Juli pukul {a[11:].replace(':', '.')}, "
    f"kembali berproduksi {b[8:10]} Juli pukul {b[11:].replace(':', '.')}, laju produksi {q} bopd"
    for s, a, b, q in KEJADIAN
) + ("\nHitung total deferred production ketiga sumur dalam barel. Deferred production setiap sumur "
     "adalah durasi berhenti (jam) dikali laju produksi dibagi 24. "
     "Jawab hanya dengan satu angka dengan satu desimal.")

FMT = "%Y-%m-%d %H:%M"
kunci = sum(
    (datetime.strptime(b, FMT) - datetime.strptime(a, FMT)).total_seconds() / 3600 * q / 24
    for _, a, b, q in KEJADIAN
)
print(SOAL)
print(f"\nKunci (dihitung dengan kode): {kunci:.1f} barel\n")


def angka_terakhir(teks: str) -> float | None:
    """Angka terakhir pada jawaban model, contoh '214,5' menjadi 214.5."""
    temuan = re.findall(r"\d+(?:[.,]\d+)?", teks)
    return float(temuan[-1].replace(",", ".")) if temuan else None


for mode in ("none", "high"):
    benar = 0
    for i in range(3):
        # TODO(U2.5): panggil chat_detail(SOAL, reasoning=mode) dan simpan hasilnya pada variabel r
        r = None  # TODO: ganti dengan implementasi Anda
        jawaban = angka_terakhir(r.text)
        sesuai = jawaban is not None and abs(jawaban - kunci) < 0.05
        benar += sesuai
        print(f"reasoning={mode:4s} percobaan {i + 1}: {r.text.strip()[-8:]:>8s} ({'benar' if sesuai else 'salah'}) | "
              f"output tokens {r.completion_tokens:4d} (reasoning {r.reasoning_tokens:4d}) | "
              f"{r.latency_s:4.1f} detik | USD {r.cost_usd:.6f}")
    print(f"reasoning={mode:4s} benar {benar} dari 3\n")

# %%
# Menampilkan sebagian teks reasoning
r = chat_detail(SOAL, reasoning="high", show_reasoning=True)
print(r.reasoning[:600] or "(penyedia model tidak mengirim teks reasoning)")

# %% [markdown]
# ## Langkah 6 - Sifat stateless dan riwayat percakapan

# %%
pesan_1 = [{"role": "user", "content": "Catat data berikut. Sumur SR-014 mengalami trip overload pada "
                                       "pukul 07.30 dan kembali beroperasi pada pukul 15.00."}]
PERTANYAAN = "Berapa jam sumur tersebut tidak beroperasi?"


def ringkas(teks: str, n: int = 90) -> str:
    """Jawaban dalam satu baris, dipotong n karakter, agar mudah dibandingkan."""
    return " ".join(teks.split())[:n]


r1 = chat_detail(pesan_1)
r2 = chat_detail(PERTANYAAN)  # request baru tanpa riwayat

# TODO(U2.6): susun messages berisi pesan_1, jawaban assistant (r1.text), lalu PERTANYAAN
riwayat = None  # TODO: ganti dengan implementasi Anda
r3 = chat_detail(riwayat)

for nama, r in (("Request 1", r1), ("Request 2", r2), ("Request 3", r3)):
    print(f"[{nama}] input tokens {r.prompt_tokens:3d} | {ringkas(r.text)}")

# %% [markdown]
# ## Langkah 7 - Rekapitulasi penggunaan

# %%
print(usage_summary())

# %% [markdown]
# ## Langkah tambahan (opsional) - Model online dan model lokal
# Jalankan hanya bila server model lokal tersedia dan variabel LOCAL_* pada file .env sudah diisi.

# %%
PERTANYAAN_ESP = "Sebutkan tiga penyebab umum ESP trip underload. Jawab dalam bentuk daftar singkat."
for profil in ("online", "local"):
    try:
        r = chat_detail(PERTANYAAN_ESP, profile=profil, retries=1)
        print(f"=== {profil} | {r.latency_s:.1f} detik | output tokens {r.completion_tokens}\n{r.text}\n")
    except Exception as e:  # noqa: BLE001
        print(f"=== {profil}: tidak tersedia ({type(e).__name__})\n")
