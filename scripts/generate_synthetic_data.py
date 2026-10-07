"""Generator data sintetis untuk workshop (deterministik, seed tetap).

Semua nama lapangan, sumur, peralatan, orang, dan angka adalah FIKTIF.
Konteks: lapangan minyak darat fiktif "Blok Sungai Jernih" milik "PT Hulu Energi Nusantara".

Output:
  data/raw/work_orders.csv            teks bebas WO (tanpa label)        -> Hari 1 Lab 2
  data/eval/work_orders_truth.csv     label ground truth WO               -> evaluasi
  data/raw/hse_incidents.csv          narasi insiden HSE (tanpa label)    -> Hari 1 Lab 3
  data/eval/hse_incidents_truth.csv   label ground truth insiden
  data/raw/daily_reports/GS-SR1_2026-07.md  log harian 31 hari          -> Hari 1 Lab 4
  data/eval/daily_gs_sr1_2026-07.csv  angka harian ground truth

Jalankan:  python scripts/generate_synthetic_data.py
"""
from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW, EVAL = ROOT / "data" / "raw", ROOT / "data" / "eval"
rng = random.Random(2026)

TECHS = ["Rahmat", "Fikri", "Sutrisno", "Yudi", "Hendra", "Arif", "Doni", "Wahyu", "Rizal", "Bambang", "Irfan", "Agus"]

# ---------------------------------------------------------------------------
# 1. WORK ORDERS
# ---------------------------------------------------------------------------


def downtime_phrase() -> tuple[str, float]:
    """Kembalikan (frasa downtime dalam berbagai gaya, jam downtime)."""
    style = rng.choice(["jam", "range", "overnight", "hari", "h", "menit", "range2"])
    if style == "jam":
        h = rng.choice([2, 3, 4, 5, 6, 8, 10, 12])
        return rng.choice([f"down ±{h} jam", f"off kurang lebih {h} jam", f"downtime {h} jam"]), float(h)
    if style == "h":
        h = rng.choice([1.5, 2.5, 3, 6, 7, 9, 14, 16])
        return f"DT {str(h).replace('.0', '')}h", float(h)
    if style == "range":
        s = rng.choice([6, 7, 8, 9, 10]) + rng.choice([0, 0.5])
        h = rng.choice([2, 3, 4.5, 5, 6.5, 7.5, 8])
        e = s + h
        f = lambda x: f"{int(x):02d}.{'30' if x % 1 else '00'}"  # noqa: E731
        return rng.choice([f"sumur off dari jam {f(s)} s/d {f(e)}", f"mati {f(s)}-{f(e)}"]), float(h)
    if style == "range2":
        s = rng.choice([13, 14, 15]) ; h = rng.choice([3, 4, 5])
        return f"stop pkl {s}.00, normal kembali pkl {s + h}.00", float(h)
    if style == "overnight":
        s = rng.choice([20, 21, 22, 23]); e = rng.choice([3, 4, 5, 6])
        return f"mati sejak pukul {s}.00 kemarin malam, running lagi {e:02d}.00 pagi", float(24 - s + e)
    if style == "hari":
        d = rng.choice([1, 1.5, 2, 3])
        txt = {1: "1 hari", 1.5: "1,5 hari", 2: "2 hari", 3: "3 hari"}[d]
        return rng.choice([f"downtime {txt}", f"sumur off {txt} nunggu rig"]), d * 24
    m = rng.choice([30, 45, 90])
    return f"down {m} menit", m / 60


