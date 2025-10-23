# History & Tracking Feature Documentation

## Overview

Fitur **History & Tracking** memungkinkan Anda untuk menyimpan snapshot data setiap kali upload terjadi, sehingga Anda dapat:
- 📊 Melihat perubahan data dari waktu ke waktu
- 📈 Membandingkan 2 tanggal berbeda untuk melihat trend
- 📉 Menganalisis kenaikan/penurunan metrics utama
- 📋 Menyimpan record lengkap dari setiap update data

## Cara Kerja

### 1. Automatic Snapshot Saving
Setiap kali Anda **upload file Excel/CSV** ke dashboard:
```
File Upload → Data Processing → Metrics Calculation → Snapshot Saved to Database
```

Sistem otomatis akan:
- Extract key metrics dari data baru (total pelanggan, revenue, quality issues, dll)
- Menyimpan snapshot ke database SQLite (`history.db`)
- Menggunakan tanggal upload sebagai ID unik (jika ada 2 upload di hari yang sama, akan di-replace)

### 2. Database Schema

Database menggunakan 3 tabel utama:

#### `snapshots` - Main history records
```sql
- id: Unique identifier
- timestamp: Waktu precise ketika snapshot dibuat
- upload_date: Tanggal upload (YYYY-MM-DD) - unique key
- total_customers: Total pelanggan
- active_customers: Pelanggan aktif
- inactive_customers: Pelanggan nonaktif
- total_revenue: Total revenue bulanan (Rp)
- avg_revenue_per_customer: Rata-rata revenue per pelanggan
- total_packages: Jumlah unique pakets
- quality_issues_count: Total data quality issues
- missing_ktp_count: Pelanggan tanpa KTP foto
- invalid_phone_count: Pelanggan dengan no HP invalid
- missing_coords_count: Pelanggan tanpa koordinat
- top_package: Nama paket paling populer
- top_package_count: Count paket paling populer
- top_location: Lokasi dengan revenue tertinggi
- top_location_revenue: Revenue dari lokasi tertinggi
- active_sales_count: Jumlah sales yang aktif
- total_psb_count: Total PSB (Pemasangan Sambungan Baru)
- raw_data: Raw JSON dari overview stats (backup)
```

#### `sales_snapshots` - Sales metrics per snapshot
```sql
- snapshot_id: Foreign key to snapshots
- sales_name: Nama sales
- customer_count: Jumlah pelanggan
- revenue: Revenue dari sales
- avg_revenue: Average revenue per customer
```

#### `package_snapshots` - Package metrics per snapshot
```sql
- snapshot_id: Foreign key to snapshots
- package_name: Nama paket
- customer_count: Jumlah pelanggan paket ini
- revenue: Revenue dari paket ini
- avg_revenue: Average revenue per customer
```

## API Endpoints

### 1. Get All History Snapshots
```
GET /api/history?limit=50
```

**Response:**
```json
{
  "success": true,
  "total": 15,
  "data": [
    {
      "id": 1,
      "upload_date": "2025-10-23",
      "total_customers": 1169,
      "active_customers": 1090,
      "total_revenue": 23456000,
      "quality_issues_count": 445,
      ...
    },
    ...
  ]
}
```

### 2. Get Specific Snapshot by Date
```
GET /api/history/2025-10-23
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "upload_date": "2025-10-23",
    "total_customers": 1169,
    "active_customers": 1090,
    ...
  }
}
```

### 3. Compare Two Snapshots
```
GET /api/history/compare?date1=2025-10-01&date2=2025-10-23
```

**Response:**
```json
{
  "success": true,
  "data": {
    "date1": "2025-10-01",
    "date2": "2025-10-23",
    "snapshot1": { ... },
    "snapshot2": { ... },
    "changes": {
      "customers": {
        "old": 1150,
        "new": 1169,
        "change": 19,
        "change_pct": 1.65
      },
      "active_customers": {
        "old": 1070,
        "new": 1090,
        "change": 20,
        "change_pct": 1.87
      },
      "revenue": {
        "old": 22500000,
        "new": 23456000,
        "change": 956000,
        "change_pct": 4.25
      },
      "quality_issues": {
        "old": 500,
        "new": 445,
        "change": -55,
        "change_pct": -11.0
      }
    }
  }
}
```

### 4. Get Trend Data (Last N days)
```
GET /api/history/trend?days=30
```

**Response:**
```json
{
  "success": true,
  "total": 15,
  "data": [
    {
      "upload_date": "2025-10-01",
      "total_customers": 1150,
      "total_revenue": 22500000,
      "customer_trend": 0,
      "revenue_trend": 0
    },
    {
      "upload_date": "2025-10-15",
      "total_customers": 1165,
      "total_revenue": 23200000,
      "customer_trend": 15,
      "revenue_trend": 700000
    },
    ...
  ]
}
```

### 5. Cleanup Old Snapshots (Admin)
```
POST /api/history/cleanup
Content-Type: application/json

{
  "keep_count": 100
}
```

**Response:**
```json
{
  "success": true,
  "message": "Cleanup completed, keeping 100 most recent snapshots"
}
```

## Frontend UI - History & Tracking Section

### Components:

#### 1. **Summary Cards**
Menampilkan quick overview:
- Total Snapshots: Berapa banyak history yang disimpan
- Last Updated: Tanggal terakhir ada update
- Total Customers Change: Perubahan jumlah pelanggan (latest vs previous)
- Revenue Change: Perubahan revenue (latest vs previous)

