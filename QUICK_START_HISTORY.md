# Quick Start - History & Tracking Feature

## 🚀 Mulai Pakai dalam 5 Menit

### Step 1: Jalankan Dashboard
```bash
# Buka terminal di folder CSV_REPORT
python app.py

# Akses http://localhost:5000
```

### Step 2: Upload File Pertama
```
1. Klik tab "Upload" di sidebar
2. Upload file Excel/CSV Anda
3. Tunggu sampai "Data berhasil di-upload" message
4. ✅ Snapshot pertama sudah tersimpan!
```

### Step 3: Upload File Kedua (Besok atau jam lain)
```
1. Klik tab "Upload"
2. Upload file yang sama atau yang baru
3. Tunggu sampai upload berhasil
4. ✅ Sekarang Anda punya 2 snapshots!
```

### Step 4: Buka History & Tracking
```
1. Klik "History & Tracking" di sidebar
2. Lihat "Summary Cards":
   - Total Snapshots: 2
   - Last Updated: hari ini
   - Customers Change: +/- X
   - Revenue Change: +/- Rp X
3. ✅ Selesai! Anda sudah bisa melihat perubahan data!
```

---

## 📊 Fitur-Fitur Utama

### 1. Summary Cards (Top Section)
Lihat quick overview:
- **Total Snapshots**: Berapa banyak history yang tersimpan
- **Last Updated**: Kapan update terakhir
- **Customers Change**: Perubahan jumlah pelanggan sejak upload sebelumnya
- **Revenue Change**: Perubahan revenue sejak upload sebelumnya

### 2. Compare Snapshots
```
Contoh:
- Snapshot 1 (Lama): 2025-10-01 → 1,150 customers
- Snapshot 2 (Baru): 2025-10-23 → 1,169 customers

Hasil Comparison:
- Total Customers: +19 (+1.65%)  ← NAIK ✓
- Active Customers: +20 (+1.87%) ← NAIK ✓
- Revenue: +Rp 956,000 (+4.25%)  ← NAIK ✓
- Quality Issues: -55 (-11.0%)   ← MEMBAIK ✓
```

### 3. Trend Chart (30 Days)
Visualisasi line chart dengan 3 metrics:
- **Blue Line**: Total Customers
- **Green Line**: Active Customers
- **Yellow Line**: Revenue (dalam juta Rp)

### 4. Snapshots Table
Lihat semua history snapshots dengan detail lengkap

---

## ❓ Common Questions

### Q: Kapan snapshot tersimpan?
**A:** Otomatis setiap kali Anda upload file dan data berhasil diproses.

### Q: Berapa lama data disimpan?
**A:** Selamanya (sampai Anda delete atau cleanup manual). Sistem akan auto-cleanup jika database terlalu besar.

### Q: Bisa compare lebih dari 2 tanggal?
**A:** Untuk sekarang hanya bisa 2 tanggal. Bisa di-enhance di masa depan untuk timeline view.

### Q: Bagaimana jika upload di hari yang sama?
**A:** Snapshot akan di-replace (tetap satu per hari). Timestamp yang tersimpan adalah waktu precise dari upload terakhir.

### Q: Apa yang di-track?
**A:**
- Total customers, active/inactive count
- Revenue & average revenue per customer
- Quality issues (missing KTP, invalid phone, etc)
- Top package & location
- Active sales count
- PSB count

---

## 🎯 Use Case Examples

### Use Case 1: Monitor Pertumbuhan Bulanan
```
Tujuan: Apakah revenue bulan Oktober lebih baik dari September?

Langkah:
1. Buka History & Tracking
2. Di "Compare Snapshots":
   - Date 1: 2025-09-01 (September)
   - Date 2: 2025-10-23 (Oktober)
3. Klik Compare
4. Lihat Revenue % change
5. Jika positif = Bulan ini lebih baik!
```

### Use Case 2: Identify Data Quality Issues
```
Tujuan: Apakah data quality membaik atau memburuk?

Langkah:
1. Buka History & Tracking
2. Lihat "Quality Issues" di comparison
3. Jika angka negatif (-55) = Data quality membaik!
4. Jika angka positif (+100) = Ada masalah baru
5. Buka Overview tab untuk detail issues
```

### Use Case 3: Quick Performance Check
```
Tujuan: Cek performa sejak upload sebelumnya

Langkah:
1. Buka History & Tracking
2. Lihat Summary Cards:
   - Customers Change: +X pelanggan?
   - Revenue Change: +/- Rp X?
3. Done! Langsung tahu apakah naik atau turun
```