# Setiap skenario: equipment_type, failure_category, component, action_category, safety_flag, template teks
# {a}=asset, {dt}=frasa downtime, {amp}/{n}= angka acak
SCENARIOS = [
    # ---------------- ESP ----------------
    ("ESP", "Electrical", "Motor", "Workover", False, [
        "ESP {a} trip OL, coba restart 2x gagal. Megger motor phase-to-ground 0 Mohm -> motor burnt. Usul pulling job ganti motor. {dt}.",
        "{a}: unit ESP ga mau start, hasil megger motor short. Diputuskan workover, motor diganti baru. {dt}",
    ]),
    ("ESP", "Electrical", "Power Cable", "Workover", False, [
        "{a} ESP trip, megger kabel drop ke 2 Mohm (normal >100). Suspect kabel bocor di splice. Rig masuk, ganti cable+splice. {dt}.",
        "kabel ESP {a} insulasi jelek (megger rendah), pompa & motor ok. Penggantian power cable via workover. {dt}",
        "Sumur {a} mati, VSD alarm ground fault. Cek JB permukaan aman, ternyata kabel downhole yg rusak. Ganti kabel lewat pulling job, {dt}.",
    ]),
    ("ESP", "Flow Assurance", "Pump Stage", "Clean/Flush", False, [
        "ESP {a} trip OL, ampere naik {amp}% dari normal. Megger kabel & motor OK, suspect pompa ngeblok pasir. Hot oil flushing lalu start ulang normal. {dt}.",
        "{a} amp tinggi + vibrasi, sand content naik. Dilakukan flushing pompa, unit running kembali. {dt}",
    ]),
    ("ESP", "Process/Trip", "Pump Intake", "Adjust/Reset", False, [
        "{a} trip UL (underload) berulang, PIP turun, indikasi gas lock / inflow kurang. Frekuensi VSD diturunkan dari 55 ke 50 Hz, reset. {dt}.",
        "underload {a}, fluid level rendah. Setting VSD diubah + restart, kabel tidak ada masalah. {dt}",
    ]),
    ("ESP", "Instrumentation/Control", "VSD", "Replace", False, [
        "VSD {a} display mati, kartu kontrol rusak (cek kabel downhole normal). Ganti control board VSD. {dt}.",
        "{a}: drive fault di VSD, IGBT module diganti teknisi electrical. ESP normal kembali. {dt}",
    ]),
    # ---------------- SRP ----------------
    ("SRP", "Mechanical", "Sucker Rod", "Workover", False, [
        "SRP {a} rod part, polished rod ringan & dyno card abnormal. Fishing job + ganti rod string sebagian. {dt}.",
        "{a} pompa angguk jalan tp ga ada produksi, dyno: rod putus. Pulling unit masuk, rod diganti. {dt}",
        "rod {a} part di kedalaman ±{n} ft, dilakukan fishing & ganti 12 joint rod. {dt}.",
    ]),
    ("SRP", "Leak/Corrosion", "Stuffing Box", "Replace", True, [
        "Stuffing box {a} bocor, minyak rembes ke cellar. Ganti packing stuffing box, area dibersihkan. {dt}.",
        "{a} leak di stuffing box, ada ceceran minyak ±{n} liter di sekitar wellhead. Packing diganti + housekeeping. {dt}",
    ]),
    ("SRP", "Mechanical", "Gearbox", "Repair", False, [
        "Gearbox pumping unit {a} bunyi kasar, oli bocor dikit. Ganti bearing gearbox + top up oli. {dt}.",
        "{a}: noise di gear reducer, setelah dibuka bearing aus. Diperbaiki bengkel lapangan. {dt}",
    ]),
    ("SRP", "Mechanical", "V-Belt", "Replace", False, [
        "V-belt prime mover {a} putus, ganti set belt baru. {dt}.",
        "{a} belt slip & 1 putus. Ganti V-belt 3 pcs dan setel tension. {dt}",
    ]),
    ("SRP", "Mechanical", "Downhole Pump", "Workover", False, [
        "{a} produksi turun drastis, dyno card menunjukkan pump worn (fluid pound). Ganti downhole pump. {dt}.",
    ]),
    # ---------------- PCP ----------------
    ("PCP", "Mechanical", "Stator", "Workover", False, [
        "PCP {a} torque tinggi lalu turun, produksi 0. Stator aus/terkelupas. Ganti pompa PCP via workover. {dt}.",
        "{a} stator PCP rusak (elastomer swell). Rig masuk ganti rotor-stator. {dt}",
    ]),
    ("PCP", "Electrical", "Drive Head Motor", "Replace", False, [
        "Motor drive head PCP {a} panas & trip thermal. Motor diganti unit spare. {dt}.",
    ]),
    # ---------------- Steam Generator ----------------
    ("Steam Generator", "Leak/Corrosion", "Convection Tube", "Repair", True, [
        "{a} tube leak di convection section, steam keluar dari casing. Unit di-shutdown, area dibarikade, tube di-plug. {dt}.",
        "Kebocoran tube {a}, ada semburan uap panas. SD emergency, perbaikan welding tube setelah cooling down. {dt}",
    ]),
    ("Steam Generator", "Instrumentation/Control", "Flame Scanner", "Replace", False, [
        "{a} trip flame failure berulang. Flame scanner kotor/rusak, diganti baru. Burner normal. {dt}.",
        "{a}: burner flame-out, cek fuel gas pressure normal, ternyata UV scanner error. Ganti scanner. {dt}",
    ]),
    ("Steam Generator", "Mechanical", "Feedwater Pump", "Repair", False, [
        "Feedwater pump {a} vibrasi tinggi, bearing diganti. Generator sempat turun rate. {dt}.",
    ]),
    # ---------------- Flowline ----------------
    ("Flowline", "Leak/Corrosion", "Pipe", "Repair", True, [
        "Flowline {a} bocor (pinhole) akibat korosi internal, tumpahan ±{n} bbl ke ROW. Clamp sementara + clean up. {dt}.",
        "{a} leak di low point, ada genangan minyak. Pasang leak clamp, laporkan ke HSE. {dt}",
    ]),
    ("Flowline", "Flow Assurance", "Pipe", "Clean/Flush", False, [
        "Flowline {a} tekanan naik, indikasi plugging parafin. Pigging + hot oil, tekanan normal. {dt}.",
        "{a} buntu wax, dilakukan hot oiling. {dt}",
    ]),
    # ---------------- Separator ----------------
    ("Separator", "Instrumentation/Control", "Level Controller", "Repair", False, [
        "Separator {a} high level alarm, LCV tidak membuka. Kalibrasi level transmitter + perbaiki positioner LCV. {dt}.",
        "{a}: level control hunting, positioner LCV rusak, diganti. Produksi GS sempat di-cut. {dt}",
    ]),
    ("Separator", "Leak/Corrosion", "Gasket", "Replace", True, [
        "Rembesan di flange manway {a}, gas detector bunyi sebentar (H2S {n} ppm). Area diisolasi, gasket diganti. {dt}.",
    ]),
    # ---------------- Gas Compressor ----------------
    ("Gas Compressor", "Mechanical", "Bearing", "Repair", False, [
        "Kompresor {a} trip high vibration. Bearing sisi drive diganti. {dt}.",
        "{a} vibrasi naik ke {n} mm/s, bearing aus. Overhaul parsial. {dt}",
    ]),
    ("Gas Compressor", "Leak/Corrosion", "Mechanical Seal", "Replace", True, [
        "Seal kompresor {a} bocor gas, LEL detector alarm. Unit SD, mechanical seal diganti. {dt}.",
    ]),
    # ---------------- Water Injection Pump ----------------
    ("Water Injection Pump", "Mechanical", "Plunger", "Replace", False, [
        "Pompa injeksi {a} plunger aus, discharge pressure drop. Ganti plunger & packing. {dt}.",
    ]),
    ("Water Injection Pump", "Process/Trip", "Suction", "Adjust/Reset", False, [
        "{a} trip low suction pressure karena level tangki rendah. Isi tangki, reset pompa. {dt}.",
    ]),
    # ---------------- PM (bukan kegagalan) ----------------
    ("SRP", "Preventive Maintenance", "Pumping Unit", "Adjust/Reset", False, [
        "PM rutin pumping unit {a}: greasing, cek alignment, setel counterbalance. {dt}.",
    ]),
    ("ESP", "Preventive Maintenance", "VSD", "Adjust/Reset", False, [
        "PM VSD {a}: bersihkan filter udara, cek koneksi terminal, thermal scan OK. {dt}.",
    ]),
]

