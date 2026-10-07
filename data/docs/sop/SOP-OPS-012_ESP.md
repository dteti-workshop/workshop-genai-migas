---
doc_id: SOP-OPS-012
title: Start-up, Monitoring, dan Troubleshooting Electric Submersible Pump (ESP)
doc_type: SOP
revision: 4
effective_date: 2025-09-01
status: active
owner: Departemen Production Operations
access_group: all
---

# SOP-OPS-012 Rev. 4 — Start-up, Monitoring, dan Troubleshooting ESP

> Dokumen FIKTIF untuk keperluan pelatihan.

## 1. Tujuan

Menjaga umur pakai (run life) ESP dan mencegah kerusakan motor/kabel akibat start-up atau restart yang tidak tepat.

## 2. Pemeriksaan Sebelum Start-up

1. Pastikan izin kerja PTW-E aktif bila membuka panel VSD (lihat SOP-HSE-004).
2. Lakukan **megger test** sistem kabel + motor dari junction box permukaan:
   - ≥ 100 MΩ : baik, boleh start.
   - 10–100 MΩ : boleh start dengan persetujuan Petroleum Engineer, monitor ketat.
   - < 10 MΩ : **jangan start**, laporkan sebagai indikasi kerusakan kabel/motor.
3. Periksa keseimbangan resistansi antar fasa (phase-to-phase), selisih maksimum 5%.
4. Pastikan valve wing dan flowline terbuka (hindari start melawan valve tertutup / dead-head).

## 3. Prosedur Start-up

1. Start VSD pada frekuensi **35 Hz**.
2. Naikkan frekuensi bertahap **5 Hz setiap 5 menit** hingga frekuensi target (umumnya 50–60 Hz).
3. Catat arus motor, tegangan, dan pump intake pressure (PIP) setiap 15 menit selama **2 jam pertama**.
4. Arus motor normal berada pada 70–100% dari nameplate. Arus > 110% atau < 60% secara terus-menerus harus dilaporkan.

## 4. Aturan Restart Setelah Trip

| Jenis trip | Tindakan sebelum restart | Batas restart |
|---|---|---|
| Overload (OL) | Cek grafik arus (amp chart), megger kabel/motor. Bila megger baik dan dicurigai pasir/emulsi, lakukan flushing | **Maksimal 3 kali dalam 24 jam**. Setelah itu wajib eskalasi ke Petroleum Engineer |
| Underload (UL) | **Tunggu minimal 30 menit** agar fluid level naik. Pertimbangkan menurunkan frekuensi 2–5 Hz | Maksimal 3 kali dalam 24 jam |
| Ground Fault | **Jangan restart.** Lakukan megger. Bila < 10 MΩ, ajukan pulling job | Tidak boleh restart sebelum hasil megger baik |
| Phase Imbalance (> 5%) | Cek tegangan suplai dan transformer step-up | Restart setelah penyebab diperbaiki |
| Overtemperature VSD | Bersihkan filter udara panel, cek kipas | Restart setelah suhu normal |

## 5. Indikasi Masalah Umum

- **Pasir (sand)**: arus naik dan berfluktuasi, sering OL. Pertimbangkan evaluasi sand control bila OL akibat pasir terjadi **≥ 2 kali dalam 30 hari**.
- **Gas lock / gas interference**: arus turun dan berfluktuasi, sering UL, PIP rendah.
- **Kabel rusak**: megger rendah, alarm ground fault di VSD.

## 6. Kriteria Bad Actor

Sumur ESP dengan **≥ 3 kegagalan (trip yang membutuhkan intervensi) dalam 90 hari** dikategorikan *bad actor* dan wajib dianalisis akar masalahnya (RCA) oleh tim Petroleum Engineering dalam rapat mingguan.

## 7. Pencatatan

Setiap trip, restart, dan hasil megger dicatat di sistem work order dengan kode peralatan dan durasi downtime.

## 8. Referensi

- MAN-VSD-FD500 Manual Variable Speed Drive FD-500 (daftar kode alarm)
- SOP-HSE-007 Lock Out Tag Out
