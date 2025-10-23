# 📊 Excelytics - WiFi Analytics Dashboard

> Solusi analytics terintegrasi untuk manajemen dan analisis data pelanggan WiFi dengan visualisasi real-time yang powerful.

![Python](https://img.shields.io/badge/Python-3.9+-blue?style=flat-square)
![Flask](https://img.shields.io/badge/Flask-2.0+-green?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-orange?style=flat-square)

---

## ✨ Fitur Utama

### 📈 Overview Dashboard
- **Statistik Real-time**: Total pelanggan, revenue, status langganan
- **Data Quality Alert**: Deteksi otomatis data tidak lengkap
  - Pelanggan tanpa dokumentasi KTP
  - Nomor telepon tidak valid
  - Koordinat geografis kosong
- **Distribusi Paket**: Visualisasi paket langganan populer
- **Analisis Lokasi**: Performance per lokasi jaringan

### 💰 Revenue Analytics
- Breakdown pendapatan per paket langganan
- Analisis range harga dan distribusi
- Top locations by revenue
- Revenue trends & forecasting

### 👥 Customer Management
- Tabel pelanggan interaktif dengan real-time filtering
- Multi-parameter filters (Status, Paket, Lokasi, Sales)
- Export data ke CSV format
- Pagination & responsive table design

### 🗺️ Geo Mapping
- Visualisasi geografis dengan koordinat real-time
- Interactive markers dengan color coding
  - 🟢 **Hijau**: Pelanggan aktif
  - 🔴 **Merah**: Pelanggan nonaktif
- Info popup detail untuk setiap lokasi

### 📊 Sales Performance
- Metrik performa per sales agent
- Customer acquisition tracking
- Revenue contribution analysis
- Top performers leaderboard

### 📅 Registration Analytics
- Trend analisis registrasi per periode
- Day-of-week pattern analysis
- Monthly comparison & seasonality
- Popular packages by period

### 🔧 PSB Tracking (Pemasangan Sambungan Baru)
- **Date Range Picker**: Custom rentang tanggal analisis
- **Quick Filters**: Pre-built date ranges (minggu lalu, bulan ini, dll)
- **Per-Agent Breakdown**: Revenue dan volume per sales
- **Summary Cards**: Overview metrics
- **Package Distribution**: Paket populer chart
- **Detailed Export**: Download ke CSV untuk follow-up

**Use Case**: Track pemasangan yang sudah closed tapi belum pembayaran diterima.

### 📋 SOP Validation & Monitoring
- Aturan SOP customizable per sales agent
- Automatic compliance checking
- Violation alerts & severity levels
- Historical tracking & trend analysis

### 🔐 Data Governance
- Automatic backup sebelum data update
- Change history tracking (NEW!)
- Snapshot management & comparison
- Data integrity validation

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- pip package manager

### Installation & Setup

1. **Clone Repository**
```bash
git clone https://github.com/azizuldz10/Excelytics-work.git
cd Excelytics-work
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

3. **Prepare Data**
- Letakkan file `data-wifi.xls` di root folder
- Atau upload melalui web interface

4. **Run Dashboard**
```bash
# Windows
python app.py

# Atau gunakan script
start_dashboard.bat
```

5. **Access Dashboard**
```
http://localhost:5000
```

---

## 📁 Project Structure

```
excelytics-work/
├── app.py                      # Flask backend & API endpoints
├── parse_html_data.py          # HTML to CSV parser
├── history_manager.py          # Database & history tracking
├── sop_rules.json              # SOP configuration
├── start_dashboard.bat         # Windows startup script
│
├── templates/
│   └── dashboard.html          # Single-page frontend app
│
└── README.md                   # Dokumentasi project
```

---

## 📊 API Reference

### Data Management
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/upload` | POST | Upload & merge Excel/CSV files |
| `/api/overview` | GET | Dashboard overview stats |
| `/api/customers` | GET | Customer list with filters |
| `/api/filters` | GET | Available filter options |

### Analytics
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/revenue-analysis` | GET | Revenue breakdown analytics |
| `/api/registration-analysis` | GET | Registration trends |
| `/api/psb-check` | GET | PSB tracking & analysis |
| `/api/map-data` | GET | Geo coordinates for mapping |

### Management
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/sop-rules` | GET/POST/PUT/DELETE | SOP rule management |
| `/api/violations` | GET | SOP violation tracking |
| `/api/history` | GET | Historical snapshots |
| `/api/history/<date>` | GET | Specific date snapshot |

---

## 🛠️ Tech Stack

### Backend
- **Flask** - Lightweight web framework
- **Pandas** - Data analysis & manipulation
- **SQLite** - History persistence
- **BeautifulSoup4** - HTML parsing

### Frontend
- **Bootstrap 5** - Responsive UI framework
- **Chart.js** - Interactive charts & graphs
- **Leaflet.js** - OpenStreetMap integration
- **Font Awesome** - Icon library

---

## 📈 Current Statistics

| Metric | Value |
|--------|-------|
| Total Customers | 1,169 |
| Active Rate | 93.24% |
| Top Package | H-MEKAR PRIME |
| Data Quality | 59.2% Complete |

---

## 🔒 Data Security & Privacy

- ✅ Automatic backup sebelum setiap update
- ✅ Change history dengan timestamp
- ✅ Customer data tidak tersimpan di repository
- ✅ SOP validation untuk compliance
- ✅ Role-based access planning (roadmap)

---

## 🐛 Troubleshooting

### Dashboard tidak bisa diakses
```bash
# Pastikan Flask server berjalan
python app.py

# Check port 5000 tersedia
netstat -ano | findstr :5000

# Coba dengan explicit host
# http://127.0.0.1:5000
```

### Data tidak muncul
```bash
# Pastikan file data ada
dir data-wifi*.csv

# Re-parse jika perlu
python parse_html_data.py

# Check console (F12) untuk errors
```

### Peta tidak muncul
- Pastikan koneksi internet aktif
- Verifikasi ada koordinat valid di data
- Check Leaflet.js CDN accessible

---

## 📝 Data Format

### Required Columns (CSV/XLS)
```
ID Pelanggan (unique identifier)
Nama Pelanggan
No Telepon
Alamat
Nama Paket Langganan
Harga Paket
Status Langganan (On/Off)
Tanggal Registrasi (YYYY-MM-DD)
Jatuh Tempo
Sales Agent (anonymized in reports)
Insentif Sales
Nama Lokasi
Nama Router
Jenis Koneksi
Titik Koordinat Lokasi (lat,lng format)
Foto KTP (URL)
Pembayaran Terakhir
```

---

## 🔄 Data Update Workflow

1. **Upload** → Kirim file Excel/CSV terbaru via web interface
2. **Validation** → Sistem cek format & data quality
3. **Backup** → Auto-backup versi sebelumnya
4. **Process** → Deduplicate & clean data
5. **Snapshot** → Save historical record
6. **Visualize** → Dashboard update real-time

---

## 🚧 Roadmap

- [ ] Multi-user support dengan authentication
- [ ] Role-based access control (Admin, Manager, Agent)
- [ ] Advanced predictive analytics
- [ ] WhatsApp integration untuk alerts
- [ ] Mobile app native
- [ ] Real-time collaboration features

---

## 💡 Best Practices

1. **Regular Backups**: Upload data secara berkala untuk tracking trends
2. **Data Validation**: Cek data quality alerts sebelum analysis
3. **SOP Compliance**: Review violations secara rutin
4. **History Tracking**: Gunakan snapshot compare untuk identify issues
5. **Export Reports**: Download custom reports untuk stakeholder meetings

---

## 📞 Support & Feedback

Untuk pertanyaan, bugs, atau feature requests:
- 📧 Email: [contact info]
- 🐛 Issues: [GitHub issues]
- 💬 Discussion: [GitHub discussions]

---

## 📄 License

MIT License - Bebas untuk digunakan dan dimodifikasi dengan proper attribution.

---

**Made with ❤️ for better WiFi analytics**

Last Updated: October 2025