NOISE = [
    "", "", "", " Sumur sebelahnya aman.", " Info ke foreman.", " Mohon follow up PO spare.",
    " Kondisi hujan, akses jalan licin.", " Cek SRP lain di pad yg sama normal.",
    " Lapor via radio ke control room.", " Ref WO sebelumnya.",
]

ASSET_POOL = {
    "ESP": [f"SR-{i:03d}" for i in range(1, 61)] + [f"ML-{i:03d}" for i in range(1, 31)],
    "SRP": [f"KN-{i:03d}" for i in range(1, 181)],
    "PCP": [f"ML-{i:03d}" for i in range(31, 51)],
    "Steam Generator": [f"SG-KN-{i:02d}" for i in range(1, 13)],
    "Flowline": [f"FL-KN-{i:03d}" for i in range(1, 40)] + [f"FL-SR-{i:03d}" for i in range(1, 25)],
    "Separator": ["V-SR1-101", "V-SR1-102", "V-KN2-101", "V-ML1-101"],
    "Gas Compressor": ["K-ML1-201", "K-ML1-202", "K-SR1-201"],
    "Water Injection Pump": ["P-SR1-301", "P-SR1-302", "P-KN1-301"],
}
# "bad actor": sumur/aset yang sering rusak (supaya analisis Pareto menarik)
BAD_ACTORS = {"ESP": ["SR-014", "SR-027", "SR-041"], "SRP": ["KN-077", "KN-112"], "Flowline": ["FL-KN-019"]}
AREA = {"SR": "Seruni", "ML": "Melati", "KN": "Kenanga"}
SCENARIO_WEIGHTS = [6, 9, 6, 5, 3, 10, 6, 3, 4, 3, 3, 1, 2, 3, 1, 4, 3, 2, 1, 2, 1, 1, 1, 3, 2]


