"""
Data validators - centralized data quality and validation logic
Replaces scattered validation code across app.py
"""
import pandas as pd
from config import DATA_QUALITY_RULES


class DataValidator:
    """Centralized data validation and quality checks"""

    @staticmethod
    def is_ktp_missing(ktp_url):
        """
        Check if KTP (ID photo) URL is missing or invalid

        Args:
            ktp_url: URL string to check

        Returns:
            bool - True if KTP is missing/invalid
        """
        if pd.isna(ktp_url):
            return True

        ktp_str = str(ktp_url).strip()

        # Check for empty or placeholder values
        if ktp_str in ['', 'nan']:
            return True

        # Check if it's just the base URL
        base_url = DATA_QUALITY_RULES['base_ktp_url']
        if ktp_str == base_url or ktp_str.endswith('/'):
            return True

        # Check if path is too short (no actual filename)
        if ktp_str.count('/') <= 4:
            return True

        return False

    @staticmethod
    def is_phone_invalid(phone):
        """
        Check if phone number is invalid

        Args:
            phone: Phone number to validate

        Returns:
            bool - True if phone is invalid
        """
        if pd.isna(phone):
            return True

        phone_str = str(phone).strip()

        # Check for empty or placeholder values
        if phone_str in ['', 'nan']:
            return True

        # Check if too short
        if len(phone_str) <= 2:
            return True

        # Check for anomaly values
        if phone_str in ['0', '00', '01', '1', '11']:
            return True

        # Extract only digits
        digits_only = ''.join(filter(str.isdigit, phone_str))

        # Check minimum digits
        min_digits = DATA_QUALITY_RULES['min_phone_digits']
        if len(digits_only) < min_digits:
            return True

        return False

    @staticmethod
    def is_coordinate_missing(coord):
        """
        Check if coordinate is missing or invalid

        Args:
            coord: Coordinate string (format: "lat,lng")

        Returns:
            bool - True if coordinate is missing/invalid
        """
        if pd.isna(coord):
            return True

        coord_str = str(coord).strip()

        # Check for empty or placeholder values
        if coord_str in ['', 'nan']:
            return True

        # Must have comma separator
        if ',' not in coord_str:
            return True

        # Try to parse coordinates
        try:
            parts = coord_str.split(',')
            if len(parts) != 2:
                return True

            lat = float(parts[0].strip())
            lng = float(parts[1].strip())

            # Can't be 0,0 (invalid coordinates)
            if lat == 0 and lng == 0:
                return True

            return False
        except (ValueError, AttributeError):
            return True

    @staticmethod
    def validate_jatuh_tempo(value):
        """
        Validate jatuh tempo (due date day of month)

        Args:
            value: Day of month to validate

        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        try:
            jatuh_tempo = int(value)
            if jatuh_tempo < 1 or jatuh_tempo > 31:
                return False, "Jatuh tempo harus angka 1-31"
            return True, None
        except (ValueError, TypeError):
            return False, "Jatuh tempo harus berupa angka"

    @staticmethod
    def validate_insentif(value):
        """
        Validate insentif (incentive amount)
        Supports both single value and array

        Args:
            value: int, list - incentive value(s)

        Returns:
            tuple: (is_valid: bool, validated_list: list or None, error_message: str or None)
        """
        try:
            # Convert single value to list
            if isinstance(value, int):
                insentif_list = [value]
            elif isinstance(value, list):
                insentif_list = value
            else:
                return False, None, "Insentif harus berupa angka atau array angka"

            # Validate each value
            validated_insentif = []
            for ins in insentif_list:
                try:
                    ins_value = int(ins)
                    if ins_value < 0:
                        return False, None, "Semua nilai insentif harus angka positif"
                    validated_insentif.append(ins_value)
                except (ValueError, TypeError):
                    return False, None, "Semua nilai insentif harus angka"

            # Remove duplicates and sort
            validated_insentif = sorted(list(set(validated_insentif)))

            if len(validated_insentif) == 0:
                return False, None, "Minimal harus ada 1 nilai insentif"

            return True, validated_insentif, None

        except Exception as e:
            return False, None, f"Error validating insentif: {str(e)}"

    @staticmethod
    def validate_lokasi(value):
        """
        Validate lokasi (location) - must be array

        Args:
            value: list - location values

        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        if not isinstance(value, list) or len(value) == 0:
            return False, "Lokasi harus array dan tidak boleh kosong"
        return True, None

    @staticmethod
    def clean_price(price_str):
        """
        Clean and parse price string to integer

        Args:
            price_str: Price string (can include Rp, dots, commas)

        Returns:
            int - cleaned price, 0 if parsing fails
        """
        if pd.isna(price_str):
            return 0

        try:
            # Remove common price formatting
            cleaned = str(price_str).replace('Rp.', '').replace('Rp', '').replace('.', '').replace(',', '').strip()
            return int(cleaned) if cleaned else 0
        except (ValueError, AttributeError):
            return 0

    @staticmethod
    def clean_incentive(incentive_str):
        """
        Clean and parse incentive string to integer

        Args:
            incentive_str: Incentive string

        Returns:
            int - cleaned incentive, 0 if parsing fails
        """
        if pd.isna(incentive_str):
            return 0

        try:
            cleaned = str(incentive_str).replace('.', '').replace(',', '').strip()
            return int(cleaned) if cleaned else 0
        except (ValueError, AttributeError):
            return 0


def validate_data_quality(df):
    """
    Calculate data quality metrics for entire dataframe

    Args:
        df: pandas DataFrame with customer data

    Returns:
        dict - quality metrics
    """
    validator = DataValidator()

    # Apply validators
    df['Missing_KTP'] = df['Foto KTP'].apply(validator.is_ktp_missing)
    df['Invalid_Phone'] = df['Tlp'].apply(validator.is_phone_invalid)
    df['Missing_Coordinate'] = df['Titik Koordinat Lokasi'].apply(validator.is_coordinate_missing)
    df['Incomplete_Data'] = df['Missing_KTP'] | df['Invalid_Phone']

    # Count issues
    return {
        'missing_ktp_count': int(df['Missing_KTP'].sum()),
        'invalid_phone_count': int(df['Invalid_Phone'].sum()),
        'incomplete_data_count': int(df['Incomplete_Data'].sum()),
        'missing_coordinate_count': int(df['Missing_Coordinate'].sum()),
        'df': df  # Return modified dataframe
    }
