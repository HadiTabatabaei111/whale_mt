"""
🚀 سرور اصلی Flask
"""
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from datetime import datetime, timedelta
import threading
import time
import json

from database import signal_db
from data_fetcher import exchange_manager
from signals import signal_generator
from indicators import TechnicalIndicators
from signal_validator import validator

app = Flask(__name__)
app.config['SECRET_KEY'] = 'crypto_futures_secret_2024'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ذخیره داده ها
cache = {
    'signals': [],
    'pump_dump': [],
    'movers': {'gainers': [], 'losers': []},
    'last_update': None
}

def scan_all_symbols():
    """اسکن همه ارزها"""
    global cache

    while True:
        try:
            all_signals = []
            pump_dump_alerts = []

            symbols = exchange_manager.symbols[:100]  # 100 تا اول

            for i, symbol in enumerate(symbols):
                try:
                    df = exchange_manager.fetch_ohlcv(symbol, '15m', 200)
                    if df.empty:
                        continue

                    # تولید سیگنال
                    signals = signal_generator.get_best_signals(df, symbol, 3)

                    for sig in signals:
                        sig['detected_at'] = datetime.utcnow().isoformat()
                        all_signals.append(sig)

                        # ذخیره در دیتابیس
                        signal_db.save_signal(sig)

                        # پامپ و دامپ
                        if 'PUMP' in sig.get('type', '') or 'DUMP' in sig.get('type', ''):
                            pump_dump_alerts.append(sig)
                            signal_db.save_pump_dump(sig)

                    # ارسال به کلاینت
                    if signals:
                        socketio.emit('new_signals', signals)

                    time.sleep(0.3)

                except Exception as e:
                    continue

            # بروزرسانی کش
            cache['signals'] = all_signals[-100:]
            cache['pump_dump'] = pump_dump_alerts[-50:]
            cache['movers'] = exchange_manager.get_top_movers(20)
            cache['last_update'] = datetime.utcnow().isoformat()

            # ارسال بروزرسانی
            socketio.emit('cache_update', cache)

            print(f"✅ Scan complete: {len(all_signals)} signals found")

            time.sleep(60)  # هر 1 دقیقه

        except Exception as e:
            print(f"Scan error: {e}")
            time.sleep(30)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analytics')
def analytics():
    return render_template('analytics.html')

@app.route('/api/signals')
def get_signals():
    return jsonify(cache['signals'][-50:])

@app.route('/api/signals/history')
def get_signal_history():
    days = request.args.get('days', 7, type=int)
    signals = signal_db.get_signal_history(days)
    return jsonify(signals)

@app.route('/api/pump-dump')
def get_pump_dump():
    return jsonify(cache['pump_dump'])

@app.route('/api/pump-dump/history')
def get_pump_dump_history():
    hours = request.args.get('hours', 24, type=int)
    alerts = signal_db.get_pump_dump_history(hours)
    return jsonify(alerts)

@app.route('/api/movers')
def get_movers():
    return jsonify(cache['movers'])

@app.route('/api/stats')
def get_stats():
    stats = signal_db.get_statistics()
    return jsonify(stats)

@app.route('/api/exchange/change', methods=['POST'])
def change_exchange():
    data = request.json
    new_exchange = data.get('exchange', 'kucoin')

    success = exchange_manager.change_exchange(new_exchange)
    if success:
        exchange_manager.load_symbols()
        return jsonify({'success': True, 'exchange': new_exchange})
    return jsonify({'success': False})

@app.route('/api/exchanges')
def get_exchanges():
    return jsonify({
        'current': exchange_manager.exchange_id,
        'available': list(exchange_manager.SUPPORTED_EXCHANGES.keys())
    })

@app.route('/api/symbols')
def get_symbols():
    return jsonify({
        'count': len(exchange_manager.symbols),
        'symbols': exchange_manager.symbols[:50]
    })

@app.route('/api/analyze/<symbol>')
def analyze_symbol(symbol):
    try:
        symbol = symbol.replace('_', '/')
        df = exchange_manager.fetch_ohlcv(symbol, '15m', 200)

        if df.empty:
            return jsonify({'error': 'No data'})

        signals = signal_generator.analyze(df, symbol)
        indicators = TechnicalIndicators.get_indicator_summary(df)

        return jsonify({
            'symbol': symbol,
            'signals': signals,
            'indicators': indicators,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@socketio.on('connect')
def handle_connect():
    emit('connected', {'status': 'ok', 'exchange': exchange_manager.exchange_id})

@socketio.on('subscribe')
def handle_subscribe(data):
    symbol = data.get('symbol')
    if symbol:
        emit('subscribed', {'symbol': symbol})

if __name__ == '__main__':
    print("🚀 Starting Crypto Futures Signal System...")

    # بارگذاری ارزها
    exchange_manager.load_symbols(250)

    # شروع اعتبارسنجی
    validator.start()

    # شروع اسکنر
    scanner_thread = threading.Thread(target=scan_all_symbols, daemon=True)
    scanner_thread.start()

    print("📊 Server running on http://localhost:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