def area_of(asset: str) -> str:
    for code, name in AREA.items():
        if code in asset:
            return name
    raise ValueError(asset)


def gen_work_orders(n: int = 400) -> None:
    rows, truth = [], []
    start = date(2026, 1, 1)
    for i in range(n):
        sc = rng.choices(SCENARIOS, weights=SCENARIO_WEIGHTS)[0]
        eq, fcat, comp, act, safety, templates = sc
        pool = ASSET_POOL[eq]
        if eq in BAD_ACTORS and fcat != "Preventive Maintenance" and rng.random() < 0.35:
            asset = rng.choice(BAD_ACTORS[eq])
        else:
            asset = rng.choice(pool)
        # tren: rod part meningkat sejak Juli (bahan analisis)
        day = rng.randint(0, 272)
        if comp == "Sucker Rod" and rng.random() < 0.5:
            day = rng.randint(181, 272)
        tgl = start + timedelta(days=day)
        dt_txt, dt_h = downtime_phrase()
        if fcat == "Preventive Maintenance":
            h = rng.choice([1, 2, 3])
            dt_txt, dt_h = f"unit stop {h} jam selama PM", float(h)
        text = rng.choice(templates).format(a=asset, dt=dt_txt, amp=rng.choice([20, 30, 35, 40]),
                                            n=rng.choice([3, 5, 8, 12, 15, 2450, 3100]))
        text += rng.choice(NOISE)
        # sesekali huruf kecil semua / singkatan untuk realisme
        if rng.random() < 0.15:
            text = text.lower()
        wo_id = f"WO-26-{10000 + i * 7 + rng.randint(0, 6)}"
        rows.append({"wo_id": wo_id, "tanggal": tgl.isoformat(), "area": area_of(asset),
                     "dilaporkan_oleh": rng.choice(TECHS), "deskripsi": text})
        truth.append({"wo_id": wo_id, "asset_id": asset, "equipment_type": eq, "failure_category": fcat,
                      "component": comp, "action_category": act, "downtime_hours": round(dt_h, 2),
                      "safety_flag": safety})
    order = sorted(range(n), key=lambda k: rows[k]["tanggal"])
    _write_csv(RAW / "work_orders.csv", [rows[k] for k in order])
    _write_csv(EVAL / "work_orders_truth.csv", [truth[k] for k in order])


# ---------------------------------------------------------------------------
# 2. HSE INCIDENTS
# ---------------------------------------------------------------------------
# Definisi (juga dipakai di labsheet sebagai "guideline klasifikasi"):
#  Near Miss               : tidak ada cedera & tidak ada kerusakan, tetapi berpotensi
#  First Aid Case (FAC)    : cedera ringan, cukup P3K, langsung kembali bekerja
#  Medical Treatment (MTC) : butuh penanganan tenaga medis (jahitan, obat resep), tidak kehilangan hari kerja
#  Lost Time Injury (LTI)  : pekerja tidak bisa bekerja >= 1 shift/hari berikutnya
#  Property Damage         : kerusakan aset/kendaraan tanpa cedera
#  Environmental Spill     : tumpahan minyak/air terproduksi ke lingkungan