#### 2. **Compare Snapshots**
- Pilih 2 tanggal berbeda
- Klik "Compare" untuk melihat perbedaan
- Hasil ditampilkan dengan:
  - Absolute change (berapa banyak berubah)
  - Percentage change (% perubahan)
  - Color indicator (hijau = baik, merah = kurang baik)

#### 3. **Trend Chart**
- Visualisasi 30 hari terakhir
- 3 metrics:
  - Total Pelanggan (line chart, left axis)
  - Pelanggan Aktif (line chart, left axis)
  - Revenue (line chart, right axis in millions)
- Interactive: hover untuk lihat nilai exact

#### 4. **Snapshots Table**
- List semua snapshots
- Columns: Date, Total Customers, Active Customers, Revenue, Top Package, Quality Issues
- Action buttons:
  - View icon: Lihat detail snapshot

## Use Cases

### Use Case 1: Tracking Monthly Growth
1. Buka menu "History & Tracking"
2. Lihat "Trend (30 Hari Terakhir)" chart
3. Amati apakah ada trend naik atau turun untuk:
   - Total pelanggan
   - Revenue
4. Identifikasi bulan terbaik

### Use Case 2: Comparing Two Dates
1. Buka "Compare Snapshots"
2. Pilih tanggal lama di "Snapshot 1"
3. Pilih tanggal baru di "Snapshot 2"
4. Klik "Compare"
5. Lihat hasil perbandingan dengan % change
6. Contoh: Apakah revenue naik atau turun dari Sept 20 ke Oct 23?

### Use Case 3: Quality Improvement Tracking
1. Buka Compare Snapshots
2. Bandingkan "Quality Issues" dari 2 tanggal
3. Jika ada penurunan = data quality membaik
4. Jika ada kenaikan = ada masalah dengan upload data baru

### Use Case 4: Sales Performance Analysis
1. Upload data baru tanggal X
2. Buka "Snapshots Table"
3. Perhatikan metrics pada tanggal tersebut
4. Bandingkan dengan tanggal sebelumnya
5. Analisis apakah kinerja sales meningkat atau menurun

## Python API Usage

### Example 1: Create manual snapshot
```python
from history_manager import get_history_manager
from app import create_overview_stats

# Get current stats
stats = create_overview_stats()

# Save snapshot
history_mgr = get_history_manager()
snapshot_id = history_mgr.save_snapshot(stats, upload_date='2025-10-23')
print(f"Snapshot saved with ID: {snapshot_id}")
```

### Example 2: Get comparison
```python
history_mgr = get_history_manager()
comparison = history_mgr.get_comparison('2025-10-01', '2025-10-23')

print(f"Customer change: {comparison['changes']['customers']['change']}")
print(f"Revenue change: {comparison['changes']['revenue']['change_pct']}%")
```

### Example 3: Get trend
```python
history_mgr = get_history_manager()
trend = history_mgr.get_trend(days=30)

for day in trend:
    print(f"{day['upload_date']}: {day['total_customers']} customers, trend: {day['customer_trend']}")
```

### Example 4: Cleanup old data
```python
history_mgr = get_history_manager()
history_mgr.delete_old_snapshots(keep_count=50)  # Keep only 50 most recent
```

## Data Persistence

### Database Location
- File: `history.db` (SQLite database)
- Lokasi: Root folder project (sama dengan `app.py`)
- Ukuran: ~100KB per 100 snapshots (tergantung ukuran raw_data)

### Automatic Backup
- Database tidak punya automatic backup
- Rekomendasikan: Download file `history.db` secara berkala

### Manual Export (Future Enhancement)
Endpoint `/api/history/cleanup` bisa diperluas untuk add export functionality

## Performance Notes

- **Query speed**: Snapshot lookup sangat cepat (indexed by date)
- **Memory**: Trend calculation untuk 30 days = minimal memory
- **Storage**: ~1MB per 1000 snapshots (dengan raw_data)
- **Recommendation**: Cleanup jika database > 50MB (run cleanup to keep 100-200 snapshots)

## Troubleshooting

### Issue: No history snapshots showing
**Solution:**
1. Pastikan sudah upload file minimal 1x
2. Check browser console untuk error
3. Pastikan Flask app running dengan debug mode

### Issue: Comparison showing all zeros
**Solution:**
1. Pastikan kedua tanggal ada di database
2. Lihat Snapshots Table untuk melihat date yang tersedia
3. Coba dates yang lebih close

### Issue: Trend chart tidak muncul
**Solution:**
1. Perlu minimal 2 snapshots untuk trend chart
2. Jalankan upload 2x dengan interval berbeda
3. Tunggu > 5 detik sebelum membuka History section

### Issue: Database file not found
**Solution:**
1. Database akan otomatis dibuat saat pertama kali upload
2. Jika masih error, jalankan: `python -c "from history_manager import get_history_manager; get_history_manager()"`

## Future Enhancements

Possible features untuk ditambahkan:
- [ ] Export history ke CSV/Excel
- [ ] Scheduled automatic snapshots (daily, weekly)
- [ ] Alert jika ada anomali (contoh: revenue drop > 20%)
- [ ] Correlation analysis (apakah promo timings mempengaruhi sales?)
- [ ] Predictive analytics (forecast revenue bulan depan)
- [ ] Dashboard comparison view (side-by-side old vs new)
- [ ] Historical SOP violations tracking
- [ ] Data restore dari snapshot (rollback functionality)

## Support

Untuk pertanyaan atau issues, buat issue di repository atau hubungi tim development.
