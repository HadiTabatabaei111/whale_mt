"""
مدیریت دیتابیس SQLite برای ذخیره سیگنالها و اعتبارسنجی
"""
import sqlite3
from datetime import datetime, timedelta
import json
import threading

class SignalDatabase:
    def __init__(self, db_path='signals.db'):
        self.db_path = db_path
        self.lock = threading.Lock()
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()

            # جدول سیگنالها
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    target_price REAL,
                    stop_loss REAL,
                    strength INTEGER DEFAULT 50,
                    reason TEXT,
                    indicator_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'ACTIVE',
                    validated INTEGER DEFAULT 0,
                    validation_result TEXT,
                    final_price REAL,
                    profit_loss REAL,
                    closed_at TIMESTAMP
                )
            ''')

            # جدول اعتبارسنجی
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS signal_validations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id INTEGER,
                    check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    current_price REAL,
                    price_change_pct REAL,
                    status TEXT,
                    notes TEXT,
                    FOREIGN KEY (signal_id) REFERENCES signals(id)
                )
            ''')

            # جدول پامپ و دامپ
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pump_dump_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    price_at_alert REAL,
                    volume_change REAL,
                    price_change REAL,
                    strength INTEGER,
                    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    validated INTEGER DEFAULT 0,
                    validation_data TEXT,
                    peak_price REAL,
                    final_move REAL
                )
            ''')

            # جدول آمار
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS signal_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE UNIQUE,
                    total_signals INTEGER DEFAULT 0,
                    successful_signals INTEGER DEFAULT 0,
                    failed_signals INTEGER DEFAULT 0,
                    total_profit REAL DEFAULT 0,
                    win_rate REAL DEFAULT 0
                )
            ''')

            conn.commit()
            conn.close()

    def save_signal(self, signal_data):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO signals
                (symbol, signal_type, direction, entry_price, target_price,
                 stop_loss, strength, reason, indicator_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal_data.get('symbol'),
                signal_data.get('type', 'UNKNOWN'),
                signal_data.get('signal', 'NEUTRAL'),
                signal_data.get('price', 0),
                signal_data.get('target'),
                signal_data.get('stop_loss'),
                signal_data.get('strength', 50),
                signal_data.get('reason', ''),
                json.dumps(signal_data.get('indicators', {}))
            ))

            signal_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return signal_id

    def save_pump_dump(self, alert_data):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO pump_dump_alerts
                (symbol, alert_type, price_at_alert, volume_change,
                 price_change, strength)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                alert_data.get('symbol'),
                alert_data.get('alert_type'),
                alert_data.get('price', 0),
                alert_data.get('volume_change', 0),
                alert_data.get('price_change', 0),
                alert_data.get('strength', 50)
            ))

            alert_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return alert_id

    def get_active_signals(self, limit=100):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM signals
            WHERE status = 'ACTIVE'
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def update_signal_validation(self, signal_id, current_price, status, notes=''):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()

            # دریافت قیمت ورود
            cursor.execute('SELECT entry_price FROM signals WHERE id = ?', (signal_id,))
            row = cursor.fetchone()
            if row:
                entry_price = row['entry_price']
                price_change = ((current_price - entry_price) / entry_price) * 100 if entry_price else 0

                # ثبت اعتبارسنجی
                cursor.execute('''
                    INSERT INTO signal_validations
                    (signal_id, current_price, price_change_pct, status, notes)
                    VALUES (?, ?, ?, ?, ?)
                ''', (signal_id, current_price, price_change, status, notes))

                # بروزرسانی سیگنال اصلی
                if status in ['SUCCESS', 'FAILED', 'STOPPED']:
                    cursor.execute('''
                        UPDATE signals
                        SET status = 'CLOSED', validated = 1,
                            validation_result = ?, final_price = ?,
                            profit_loss = ?, closed_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (status, current_price, price_change, signal_id))

            conn.commit()
            conn.close()

    def get_signal_history(self, days=7, limit=500):
        conn = self.get_connection()
        cursor = conn.cursor()

        since = datetime.now() - timedelta(days=days)

        cursor.execute('''
            SELECT * FROM signals
            WHERE created_at >= ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (since, limit))

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_pump_dump_history(self, hours=24):
        conn = self.get_connection()
        cursor = conn.cursor()

        since = datetime.now() - timedelta(hours=hours)

        cursor.execute('''
            SELECT * FROM pump_dump_alerts
            WHERE detected_at >= ?
            ORDER BY detected_at DESC
        ''', (since,))

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_statistics(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        # آمار کلی
        cursor.execute('''
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN validation_result = 'SUCCESS' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN validation_result = 'FAILED' THEN 1 ELSE 0 END) as losses,
                AVG(CASE WHEN validated = 1 THEN profit_loss ELSE NULL END) as avg_profit
            FROM signals
            WHERE validated = 1
        ''')

        stats = dict(cursor.fetchone())

        # آمار امروز
        today = datetime.now().date()
        cursor.execute('''
            SELECT COUNT(*) as today_signals
            FROM signals
            WHERE DATE(created_at) = ?
        ''', (today,))

        stats['today_signals'] = cursor.fetchone()['today_signals']

        conn.close()
        return stats

# نمونه گلوبال
signal_db = SignalDatabase()