HAZARD_CUES = {
    "H2S/Gas": ["gas detector personal berbunyi {n} ppm H2S saat membuka hatch tangki", "terhirup bau gas saat bleed-off di wellhead, detector menunjukkan {n} ppm H2S"],
    "Hot Work/Fire": ["percikan las mengenai kain majun dan sempat menyala", "saat pekerjaan grinding, percikan api mengenai ceceran minyak"],
    "Working at Height": ["pekerja di platform separator (±{n} m) tidak mengaitkan full body harness", "tangga portable bergeser saat dipakai naik ke tangki"],
    "Dropped Object": ["kunci pipa jatuh dari monkey board saat pekerjaan rig", "baut jatuh dari pipe rack ketika lifting"],
    "Vehicle/Driving": ["kendaraan operasional tergelincir di jalan tanah licin dekat pad {w}", "pick-up mundur menyenggol pagar wellhead {w}"],
    "Steam/Hot Surface": ["kebocoran fitting steam line di {w}, uap panas menyembur ke arah jalur pejalan kaki", "pekerja bekerja dekat flowline panas tanpa sarung tangan tahan panas di sumur steamflood {w}"],
    "Electrical": ["panel VSD terbuka tanpa LOTO saat pengecekan", "kabel ekstensi terkelupas dipakai di area basah"],
    "Manual Handling": ["pekerja mengangkat valve 40 kg tanpa alat bantu", "drum chemical dipindahkan secara manual oleh satu orang"],
    "Pinch Point": ["pekerja memposisikan tangan di antara rod elevator dan tubing saat tripping", "V-belt pumping unit dipasang tanpa mematikan prime mover"],
}
OUTCOMES = {
    "Near Miss": ["Tidak ada korban maupun kerusakan. Pekerjaan dihentikan dan dilakukan toolbox talk ulang.",
                  "Beruntung tidak ada yang cedera dan tidak ada aset rusak. Dilaporkan sebagai pembelajaran.",
                  "Tidak terjadi cedera; supervisor menghentikan pekerjaan sebelum terjadi kontak."],
    "First Aid Case": ["Korban mengalami lecet ringan, dibersihkan dan diberi plester di P3K lokasi lalu kembali bekerja.",
                       "Iritasi ringan pada mata, dibilas eyewash station, korban melanjutkan pekerjaan.",
                       "Memar kecil, dikompres dingin oleh first aider, lanjut bekerja di shift yang sama."],
    "Medical Treatment Case": ["Korban dibawa ke klinik, luka dijahit 4 jahitan dan diberi obat resep dokter. Masuk kerja keesokan harinya seperti biasa.",
                               "Dirujuk ke dokter perusahaan dan mendapat antibiotik resep; tidak ada hari kerja hilang.",
                               "Mendapat perawatan luka bakar derajat 1 oleh dokter klinik, kembali bekerja shift berikutnya."],
    "Lost Time Injury": ["Korban dirawat di RS dan mendapat surat istirahat {n} hari dari dokter.",
                         "Terjadi patah tulang jari, korban tidak dapat bekerja selama {n} hari.",
                         "Korban mengalami luka bakar derajat 2 dan menjalani perawatan, absen kerja {n} hari."],
    "Property Damage": ["Tidak ada cedera, namun peralatan di lokasi rusak dan harus diganti, estimasi biaya Rp {n} juta.",
                        "Tidak ada korban; aset perusahaan mengalami kerusakan dan perlu perbaikan oleh workshop.",
                        "Tidak ada yang cedera, tetapi housing instrumen pecah dan perlu penggantian."],
    "Environmental Spill": ["Tumpahan minyak ±{n} barel keluar ke area tanah di luar bund wall, dilakukan oil boom & clean up.",
                            "Air terproduksi ±{n} barel meluap dari pit ke parit, dilakukan containment.",
                            "Ceceran minyak ±{n} barel mencapai saluran drainase, tim tanggap darurat dikerahkan."],
}
SEVERITY = {"Near Miss": "Rendah", "First Aid Case": "Rendah", "Medical Treatment Case": "Sedang",
            "Property Damage": "Sedang", "Lost Time Injury": "Tinggi", "Environmental Spill": "Tinggi"}