### Use Case 4: Compare Two Specific Weeks
```
Tujuan: Bandingkan minggu 1 vs minggu 2 Oktober

Langkah:
1. Buka History & Tracking
2. Di Compare:
   - Date 1: 2025-10-01 (Minggu 1)
   - Date 2: 2025-10-15 (Minggu 2)
3. Klik Compare
4. Lihat perubahan detail per metric
5. Analyze trend dan growth rate
```

---

## 💡 Tips & Tricks

### Tip 1: Upload Regular
Upload file Anda secara berkala (daily atau weekly) agar bisa melihat trend yang jelas.

### Tip 2: Consistent Upload Time
Kalau bisa upload di waktu yang sama setiap hari agar comparison lebih fair.

### Tip 3: Compare dengan Periode Sebelumnya
Jangan hanya compare dengan upload sebelumnya. Coba compare dengan 1 minggu/bulan lalu untuk melihat trend yang lebih besar.

### Tip 4: Check Quality Issues
Setiap kali ada perubahan besar di customers/revenue, cek Quality Issues untuk memastikan data valid.

### Tip 5: Export & Backup
Snapshots disimpan di `history.db`. Backup file ini secara berkala!

---

## 🔧 Troubleshooting

### Problem: History section kosong
**Solution:** Upload minimal 1 file dulu. Snapshot dibuat saat upload berhasil.

### Problem: Trend chart tidak muncul
**Solution:** Butuh minimal 2 snapshots. Upload 2x dengan interval berbeda, tunggu 5 detik, refresh.

### Problem: Comparison shows all zeros
**Solution:** Pastikan kedua date ada di database. Check Snapshots Table untuk lihat available dates.

### Problem: Error "No snapshot found"
**Solution:**
1. Cek apakah sudah pernah upload di date tersebut
2. Lihat Snapshots Table untuk list dates yang ada
3. Pastikan format date: YYYY-MM-DD (e.g., 2025-10-23)

### Problem: Database file missing
**Solution:** Database otomatis dibuat saat first upload. Jika tidak ada, jalankan:
```bash
python -c "from history_manager import get_history_manager; get_history_manager()"
```

---

## 📈 Interpretation Guide

### Metrics Explanation

**Customers Change**
```
+50 (+4.3%)  = GOOD! Semakin banyak customers
-10 (-0.9%)  = WARNING! Customers berkurang
 0  (0.0%)   = FLAT! Stabil
```

**Revenue Change**
```
+Rp 1,000,000 (+5%) = GOOD! Revenue naik
-Rp 500,000 (-2%)   = BAD! Revenue turun
```

**Quality Issues Change**
```
-100 (-20%)  = GOOD! Data quality membaik
+50 (+10%)   = BAD! Data quality memburuk
```

**Active Customers %**
```
95% = GOOD! Hampir semua active
80% = OK, bisa diperbaiki
50% = BAD! Banyak inactive customers
```

---

## 📚 More Documentation

Untuk informasi lebih detail:
- **Detailed Feature Docs**: `HISTORY_TRACKING.md`
- **Implementation Summary**: `HISTORY_IMPLEMENTATION_SUMMARY.md`
- **Project Architecture**: `CLAUDE.md`

---

## 🎓 Learn by Example

### Example 1: First Time Setup
```
Day 1 (Oct 1):
- Upload customer list Excel
- Dashboard shows 1,150 customers
- Revenue: Rp 22,500,000
- Issues: 500

Day 2 (Oct 23):
- Upload updated customer list
- Dashboard shows 1,169 customers
- Revenue: Rp 23,456,000
- Issues: 445

Action:
- Buka History & Tracking
- Compare Oct 1 vs Oct 23
- See: +19 customers (+1.65%), +Rp 956K revenue, -55 issues (-11%)
- Conclusion: Business growing, data quality improving!
```

### Example 2: Detecting Problems
```
Day 1 (Oct 15):
- Revenue: Rp 10,000,000
- Issues: 100

Day 2 (Oct 16):
- Revenue: Rp 9,000,000
- Issues: 500

Action:
- Buka History & Tracking
- Compare Oct 15 vs Oct 16
- See: -Rp 1M revenue (-10%), +400 issues (+400%)
- Conclusion: Sesuatu salah! Data quality drop drastis
- Next: Check Overview tab untuk detail issues, audit data baru
```

---

## ✅ Checklist

- [ ] Sudah baca `HISTORY_TRACKING.md` untuk detail
- [ ] Sudah test upload 2x file
- [ ] Sudah buka History & Tracking section
- [ ] Sudah coba Compare Snapshots
- [ ] Sudah lihat Trend Chart
- [ ] Sudah memahami metrics interpretation
- [ ] Ready untuk monitoring data WiFi Anda! 🚀

---

**Selamat menggunakan History & Tracking Feature!** 📊✨
