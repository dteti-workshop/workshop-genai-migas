---
doc_id: MAN-VSD-FD500
title: Manual Operasi Variable Speed Drive FD-500
doc_type: Manual
revision: 1.2
effective_date: 2024-01-15
status: active
owner: Vendor Fiktif-Drive (didistribusikan oleh Dept. Electrical)
access_group: all
---

# Manual Operasi Variable Speed Drive FD-500

Dokumen FIKTIF untuk keperluan pelatihan. Merek dan tipe peralatan tidak nyata.

## Bab 1. Gambaran Umum

FD-500 adalah variable speed drive (VSD) 6-pulse untuk mengendalikan motor ESP 100-500 HP. VSD mengubah frekuensi keluaran (30-70 Hz) sehingga kecepatan pompa dapat disesuaikan dengan kemampuan alir sumur.

Spesifikasi utama: tegangan masuk 380-480 VAC 3 fasa, frekuensi keluaran 30-70 Hz, suhu operasi -10 sampai 50 derajat C, proteksi panel IP54.

## Bab 2. Panel Operator

Panel menampilkan frekuensi aktual, arus motor (A), tegangan keluaran (V), status running/stop, dan kode alarm aktif. Tombol: START, STOP, RESET, MENU, panah naik/turun.

Riwayat 50 alarm terakhir dapat dilihat melalui MENU > HISTORY. Data trending arus 7 hari terakhir dapat diunduh lewat port USB.

## Bab 3. Daftar Kode Alarm dan Fault

| Kode | Nama | Kemungkinan penyebab | Tindakan yang disarankan | Auto-restart |
|---|---|---|---|---|
| F01 | Overcurrent | Hubung singkat keluaran, pompa macet | Cek megger kabel dan motor, jangan reset berulang | Tidak |
| F02 | DC Bus Overvoltage | Lonjakan tegangan suplai, deselerasi terlalu cepat | Cek suplai, perpanjang waktu deselerasi | Ya (1x) |
| F03 | DC Bus Undervoltage | Tegangan suplai turun / hilang fasa | Cek trafo dan suplai PLN/genset | Ya (3x) |
| F07 | Ground Fault | Insulasi kabel atau motor rusak | JANGAN restart. Lakukan megger test. Lihat SOP-OPS-012 | Tidak |
| F11 | Motor Overload (OL) | Beban pompa berlebih: pasir, emulsi, viskositas tinggi | Cek amp chart, megger, pertimbangkan flushing | Tidak |
| F12 | Motor Underload (UL) | Gas lock, inflow rendah, poros patah | Tunggu fluid level naik minimal 30 menit, turunkan frekuensi | Ya, setelah delay 30 menit |
| F15 | Phase Imbalance | Ketidakseimbangan tegangan > 5%, koneksi longgar | Cek terminal dan trafo step-up | Tidak |
| F21 | Heatsink Overtemperature | Filter udara tersumbat, kipas rusak, suhu lingkungan tinggi | Bersihkan filter, cek kipas pendingin | Ya, setelah suhu turun |
| F30 | Communication Loss | Kabel komunikasi SCADA/RTU terputus | Cek kabel dan modul komunikasi; VSD tetap berjalan | Tidak berlaku |

## Bab 4. Prosedur Reset Alarm

1. Identifikasi kode alarm pada layar dan catat di logbook.
2. Untuk alarm yang tidak boleh auto-restart, lakukan investigasi sesuai tabel di Bab 3 sebelum menekan RESET.
3. Tekan RESET selama 3 detik. Bila alarm muncul kembali dalam 10 menit, jangan reset lagi; eskalasi ke teknisi electrical.

## Bab 5. Perawatan

- Bersihkan atau ganti filter udara panel setiap 1 bulan (lebih sering di musim kemarau berdebu).
- Thermal scan terminal daya setiap 3 bulan.
- Kencangkan ulang terminal daya setiap 6 bulan (dengan LOTO, tunggu kapasitor DC bus discharge minimal 5 menit).
- Ganti kipas pendingin setiap 3 tahun.
