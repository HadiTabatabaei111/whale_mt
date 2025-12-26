"""
اعتبارسنجی سیگنالها هر 3 دقیقه
"""
from datetime import datetime, timedelta
from database import signal_db
from data_fetcher import exchange_manager
import threading
import time

class SignalValidator:
    """اعتبارسنجی سیگنالها"""

    def __init__(self, check_interval=180):  # 3 دقیقه
        self.check_interval = check_interval
        self.running = False
        self.thread = None

    def validate_signal(self, signal):
        """اعتبارسنجی یک سیگنال"""
        try:
            symbol = signal['symbol']
            entry_price = signal['entry_price']
            direction = signal['direction']
            target = signal.get('target_price')
            stop_loss = signal.get('stop_loss')

            # دریافت قیمت فعلی
            ticker = exchange_manager.get_ticker(symbol)
            if not ticker:
                return None

            current_price = ticker['price']

            # محاسبه تغییر قیمت
            if direction == 'BUY':
                change_pct = ((current_price - entry_price) / entry_price) * 100
            else:
                change_pct = ((entry_price - current_price) / entry_price) * 100

            # تعیین وضعیت
            status = 'ACTIVE'
            notes = f"Price: {current_price:.6f} | Change: {change_pct:+.2f}%"

            if target and direction == 'BUY' and current_price >= target:
                status = 'SUCCESS'
                notes = f"🎯 Target reached! +{change_pct:.2f}%"
            elif target and direction == 'SELL' and current_price <= target:
                status = 'SUCCESS'
                notes = f"🎯 Target reached! +{change_pct:.2f}%"
            elif stop_loss and direction == 'BUY' and current_price <= stop_loss:
                status = 'STOPPED'
                notes = f"🛑 Stop loss hit! {change_pct:.2f}%"
            elif stop_loss and direction == 'SELL' and current_price >= stop_loss:
                status = 'STOPPED'
                notes = f"🛑 Stop loss hit! {change_pct:.2f}%"
            elif change_pct >= 5:
                status = 'SUCCESS'
                notes = f"✅ +5% profit! {change_pct:.2f}%"
            elif change_pct <= -5:
                status = 'FAILED'
                notes = f"❌ -5% loss! {change_pct:.2f}%"

            # ذخیره نتیجه
            signal_db.update_signal_validation(
                signal['id'],
                current_price,
                status,
                notes
            )

            return {
                'signal_id': signal['id'],
                'symbol': symbol,
                'current_price': current_price,
                'change_pct': change_pct,
                'status': status,
                'notes': notes
            }

        except Exception as e:
            print(f"Error validating signal: {e}")
            return None

    def validate_all_active(self):
        """اعتبارسنجی همه سیگنالهای فعال"""
        active_signals = signal_db.get_active_signals()
        results = []

        for signal in active_signals:
            result = self.validate_signal(signal)
            if result:
                results.append(result)
            time.sleep(0.2)  # Rate limiting

        return results

    def run_validation_loop(self):
        """حلقه اعتبارسنجی"""
        while self.running:
            try:
                print(f"\n🔍 Validating signals at {datetime.now()}")
                results = self.validate_all_active()

                success = len([r for r in results if r['status'] == 'SUCCESS'])
                failed = len([r for r in results if r['status'] in ['FAILED', 'STOPPED']])

                print(f"✅ Validated {len(results)} signals | Success: {success} | Failed: {failed}")

            except Exception as e:
                print(f"Validation error: {e}")

            time.sleep(self.check_interval)

    def start(self):
        """شروع اعتبارسنجی"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run_validation_loop, daemon=True)
            self.thread.start()
            print("🔄 Signal validator started (every 3 minutes)")

    def stop(self):
        """توقف"""
        self.running = False

validator = SignalValidator()
