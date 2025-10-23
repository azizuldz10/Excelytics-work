import pandas as pd
from bs4 import BeautifulSoup

# Read HTML file
with open('data-wifi.xls', 'r', encoding='utf-8') as f:
    html_content = f.read()

# Parse HTML
soup = BeautifulSoup(html_content, 'html.parser')
table = soup.find('table')

# Extract headers
headers = []
for th in table.find('thead').find_all('th'):
    headers.append(th.text.strip())

# Extract data rows
data = []
for tr in table.find('tbody').find_all('tr'):
    row = []
    for td in tr.find_all('td'):
        row.append(td.text.strip())
    if row:
        data.append(row)

# Create DataFrame
df = pd.DataFrame(data, columns=headers)

# Save to CSV for easier processing
df.to_csv('data-wifi-clean.csv', index=False, encoding='utf-8-sig')

print("=" * 80)
print("DATA BERHASIL DIPARSE!")
print("=" * 80)
print(f"\nJumlah Pelanggan: {len(df)}")
print(f"Jumlah Kolom: {len(df.columns)}")

print("\n" + "=" * 80)
print("KOLOM-KOLOM DATA:")
print("=" * 80)
for i, col in enumerate(df.columns, 1):
    print(f"{i:2d}. {col}")

print("\n" + "=" * 80)
print("PREVIEW DATA (5 baris pertama):")
print("=" * 80)
print(df.head().to_string())

# Basic analytics
print("\n" + "=" * 80)
print("ANALISIS CEPAT:")
print("=" * 80)

if 'Status Langganan' in df.columns:
    print("\nStatus Langganan:")
    print(df['Status Langganan'].value_counts())

if 'Jenis' in df.columns:
    print("\nJenis Langganan:")
    print(df['Jenis'].value_counts())

if 'Nama Langganan' in df.columns:
    print("\nNama Paket Langganan:")
    print(df['Nama Langganan'].value_counts())

print("\n✓ File CSV bersih telah disimpan: data-wifi-clean.csv")
