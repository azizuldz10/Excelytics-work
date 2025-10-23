"""
File parser - centralized Excel/CSV parsing logic
Replaces duplicated parsing code with strategy pattern
"""
import pandas as pd
import os
from config import MAIN_DATA_FILE, READ_STRATEGIES


def find_header_row(file_path, file_ext):
    """
    Find the row containing 'ID Pelanggan' column

    Args:
        file_path: Path to file
        file_ext: File extension (csv, xls, xlsx)

    Returns:
        int - row index of header row (0 if not found)
    """
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
            except Exception:
                try:
                    temp_df = pd.read_excel(file_path, engine='openpyxl', header=None, nrows=10)
                except Exception:
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


def _attempt_read_with_engine(file_path, file_ext, engine, encoding=None, header_row=0):
    """
    Attempt to read file with specific engine and encoding

    Args:
        file_path: Path to file
        file_ext: File extension
        engine: Engine to use (openpyxl, xlrd, etc.)
        encoding: Encoding for CSV (utf-8-sig, latin1, etc.)
        header_row: Row to use as header

    Returns:
        tuple: (success: bool, dataframe or error_message, engine_used)
    """
    try:
        if file_ext == 'csv':
            df = pd.read_csv(file_path, encoding=encoding or 'utf-8-sig', skiprows=header_row)
            print(f"✓ Successfully read CSV with {encoding or 'utf-8-sig'}: {len(df)} rows")
            return True, df, encoding or 'utf-8-sig'

        elif file_ext in ['xls', 'xlsx']:
            df = pd.read_excel(file_path, engine=engine, skiprows=header_row)
            print(f"✓ Successfully read with {engine}: {len(df)} rows")
            return True, df, engine

    except Exception as e:
        error_msg = f"{engine or 'encoding=' + (encoding or 'unknown')}: {str(e)}"
        print(f"✗ Failed: {error_msg}")
        return False, error_msg, None

    return False, f"Unsupported format: {file_ext}", None


def read_excel_file(file_path):
    """
    Read single Excel/CSV file with intelligent fallback strategy

    Args:
        file_path: Path to file

    Returns:
        tuple: (success: bool, dataframe or error_message, file_ext)
    """
    try:
        # Determine file extension
        file_ext = file_path.rsplit('.', 1)[1].lower()

        if file_ext not in READ_STRATEGIES:
            return False, f"Format file tidak didukung: {file_ext}", None

        print(f"\n--- Processing File: {file_path} ---")

        # Find header row
        header_row = find_header_row(file_path, file_ext)
        print(f"Using header row: {header_row}")

        # Try reading with strategies
        strategies = READ_STRATEGIES[file_ext]
        error_messages = []

        for strategy in strategies:
            if file_ext == 'csv':
                # CSV uses encoding as strategy
                success, result, _ = _attempt_read_with_engine(file_path, file_ext, None, strategy, header_row)
            else:
                # Excel uses engine as strategy
                success, result, _ = _attempt_read_with_engine(file_path, file_ext, strategy, None, header_row)

            if success:
                df = result
                break
            else:
                error_messages.append(result)

        # If all strategies failed, try CSV as last resort
        if 'df' not in locals() and file_ext in ['xls', 'xlsx']:
            print("Trying CSV as last resort fallback...")
            success, result, _ = _attempt_read_with_engine(file_path, file_ext, None, 'utf-8-sig', header_row)
            if success:
                df = result
            else:
                error_messages.append(result)

        # Check if we got a dataframe
        if 'df' not in locals() or df is None:
            error_detail = "\n".join(error_messages)
            return False, f"Gagal membaca file. Detail:\n{error_detail}", None

        print(f"Successfully read {len(df)} rows")
        print(f"Columns (first 10): {list(df.columns)[:10]}")

        # Clean column names
        df.columns = df.columns.str.strip()

        # Verify ID Pelanggan column exists
        if 'ID Pelanggan' not in df.columns:
            print(f"ERROR: 'ID Pelanggan' column not found!")
            print(f"Available columns: {list(df.columns)}")

            # Try to find similar columns
            possible_cols = [col for col in df.columns
                           if 'ID' in str(col).upper() or 'PELANGGAN' in str(col).upper()]
            if possible_cols:
                return False, f"Kolom 'ID Pelanggan' tidak ditemukan. Kolom yang mirip: {', '.join(possible_cols[:5])}", None
            else:
                return False, f"Kolom 'ID Pelanggan' tidak ditemukan. Kolom tersedia: {', '.join(list(df.columns)[:10])}", None

        return True, df, file_ext

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Error in read_excel_file: {error_detail}")
        return False, f"Error: {str(e)}", None


def merge_dataframes(dataframes):
    """
    Merge multiple dataframes and deduplicate

    Args:
        dataframes: List of DataFrames to merge

    Returns:
        tuple: (success: bool, merged_df or error_message, stats)
    """
    try:
        if not dataframes:
            return False, "No dataframes to merge", None

        print(f"\n--- Merging {len(dataframes)} dataframes ---")

        # Calculate stats before merge
        total_rows_before = sum(len(df) for df in dataframes)

        # Merge all dataframes
        merged_df = pd.concat(dataframes, ignore_index=True)
        print(f"Merged data: {len(merged_df)} rows")

        # Remove duplicates based on ID Pelanggan
        merged_df = merged_df.drop_duplicates(subset=['ID Pelanggan'], keep='first')
        duplicates_removed = total_rows_before - len(merged_df)
        print(f"Removed {duplicates_removed} duplicates")

        # Clean column names
        merged_df.columns = merged_df.columns.str.strip()

        stats = {
            'total_rows_before_merge': total_rows_before,
            'total_rows_after_merge': len(merged_df),
            'duplicates_removed': duplicates_removed,
            'columns': len(merged_df.columns)
        }

        return True, merged_df, stats

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Error in merge_dataframes: {error_detail}")
        return False, f"Error merging dataframes: {str(e)}", None


def save_data(df, backup_existing=True):
    """
    Save dataframe to CSV and optionally backup existing file

    Args:
        df: DataFrame to save
        backup_existing: Whether to backup existing file

    Returns:
        tuple: (success: bool, message, backup_file)
    """
    try:
        import shutil
        from datetime import datetime

        backup_file = None

        # Backup old file if exists
        if backup_existing and os.path.exists(MAIN_DATA_FILE):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f'{MAIN_DATA_FILE.replace(".csv", "")}_backup_{timestamp}.csv'
            shutil.copy(MAIN_DATA_FILE, backup_file)
            print(f"Backup created: {backup_file}")

        # Save new file
        df.to_csv(MAIN_DATA_FILE, index=False, encoding='utf-8-sig')
        print(f"Saved data: {len(df)} rows, {len(df.columns)} columns")

        return True, f"Data berhasil disimpan: {len(df)} rows", backup_file

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Error saving data: {error_detail}")
        return False, f"Error saving data: {str(e)}", None
