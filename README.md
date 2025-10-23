# Dashboard Analytics WiFi

Dashboard web interaktif untuk menganalisis data pelanggan WiFi dengan visualisasi lengkap.

## Fitur Dashboard

### 1. Overview Dashboard
- Total pelanggan dan statistik status (aktif/nonaktif)
- Pendapatan bulanan total dan rata-rata per pelanggan
- **Data Quality Alert (NEW!)** - Deteksi otomatis data tidak lengkap:
  - Pelanggan tanpa foto KTP (URL hanya base path)
  - Pelanggan dengan no HP tidak valid (null, "01", atau < 8 digit)
  - Modal detail list pelanggan bermasalah
  - Export data tidak lengkap ke CSV
- Distribusi paket langganan
- Analisis lokasi dan router
- Grafik status pelanggan

### 2. Analisis Pendapatan
- Pendapatan per paket langganan
- Distribusi range harga
- Top lokasi berdasarkan pendapatan
- Total revenue analysis

### 3. Data Pelanggan
- Tabel data pelanggan yang dapat difilter
- Filter berdasarkan: Status, Paket, Lokasi, Sales
- Export data ke CSV
- Menampilkan hingga 100 data pelanggan

### 4. Peta Lokasi
- Visualisasi geografis pelanggan dengan koordinat
- Marker berwarna (hijau = aktif, merah = nonaktif)
- Info popup untuk setiap pelanggan

### 5. Performa Sales
- Analisis performa setiap sales
- Jumlah pelanggan per sales
- Total pendapatan per sales
- Top 10 sales terbaik

### 6. Analisis Registrasi
- **Analisis periode 20-30 September 2025**
- **Pola registrasi per hari dalam seminggu** (Insight: 69% registrasi di hari Jumat!)
- **Perbandingan September vs Oktober 2025**
- **Top 10 bulan dengan registrasi terbanyak**
- **Paket terpopuler per periode**
- **Tren registrasi harian dan bulanan**

### 7. Cek PSB - Pemasangan Sambungan Baru (NEW!)
- **Date range picker** - Pilih rentang tanggal custom
- **Quick select buttons** - Pilih cepat: 20-30 Sept, September Penuh, Oktober, Bulan Ini, 7 Hari Terakhir
- **Filter per sales** - Lihat PSB per sales atau semua sales
- **Summary cards** - Total PSB, Potensi Revenue, Jumlah Sales, Rata-rata per hari
- **Breakdown per sales** - Progress bar & detail revenue per sales
- **Chart paket terpopuler** - Visualisasi paket yang paling banyak dipasang
- **Tabel detail pelanggan** - Semua pelanggan yang pasang di periode tersebut
- **Export to CSV** - Download data PSB untuk periode yang dipilih

**Use Case:**
Fitur ini sangat berguna untuk tracking pemasangan yang sudah di-close fiktif tapi belum bayaran.
Contoh: Cek berapa pelanggan yang pasang oleh Sales CEPI di tanggal 20-30 September.

**Contoh Hasil:**
- **20-30 Sept 2025**: 15 PSB (CEPI: 9, ENONGS: 6) - Potensi Rp 2,420,000
- **September Penuh**: 59 PSB (CEPI: 37, ENONGS: 22) - Potensi Rp 8,910,000
- **Oktober Penuh**: 27 PSB (CEPI: 18, ENONGS: 9) - Potensi Rp 4,110,000

## Cara Menjalankan

### Persiapan
1. Pastikan file `data-wifi.xls` ada di folder yang sama
2. Pastikan Python 3.9+ sudah terinstall
3. Install dependencies yang dibutuhkan (sudah dilakukan)

### Menjalankan Dashboard

**Windows:**
```bash
python app.py
```

**Atau gunakan script:**
```bash
start_dashboard.bat
```

Dashboard akan berjalan di: **http://localhost:5000**

### Akses Dashboard
1. Buka browser (Chrome, Firefox, Edge)
2. Kunjungi: http://localhost:5000
3. Dashboard akan langsung menampilkan data overview

## Struktur File

```
CSV_REPORT/
├── data-wifi.xls              # File data asli (HTML table)
├── data-wifi-clean.csv        # File data yang sudah diparse
├── app.py                     # Backend Flask application
├── parse_html_data.py         # Script parsing HTML ke CSV
├── analyze_data.py            # Script analisis data
├── start_dashboard.bat        # Script untuk start dashboard
├── templates/
│   └── dashboard.html         # Frontend dashboard
└── README.md                  # Dokumentasi ini
```

## Teknologi yang Digunakan

### Backend
- **Flask** - Web framework Python
- **Pandas** - Data analysis dan processing
- **BeautifulSoup4** - HTML parsing

### Frontend
- **Bootstrap 5** - UI framework
- **Chart.js** - Visualisasi grafik interaktif
- **Leaflet.js** - Peta interaktif
- **Font Awesome** - Icons

## Statistik Data

Berdasarkan data saat ini:
- **Total Pelanggan:** 1,169 pelanggan
- **Pelanggan Aktif:** 1,090 (93.24%)
- **Pelanggan Nonaktif:** 79 (6.76%)
- **Paket Terpopuler:** H-MEKAR PRIME (767 pelanggan)

### Data Quality Status
- **Pelanggan tanpa Foto KTP:** 443 pelanggan
- **Pelanggan dengan No HP Invalid:** 3 pelanggan
- **Total Data Tidak Lengkap:** 445 pelanggan aktif (40.8%)

## Fitur Tambahan

### Export Data
Anda dapat mengekspor data pelanggan yang sudah difilter ke format CSV melalui tombol "Export CSV" di halaman Data Pelanggan.

### Filter Interaktif
Dashboard mendukung filter multi-parameter:
- Status: Aktif/Nonaktif
- Paket Langganan: Semua paket yang tersedia
- Lokasi: Semua lokasi pelanggan
- Sales: Semua nama sales

### Responsive Design
Dashboard dapat diakses melalui desktop, tablet, dan mobile dengan tampilan yang menyesuaikan.

## Troubleshooting

### Dashboard tidak bisa diakses
- Pastikan Python app.py sudah berjalan
- Check port 5000 tidak digunakan aplikasi lain
- Coba akses http://127.0.0.1:5000

### Data tidak muncul
- Pastikan file data-wifi-clean.csv sudah ada
- Jalankan ulang parse_html_data.py jika perlu
- Check console browser untuk error (F12)

### Peta tidak muncul
- Pastikan koneksi internet aktif (untuk load map tiles)
- Check apakah ada koordinat valid di data

## Update Data

Untuk update data pelanggan:
1. Upload file `data-wifi.xls` yang baru
2. Jalankan: `python parse_html_data.py`
3. Refresh browser atau restart aplikasi

## Support & Contact

Untuk pertanyaan atau bantuan, hubungi administrator sistem.
