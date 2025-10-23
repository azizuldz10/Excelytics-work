"""
History Manager - Mengelola snapshot dan history tracking untuk dashboard
Menyimpan semua metrics setiap kali data di-upload atau di-refresh
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
import pandas as pd

# Database path
DB_PATH = 'history.db'

class HistoryManager:
    """Manage historical data snapshots"""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Tabel untuk menyimpan snapshots
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                upload_date DATE NOT NULL,
                total_customers INTEGER,
                active_customers INTEGER,
                inactive_customers INTEGER,
                total_revenue INTEGER,
                avg_revenue_per_customer REAL,
                total_packages INTEGER,
                quality_issues_count INTEGER,
                missing_ktp_count INTEGER,
                invalid_phone_count INTEGER,
                missing_coords_count INTEGER,
                top_package TEXT,
                top_package_count INTEGER,
                top_location TEXT,
                top_location_revenue INTEGER,
                active_sales_count INTEGER,
                total_psb_count INTEGER,
                raw_data TEXT,
                UNIQUE(upload_date)
            )
        ''')

        # Tabel untuk menyimpan detail metrics per sales
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sales_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                sales_name TEXT NOT NULL,
                customer_count INTEGER,
                revenue INTEGER,
                avg_revenue REAL,
                FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
            )
        ''')

        # Tabel untuk menyimpan detail metrics per package
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS package_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                package_name TEXT NOT NULL,
                customer_count INTEGER,
                revenue INTEGER,
                avg_revenue REAL,
                FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
            )
        ''')

        conn.commit()
        conn.close()

    def save_snapshot(self, overview_stats, upload_date=None):
        """
        Save a snapshot of current overview stats

        Args:
            overview_stats: Dict containing overview data from /api/overview
            upload_date: Optional date to use (default: today)

        Returns:
            snapshot_id if successful, None otherwise
        """
        try:
            if upload_date is None:
                upload_date = datetime.now().strftime('%Y-%m-%d')
            else:
                # Ensure upload_date is string in YYYY-MM-DD format
                if isinstance(upload_date, datetime):
                    upload_date = upload_date.strftime('%Y-%m-%d')

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Extract main metrics
            stats = overview_stats.get('stats', {})
            quality = overview_stats.get('quality_checks', {})

            total_customers = stats.get('total_customers', 0)
            active_customers = stats.get('active_customers', 0)
            inactive_customers = stats.get('inactive_customers', 0)
            total_revenue = stats.get('total_revenue', 0)
            avg_revenue = stats.get('avg_revenue_per_customer', 0)

            # Quality issues
            quality_issues = quality.get('total_issues', 0)
            missing_ktp = quality.get('missing_ktp_count', 0)
            invalid_phone = quality.get('invalid_phone_count', 0)
            missing_coords = quality.get('missing_coords_count', 0)

            # Top items
            top_package = stats.get('top_package', 'N/A')
            top_package_count = stats.get('top_package_count', 0)
            top_location = stats.get('top_location', 'N/A')
            top_location_revenue = stats.get('top_location_revenue', 0)

            # Additional metrics
            active_sales = stats.get('active_sales', 0)
            total_psb = stats.get('total_psb_count', 0)

            # Insert main snapshot
            cursor.execute('''
                INSERT OR REPLACE INTO snapshots (
                    timestamp, upload_date,
                    total_customers, active_customers, inactive_customers,
                    total_revenue, avg_revenue_per_customer, total_packages,
                    quality_issues_count, missing_ktp_count, invalid_phone_count, missing_coords_count,
                    top_package, top_package_count, top_location, top_location_revenue,
                    active_sales_count, total_psb_count, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                upload_date,
                total_customers,
                active_customers,
                inactive_customers,
                total_revenue,
                avg_revenue,
                stats.get('total_packages', 0),
                quality_issues,
                missing_ktp,
                invalid_phone,
                missing_coords,
                top_package,
                top_package_count,
                top_location,
                top_location_revenue,
                active_sales,
                total_psb,
                json.dumps(overview_stats)
            ))

            snapshot_id = cursor.lastrowid

            conn.commit()
            conn.close()

            print(f"✓ Snapshot saved (ID: {snapshot_id}, Date: {upload_date})")
            return snapshot_id

        except Exception as e:
            print(f"✗ Error saving snapshot: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return None

    def save_sales_snapshot(self, snapshot_id, sales_data):
        """
        Save sales metrics for a snapshot

        Args:
            snapshot_id: ID of the snapshot
            sales_data: List of dicts with sales metrics
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for sales in sales_data:
                cursor.execute('''
                    INSERT INTO sales_snapshots (
                        snapshot_id, sales_name, customer_count, revenue, avg_revenue
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (
                    snapshot_id,
                    sales.get('name'),
                    sales.get('customer_count', 0),
                    sales.get('revenue', 0),
                    sales.get('avg_revenue', 0)
                ))

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error saving sales snapshot: {str(e)}")

    def save_package_snapshot(self, snapshot_id, package_data):
        """Save package metrics for a snapshot"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for package in package_data:
                cursor.execute('''
                    INSERT INTO package_snapshots (
                        snapshot_id, package_name, customer_count, revenue, avg_revenue
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (
                    snapshot_id,
                    package.get('name'),
                    package.get('customer_count', 0),
                    package.get('revenue', 0),
                    package.get('avg_revenue', 0)
                ))

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error saving package snapshot: {str(e)}")

    def get_history(self, limit=50):
        """Get all snapshots sorted by date (newest first)"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM snapshots
                ORDER BY upload_date DESC
                LIMIT ?
            ''', (limit,))

            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting history: {str(e)}")
            return []

    def get_snapshot_by_date(self, date_str):
        """Get specific snapshot by date (YYYY-MM-DD format)"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM snapshots WHERE upload_date = ?', (date_str,))
            row = cursor.fetchone()
            conn.close()

            return dict(row) if row else None
        except Exception as e:
            print(f"Error getting snapshot: {str(e)}")
            return None

    def get_comparison(self, date1, date2):
        """
        Compare two snapshots

        Args:
            date1: First date (YYYY-MM-DD)
            date2: Second date (YYYY-MM-DD)

        Returns:
            Dict with comparison data and changes
        """
        snap1 = self.get_snapshot_by_date(date1)
        snap2 = self.get_snapshot_by_date(date2)

        if not snap1 or not snap2:
            return {'error': 'One or both snapshots not found'}

        # Calculate differences
        def calc_change(old, new):
            """Calculate percentage change"""
            if old == 0:
                return 0 if new == 0 else 100
            return round(((new - old) / old) * 100, 2)

        comparison = {
            'date1': date1,
            'date2': date2,
            'snapshot1': snap1,
            'snapshot2': snap2,
            'changes': {
                'customers': {
                    'old': snap1['total_customers'],
                    'new': snap2['total_customers'],
                    'change': snap2['total_customers'] - snap1['total_customers'],
                    'change_pct': calc_change(snap1['total_customers'], snap2['total_customers'])
                },
                'active_customers': {
                    'old': snap1['active_customers'],
                    'new': snap2['active_customers'],
                    'change': snap2['active_customers'] - snap1['active_customers'],
                    'change_pct': calc_change(snap1['active_customers'], snap2['active_customers'])
                },
                'revenue': {
                    'old': snap1['total_revenue'],
                    'new': snap2['total_revenue'],
                    'change': snap2['total_revenue'] - snap1['total_revenue'],
                    'change_pct': calc_change(snap1['total_revenue'], snap2['total_revenue'])
                },
                'quality_issues': {
                    'old': snap1['quality_issues_count'],
                    'new': snap2['quality_issues_count'],
                    'change': snap2['quality_issues_count'] - snap1['quality_issues_count'],
                    'change_pct': calc_change(snap1['quality_issues_count'], snap2['quality_issues_count'])
                }
            }
        }

        return comparison

    def get_trend(self, days=30):
        """
        Get trend data for last N days

        Returns:
            List of snapshots with calculated trends
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM snapshots
                ORDER BY upload_date ASC
                LIMIT ?
            ''', (days,))

            rows = cursor.fetchall()
            conn.close()

            data = [dict(row) for row in rows]

            # Calculate trends
            for i, item in enumerate(data):
                if i > 0:
                    prev = data[i-1]
                    item['customer_trend'] = item['total_customers'] - prev['total_customers']
                    item['revenue_trend'] = item['total_revenue'] - prev['total_revenue']
                else:
                    item['customer_trend'] = 0
                    item['revenue_trend'] = 0

            return data
        except Exception as e:
            print(f"Error getting trend: {str(e)}")
            return []

    def delete_old_snapshots(self, keep_count=100):
        """Clean up old snapshots, keep only the most recent N"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get total count
            cursor.execute('SELECT COUNT(*) FROM snapshots')
            total = cursor.fetchone()[0]

            if total > keep_count:
                # Delete old ones
                cursor.execute('''
                    DELETE FROM snapshots WHERE id IN (
                        SELECT id FROM snapshots
                        ORDER BY upload_date DESC
                        LIMIT -1 OFFSET ?
                    )
                ''', (keep_count,))

                deleted = cursor.rowcount
                conn.commit()
                print(f"✓ Deleted {deleted} old snapshots (kept {keep_count})")

            conn.close()
        except Exception as e:
            print(f"Error cleaning up snapshots: {str(e)}")


# Singleton instance
_history_manager = None

def get_history_manager():
    """Get or create history manager instance"""
    global _history_manager
    if _history_manager is None:
        _history_manager = HistoryManager()
    return _history_manager
