"""
Configuration file for CSV Report application
Centralize all constants and configuration values
"""
import os

# ===== FILE UPLOAD CONFIGURATION =====
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xls', 'xlsx', 'csv'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
MAX_DISPLAY_ROWS = 100  # Customer list display limit

# ===== DATA FILES =====
MAIN_DATA_FILE = 'data-wifi-clean.csv'
SOP_RULES_FILE = 'sop_rules.json'
HISTORY_DB_FILE = 'history.db'

# ===== PROFITABILITY ANALYSIS =====
FIXED_COST_PER_CUSTOMER = 50000  # Rp per month
VARIABLE_COST_PERCENTAGE = 0.20  # 20% of revenue

# ===== CHURN ANALYSIS =====
CHURN_RISK_WEIGHTS = {
    'days_since_payment': {
        'critical': (180, 40),      # > 180 days = +40 points
        'high': (90, 25),            # 90-180 days = +25 points
        'medium': (30, 10),          # 30-90 days = +10 points
    },
    'status_offline': 30,            # Off status = +30 points
    'new_customer_bonus': -10,       # < 30 days tenure = -10 points
    'loyal_bonus': -5,               # > 365 days tenure = -5 points
}

# ===== DATA QUALITY VALIDATION =====
DATA_QUALITY_RULES = {
    'min_phone_digits': 8,           # Minimum phone number digits
    'base_ktp_url': 'https://e.ebilling.id:2096/img/ktp/',
    'coordinate_has_comma': True,    # Must have comma separator
    'coordinate_not_zero': True,     # Can't be 0,0
}

# ===== DATE FORMATS =====
SUPPORTED_DATE_FORMATS = [
    '%Y-%m-%d',          # YYYY-MM-DD
    '%d-%B-%Y',          # DD-Month-YYYY (e.g., 16-October-2025)
]

# ===== EXCEL/CSV READING STRATEGIES =====
# Order matters - tried in sequence
READ_STRATEGIES = {
    'csv': ['utf-8-sig', 'latin1'],
    'xlsx': ['openpyxl'],
    'xls': ['xlrd', 'openpyxl'],
}

# ===== LOG LEVELS =====
LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Create uploads folder if not exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