TYPE_W = {"Near Miss": 30, "First Aid Case": 22, "Medical Treatment Case": 14, "Lost Time Injury": 6,
          "Property Damage": 14, "Environmental Spill": 10}
COMPAT = {  # bahaya yang masuk akal per jenis insiden
    "Environmental Spill": ["Steam/Hot Surface", "Vehicle/Driving", "Hot Work/Fire"],
    "Property Damage": ["Vehicle/Driving", "Electrical", "Dropped Object", "Hot Work/Fire"],
}


def gen_hse(n: int = 120) -> None:
    rows, truth = [], []
    for i in range(n):
        itype = rng.choices(list(TYPE_W), weights=list(TYPE_W.values()))[0]
        hazards = COMPAT.get(itype, list(HAZARD_CUES))
        hz = rng.choice(hazards)
        well = rng.choice(ASSET_POOL["SRP"] + ASSET_POOL["ESP"])
        cue = rng.choice(HAZARD_CUES[hz]).format(n=rng.choice([3, 4, 6, 8, 12, 15, 25]), w=well)
        if itype == "Environmental Spill":
            cue = rng.choice(["flowline " + well + " bocor karena korosi", "valve drain tangki tidak tertutup penuh setelah sampling",
                              "truk vakum tergelincir dan hose terlepas saat transfer"])
        outcome = rng.choice(OUTCOMES[itype]).format(n=rng.choice([2, 3, 5, 7, 10, 14, 25, 40]))
        tgl = date(2026, 1, 1) + timedelta(days=rng.randint(0, 272))
        jam = f"{rng.randint(6, 22):02d}.{rng.choice(['00', '15', '30', '45'])}"
        lokasi = rng.choice(["GS-SR1", "GS-KN1", "GS-KN2", "GS-ML1", f"Pad sumur {well}", "Workshop Kenanga", "Jalan akses Seruni"])
        narr = (f"Pada {tgl.strftime('%d/%m/%Y')} pukul {jam} di {lokasi}, {cue}. {outcome}")
        if rng.random() < 0.3:
            narr += rng.choice([" Tindakan: refresh training JSA.", " Investigasi oleh supervisor HSE.", " Kontraktor terkait diberi teguran."])
        iid = f"HSE-26-{i + 1:04d}"
        rows.append({"incident_id": iid, "tanggal": tgl.isoformat(), "lokasi": lokasi, "narasi": narr})
        truth.append({"incident_id": iid, "incident_type": itype, "hazard": hz if itype != "Environmental Spill" else "Spill/Release",
                      "severity": SEVERITY[itype]})
    _write_csv(RAW / "hse_incidents.csv", rows)
    _write_csv(EVAL / "hse_incidents_truth.csv", truth)


# ---------------------------------------------------------------------------
# 3. DAILY REPORT GS-SR1 JULI 2026 (teks panjang untuk uji long context)
# ---------------------------------------------------------------------------

EVENTS = {
    3: ("SR-014 trip OL, ESP di-restart setelah flushing", 85, None),
    6: ("PM separator V-SR1-102, produksi dialihkan ke V-SR1-101", 0, None),
    9: ("SR-027 underload, setting VSD diturunkan ke 50 Hz", 60, None),
    14: ("High level alarm V-SR1-101, LCV macet. Produksi GS di-cut 4 jam", 320, None),
    17: ("Hujan lebat, akses ke SR-041 terputus, sumur tidak bisa dicek 1 shift", 40, None),
    19: ("SR-041 kabel ESP ground fault, menunggu rig workover", 110, None),
    20: ("SR-041 masih off menunggu rig", 110, None),
    21: ("Rig masuk SR-041, ganti power cable", 110, None),
    22: ("Gas detector di SR-027 menunjukkan H2S 12 ppm saat pengambilan sampel; area dievakuasi sementara, pekerjaan dilanjutkan setelah ventilasi dan pemakaian SCBA", 0, "H2S"),
    25: ("Water injection pump P-SR1-301 trip low suction, reset setelah level tangki naik", 0, None),
    28: ("Kunjungan audit internal HSE, temuan: 2 fire extinguisher kedaluwarsa", 0, None),
    30: ("SR-014 trip lagi (OL), flushing kedua bulan ini; usulan evaluasi sand control", 90, None),
}


