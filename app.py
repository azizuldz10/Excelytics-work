from flask import Flask, render_template, jsonify, request
from flask.json.provider import DefaultJSONProvider
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
import shutil
from werkzeug.utils import secure_filename
from history_manager import get_history_manager

# Import from new refactored modules
import config
from utils import (
    parse_date_flexible, get_days_since, get_tenure_days,
    DataValidator, validate_data_quality,
    read_excel_file as utils_read_excel_file, merge_dataframes, save_data
)

# Custom JSON provider to handle NaN
class CustomJSONProvider(DefaultJSONProvider):
    def default(self, obj):
        if isinstance(obj, float):
            if np.isnan(obj) or np.isinf(obj):
                return None
        return super().default(obj)

app = Flask(__name__)
app.json = CustomJSONProvider(app)

# Use centralized configuration from config.py
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH

# Load data from centralized path
def load_data():
    """Load main data file"""
    df = pd.read_csv(config.MAIN_DATA_FILE, encoding='utf-8-sig')
    return df

# Use DataValidator for price cleaning (alias for backward compatibility)
clean_price = DataValidator.clean_price

# Helper function to check allowed file
def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS

# Function to merge and clean multiple files
def merge_and_clean_files(file_paths):
    """
    Merge multiple Excel/CSV files and clean data
    Returns: (success, message, stats)
    """
    try:
        all_dataframes = []
        file_info = []

        print(f"Processing {len(file_paths)} files...")

        # Read each file
        for idx, file_path in enumerate(file_paths, 1):
            print(f"\n--- Processing File {idx}: {file_path} ---")
            success, df_or_message, file_ext = read_excel_file(file_path)

            if not success:
                return False, f"Error reading file {idx}: {df_or_message}", None

            df = df_or_message
            file_info.append({
                'file_num': idx,
                'filename': os.path.basename(file_path),
                'rows': len(df),
                'columns': len(df.columns)
            })

            all_dataframes.append(df)
            print(f"File {idx} loaded: {len(df)} rows, {len(df.columns)} columns")

        # Merge all dataframes
        print(f"\n--- Merging {len(all_dataframes)} dataframes ---")
        merged_df = pd.concat(all_dataframes, ignore_index=True)
        print(f"Merged data: {len(merged_df)} rows")

        # Calculate stats before deduplication
        total_rows_before = len(merged_df)

        # Check for ID Pelanggan column
        if 'ID Pelanggan' not in merged_df.columns:
            return False, f"Kolom 'ID Pelanggan' tidak ditemukan di file yang di-upload!", None

        # Remove duplicates based on ID Pelanggan (keep first occurrence)
        merged_df = merged_df.drop_duplicates(subset=['ID Pelanggan'], keep='first')
        duplicates_removed = total_rows_before - len(merged_df)
        print(f"Removed {duplicates_removed} duplicates")

        # Clean column names
        merged_df.columns = merged_df.columns.str.strip()

        # Backup old file
        if os.path.exists('data-wifi-clean.csv'):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f'data-wifi-clean_backup_{timestamp}.csv'
            shutil.copy('data-wifi-clean.csv', backup_name)
            print(f"Backup created: {backup_name}")

        # Save merged and cleaned data
        merged_df.to_csv('data-wifi-clean.csv', index=False, encoding='utf-8-sig')
        print(f"Saved merged data: {len(merged_df)} rows, {len(merged_df.columns)} columns")

        # Prepare statistics
        stats = {
            'files_count': len(file_paths),
            'file_info': file_info,
            'total_rows_before_merge': sum(f['rows'] for f in file_info),
            'total_rows_after_merge': total_rows_before,
            'duplicates_removed': duplicates_removed,
            'final_rows': len(merged_df),
            'columns': len(merged_df.columns)
        }

        message = f"Berhasil merge {len(file_paths)} file! Total {len(merged_df)} pelanggan unique."
        return True, message, stats

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Error in merge_and_clean_files: {error_detail}")
        return False, f"Error: {str(e)}", None


# Function to read single Excel/CSV file
def read_excel_file(file_path):
    """
    Read single Excel/CSV file
    Returns: (success, dataframe_or_error_message, file_ext)
    """
    try:
        # Determine engine based on file extension
        file_ext = file_path.rsplit('.', 1)[1].lower()

        df = None
        error_messages = []

        # Smart header detection
        def find_header_row(file_path, file_ext):
            """Find the row that contains 'ID Pelanggan' column"""
            try:
                print(f"Searching for header row with 'ID Pelanggan'...")
                # Read first 10 rows without header to inspect
                if file_ext == 'csv':
                    temp_df = pd.read_csv(file_path, encoding='utf-8-sig', header=None, nrows=10)
                elif file_ext == 'xlsx':
                    temp_df = pd.read_excel(file_path, engine='openpyxl', header=None, nrows=10)
                elif file_ext == 'xls':
                    try:
                        temp_df = pd.read_excel(file_path, engine='xlrd', header=None, nrows=10)
                    except:
                        try:
                            temp_df = pd.read_excel(file_path, engine='openpyxl', header=None, nrows=10)
                        except:
                            temp_df = pd.read_csv(file_path, encoding='utf-8-sig', header=None, nrows=10)
                else:
                    return 0

                # Search for row containing "ID Pelanggan"
                for idx, row in temp_df.iterrows():
                    row_values = row.astype(str).tolist()
                    if any('ID Pelanggan' in str(val) for val in row_values):
                        print(f"Found header row at index {idx}")
                        return idx

                print("Header row not found, using default (0)")
                return 0
            except Exception as e:
                print(f"Error finding header row: {str(e)}")
                return 0

        # Find the correct header row
        header_row = find_header_row(file_path, file_ext)

        # Read file based on extension
        if file_ext == 'csv':
            try:
                print(f"Reading CSV file with header at row {header_row}...")
                df = pd.read_csv(file_path, encoding='utf-8-sig', skiprows=header_row)
                print(f"Successfully read CSV: {len(df)} rows")
            except Exception as e:
                error_messages.append(f"CSV (utf-8-sig): {str(e)}")
                try:
                    df = pd.read_csv(file_path, encoding='latin1', skiprows=header_row)
                    print(f"Successfully read CSV with latin1: {len(df)} rows")
                except Exception as e2:
                    error_messages.append(f"CSV (latin1): {str(e2)}")

        elif file_ext == 'xlsx':
            try:
                print(f"Trying to read with openpyxl engine (header at row {header_row})...")
                df = pd.read_excel(file_path, engine='openpyxl', skiprows=header_row)
                print(f"Successfully read with openpyxl: {len(df)} rows")
            except Exception as e:
                error_messages.append(f"openpyxl: {str(e)}")
                try:
                    print(f"Trying CSV as fallback...")
                    df = pd.read_csv(file_path, encoding='utf-8-sig', skiprows=header_row)
                    print(f"Successfully read as CSV: {len(df)} rows")
                except Exception as e2:
                    error_messages.append(f"CSV fallback: {str(e2)}")

        elif file_ext == 'xls':
            try:
                print(f"Trying to read with xlrd engine (header at row {header_row})...")
                df = pd.read_excel(file_path, engine='xlrd', skiprows=header_row)
                print(f"Successfully read with xlrd: {len(df)} rows")
            except Exception as e:
                error_messages.append(f"xlrd: {str(e)}")
                try:
                    print(f"Trying openpyxl as fallback...")
                    df = pd.read_excel(file_path, engine='openpyxl', skiprows=header_row)
                    print(f"Successfully read with openpyxl fallback: {len(df)} rows")
                except Exception as e2:
                    error_messages.append(f"openpyxl fallback: {str(e2)}")
                    try:
                        print(f"Trying CSV as fallback...")
                        df = pd.read_csv(file_path, encoding='utf-8-sig', skiprows=header_row)
                        print(f"Successfully read as CSV: {len(df)} rows")
                    except Exception as e3:
                        error_messages.append(f"CSV fallback: {str(e3)}")

        else:
            return False, f"Format file tidak didukung: {file_ext}", None

        # If still failed, return error
        if df is None:
            error_detail = "\n".join(error_messages)
            return False, f"Gagal membaca file. Detail: {error_detail}", None

        print(f"Successfully read {len(df)} rows")
        print(f"Columns found: {list(df.columns)[:10]}")

        # Clean column names
        df.columns = df.columns.str.strip()

        # Check for ID Pelanggan
        if 'ID Pelanggan' not in df.columns:
            print(f"ERROR: 'ID Pelanggan' column not found!")
            print(f"Available columns: {list(df.columns)}")
            possible_cols = [col for col in df.columns if 'ID' in str(col).upper() or 'PELANGGAN' in str(col).upper()]
            if possible_cols:
                return False, f"Kolom 'ID Pelanggan' tidak ditemukan. Kolom yang mirip: {', '.join(possible_cols[:5])}", None
            else:
                return False, f"Kolom 'ID Pelanggan' tidak ditemukan. Kolom yang tersedia: {', '.join(list(df.columns)[:10])}", None

        return True, df, file_ext

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Error in read_excel_file: {error_detail}")
        return False, f"Error: {str(e)}", None


