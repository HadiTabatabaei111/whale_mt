"""
دریافت داده از صرافیهای بدون تحریم
KuCoin, Bybit, OKX, Gate.io, MEXC
"""
import ccxt
import pandas as pd
from datetime import datetime
import time
import asyncio

class ExchangeManager:
    """مدیریت صرافیها"""

    SUPPORTED_EXCHANGES = {
        'kucoin': {
            'name': 'KuCoin',
            'class': ccxt.kucoinfutures,
            'sanctioned': False
        },
        'bybit': {
            'name': 'Bybit',
            'class': ccxt.bybit,
            'sanctioned': False
        },
        'okx': {
            'name': 'OKX',
            'class': ccxt.okx,
            'sanctioned': False
        },
        'gate': {
            'name': 'Gate.io',
            'class': ccxt.gateio,
            'sanctioned': False
        },
        'mexc': {
            'name': 'MEXC',
            'class': ccxt.mexc,
            'sanctioned': False
        },
        'bitget': {
            'name': 'Bitget',
            'class': ccxt.bitget,
            'sanctioned': False
        }
    }

    def __init__(self, exchange_id='kucoin'):
        self.exchange_id = exchange_id
        self.exchange = None
        self.symbols = []
        self.init_exchange()

    def init_exchange(self):
        """راهاندازی صرافی"""
        if self.exchange_id not in self.SUPPORTED_EXCHANGES:
            self.exchange_id = 'kucoin'

        try:
            exchange_info = self.SUPPORTED_EXCHANGES[self.exchange_id]
            self.exchange = exchange_info['class']({
                'enableRateLimit': True,
                'options': {'defaultType': 'swap'}
            })
            print(f"✅ Connected to {exchange_info['name']}")
        except Exception as e:
            print(f"❌ Error connecting: {e}")
            # Fallback to KuCoin
            self.exchange = ccxt.kucoinfutures({'enableRateLimit': True})

    def change_exchange(self, new_exchange_id):
        """تغییر صرافی"""
        if new_exchange_id in self.SUPPORTED_EXCHANGES:
            self.exchange_id = new_exchange_id
            self.init_exchange()
            self.load_symbols()
            return True
        return False

    def load_symbols(self, limit=250):
        """بارگذاری لیست ارزها"""
        try:
            self.exchange.load_markets()

            futures_symbols = []
            for symbol, market in self.exchange.markets.items():
                if market.get('swap') or market.get('future'):
                    if market.get('active', True):
                        futures_symbols.append(symbol)

            # مرتبسازی و محدود کردن
            self.symbols = futures_symbols[:limit]
            print(f"📊 Loaded {len(self.symbols)} futures symbols from {self.exchange_id}")
            return self.symbols
        except Exception as e:
            print(f"❌ Error loading symbols: {e}")
            self.symbols = ['BTC/USDT:USDT', 'ETH/USDT:USDT']
            return self.symbols

    def fetch_ohlcv(self, symbol, timeframe='15m', limit=200):
        """دریافت کندلها"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['symbol'] = symbol

            return df
        except Exception as e:
            print(f"❌ Error fetching {symbol}: {e}")
            return pd.DataFrame()

    def get_ticker(self, symbol):
        """دریافت قیمت لحظهای"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return {
                'symbol': symbol,
                'price': ticker.get('last', 0),
                'change_24h': ticker.get('percentage', 0),
                'volume_24h': ticker.get('quoteVolume', 0),
                'high_24h': ticker.get('high', 0),
                'low_24h': ticker.get('low', 0)
            }
        except:
            return None

    def get_all_tickers(self):
        """دریافت همه قیمتها"""
        try:
            tickers = self.exchange.fetch_tickers()
            return tickers
        except:
            return {}

    def get_top_movers(self, limit=20):
        """برترین تغییرات قیمت"""
        try:
            tickers = self.get_all_tickers()

            movers = []
            for symbol, data in tickers.items():
                if data.get('percentage') is not None:
                    movers.append({
                        'symbol': symbol,
                        'price': data.get('last', 0),
                        'change': data.get('percentage', 0),
                        'volume': data.get('quoteVolume', 0)
                    })

            # مرتب سازی بر اساس تغییرات
            gainers = sorted(movers, key=lambda x: x['change'], reverse=True)[:limit]
            losers = sorted(movers, key=lambda x: x['change'])[:limit]

            return {'gainers': gainers, 'losers': losers}
        except Exception as e:
            print(f"Error getting movers: {e}")
            return {'gainers': [], 'losers': []}

# نمونه گلوبال
exchange_manager = ExchangeManager('kucoin')