def gen_daily_report() -> None:
    base_oil, base_water, base_gas = 4380, 39200, 2.15
    lines = ["# Laporan Harian Operasi — Gathering Station GS-SR1 (Area Seruni)",
             "", "Periode: 1–31 Juli 2026  ", "Disusun oleh: Shift Supervisor GS-SR1  ",
             "Klasifikasi: Internal — data FIKTIF untuk pelatihan", ""]
    truth = []
    for d in range(1, 32):
        tgl = date(2026, 7, d)
        deferred = EVENTS.get(d, (None, 0, None))[1]
        oil = int(base_oil - deferred + rng.randint(-60, 60) - d * 3)
        water = int(base_water + rng.randint(-500, 500) + d * 25)
        gas = round(base_gas + rng.uniform(-0.08, 0.08), 2)
        wells_on = 54 - (1 if d in (19, 20, 21) else 0) - (1 if d in (3, 30) else 0)
        wc = water / (water + oil) * 100
        ev = EVENTS.get(d, (None, 0, None))[0]
        sup = rng.choice(["Hendra Saputra", "Rizal Munandar", "Agus Pratama"])
        para = [f"## {tgl.strftime('%A, %d %B %Y').replace('Monday','Senin').replace('Tuesday','Selasa').replace('Wednesday','Rabu').replace('Thursday','Kamis').replace('Friday','Jumat').replace('Saturday','Sabtu').replace('Sunday','Minggu').replace('July','Juli')}", "",
                f"Supervisor shift: {sup}. Sumur aktif {wells_on} dari 55 sumur ESP terhubung ke GS-SR1. "
                f"Produksi minyak bersih tercatat {_id(oil)} bopd, air terproduksi {_id(water)} bwpd "
                f"(water cut {_id(wc, 1)}%), dan gas {_id(gas, 2)} MMscfd.",
                ]
        routine = rng.sample([
            "Safety talk pagi membahas penggunaan APD dan prosedur PTW.",
            "Pengecekan rutin tekanan header produksi dalam batas normal.",
            "Sampling BS&W dilakukan pukul 10.00 dan 16.00, hasil sesuai spesifikasi.",
            "Pigging rutin flowline FL-SR-007 berjalan lancar.",
            "Operator melakukan patroli sumur pad A dan pad C, tidak ada temuan.",
            "Chemical injection demulsifier dijaga pada 25 ppm.",
            "Level tangki pengumpul stabil di 60–70%.",
            "Housekeeping area pompa transfer.",
        ], k=3)
        para.append(" ".join(routine))
        if ev:
            para.append(f"**Kejadian:** {ev}." + (f" Estimasi produksi tertunda (deferred) {deferred} bbl." if deferred else ""))
        else:
            para.append("Tidak ada kejadian signifikan.")
        lines += para + [""]
        truth.append({"tanggal": tgl.isoformat(), "oil_bopd": oil, "water_bwpd": water, "gas_mmscfd": gas,
                      "wells_on": wells_on, "deferred_bbl": deferred, "event": ev or ""})
    (RAW / "daily_reports").mkdir(parents=True, exist_ok=True)
    (RAW / "daily_reports" / "GS-SR1_2026-07.md").write_text("\n".join(lines), encoding="utf-8")
    _write_csv(EVAL / "daily_gs_sr1_2026-07.csv", truth)


def _id(x: float, dec: int = 0) -> str:
    """Format angka gaya Indonesia: 4.215 dan 2,15"""
    return f"{x:,.{dec}f}".replace(",", "#").replace(".", ",").replace("#", ".")


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"  tulis {path.relative_to(ROOT)} ({len(rows)} baris)")


if __name__ == "__main__":
    gen_work_orders()
    gen_hse()
    gen_daily_report()
