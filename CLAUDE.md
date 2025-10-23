# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Deskripsi Proyek

Dashboard web analytics untuk mengelola dan menganalisis data pelanggan WiFi. Aplikasi Flask dengan frontend Bootstrap yang menyediakan visualisasi data, analisis kinerja sales, tracking PSB (Pemasangan Sambungan Baru), validasi SOP, dan deteksi kualitas data.

## Arsitektur Aplikasi

### Backend (Flask)
- **File utama**: `app.py` - Flask server dengan API endpoints
- **Data processing**: Pandas untuk manipulasi data CSV
- **File parsing**: `parse_html_data.py` - Parsing HTML table dari `.xls` ke CSV
- **History Manager**: `history_manager.py` - SQLite-based snapshot tracking (NEW!)

### Frontend
- **Template**: `templates/dashboard.html` - Single-page application dengan multiple sections
- **Libraries**: Bootstrap 5, Chart.js, Leaflet.js, Font Awesome

### Data Flow
1. **Input**: File Excel/CSV di-upload melalui web UI atau file `data-wifi.xls`
2. **Processing**:
   - `parse_html_data.py` mengekstrak HTML table dari `.xls` ke CSV
   - `app.py` membaca `data-wifi-clean.csv` dan memproses dengan Pandas
   - Automatic deduplication berdasarkan `ID Pelanggan`
   - Smart header detection untuk menangani berbagai format file
3. **Output**: JSON responses untuk frontend, CSV export untuk user

### File Konfigurasi
- **sop_rules.json**: Menyimpan aturan SOP per sales (jatuh tempo, insentif, lokasi)
- **data-wifi-clean.csv**: Data pelanggan yang sudah di-clean (auto-generated)
- Backup files: `data-wifi-clean_backup_YYYYMMDD_HHMMSS.csv` (auto-created sebelum update)

## Command Reference

### Development
```bash
# Menjalankan dashboard (Windows)
python app.py
# atau
start_dashboard.bat

# Parsing HTML data dari .xls ke CSV
python parse_html_data.py
```

### Testing & Debugging
```bash
# Test Flask server
curl http://localhost:5000/api/overview

# Debug mode sudah aktif di app.py (debug=True)
# Server akan auto-reload saat ada perubahan file
```

## API Endpoints

### Data Management
- `POST /api/upload` - Upload dan merge multiple Excel/CSV files
- `GET /api/overview` - Overview stats, data quality checks
- `GET /api/customers` - Customer list dengan filter
- `GET /api/filters` - Available filter options

### Analytics
- `GET /api/revenue-analysis` - Revenue breakdown by package/location/sales
- `GET /api/registration-analysis` - Registration trends dan growth analysis
- `GET /api/psb-check` - PSB (Pemasangan Sambungan Baru) tracking
- `GET /api/blacklist` - Customer yang never paid (Pembayaran Terakhir = "Data Belum Ada")
- `GET /api/map-data` - Geo coordinates untuk mapping

### SOP Management
- `GET /api/sop-rules` - Get all SOP rules
- `POST /api/sop-rules` - Add new SOP rule
- `PUT /api/sop-rules/<sales>` - Update SOP rule
- `DELETE /api/sop-rules/<sales>` - Delete SOP rule
- `GET /api/violations` - Get all SOP violations
- `GET /api/locations` - Get unique locations for SOP form

### History & Tracking (NEW!)
- `GET /api/history` - Get all historical snapshots (last 50)
- `GET /api/history/<date>` - Get specific snapshot by date (YYYY-MM-DD)
- `GET /api/history/compare?date1=X&date2=Y` - Compare two snapshots
- `GET /api/history/trend?days=N` - Get trend data for last N days
- `POST /api/history/cleanup` - Clean up old snapshots (keep N most recent)

## Struktur Data