# Function to clean uploaded Excel data (LEGACY - kept for backwards compatibility)
def clean_uploaded_data(file_path):
    """
    Clean uploaded Excel/CSV file and save as CSV
    Returns: (success, message, stats)
    """
    try:
        # Determine engine based on file extension
        file_ext = file_path.rsplit('.', 1)[1].lower()

        # Try to read file with multiple methods
        df = None
        error_messages = []

        # Smart header detection: Read file without header first to find the correct header row
        def find_header_row(file_path, file_ext):
            """Find the row that contains 'ID Pelanggan' column"""
            try:
                print(f"Searching for header row with 'ID Pelanggan'...")
                # Read first 10 rows without header to inspect
                if file_ext == 'csv':
                    temp_df = pd.read_csv(file_path, encoding='utf-8-sig', header=None, nrows=10)
                elif file_ext == 'xlsx':
                    temp_df = pd.read_excel(file_path, engine='openpyxl', header=None, nrows=10)
                elif file_ext == 'xls':
                    try:
                        temp_df = pd.read_excel(file_path, engine='xlrd', header=None, nrows=10)
                    except:
                        try:
                            temp_df = pd.read_excel(file_path, engine='openpyxl', header=None, nrows=10)
                        except:
                            temp_df = pd.read_csv(file_path, encoding='utf-8-sig', header=None, nrows=10)
                else:
                    return 0

                # Search for row containing "ID Pelanggan"
                for idx, row in temp_df.iterrows():
                    row_values = row.astype(str).tolist()
                    if any('ID Pelanggan' in str(val) for val in row_values):
                        print(f"Found header row at index {idx}")
                        return idx

                print("Header row not found, using default (0)")
                return 0
            except Exception as e:
                print(f"Error finding header row: {str(e)}")
                return 0

        # Find the correct header row
        header_row = find_header_row(file_path, file_ext)

        # Method 1: If CSV, read directly
        if file_ext == 'csv':
            try:
                print(f"Reading CSV file with header at row {header_row}...")
                df = pd.read_csv(file_path, encoding='utf-8-sig', skiprows=header_row)
                print(f"Successfully read CSV: {len(df)} rows")
            except Exception as e:
                error_messages.append(f"CSV (utf-8-sig): {str(e)}")
                # Try different encodings
                try:
                    df = pd.read_csv(file_path, encoding='latin1', skiprows=header_row)
                    print(f"Successfully read CSV with latin1: {len(df)} rows")
                except Exception as e2:
                    error_messages.append(f"CSV (latin1): {str(e2)}")

        # Method 2: Try openpyxl for .xlsx
        elif file_ext == 'xlsx':
            try:
                print(f"Trying to read with openpyxl engine (header at row {header_row})...")
                df = pd.read_excel(file_path, engine='openpyxl', skiprows=header_row)
                print(f"Successfully read with openpyxl: {len(df)} rows")
            except Exception as e:
                error_messages.append(f"openpyxl: {str(e)}")
                # Try CSV as fallback (sometimes .xlsx is actually .csv)
                try:
                    print(f"Trying CSV as fallback...")
                    df = pd.read_csv(file_path, encoding='utf-8-sig', skiprows=header_row)
                    print(f"Successfully read as CSV: {len(df)} rows")
                except Exception as e2:
                    error_messages.append(f"CSV fallback (utf-8-sig): {str(e2)}")
                    # Try latin1 encoding
                    try:
                        df = pd.read_csv(file_path, encoding='latin1', skiprows=header_row)
                        print(f"Successfully read as CSV with latin1: {len(df)} rows")
                    except Exception as e3:
                        error_messages.append(f"CSV fallback (latin1): {str(e3)}")

        # Method 3: Try xlrd for .xls
        elif file_ext == 'xls':
            try:
                print(f"Trying to read with xlrd engine (header at row {header_row})...")
                df = pd.read_excel(file_path, engine='xlrd', skiprows=header_row)
                print(f"Successfully read with xlrd: {len(df)} rows")
            except Exception as e:
                error_messages.append(f"xlrd: {str(e)}")
                # Try openpyxl as fallback (sometimes .xls is actually .xlsx)
                try:
                    print(f"Trying openpyxl as fallback...")
                    df = pd.read_excel(file_path, engine='openpyxl', skiprows=header_row)
                    print(f"Successfully read with openpyxl fallback: {len(df)} rows")
                except Exception as e2:
                    error_messages.append(f"openpyxl fallback: {str(e2)}")
                    # Try CSV as last fallback (sometimes .xls is actually .csv)
                    try:
                        print(f"Trying CSV as fallback...")
                        df = pd.read_csv(file_path, encoding='utf-8-sig', skiprows=header_row)
                        print(f"Successfully read as CSV: {len(df)} rows")
                    except Exception as e3:
                        error_messages.append(f"CSV fallback (utf-8-sig): {str(e3)}")
                        # Try latin1 encoding
                        try:
                            df = pd.read_csv(file_path, encoding='latin1', skiprows=header_row)
                            print(f"Successfully read as CSV with latin1: {len(df)} rows")
                        except Exception as e4:
                            error_messages.append(f"CSV fallback (latin1): {str(e4)}")

        else:
            return False, f"Format file tidak didukung: {file_ext}", None

        # If still failed, return error
        if df is None:
            error_detail = "\n".join(error_messages)
            return False, f"Gagal membaca file. Pastikan file tidak corrupt dan format benar (.xlsx, .xls, atau .csv).\n\nDetail: {error_detail}", None

        print(f"Successfully read {len(df)} rows")
        print(f"Columns found: {list(df.columns)[:10]}")

        # Final check for ID Pelanggan
        if 'ID Pelanggan' not in df.columns:
            print(f"ERROR: 'ID Pelanggan' column not found!")
            print(f"Available columns: {list(df.columns)}")
            # Try to find similar column
            possible_cols = [col for col in df.columns if 'ID' in str(col).upper() or 'PELANGGAN' in str(col).upper()]
            if possible_cols:
                return False, f"Kolom 'ID Pelanggan' tidak ditemukan. Kolom yang mirip: {', '.join(possible_cols[:5])}", None
            else:
                return False, f"Kolom 'ID Pelanggan' tidak ditemukan. Kolom yang tersedia: {', '.join(list(df.columns)[:10])}", None

        original_count = len(df)

        # Remove duplicates based on ID Pelanggan
        df = df.drop_duplicates(subset=['ID Pelanggan'], keep='first')
        duplicates_removed = original_count - len(df)
        print(f"Removed {duplicates_removed} duplicates")

        # Clean column names (strip whitespace)
        df.columns = df.columns.str.strip()

        # Backup old file
        if os.path.exists('data-wifi-clean.csv'):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f'data-wifi-clean_backup_{timestamp}.csv'
            shutil.copy('data-wifi-clean.csv', backup_name)
            print(f"Backup created: {backup_name}")

        # Save cleaned data
        df.to_csv('data-wifi-clean.csv', index=False, encoding='utf-8-sig')
        print(f"Saved cleaned data: {len(df)} rows, {len(df.columns)} columns")

        stats = {
            'original_rows': original_count,
            'cleaned_rows': len(df),
            'duplicates_removed': duplicates_removed,
            'columns': len(df.columns)
        }

        return True, "Data berhasil di-upload dan di-clean!", stats

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Error in clean_uploaded_data: {error_detail}")
        return False, f"Error: {str(e)}", None