### Required Columns (data-wifi-clean.csv)
File CSV harus memiliki kolom-kolom berikut:
- **ID Pelanggan** (required) - Unique identifier, digunakan untuk deduplication
- Nama Pelanggan, Tlp, Alamat
- Nama Langganan, Harga, Status Langganan (On/Off)
- Tanggal Registrasi, Jatuh Tempo
- Nama Sales, Insentif Sales, Metode Insentif
- Nama Lokasi, Nama Router, Jenis Koneksi
- Titik Koordinat Lokasi (format: "lat,lng")
- Foto KTP (URL)
- Pembayaran Terakhir

### Data Quality Checks
Aplikasi secara otomatis mendeteksi:
1. **Missing KTP**: Foto KTP URL hanya base path atau kosong
2. **Invalid Phone**: No HP null, "01", atau < 8 digit
3. **Missing Coordinates**: Koordinat tidak valid atau 0,0

## Fitur Penting

### 1. Multi-File Upload & Merge
- Support .xls, .xlsx, .csv
- Smart header detection (mencari row dengan "ID Pelanggan")
- Auto deduplication based on ID Pelanggan
- Fallback ke multiple parsing engines (xlrd, openpyxl, CSV)
- Automatic backup sebelum overwrite

### 2. PSB Tracking
- Filter by date range dan sales
- Calculate potential revenue dan fee per sales
- Export functionality
- **Use Case**: Track pemasangan yang di-close fiktif tapi belum bayaran

### 3. SOP Validation
- Store rules per sales (jatuh tempo, insentif array, lokasi array)
- Validate data against rules
- Severity levels: high (jatuh tempo), medium (insentif), low (lokasi)
- Support multiple insentif values (e.g., [20000, 30000])

### 4. Blacklist Detection
- Find customers yang never paid (Pembayaran Terakhir = "Data Belum Ada")
- Filter by minimum months unpaid
- Calculate potential loss

### 5. History & Tracking (NEW!)
- Automatic snapshot saving setiap upload
- SQLite database untuk persistent storage
- Compare 2 tanggal untuk melihat perubahan
- Trend visualization (30 hari terakhir)
- Metrics tracked: customers, revenue, quality issues, sales performance
- Use Case: Monitor growth trends, identify data quality issues, compare performance periods
- Database: `history.db` (auto-created on first upload)
- Untuk detail lengkap, lihat: `HISTORY_TRACKING.md`

## Development Notes

### JSON Serialization
- Custom `CustomJSONProvider` untuk handle NaN/inf values
- Semua numeric NaN dikonversi ke `None` sebelum return JSON
- Helper function `clean_for_json()` untuk recursive cleaning

### Date Parsing
Multiple format support:
- YYYY-MM-DD
- DD-Month-YYYY (e.g., 16-October-2025)
- Pandas auto-parsing sebagai fallback

### Error Handling
- File upload: Multiple engine fallback (xlrd → openpyxl → CSV dengan encoding fallback)
- Smart error messages dengan suggestions (e.g., kolom mirip jika ID Pelanggan tidak ada)
- Try-except di setiap API endpoint dengan traceback logging

### Performance
- Customer list dibatasi 100 rows untuk UI
- Backup files tidak di-cleanup otomatis (perlu manual cleanup jika storage penuh)

## Common Development Tasks

### Menambah Column Validation Baru
1. Edit `validate_data_against_sop()` di app.py:1388
2. Tambahkan validation logic di loop per customer
3. Update `violations_by_type` counter
4. Update frontend di `dashboard.html` untuk menampilkan violation baru

### Menambah API Endpoint Baru
1. Tambahkan `@app.route()` di app.py
2. Load data dengan `load_data()`
3. Process dengan Pandas
4. Return dengan `jsonify(clean_for_json(data))`
5. Update frontend untuk consume endpoint baru

### Menambah Filter Baru
1. Update `get_customers()` di app.py:716 untuk apply filter
2. Update `get_filters()` di app.py:778 untuk return options
3. Update frontend filter UI di dashboard.html