def create_overview_stats():
    """
    Create comprehensive overview stats for history tracking
    Returns dict with all key metrics from current data
    """
    try:
        df = load_data()

        # Basic stats
        total_customers = len(df)
        active_customers = len(df[df['Status Langganan'] == 'On'])
        inactive_customers = len(df[df['Status Langganan'] == 'Off'])

        # Revenue calculation
        df['Harga_Clean'] = df['Harga'].apply(clean_price)
        total_monthly_revenue = int(df[df['Status Langganan'] == 'On']['Harga_Clean'].sum())
        avg_revenue_per_customer = int(df[df['Status Langganan'] == 'On']['Harga_Clean'].mean())

        # Data Quality Checks - use refactored validators
        validator = DataValidator()
        df['Missing_KTP'] = df['Foto KTP'].apply(validator.is_ktp_missing)
        df['Invalid_Phone'] = df['Tlp'].apply(validator.is_phone_invalid)
        df['Incomplete_Data'] = df['Missing_KTP'] | df['Invalid_Phone']

        missing_ktp_count = int(df['Missing_KTP'].sum())
        invalid_phone_count = int(df['Invalid_Phone'].sum())
        incomplete_data_count = int(df['Incomplete_Data'].sum())

        # Package distribution
        package_dist = df['Nama Langganan'].value_counts().to_dict()
        top_package = max(package_dist.items(), key=lambda x: x[1])

        # Location distribution with revenue
        location_revenue = {}
        for location in df['Nama Lokasi'].dropna().unique():
            location_df = df[df['Nama Lokasi'] == location]
            location_df['Harga_Clean'] = location_df['Harga'].apply(clean_price)
            revenue = int(location_df[location_df['Status Langganan'] == 'On']['Harga_Clean'].sum())
            location_revenue[location] = revenue

        top_location = max(location_revenue.items(), key=lambda x: x[1]) if location_revenue else ('N/A', 0)

        # Active sales count
        active_sales = len(df['Nama Sales'].dropna().unique())

        # PSB count (using Tanggal Registrasi)
        total_psb = len(df[df['Tanggal Registrasi'].notna()])

        stats = {
            'total_customers': total_customers,
            'active_customers': active_customers,
            'inactive_customers': inactive_customers,
            'total_revenue': total_monthly_revenue,
            'avg_revenue_per_customer': avg_revenue_per_customer,
            'total_packages': len(package_dist),
            'top_package': top_package[0] if top_package else 'N/A',
            'top_package_count': int(top_package[1]) if top_package else 0,
            'top_location': top_location[0] if top_location else 'N/A',
            'top_location_revenue': int(top_location[1]) if top_location else 0,
            'active_sales': active_sales,
            'total_psb_count': total_psb
        }

        quality = {
            'total_issues': missing_ktp_count + invalid_phone_count + incomplete_data_count,
            'missing_ktp_count': missing_ktp_count,
            'invalid_phone_count': invalid_phone_count,
            'incomplete_data_count': incomplete_data_count
        }

        return {
            'stats': stats,
            'quality_checks': quality
        }

    except Exception as e:
        print(f"Error creating overview stats: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """
    Upload and clean Excel file(s) - supports multiple files
    """
    # Check if files are in request
    if 'files' not in request.files:
        return jsonify({'success': False, 'message': 'No files uploaded'}), 400

    files = request.files.getlist('files')

    # Check if any file is selected
    if len(files) == 0 or all(f.filename == '' for f in files):
        return jsonify({'success': False, 'message': 'No files selected'}), 400

    try:
        uploaded_files = []
        file_stats = []

        # Process each file
        for idx, file in enumerate(files, 1):
            if file.filename == '':
                continue

            # Check file extension
            if not allowed_file(file.filename):
                return jsonify({
                    'success': False,
                    'message': f'File {file.filename} harus format .xls, .xlsx, atau .csv'
                }), 400

            # Save uploaded file temporarily
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            upload_filename = f'upload_{timestamp}_{idx}_{filename}'
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], upload_filename)
            file.save(file_path)
            uploaded_files.append(file_path)

            print(f"Saved file {idx}: {upload_filename}")

        # Merge and process all files
        success, message, stats = merge_and_clean_files(uploaded_files)

        # Remove uploaded files after processing
        for file_path in uploaded_files:
            if os.path.exists(file_path):
                os.remove(file_path)

        if success:
            # Save snapshot to history after successful upload
            try:
                overview_stats = create_overview_stats()
                if overview_stats:
                    history_mgr = get_history_manager()
                    snapshot_id = history_mgr.save_snapshot(overview_stats)
                    print(f"✓ History snapshot saved (ID: {snapshot_id})")
            except Exception as e:
                print(f"Warning: Failed to save history snapshot: {str(e)}")

            return jsonify({
                'success': True,
                'message': message,
                'stats': stats
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 500

    except Exception as e:
        # Clean up files on error
        for file_path in uploaded_files:
            if os.path.exists(file_path):
                os.remove(file_path)

        return jsonify({
            'success': False,
            'message': f'Error processing files: {str(e)}'
        }), 500

@app.route('/api/overview')
def get_overview():
    df = load_data()

    # Basic stats
    total_customers = len(df)
    active_customers = len(df[df['Status Langganan'] == 'On'])
    inactive_customers = len(df[df['Status Langganan'] == 'Off'])

    # Revenue calculation
    df['Harga_Clean'] = df['Harga'].apply(clean_price)
    total_monthly_revenue = df[df['Status Langganan'] == 'On']['Harga_Clean'].sum()
    avg_revenue_per_customer = df[df['Status Langganan'] == 'On']['Harga_Clean'].mean()

    # Use refactored data validators instead of duplicating inline logic
    validator = DataValidator()
    df['Missing_KTP'] = df['Foto KTP'].apply(validator.is_ktp_missing)
    df['Invalid_Phone'] = df['Tlp'].apply(validator.is_phone_invalid)
    df['Incomplete_Data'] = df['Missing_KTP'] | df['Invalid_Phone']
    df['Missing_Coordinate'] = df['Titik Koordinat Lokasi'].apply(validator.is_coordinate_missing)

    # Count data quality issues
    missing_ktp_count = df['Missing_KTP'].sum()
    invalid_phone_count = df['Invalid_Phone'].sum()
    incomplete_data_count = df['Incomplete_Data'].sum()
    missing_coordinate_count = df['Missing_Coordinate'].sum()

    # Get list of customers with incomplete data (only active customers)
    incomplete_customers_df = df[df['Incomplete_Data'] & (df['Status Langganan'] == 'On')][
        ['ID Pelanggan', 'Nama Pelanggan', 'Tlp', 'Foto KTP', 'Nama Sales',
         'Nama Langganan', 'Missing_KTP', 'Invalid_Phone']
    ].fillna('')  # Replace NaN with empty string
    incomplete_customers = incomplete_customers_df.to_dict('records')

    # Package distribution
    package_dist = df['Nama Langganan'].value_counts().to_dict()

    # Status distribution
    status_dist = df['Status Langganan'].value_counts().to_dict()

    # Sales performance
    sales_dist = df['Nama Sales'].value_counts().head(10).to_dict()

    # Sales performance detailed (with active/inactive breakdown)
    sales_detailed = {}
    for sales_name in df['Nama Sales'].dropna().unique():
        sales_df = df[df['Nama Sales'] == sales_name]
        active_count = len(sales_df[sales_df['Status Langganan'] == 'On'])
        inactive_count = len(sales_df[sales_df['Status Langganan'] == 'Off'])
        sales_detailed[sales_name] = {
            'active': int(active_count),
            'inactive': int(inactive_count),
            'total': int(len(sales_df))
        }

    # Location distribution
    location_dist = df['Nama Lokasi'].value_counts().head(15).to_dict()

    # Connection type
    connection_type = df['Jenis Koneksi'].value_counts().to_dict()

    # Router distribution
    router_dist = df['Nama Router'].value_counts().head(10).to_dict()

    response_data = {
        'overview': {
            'total_customers': int(total_customers),
            'active_customers': int(active_customers),
            'inactive_customers': int(inactive_customers),
            'active_rate': round((active_customers / total_customers * 100), 2),
            'total_monthly_revenue': int(total_monthly_revenue),
            'avg_revenue_per_customer': int(avg_revenue_per_customer)
        },
        'data_quality': {
            'missing_ktp': int(missing_ktp_count),
            'invalid_phone': int(invalid_phone_count),
            'incomplete_data': int(incomplete_data_count),
            'missing_coordinate': int(missing_coordinate_count),
            'incomplete_customers': incomplete_customers[:100]  # Limit to 100
        },
        'package_distribution': package_dist,
        'status_distribution': status_dist,
        'sales_performance': sales_dist,
        'sales_detailed': sales_detailed,
        'location_distribution': location_dist,
        'connection_type': connection_type,
        'router_distribution': router_dist
    }

    # Clean data before JSON serialization
    return jsonify(clean_for_json(response_data))

@app.route('/api/revenue-analysis')
def revenue_analysis():
    """Enhanced Revenue Analytics Dashboard"""
    df = load_data()
    df['Harga_Clean'] = df['Harga'].apply(clean_price)

    # Filter to active customers for accurate revenue
    df_active = df[df['Status Langganan'] == 'On'].copy()

    total_revenue = int(df_active['Harga_Clean'].sum())
    total_customers = len(df_active)
    avg_arpu = int(df_active['Harga_Clean'].mean()) if total_customers > 0 else 0

    # Revenue by package
    revenue_by_package = df_active.groupby('Nama Langganan').agg({
        'Harga_Clean': ['sum', 'count', 'mean']
    }).round(0)

    package_data = {}
    for package, row in revenue_by_package.iterrows():
        revenue = int(row[('Harga_Clean', 'sum')])
        count = int(row[('Harga_Clean', 'count')])
        avg = int(row[('Harga_Clean', 'mean')])
        percentage = round((revenue / total_revenue * 100), 2) if total_revenue > 0 else 0

        package_data[package] = {
            'revenue': revenue,
            'customer_count': count,
            'avg_revenue_per_customer': avg,
            'percentage_of_total': percentage,
            'revenue_formatted': f'Rp {revenue:,.0f}'
        }

    # Sort by revenue
    revenue_by_package_sorted = dict(sorted(package_data.items(),
                                           key=lambda x: x[1]['revenue'],
                                           reverse=True))

    # Revenue by location
    revenue_by_location = df_active.groupby('Nama Lokasi').agg({
        'Harga_Clean': ['sum', 'count', 'mean']
    }).round(0)

    location_data = {}
    for location, row in revenue_by_location.iterrows():
        revenue = int(row[('Harga_Clean', 'sum')])
        count = int(row[('Harga_Clean', 'count')])
        avg = int(row[('Harga_Clean', 'mean')])
        percentage = round((revenue / total_revenue * 100), 2) if total_revenue > 0 else 0

        location_data[location] = {
            'revenue': revenue,
            'customer_count': count,
            'avg_revenue_per_customer': avg,
            'percentage_of_total': percentage,
            'revenue_formatted': f'Rp {revenue:,.0f}'
        }

    # Sort by revenue and limit to top 15
    revenue_by_location_sorted = dict(sorted(location_data.items(),
                                            key=lambda x: x[1]['revenue'],
                                            reverse=True)[:15])

    # Revenue by sales
    revenue_by_sales = df_active.groupby('Nama Sales').agg({
        'Harga_Clean': ['sum', 'count', 'mean']
    }).round(0)

    sales_data = {}
    for sales, row in revenue_by_sales.iterrows():
        revenue = int(row[('Harga_Clean', 'sum')])
        count = int(row[('Harga_Clean', 'count')])
        avg = int(row[('Harga_Clean', 'mean')])
        percentage = round((revenue / total_revenue * 100), 2) if total_revenue > 0 else 0

        sales_data[sales] = {
            'revenue': revenue,
            'customer_count': count,
            'avg_revenue_per_customer': avg,
            'percentage_of_total': percentage,
            'revenue_formatted': f'Rp {revenue:,.0f}'
        }

    # Sort by revenue
    revenue_by_sales_sorted = dict(sorted(sales_data.items(),
                                         key=lambda x: x[1]['revenue'],
                                         reverse=True))

    # Price range distribution
    price_ranges = {
        '< 100K': len(df_active[df_active['Harga_Clean'] < 100000]),
        '100K - 150K': len(df_active[(df_active['Harga_Clean'] >= 100000) & (df_active['Harga_Clean'] < 150000)]),
        '150K - 200K': len(df_active[(df_active['Harga_Clean'] >= 150000) & (df_active['Harga_Clean'] < 200000)]),
        '200K - 250K': len(df_active[(df_active['Harga_Clean'] >= 200000) & (df_active['Harga_Clean'] < 250000)]),
        '>= 250K': len(df_active[df_active['Harga_Clean'] >= 250000])
    }

    # Top performers
    top_package = max(revenue_by_package_sorted.items(), key=lambda x: x[1]['revenue']) if revenue_by_package_sorted else None
    top_location = max(revenue_by_location_sorted.items(), key=lambda x: x[1]['revenue']) if revenue_by_location_sorted else None
    top_sales = max(revenue_by_sales_sorted.items(), key=lambda x: x[1]['revenue']) if revenue_by_sales_sorted else None

    response = {
        'summary': {
            'total_revenue': total_revenue,
            'total_revenue_formatted': f'Rp {total_revenue:,.0f}',
            'active_customers': total_customers,
            'average_arpu': avg_arpu,
            'average_arpu_formatted': f'Rp {avg_arpu:,.0f}'
        },
        'by_package': revenue_by_package_sorted,
        'by_location': revenue_by_location_sorted,
        'by_sales': revenue_by_sales_sorted,
        'price_ranges': price_ranges,
        'top_performers': {
            'top_package': {
                'name': top_package[0] if top_package else 'N/A',
                'revenue': top_package[1]['revenue'] if top_package else 0,
                'customer_count': top_package[1]['customer_count'] if top_package else 0,
                'revenue_formatted': top_package[1]['revenue_formatted'] if top_package else 'N/A'
            },
            'top_location': {
                'name': top_location[0] if top_location else 'N/A',
                'revenue': top_location[1]['revenue'] if top_location else 0,
                'customer_count': top_location[1]['customer_count'] if top_location else 0,
                'revenue_formatted': top_location[1]['revenue_formatted'] if top_location else 'N/A'
            },
            'top_sales': {
                'name': top_sales[0] if top_sales else 'N/A',
                'revenue': top_sales[1]['revenue'] if top_sales else 0,
                'customer_count': top_sales[1]['customer_count'] if top_sales else 0,
                'revenue_formatted': top_sales[1]['revenue_formatted'] if top_sales else 'N/A'
            }
        }
    }

    return jsonify(clean_for_json(response))

@app.route('/api/customers')
def get_customers():
    df = load_data()

    # Get filter parameters
    status = request.args.get('status', 'all')
    package = request.args.get('package', 'all')
    location = request.args.get('location', 'all')
    sales = request.args.get('sales', 'all')

    # Apply filters
    if status != 'all':
        df = df[df['Status Langganan'] == status]
    if package != 'all':
        df = df[df['Nama Langganan'] == package]
    if location != 'all':
        df = df[df['Nama Lokasi'] == location]
    if sales != 'all':
        df = df[df['Nama Sales'] == sales]

    # Select relevant columns for display
    display_columns = [
        'No', 'ID Pelanggan', 'Nama Pelanggan', 'Tlp',
        'Nama Langganan', 'Harga', 'Status Langganan',
        'Nama Lokasi', 'Nama Sales', 'Jatuh Tempo'
    ]

    result_df = df[display_columns].head(100)  # Limit to 100 for performance

    return jsonify({
        'total': len(df),
        'displayed': len(result_df),
        'customers': result_df.to_dict('records')
    })

@app.route('/api/map-data')
def get_map_data():
    df = load_data()

    # Extract coordinates
    map_data = []
    for idx, row in df.iterrows():
        coords = str(row['Titik Koordinat Lokasi'])
        if coords and coords != 'nan' and ',' in coords:
            try:
                lat, lng = coords.split(',')
                lat = float(lat.strip())
                lng = float(lng.strip())

                map_data.append({
                    'lat': lat,
                    'lng': lng,
                    'name': row['Nama Pelanggan'],
                    'package': row['Nama Langganan'],
                    'status': row['Status Langganan'],
                    'location': row['Nama Lokasi']
                })
            except:
                continue

    return jsonify({'markers': map_data})

@app.route('/api/filters')
def get_filters():
    df = load_data()

    return jsonify({
        'packages': sorted(df['Nama Langganan'].dropna().unique().tolist()),
        'locations': sorted(df['Nama Lokasi'].dropna().unique().tolist()),
        'sales': sorted(df['Nama Sales'].dropna().unique().tolist()),
        'statuses': ['On', 'Off']
    })

@app.route('/api/registration-analysis')
def registration_analysis():
    df = load_data()

    # Use refactored date parser instead of duplicating logic
    df['Tanggal_Parsed'] = df['Tanggal Registrasi'].apply(parse_date_flexible)
    df_valid = df[df['Tanggal_Parsed'].notna()].copy()

    # Extract date components
    df_valid['Tahun'] = df_valid['Tanggal_Parsed'].dt.year
    df_valid['Bulan'] = df_valid['Tanggal_Parsed'].dt.month
    df_valid['Year_Month'] = df_valid['Tanggal_Parsed'].dt.strftime('%Y-%m')
    df_valid['Nama_Bulan'] = df_valid['Tanggal_Parsed'].dt.strftime('%B %Y')

    # Monthly analysis dengan growth
    monthly_data = df_valid.groupby(['Year_Month', 'Nama_Bulan']).size().reset_index(name='count')
    monthly_data = monthly_data.sort_values('Year_Month')

    # Calculate growth percentage
    monthly_analysis = []
    for i, row in monthly_data.iterrows():
        month_data = {
            'month': row['Nama_Bulan'],
            'year_month': row['Year_Month'],
            'count': int(row['count']),
            'growth': 0,
            'growth_type': 'stable'
        }

        # Calculate growth from previous month
        if i > 0:
            prev_count = monthly_data.iloc[i-1]['count']
            if prev_count > 0:
                growth_pct = ((row['count'] - prev_count) / prev_count) * 100
                month_data['growth'] = round(growth_pct, 1)
                if growth_pct > 0:
                    month_data['growth_type'] = 'increase'
                elif growth_pct < 0:
                    month_data['growth_type'] = 'decrease'

        monthly_analysis.append(month_data)

    # Get last 12 months for chart
    last_12_months = monthly_analysis[-12:] if len(monthly_analysis) > 12 else monthly_analysis

    # Top months
    top_months = sorted(monthly_analysis, key=lambda x: x['count'], reverse=True)[:10]

    return jsonify({
        'total_with_dates': len(df_valid),
        'monthly_analysis': monthly_analysis,
        'last_12_months': last_12_months,
        'top_months': top_months
    })

@app.route('/api/psb-check')
def psb_check():
    df = load_data()

    # Get parameters
    start_date = request.args.get('start_date')  # Format: YYYY-MM-DD
    end_date = request.args.get('end_date')  # Format: YYYY-MM-DD
    sales = request.args.get('sales', 'all')

    # Use refactored date parser
    df['Tanggal_Parsed'] = df['Tanggal Registrasi'].apply(parse_date_flexible)
    df_valid = df[df['Tanggal_Parsed'].notna()].copy()

    # Apply date range filter
    if start_date and end_date:
        try:
            start = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date)
            df_valid = df_valid[(df_valid['Tanggal_Parsed'] >= start) &
                               (df_valid['Tanggal_Parsed'] <= end)]
        except:
            pass

    # Apply sales filter
    if sales != 'all':
        df_valid = df_valid[df_valid['Nama Sales'] == sales]

    # Calculate price
    df_valid['Harga_Clean'] = df_valid['Harga'].apply(clean_price)

    # Calculate fee/incentive
    def clean_incentive(inc_str):
        if pd.isna(inc_str):
            return 0
        try:
            return int(str(inc_str).replace('.', '').replace(',', '').strip())
        except:
            return 0

    df_valid['Insentif_Clean'] = df_valid['Insentif Sales'].apply(clean_incentive)

    # Summary per sales with fee
    sales_data = []
    for sales_name in df_valid['Nama Sales'].unique():
        sales_df = df_valid[df_valid['Nama Sales'] == sales_name]
        total_fee = sales_df['Insentif_Clean'].sum()

        sales_data.append({
            'sales_name': sales_name,
            'count': len(sales_df),
            'revenue': int(sales_df['Harga_Clean'].sum()),
            'total_fee': int(total_fee),
            'avg_fee': int(total_fee / len(sales_df)) if len(sales_df) > 0 else 0
        })

    # Sort by count
    sales_data = sorted(sales_data, key=lambda x: x['count'], reverse=True)

    # Convert to dict for sales_summary
    sales_summary = {}
    for s in sales_data:
        sales_summary[s['sales_name']] = {
            'ID': s['count'],
            'Harga_Clean': s['revenue'],
            'Total_Fee': s['total_fee'],
            'Avg_Fee': s['avg_fee']
        }

    # Summary per package
    package_summary = df_valid.groupby('Nama Langganan').agg({
        'ID': 'count',
        'Harga_Clean': 'sum'
    }).to_dict('index')

    # Summary per location
    location_summary = df_valid.groupby('Nama Lokasi').agg({
        'ID': 'count'
    }).to_dict('index')

    # Daily trend in period
    daily_summary = df_valid.groupby(df_valid['Tanggal_Parsed'].dt.strftime('%d-%m-%Y')).agg({
        'ID': 'count'
    }).to_dict()['ID']

    # Get detail customers
    detail_columns = [
        'Tanggal Registrasi', 'ID Pelanggan', 'Nama Pelanggan', 'Tlp',
        'Nama Langganan', 'Harga', 'Nama Lokasi', 'Nama Sales',
        'Status Langganan', 'Alamat', 'Insentif Sales', 'Metode Insentif'
    ]

    customers = df_valid[detail_columns].to_dict('records')

    # Total fee summary
    total_fee_all_sales = int(df_valid['Insentif_Clean'].sum())

    return jsonify({
        'total': len(df_valid),
        'total_potential_revenue': int(df_valid['Harga_Clean'].sum()),
        'total_fee': total_fee_all_sales,
        'sales_summary': sales_summary,
        'package_summary': package_summary,
        'location_summary': location_summary,
        'daily_summary': daily_summary,
        'customers': customers,
        'date_range': {
            'start': start_date,
            'end': end_date
        }
    })

@app.route('/api/blacklist')
def blacklist_check():
    df = load_data()

    # Get parameters
    min_months = int(request.args.get('min_months', 3))
    sales = request.args.get('sales', 'all')

    # Use refactored date parser
    df['Tanggal_Parsed'] = df['Tanggal Registrasi'].apply(parse_date_flexible)
    df_valid = df[df['Tanggal_Parsed'].notna()].copy()

    # Filter: Only customers with "Data Belum Ada" in Pembayaran Terakhir
    # This means they never paid since registration
    df_valid['Bayar_Check'] = df_valid['Pembayaran Terakhir'].astype(str).str.strip()
    df_blacklist = df_valid[df_valid['Bayar_Check'] == 'Data Belum Ada'].copy()

    # Calculate months since registration
    today = datetime.now()
    df_blacklist['Months_Since_Reg'] = df_blacklist['Tanggal_Parsed'].apply(
        lambda x: int((today - x).days / 30) if pd.notna(x) else 0
    )

    # Filter by minimum months
    df_blacklist = df_blacklist[df_blacklist['Months_Since_Reg'] >= min_months]

    # Apply sales filter
    if sales != 'all':
        df_blacklist = df_blacklist[df_blacklist['Nama Sales'] == sales]

    # Calculate price
    df_blacklist['Harga_Clean'] = df_blacklist['Harga'].apply(clean_price)

    # Summary statistics
    total_blacklist = len(df_blacklist)
    total_potential_loss = df_blacklist['Harga_Clean'].sum()
    avg_months_unpaid = df_blacklist['Months_Since_Reg'].mean() if total_blacklist > 0 else 0

    # Prepare customer list
    detail_columns = [
        'ID Pelanggan', 'Nama Pelanggan', 'Tlp', 'Alamat',
        'Nama Langganan', 'Harga', 'Tanggal Registrasi',
        'Nama Lokasi', 'Nama Sales', 'Status Langganan'
    ]

    # Fill NaN values before converting to dict
    df_blacklist_clean = df_blacklist[detail_columns].fillna('')

    customers = []
    for idx, row in df_blacklist.iterrows():
        customer_data = {col: ('' if pd.isna(row[col]) else row[col]) for col in detail_columns}
        customer_data['Months_Unpaid'] = int(row['Months_Since_Reg'])
        customers.append(customer_data)

    # Sort by months unpaid (descending)
    customers = sorted(customers, key=lambda x: x['Months_Unpaid'], reverse=True)

    # Sales breakdown
    sales_summary = df_blacklist.groupby('Nama Sales').agg({
        'ID': 'count',
        'Harga_Clean': 'sum'
    }).to_dict('index')

    # Location breakdown
    location_summary = df_blacklist.groupby('Nama Lokasi').agg({
        'ID': 'count'
    }).sort_values('ID', ascending=False).to_dict('index')

    response_data = {
        'total': total_blacklist,
        'total_potential_loss': int(total_potential_loss),
        'avg_months_unpaid': round(avg_months_unpaid, 1),
        'total_devices': total_blacklist,  # Same as total blacklist
        'customers': customers,
        'sales_summary': sales_summary,
        'location_summary': location_summary,
        'filter': {
            'min_months': min_months,
            'sales': sales
        }
    }

    return jsonify(clean_for_json(response_data))

# ========================================
# SOP RULES MANAGEMENT
# ========================================

SOP_RULES_FILE = 'sop_rules.json'

def load_sop_rules():
    """Load SOP rules from JSON file"""
    try:
        if os.path.exists(SOP_RULES_FILE):
            with open(SOP_RULES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Error loading SOP rules: {str(e)}")
        return {}

def save_sop_rules(rules):
    """Save SOP rules to JSON file"""
    try:
        with open(SOP_RULES_FILE, 'w', encoding='utf-8') as f:
            json.dump(rules, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving SOP rules: {str(e)}")
        return False

@app.route('/api/sop-rules', methods=['GET'])
def get_sop_rules():
    """Get all SOP rules"""
    rules = load_sop_rules()
    return jsonify({
        'success': True,
        'rules': rules
    })

@app.route('/api/sop-rules', methods=['POST'])
def add_sop_rule():
    """Add new SOP rule"""
    try:
        data = request.json

        # Validate required fields
        required_fields = ['nama_sales', 'jatuh_tempo', 'insentif', 'lokasi']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Field {field} is required'
                }), 400

        nama_sales = data['nama_sales'].strip()

        if not nama_sales:
            return jsonify({
                'success': False,
                'message': 'Nama sales tidak boleh kosong'
            }), 400

        # Load existing rules
        rules = load_sop_rules()

        # Check if sales already exists
        if nama_sales in rules:
            return jsonify({
                'success': False,
                'message': f'Sales {nama_sales} sudah ada. Gunakan update untuk mengubah.'
            }), 400

        # Validate jatuh tempo (1-31)
        try:
            jatuh_tempo = int(data['jatuh_tempo'])
            if jatuh_tempo < 1 or jatuh_tempo > 31:
                raise ValueError()
        except:
            return jsonify({
                'success': False,
                'message': 'Jatuh tempo harus angka 1-31'
            }), 400

        # Validate insentif (support both array and single value)
        insentif_data = data['insentif']

        # Convert single value to list for consistency
        if isinstance(insentif_data, int):
            insentif_list = [insentif_data]
        elif isinstance(insentif_data, list):
            insentif_list = insentif_data
        else:
            return jsonify({
                'success': False,
                'message': 'Insentif harus berupa angka atau array angka'
            }), 400

        # Validate each insentif value
        validated_insentif = []
        for ins in insentif_list:
            try:
                ins_value = int(ins)
                if ins_value < 0:
                    raise ValueError()
                validated_insentif.append(ins_value)
            except:
                return jsonify({
                    'success': False,
                    'message': 'Semua nilai insentif harus angka positif'
                }), 400

        # Remove duplicates and sort
        validated_insentif = sorted(list(set(validated_insentif)))

        if len(validated_insentif) == 0:
            return jsonify({
                'success': False,
                'message': 'Minimal harus ada 1 nilai insentif'
            }), 400

        # Validate lokasi (array)
        lokasi = data['lokasi']
        if not isinstance(lokasi, list) or len(lokasi) == 0:
            return jsonify({
                'success': False,
                'message': 'Lokasi harus array dan tidak boleh kosong'
            }), 400

        # Add new rule
        from datetime import datetime
        rules[nama_sales] = {
            'jatuh_tempo': jatuh_tempo,
            'insentif': validated_insentif,  # Store as array
            'lokasi': lokasi,
            'active': True,
            'created_at': datetime.now().strftime('%Y-%m-%d'),
            'updated_at': datetime.now().strftime('%Y-%m-%d')
        }

        # Save rules
        if save_sop_rules(rules):
            return jsonify({
                'success': True,
                'message': f'SOP rule untuk {nama_sales} berhasil ditambahkan'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Gagal menyimpan SOP rule'
            }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/sop-rules/<sales>', methods=['PUT'])
def update_sop_rule(sales):
    """Update SOP rule"""
    try:
        data = request.json

        # Load existing rules
        rules = load_sop_rules()

        # Check if sales exists
        if sales not in rules:
            return jsonify({
                'success': False,
                'message': f'Sales {sales} tidak ditemukan'
            }), 404

        # Validate jatuh tempo if provided
        if 'jatuh_tempo' in data:
            try:
                jatuh_tempo = int(data['jatuh_tempo'])
                if jatuh_tempo < 1 or jatuh_tempo > 31:
                    raise ValueError()
                rules[sales]['jatuh_tempo'] = jatuh_tempo
            except:
                return jsonify({
                    'success': False,
                    'message': 'Jatuh tempo harus angka 1-31'
                }), 400

        # Validate insentif if provided (support both array and single value)
        if 'insentif' in data:
            insentif_data = data['insentif']

            # Convert single value to list for consistency
            if isinstance(insentif_data, int):
                insentif_list = [insentif_data]
            elif isinstance(insentif_data, list):
                insentif_list = insentif_data
            else:
                return jsonify({
                    'success': False,
                    'message': 'Insentif harus berupa angka atau array angka'
                }), 400

            # Validate each insentif value
            validated_insentif = []
            for ins in insentif_list:
                try:
                    ins_value = int(ins)
                    if ins_value < 0:
                        raise ValueError()
                    validated_insentif.append(ins_value)
                except:
                    return jsonify({
                        'success': False,
                        'message': 'Semua nilai insentif harus angka positif'
                    }), 400

            # Remove duplicates and sort
            validated_insentif = sorted(list(set(validated_insentif)))

            if len(validated_insentif) == 0:
                return jsonify({
                    'success': False,
                    'message': 'Minimal harus ada 1 nilai insentif'
                }), 400

            rules[sales]['insentif'] = validated_insentif

        # Validate lokasi if provided
        if 'lokasi' in data:
            lokasi = data['lokasi']
            if not isinstance(lokasi, list) or len(lokasi) == 0:
                return jsonify({
                    'success': False,
                    'message': 'Lokasi harus array dan tidak boleh kosong'
                }), 400
            rules[sales]['lokasi'] = lokasi

        # Update active status if provided
        if 'active' in data:
            rules[sales]['active'] = bool(data['active'])

        # Update timestamp
        from datetime import datetime
        rules[sales]['updated_at'] = datetime.now().strftime('%Y-%m-%d')

        # Save rules
        if save_sop_rules(rules):
            return jsonify({
                'success': True,
                'message': f'SOP rule untuk {sales} berhasil diupdate'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Gagal menyimpan SOP rule'
            }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/sop-rules/<sales>', methods=['DELETE'])
def delete_sop_rule(sales):
    """Delete SOP rule"""
    try:
        # Load existing rules
        rules = load_sop_rules()

        # Check if sales exists
        if sales not in rules:
            return jsonify({
                'success': False,
                'message': f'Sales {sales} tidak ditemukan'
            }), 404

        # Delete rule
        del rules[sales]

        # Save rules
        if save_sop_rules(rules):
            return jsonify({
                'success': True,
                'message': f'SOP rule untuk {sales} berhasil dihapus'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Gagal menyimpan SOP rule'
            }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

# ========================================
# SOP VALIDATION FUNCTIONS
# ========================================

def validate_data_against_sop(df):
    """
    Validate data against SOP rules
    Returns: dict with violations by type
    """
    rules = load_sop_rules()

    if not rules:
        return {
            'total_violations': 0,
            'violations_by_type': {},
            'violations': []
        }

    violations = []

    # Only validate active rules
    active_rules = {k: v for k, v in rules.items() if v.get('active', True)}

    for idx, row in df.iterrows():
        sales_name = str(row['Nama Sales']).strip()

        # Skip if sales not in SOP rules
        if sales_name not in active_rules:
            continue

        sop_rule = active_rules[sales_name]
        customer_violations = []

        # 1. Validate Jatuh Tempo
        try:
            jatuh_tempo_actual = int(row['Jatuh Tempo'])
            jatuh_tempo_expected = sop_rule['jatuh_tempo']

            if jatuh_tempo_actual != jatuh_tempo_expected:
                customer_violations.append({
                    'type': 'jatuh_tempo',
                    'field': 'Jatuh Tempo',
                    'expected': jatuh_tempo_expected,
                    'actual': jatuh_tempo_actual,
                    'severity': 'high'
                })
        except:
            pass

        # 2. Validate Insentif Sales
        try:
            # Clean insentif value
            insentif_str = str(row['Insentif Sales']).replace('.', '').replace(',', '').strip()
            insentif_actual = int(insentif_str) if insentif_str and insentif_str != 'nan' else 0
            insentif_allowed = sop_rule['insentif']

            # Support both single value (old format) and array (new format)
            if isinstance(insentif_allowed, list):
                # New format: array of allowed values [20000, 30000]
                if insentif_actual not in insentif_allowed:
                    expected_str = ' / '.join([f'Rp {v:,}' for v in insentif_allowed])
                    customer_violations.append({
                        'type': 'insentif',
                        'field': 'Insentif Sales',
                        'expected': expected_str,
                        'actual': f'Rp {insentif_actual:,}',
                        'severity': 'medium'
                    })
            else:
                # Old format: single value for backward compatibility
                if insentif_actual != insentif_allowed:
                    customer_violations.append({
                        'type': 'insentif',
                        'field': 'Insentif Sales',
                        'expected': f'Rp {insentif_allowed:,}',
                        'actual': f'Rp {insentif_actual:,}',
                        'severity': 'medium'
                    })
        except:
            pass

        # 3. Validate Lokasi
        try:
            lokasi_actual = str(row['Nama Lokasi']).strip()
            lokasi_allowed = sop_rule['lokasi']

            if lokasi_actual not in lokasi_allowed:
                customer_violations.append({
                    'type': 'lokasi',
                    'field': 'Lokasi',
                    'expected': ', '.join(lokasi_allowed),
                    'actual': lokasi_actual,
                    'severity': 'low'
                })
        except:
            pass

        # If customer has violations, add to list
        if customer_violations:
            violations.append({
                'id_pelanggan': str(row['ID Pelanggan']),
                'nama_pelanggan': str(row['Nama Pelanggan']),
                'nama_sales': sales_name,
                'telepon': str(row['Tlp']),
                'paket': str(row['Nama Langganan']),
                'violations': customer_violations
            })

    # Count violations by type
    violations_by_type = {
        'jatuh_tempo': 0,
        'insentif': 0,
        'lokasi': 0
    }

    for violation in violations:
        for v in violation['violations']:
            violations_by_type[v['type']] += 1

    return {
        'total_violations': len(violations),
        'violations_by_type': violations_by_type,
        'violations': violations
    }

@app.route('/api/violations')
def get_violations():
    """Get all SOP violations from current data"""
    try:
        df = load_data()
        validation_result = validate_data_against_sop(df)

        return jsonify({
            'success': True,
            'data': validation_result
        })
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Error in get_violations: {error_detail}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/locations')
def get_unique_locations():
    """Get unique locations from data for SOP rules form"""
    try:
        df = load_data()
        locations = sorted(df['Nama Lokasi'].dropna().unique().tolist())
        return jsonify({
            'success': True,
            'locations': locations
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

# ===== HISTORY & TRACKING ENDPOINTS =====

@app.route('/api/history', methods=['GET'])
def get_history():
    """Get all historical snapshots (last 50)"""
    try:
        limit = request.args.get('limit', 50, type=int)
        history_mgr = get_history_manager()
        snapshots = history_mgr.get_history(limit=limit)

        return jsonify({
            'success': True,
            'total': len(snapshots),
            'data': clean_for_json(snapshots)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/history/<date_str>', methods=['GET'])
def get_history_by_date(date_str):
    """Get specific snapshot by date (YYYY-MM-DD format)"""
    try:
        history_mgr = get_history_manager()
        snapshot = history_mgr.get_snapshot_by_date(date_str)

        if not snapshot:
            return jsonify({
                'success': False,
                'message': f'No snapshot found for date: {date_str}'
            }), 404

        return jsonify({
            'success': True,
            'data': clean_for_json(snapshot)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/history/compare', methods=['GET'])
def compare_history():
    """Compare two snapshots by date"""
    try:
        date1 = request.args.get('date1')
        date2 = request.args.get('date2')

        if not date1 or not date2:
            return jsonify({
                'success': False,
                'message': 'date1 and date2 parameters required (YYYY-MM-DD format)'
            }), 400

        history_mgr = get_history_manager()
        comparison = history_mgr.get_comparison(date1, date2)

        if 'error' in comparison:
            return jsonify({
                'success': False,
                'message': comparison['error']
            }), 404

        return jsonify({
            'success': True,
            'data': clean_for_json(comparison)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/history/trend', methods=['GET'])
def get_history_trend():
    """Get trend data for last N days"""
    try:
        days = request.args.get('days', 30, type=int)
        history_mgr = get_history_manager()
        trend = history_mgr.get_trend(days=days)

        return jsonify({
            'success': True,
            'total': len(trend),
            'data': clean_for_json(trend)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/history/cleanup', methods=['POST'])
def cleanup_history():
    """Clean up old snapshots, keep only N most recent (admin endpoint)"""
    try:
        keep_count = request.json.get('keep_count', 100)
        history_mgr = get_history_manager()
        history_mgr.delete_old_snapshots(keep_count=keep_count)

        return jsonify({
            'success': True,
            'message': f'Cleanup completed, keeping {keep_count} most recent snapshots'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/customer-segmentation')
def customer_segmentation():
    """Customer Segmentation using RFM Analysis + Churn Risk"""
    try:
        df = load_data()
        today = pd.Timestamp.now()

        # Use refactored date parser instead of duplicating
        df['Tanggal_Registrasi_Parsed'] = df['Tanggal Registrasi'].apply(parse_date_flexible)
        df['Pembayaran_Terakhir_Parsed'] = df['Pembayaran Terakhir'].apply(parse_date_flexible)

        # Calculate metrics using refactored utilities
        df['Tenure_Days'] = df['Tanggal_Registrasi_Parsed'].apply(lambda x: get_tenure_days(x, today) if pd.notna(x) else 0)
        df['Days_Since_Payment'] = df['Pembayaran_Terakhir_Parsed'].apply(lambda x: get_days_since(x, today) if pd.notna(x) else 999)
        df['Harga_Clean'] = df['Harga'].apply(clean_price)

        # RFM Scoring (1-5 scale)
        def score_rfm(values, reverse=False):
            """Score values 1-5 based on quantiles, handle duplicates"""
            try:
                if reverse:
                    result = pd.qcut(values, q=5, labels=[5, 4, 3, 2, 1], duplicates='drop')
                else:
                    result = pd.qcut(values, q=5, labels=False, duplicates='drop')
                    result = result + 1  # Convert 0-based to 1-based
                return result
            except:
                # If qcut fails, use rank-based scoring
                if reverse:
                    return 6 - pd.cut(values, bins=5, labels=False, duplicates='drop')
                else:
                    return pd.cut(values, bins=5, labels=False, duplicates='drop') + 1

        # Recency: Recent payment = high score (active customers)
        df['R_Score'] = score_rfm(df['Days_Since_Payment'].fillna(999), reverse=True)

        # Frequency: Longer tenure = high score
        df['F_Score'] = score_rfm(df['Tenure_Days'].fillna(0))

        # Monetary: Higher revenue = high score
        df['M_Score'] = score_rfm(df['Harga_Clean'].fillna(0))

        # Convert to numeric
        df['R_Score'] = pd.to_numeric(df['R_Score'], errors='coerce').fillna(1)
        df['F_Score'] = pd.to_numeric(df['F_Score'], errors='coerce').fillna(1)
        df['M_Score'] = pd.to_numeric(df['M_Score'], errors='coerce').fillna(1)

        # Calculate RFM Score
        df['RFM_Score'] = df['R_Score'] + df['F_Score'] + df['M_Score']

        # Churn Risk Score (0-100)
        df['Churn_Risk_Score'] = 0.0

        # Rule 1: Days since payment (most important)
        df.loc[df['Days_Since_Payment'] > 180, 'Churn_Risk_Score'] += 40
        df.loc[(df['Days_Since_Payment'] > 90) & (df['Days_Since_Payment'] <= 180), 'Churn_Risk_Score'] += 25
        df.loc[(df['Days_Since_Payment'] > 30) & (df['Days_Since_Payment'] <= 90), 'Churn_Risk_Score'] += 10

        # Rule 2: Status langganan
        df.loc[df['Status Langganan'] == 'Off', 'Churn_Risk_Score'] += 30

        # Rule 3: Tenure (new customers = lower risk initially)
        df.loc[df['Tenure_Days'] < 30, 'Churn_Risk_Score'] -= 10
        df.loc[df['Tenure_Days'] > 365, 'Churn_Risk_Score'] -= 5

        # Clamp to 0-100
        df['Churn_Risk_Score'] = df['Churn_Risk_Score'].clip(0, 100)

        # Segment Assignment
        def assign_segment(row):
            status = row['Status Langganan']
            rfm = row['RFM_Score']
            churn = row['Churn_Risk_Score']
            days_unpaid = row['Days_Since_Payment']

            if status == 'Off':
                if churn > 70:
                    return 'Churned'
                elif churn > 50:
                    return 'At Risk'
            else:  # On
                if row['Tenure_Days'] < 30:
                    return 'New'
                elif rfm >= 13 and churn < 30:
                    return 'Champions'
                elif rfm >= 10 and churn < 50:
                    return 'Loyal'
                elif rfm >= 7 or churn < 50:
                    return 'Potential'
                else:
                    return 'At Risk'

            return 'At Risk'

        df['Segment'] = df.apply(assign_segment, axis=1)

        # Build response
        segments = {}
        for segment_name in ['Champions', 'Loyal', 'Potential', 'At Risk', 'Churned', 'New']:
            seg_df = df[df['Segment'] == segment_name]

            # Calculate revenue safely, handling NaN
            seg_revenue_sum = seg_df[seg_df['Status Langganan'] == 'On']['Harga_Clean'].sum()
            seg_revenue_mean = seg_df['Harga_Clean'].mean()
            seg_tenure_mean = seg_df['Tenure_Days'].mean()

            segments[segment_name] = {
                'count': len(seg_df),
                'percentage': round(len(seg_df) / len(df) * 100, 2),
                'avg_rfm_score': round(seg_df['RFM_Score'].mean(), 2) if not pd.isna(seg_df['RFM_Score'].mean()) else 0,
                'avg_churn_risk': round(seg_df['Churn_Risk_Score'].mean(), 2) if not pd.isna(seg_df['Churn_Risk_Score'].mean()) else 0,
                'total_revenue': int(seg_revenue_sum) if not pd.isna(seg_revenue_sum) and seg_revenue_sum > 0 else 0,
                'avg_revenue_per_customer': int(seg_revenue_mean) if not pd.isna(seg_revenue_mean) and seg_revenue_mean > 0 else 0,
                'avg_tenure_days': int(seg_tenure_mean) if not pd.isna(seg_tenure_mean) else 0,
                'active_count': len(seg_df[seg_df['Status Langganan'] == 'On']),
                'inactive_count': len(seg_df[seg_df['Status Langganan'] == 'Off']),
                'top_packages': seg_df['Nama Langganan'].value_counts().head(3).to_dict(),
                'top_locations': seg_df['Nama Lokasi'].value_counts().head(3).to_dict(),
            }

        # Overall stats
        summary = {
            'total_customers': len(df),
            'active_customers': len(df[df['Status Langganan'] == 'On']),
            'total_revenue': int(df[df['Status Langganan'] == 'On']['Harga_Clean'].sum()),
            'avg_churn_risk_all': round(df['Churn_Risk_Score'].mean(), 2),
            'high_risk_count': len(df[df['Churn_Risk_Score'] > 70]),
            'champion_retention_value': segments['Champions']['total_revenue'],
            'at_risk_recovery_potential': segments['At Risk']['total_revenue'],
        }

        return jsonify(clean_for_json({
            'success': True,
            'summary': summary,
            'segments': segments
        }))

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/profitability-analysis')
def profitability_analysis():
    """
    Profitability Analysis Dashboard
    Calculate profit margins, ROI, and profitability metrics by segment, package, and location
    """
    try:
        df = load_data()
        df['Harga_Clean'] = df['Harga'].apply(clean_price)

        # Filter to active customers
        df_active = df[df['Status Langganan'] == 'On'].copy()

        # Estimate operational costs (can be adjusted based on business model)
        # Cost structure assumptions:
        # - Fixed infrastructure cost per month per customer: ~50K
        # - Variable cost percentage of revenue: ~20%
        FIXED_COST_PER_CUSTOMER = 50000
        VARIABLE_COST_PERCENTAGE = 0.20

        def calculate_profit_metrics(price):
            """Calculate profit metrics for a given price"""
            if price <= 0:
                return {'revenue': 0, 'cost': 0, 'profit': 0, 'margin': 0, 'margin_percentage': 0}

            revenue = price
            fixed_cost = FIXED_COST_PER_CUSTOMER
            variable_cost = int(revenue * VARIABLE_COST_PERCENTAGE)
            total_cost = fixed_cost + variable_cost
            profit = revenue - total_cost
            margin_percentage = (profit / revenue * 100) if revenue > 0 else 0

            return {
                'revenue': revenue,
                'cost': total_cost,
                'profit': profit,
                'margin': profit,
                'margin_percentage': max(0, margin_percentage)  # Can't have negative margin %
            }

        df_active['Profit_Metrics'] = df_active['Harga_Clean'].apply(calculate_profit_metrics)

        # Extract profit data
        df_active['Profit'] = df_active['Profit_Metrics'].apply(lambda x: x['profit'])
        df_active['Cost'] = df_active['Profit_Metrics'].apply(lambda x: x['cost'])
        df_active['Margin_Percentage'] = df_active['Profit_Metrics'].apply(lambda x: x['margin_percentage'])

        # Overall profitability metrics
        total_revenue = int(df_active['Harga_Clean'].sum())
        total_cost = int(df_active['Cost'].sum())
        total_profit = int(df_active['Profit'].sum())
        overall_margin_percentage = (total_profit / total_revenue * 100) if total_revenue > 0 else 0

        # Profitability by package
        package_profitability = df_active.groupby('Nama Langganan').agg({
            'Harga_Clean': ['sum', 'count', 'mean'],
            'Cost': 'sum',
            'Profit': 'sum',
            'Margin_Percentage': 'mean'
        }).round(0)

        package_data = {}
        for package, row in package_profitability.iterrows():
            revenue = int(row[('Harga_Clean', 'sum')])
            count = int(row[('Harga_Clean', 'count')])
            cost = int(row[('Cost', 'sum')])
            profit = int(row[('Profit', 'sum')])
            avg_margin = row[('Margin_Percentage', 'mean')]

            package_data[package] = {
                'revenue': revenue,
                'cost': cost,
                'profit': profit,
                'customer_count': count,
                'avg_revenue_per_customer': int(row[('Harga_Clean', 'mean')]),
                'margin_percentage': float(avg_margin),
                'profitability_ratio': float(profit / revenue * 100) if revenue > 0 else 0
            }

        # Sort by profit
        package_profitability_sorted = dict(sorted(package_data.items(),
                                                    key=lambda x: x[1]['profit'],
                                                    reverse=True))

        # Profitability by location (top 15)
        location_profitability = df_active.groupby('Nama Lokasi').agg({
            'Harga_Clean': ['sum', 'count', 'mean'],
            'Cost': 'sum',
            'Profit': 'sum',
            'Margin_Percentage': 'mean'
        }).round(0)

        location_data = {}
        for location, row in location_profitability.iterrows():
            revenue = int(row[('Harga_Clean', 'sum')])
            count = int(row[('Harga_Clean', 'count')])
            cost = int(row[('Cost', 'sum')])
            profit = int(row[('Profit', 'sum')])
            avg_margin = row[('Margin_Percentage', 'mean')]

            location_data[location] = {
                'revenue': revenue,
                'cost': cost,
                'profit': profit,
                'customer_count': count,
                'avg_revenue_per_customer': int(row[('Harga_Clean', 'mean')]),
                'margin_percentage': float(avg_margin),
                'profitability_ratio': float(profit / revenue * 100) if revenue > 0 else 0
            }

        # Sort by profit and limit to top 15
        location_profitability_sorted = dict(sorted(location_data.items(),
                                                     key=lambda x: x[1]['profit'],
                                                     reverse=True)[:15])

        # Profitability by sales
        sales_profitability = df_active.groupby('Nama Sales').agg({
            'Harga_Clean': ['sum', 'count', 'mean'],
            'Cost': 'sum',
            'Profit': 'sum',
            'Margin_Percentage': 'mean'
        }).round(0)

        sales_data = {}
        for sales, row in sales_profitability.iterrows():
            revenue = int(row[('Harga_Clean', 'sum')])
            count = int(row[('Harga_Clean', 'count')])
            cost = int(row[('Cost', 'sum')])
            profit = int(row[('Profit', 'sum')])
            avg_margin = row[('Margin_Percentage', 'mean')]

            sales_data[sales] = {
                'revenue': revenue,
                'cost': cost,
                'profit': profit,
                'customer_count': count,
                'avg_revenue_per_customer': int(row[('Harga_Clean', 'mean')]),
                'margin_percentage': float(avg_margin),
                'profitability_ratio': float(profit / revenue * 100) if revenue > 0 else 0
            }

        # Sort by profit
        sales_profitability_sorted = dict(sorted(sales_data.items(),
                                                  key=lambda x: x[1]['profit'],
                                                  reverse=True))

        # Profitability by segment (from customer segmentation)
        today = pd.Timestamp.now()

        # Use refactored date parser instead of duplicating
        df_active['Tanggal_Registrasi_Parsed'] = df_active['Tanggal Registrasi'].apply(parse_date_flexible)
        df_active['Pembayaran_Terakhir_Parsed'] = df_active['Pembayaran Terakhir'].apply(parse_date_flexible)
        df_active['Tenure_Days'] = df_active['Tanggal_Registrasi_Parsed'].apply(lambda x: get_tenure_days(x, today) if pd.notna(x) else 0)
        df_active['Days_Since_Payment'] = df_active['Pembayaran_Terakhir_Parsed'].apply(lambda x: get_days_since(x, today) if pd.notna(x) else 999)

        # Segment assignment (simplified from customer_segmentation)
        def assign_segment(row):
            status = row['Status Langganan']
            tenure = row['Tenure_Days']
            days_unpaid = row['Days_Since_Payment']

            if status == 'Off':
                return 'Churned'
            elif tenure < 30:
                return 'New'
            elif pd.notna(days_unpaid):
                if days_unpaid > 180:
                    return 'At Risk'
                elif days_unpaid > 90:
                    return 'Potential'
                else:
                    return 'Loyal'
            else:
                return 'Loyal'

        df_active['Segment'] = df_active.apply(assign_segment, axis=1)

        segment_profitability = df_active.groupby('Segment').agg({
            'Harga_Clean': ['sum', 'count', 'mean'],
            'Cost': 'sum',
            'Profit': 'sum',
            'Margin_Percentage': 'mean'
        }).round(0)

        segment_data = {}
        for segment, row in segment_profitability.iterrows():
            revenue = int(row[('Harga_Clean', 'sum')])
            count = int(row[('Harga_Clean', 'count')])
            cost = int(row[('Cost', 'sum')])
            profit = int(row[('Profit', 'sum')])
            avg_margin = row[('Margin_Percentage', 'mean')]

            segment_data[segment] = {
                'revenue': revenue,
                'cost': cost,
                'profit': profit,
                'customer_count': count,
                'avg_revenue_per_customer': int(row[('Harga_Clean', 'mean')]),
                'margin_percentage': float(avg_margin),
                'profitability_ratio': float(profit / revenue * 100) if revenue > 0 else 0,
                'roi': float((profit / cost * 100)) if cost > 0 else 0  # ROI = Profit / Cost * 100
            }

        # Sort by profit
        segment_profitability_sorted = dict(sorted(segment_data.items(),
                                                    key=lambda x: x[1]['profit'],
                                                    reverse=True))

        # Profitability insights
        most_profitable_package = max(package_data.items(), key=lambda x: x[1]['profit']) if package_data else None
        least_profitable_package = min(package_data.items(), key=lambda x: x[1]['profit']) if package_data else None
        most_profitable_segment = max(segment_data.items(), key=lambda x: x[1]['profit']) if segment_data else None
        most_efficient_package = max(package_data.items(), key=lambda x: x[1]['margin_percentage']) if package_data else None

        insights = {
            'most_profitable_package': {
                'name': most_profitable_package[0],
                'profit': most_profitable_package[1]['profit'],
                'margin': most_profitable_package[1]['margin_percentage']
            } if most_profitable_package else None,
            'least_profitable_package': {
                'name': least_profitable_package[0],
                'profit': least_profitable_package[1]['profit'],
                'margin': least_profitable_package[1]['margin_percentage']
            } if least_profitable_package else None,
            'most_profitable_segment': {
                'name': most_profitable_segment[0],
                'profit': most_profitable_segment[1]['profit'],
                'roi': most_profitable_segment[1]['roi']
            } if most_profitable_segment else None,
            'most_efficient_package': {
                'name': most_efficient_package[0],
                'margin_percentage': most_efficient_package[1]['margin_percentage']
            } if most_efficient_package else None
        }

        return jsonify(clean_for_json({
            'success': True,
            'summary': {
                'total_revenue': total_revenue,
                'total_cost': total_cost,
                'total_profit': total_profit,
                'overall_margin_percentage': round(overall_margin_percentage, 2),
                'total_customers': len(df_active),
                'avg_profit_per_customer': int(total_profit / len(df_active)) if len(df_active) > 0 else 0,
                'overall_roi': round((total_profit / total_cost * 100), 2) if total_cost > 0 else 0
            },
            'by_package': package_profitability_sorted,
            'by_location': location_profitability_sorted,
            'by_sales': sales_profitability_sorted,
            'by_segment': segment_profitability_sorted,
            'insights': insights
        }))

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/api/churn-analysis')
def churn_analysis():
    """
    Churn Analysis Dashboard
    Identify at-risk customers, calculate churn probability, and provide retention strategies
    """
    try:
        df = load_data()
        today = pd.Timestamp.now()

        # Use refactored date parser instead of duplicating
        df['Tanggal_Registrasi_Parsed'] = df['Tanggal Registrasi'].apply(parse_date_flexible)
        df['Pembayaran_Terakhir_Parsed'] = df['Pembayaran Terakhir'].apply(parse_date_flexible)
        df['Harga_Clean'] = df['Harga'].apply(clean_price)

        # Calculate tenure using refactored utilities
        df['Tenure_Days'] = df['Tanggal_Registrasi_Parsed'].apply(lambda x: get_tenure_days(x, today) if pd.notna(x) else 0)
        df['Days_Since_Payment'] = df['Pembayaran_Terakhir_Parsed'].apply(lambda x: get_days_since(x, today) if pd.notna(x) else 999)

        # Churn Risk Scoring (0-100)
        df['Churn_Risk_Score'] = 0.0

        # Rule 1: Days since payment (most important - 40 points)
        df.loc[df['Days_Since_Payment'] > 180, 'Churn_Risk_Score'] += 40
        df.loc[(df['Days_Since_Payment'] > 90) & (df['Days_Since_Payment'] <= 180), 'Churn_Risk_Score'] += 25
        df.loc[(df['Days_Since_Payment'] > 30) & (df['Days_Since_Payment'] <= 90), 'Churn_Risk_Score'] += 10

        # Rule 2: Status langganan (30 points)
        df.loc[df['Status Langganan'] == 'Off', 'Churn_Risk_Score'] += 30

        # Rule 3: Tenure (new = lower risk, long-term = lower risk)
        df.loc[df['Tenure_Days'] < 30, 'Churn_Risk_Score'] -= 10  # New customers get benefit
        df.loc[df['Tenure_Days'] > 365, 'Churn_Risk_Score'] -= 5   # Loyal get small benefit

        # Clamp to 0-100
        df['Churn_Risk_Score'] = df['Churn_Risk_Score'].clip(0, 100)

        # Categorize churn risk
        def categorize_risk(score):
            if score >= 80:
                return 'Critical'
            elif score >= 60:
                return 'High'
            elif score >= 40:
                return 'Medium'
            elif score >= 20:
                return 'Low'
            else:
                return 'Very Low'

        df['Churn_Category'] = df['Churn_Risk_Score'].apply(categorize_risk)

        # Active customers only for more meaningful churn analysis
        df_active = df[df['Status Langganan'] == 'On'].copy()

        # Summary statistics
        total_customers = len(df_active)
        critical_risk = len(df_active[df_active['Churn_Risk_Score'] >= 80])
        high_risk = len(df_active[(df_active['Churn_Risk_Score'] >= 60) & (df_active['Churn_Risk_Score'] < 80)])
        medium_risk = len(df_active[(df_active['Churn_Risk_Score'] >= 40) & (df_active['Churn_Risk_Score'] < 60)])
        low_risk = len(df_active[df_active['Churn_Risk_Score'] < 40])

        critical_risk_revenue = int(df_active[df_active['Churn_Risk_Score'] >= 80]['Harga_Clean'].sum())
        high_risk_revenue = int(df_active[(df_active['Churn_Risk_Score'] >= 60) & (df_active['Churn_Risk_Score'] < 80)]['Harga_Clean'].sum())

        # Churn probability by characteristics
        churn_by_package = df_active.groupby('Nama Langganan').agg({
            'Churn_Risk_Score': ['mean', 'count'],
            'Harga_Clean': 'sum'
        }).round(2)

        package_churn_data = {}
        for package, row in churn_by_package.iterrows():
            avg_risk = float(row[('Churn_Risk_Score', 'mean')])
            count = int(row[('Churn_Risk_Score', 'count')])
            revenue = int(row[('Harga_Clean', 'sum')])

            package_churn_data[package] = {
                'avg_churn_risk': avg_risk,
                'customer_count': count,
                'total_revenue': revenue,
                'at_risk_percentage': float(count / total_customers * 100) if total_customers > 0 else 0
            }

        # Sort by avg churn risk
        package_churn_sorted = dict(sorted(package_churn_data.items(),
                                           key=lambda x: x[1]['avg_churn_risk'],
                                           reverse=True))

        # Churn by location
        churn_by_location = df_active.groupby('Nama Lokasi').agg({
            'Churn_Risk_Score': ['mean', 'count'],
            'Harga_Clean': 'sum'
        }).round(2)

        location_churn_data = {}
        for location, row in churn_by_location.iterrows():
            avg_risk = float(row[('Churn_Risk_Score', 'mean')])
            count = int(row[('Churn_Risk_Score', 'count')])
            revenue = int(row[('Harga_Clean', 'sum')])

            location_churn_data[location] = {
                'avg_churn_risk': avg_risk,
                'customer_count': count,
                'total_revenue': revenue,
                'at_risk_percentage': float(count / total_customers * 100) if total_customers > 0 else 0
            }

        # Sort by avg churn risk and limit to top 15
        location_churn_sorted = dict(sorted(location_churn_data.items(),
                                            key=lambda x: x[1]['avg_churn_risk'],
                                            reverse=True)[:15])

        # Most at-risk customers (top 20)
        at_risk_customers = df_active[df_active['Churn_Risk_Score'] >= 60].nlargest(20, 'Churn_Risk_Score')

        at_risk_list = []
        for idx, row in at_risk_customers.iterrows():
            at_risk_list.append({
                'customer_name': row['Nama Pelanggan'],
                'phone': row['Tlp'],
                'package': row['Nama Langganan'],
                'location': row['Nama Lokasi'],
                'sales': row['Nama Sales'],
                'churn_risk': float(row['Churn_Risk_Score']),
                'risk_category': categorize_risk(row['Churn_Risk_Score']),
                'days_since_payment': int(row['Days_Since_Payment']) if pd.notna(row['Days_Since_Payment']) else 0,
                'tenure_days': int(row['Tenure_Days']) if pd.notna(row['Tenure_Days']) else 0,
                'monthly_revenue': int(row['Harga_Clean'])
            })

        # Revenue at risk
        total_revenue_at_risk = int(df_active[df_active['Churn_Risk_Score'] >= 60]['Harga_Clean'].sum())
        revenue_critical_risk = int(df_active[df_active['Churn_Risk_Score'] >= 80]['Harga_Clean'].sum())

        # Churn predictions and insights
        # Average churn score by status
        avg_churn_all = float(df_active['Churn_Risk_Score'].mean())
        avg_churn_unpaid = float(df_active[df_active['Days_Since_Payment'] > 30]['Churn_Risk_Score'].mean())

        # Retention strategies
        strategies = []

        # Strategy 1: Immediate engagement
        if critical_risk > 0:
            strategies.append({
                'priority': 'Critical',
                'segment': f'{critical_risk} Critical Risk Customers',
                'strategy': 'Immediate personal outreach and special retention offer',
                'revenue_impact': revenue_critical_risk,
                'estimated_retention': min(60, 40 + critical_risk)  # Target 40-100% retention
            })

        # Strategy 2: Payment reminder campaign
        unpaid_60_90 = len(df_active[(df_active['Days_Since_Payment'] >= 60) & (df_active['Days_Since_Payment'] < 90)])
        if unpaid_60_90 > 0:
            revenue_60_90 = int(df_active[(df_active['Days_Since_Payment'] >= 60) & (df_active['Days_Since_Payment'] < 90)]['Harga_Clean'].sum())
            strategies.append({
                'priority': 'High',
                'segment': f'{unpaid_60_90} Customers 60-90 days unpaid',
                'strategy': 'Automated payment reminder via SMS/email with incentives',
                'revenue_impact': revenue_60_90,
                'estimated_retention': 70
            })

        # Strategy 3: Loyalty program
        if low_risk > 100:
            strategies.append({
                'priority': 'Medium',
                'segment': f'{low_risk} Loyal Customers',
                'strategy': 'Loyalty rewards program for 12+ month tenure customers',
                'revenue_impact': int(df_active[df_active['Churn_Risk_Score'] < 40]['Harga_Clean'].sum()),
                'estimated_retention': 95
            })

        # Strategy 4: Upsell to at-risk medium segment
        if medium_risk > 0:
            revenue_medium = int(df_active[(df_active['Churn_Risk_Score'] >= 40) & (df_active['Churn_Risk_Score'] < 60)]['Harga_Clean'].sum())
            strategies.append({
                'priority': 'Medium',
                'segment': f'{medium_risk} Medium Risk Customers',
                'strategy': 'Upgrade offer to higher tier package with promotional pricing',
                'revenue_impact': revenue_medium,
                'estimated_retention': 65
            })

        # Potential recovery value
        potential_recovery_critical = int(revenue_critical_risk * 0.5)  # 50% recovery target
        potential_recovery_high = int(high_risk_revenue * 0.4)  # 40% recovery target

        return jsonify(clean_for_json({
            'success': True,
            'summary': {
                'total_customers': total_customers,
                'avg_churn_risk_score': round(avg_churn_all, 2),
                'critical_risk_count': critical_risk,
                'high_risk_count': high_risk,
                'medium_risk_count': medium_risk,
                'low_risk_count': low_risk,
                'total_revenue': int(df_active['Harga_Clean'].sum()),
                'revenue_at_risk': total_revenue_at_risk,
                'revenue_critical_risk': revenue_critical_risk,
                'potential_recovery_value': potential_recovery_critical + potential_recovery_high,
                'percentage_at_risk': round(((critical_risk + high_risk) / total_customers * 100), 2) if total_customers > 0 else 0
            },
            'by_package': package_churn_sorted,
            'by_location': location_churn_sorted,
            'at_risk_customers': at_risk_list,
            'retention_strategies': strategies,
            'insights': {
                'highest_risk_package': max(package_churn_data.items(), key=lambda x: x[1]['avg_churn_risk'])[0] if package_churn_data else None,
                'highest_risk_location': max(location_churn_data.items(), key=lambda x: x[1]['avg_churn_risk'])[0] if location_churn_data else None,
                'avg_churn_unpaid': round(avg_churn_unpaid, 2)
            }
        }))

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
