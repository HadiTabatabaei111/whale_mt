"""
🔥 سیستم سیگنالدهی پیشرفته
Smart Money, Order Blocks, Liquidity Hunt, Divergence, Whale Detection
"""
import pandas as pd
import numpy as np
from datetime import datetime
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange
from indicators import TechnicalIndicators

class AdvancedSignalEngine:
    """موتور سیگنالدهی پیشرفته"""

    @staticmethod
    def detect_smart_money(df, volume_threshold=2.0):
        """تشخیص ورود و خروج پول هوشمند"""
        if len(df) < 30:
            return []

        df = df.copy()
        df['volume_sma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        df['price_change'] = df['close'].pct_change() * 100

        signals = []

        for i in range(20, len(df)):
            vol_ratio = df['volume_ratio'].iloc[i]
            price_change = abs(df['price_change'].iloc[i])

            if pd.isna(vol_ratio):
                continue

            if vol_ratio > volume_threshold and price_change < 0.5:
                signals.append({
                    'index': i,
                    'type': 'SMART_MONEY_ACCUMULATION',
                    'signal': 'BUY',
                    'strength': min(int(vol_ratio * 30), 95),
                    'reason': f'💰 Smart Money Accumulation (Vol: {vol_ratio:.1f}x)',
                    'price': df['close'].iloc[i],
                    'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else datetime.utcnow()
                })

            elif vol_ratio > volume_threshold and price_change > 2:
                if df['close'].iloc[i] > df['close'].iloc[i-1]:
                    signals.append({
                        'index': i,
                        'type': 'SMART_MONEY_DISTRIBUTION',
                        'signal': 'SELL',
                        'strength': min(int(vol_ratio * 25), 90),
                        'reason': f'💰 Smart Money Distribution (Vol: {vol_ratio:.1f}x)',
                        'price': df['close'].iloc[i],
                        'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else datetime.utcnow()
                    })

        return signals[-5:] if signals else []

    @staticmethod
    def find_order_blocks(df):
        """یافتن Order Blocks"""
        if len(df) < 10:
            return []

        df = df.copy()
        order_blocks = []

        for i in range(3, len(df) - 1):
            try:
                if (df['close'].iloc[i-1] < df['open'].iloc[i-1] and
                    df['close'].iloc[i] > df['open'].iloc[i] and
                    df['close'].iloc[i] > df['high'].iloc[i-1]):

                    move = ((df['close'].iloc[i] - df['low'].iloc[i-1]) / df['low'].iloc[i-1]) * 100

                    if move > 0.5:
                        order_blocks.append({
                            'index': i,
                            'type': 'BULLISH_ORDER_BLOCK',
                            'signal': 'BUY',
                            'strength': min(int(move * 20), 90),
                            'price': df['close'].iloc[i],
                            'reason': f'📦 Bullish Order Block ({move:.1f}% move)',
                            'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else datetime.utcnow()
                        })

                if (df['close'].iloc[i-1] > df['open'].iloc[i-1] and
                    df['close'].iloc[i] < df['open'].iloc[i] and
                    df['close'].iloc[i] < df['low'].iloc[i-1]):

                    move = ((df['high'].iloc[i-1] - df['close'].iloc[i]) / df['high'].iloc[i-1]) * 100

                    if move > 0.5:
                        order_blocks.append({
                            'index': i,
                            'type': 'BEARISH_ORDER_BLOCK',
                            'signal': 'SELL',
                            'strength': min(int(move * 20), 90),
                            'price': df['close'].iloc[i],
                            'reason': f'📦 Bearish Order Block ({move:.1f}% move)',
                            'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else datetime.utcnow()
                        })
            except:
                continue

        return order_blocks[-5:] if order_blocks else []

    @staticmethod
    def detect_liquidity_hunt(df, lookback=20):
        """تشخیص شکار نقدینگی"""
        if len(df) < lookback + 5:
            return []

        df = df.copy()
        signals = []

        for i in range(lookback, len(df)):
            try:
                window = df.iloc[i-lookback:i]
                current = df.iloc[i]

                prev_high = window['high'].max()
                prev_low = window['low'].min()

                if (current['low'] < prev_low and
                    current['close'] > prev_low and
                    current['close'] > current['open']):

                    hunt = ((prev_low - current['low']) / prev_low) * 100

                    signals.append({
                        'index': i,
                        'type': 'LIQUIDITY_GRAB_LOW',
                        'signal': 'BUY',
                        'strength': min(75 + int(hunt * 10), 95),
                        'price': current['close'],
                        'stop_loss': current['low'] * 0.995,
                        'reason': f'🎯 Liquidity Hunt Below Support ({hunt:.2f}%)',
                        'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else datetime.utcnow()
                    })

                if (current['high'] > prev_high and
                    current['close'] < prev_high and
                    current['close'] < current['open']):

                    hunt = ((current['high'] - prev_high) / prev_high) * 100

                    signals.append({
                        'index': i,
                        'type': 'LIQUIDITY_GRAB_HIGH',
                        'signal': 'SELL',
                        'strength': min(75 + int(hunt * 10), 95),
                        'price': current['close'],
                        'stop_loss': current['high'] * 1.005,
                        'reason': f'🎯 Liquidity Hunt Above Resistance ({hunt:.2f}%)',
                        'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else datetime.utcnow()
                    })
            except:
                continue

        return signals[-5:] if signals else []

    @staticmethod
    def find_divergences(df):
        """یافتن واگراییها"""
        if len(df) < 30:
            return []

        df = df.copy()
        df['rsi'] = RSIIndicator(df['close'], window=14).rsi()

        divergences = []
        lookback = 5

        for i in range(lookback * 2, len(df)):
            try:
                if (df['close'].iloc[i] < df['close'].iloc[i-lookback] and
                    df['rsi'].iloc[i] > df['rsi'].iloc[i-lookback] and
                    df['rsi'].iloc[i] < 40):

                    divergences.append({
                        'index': i,
                        'type': 'BULLISH_DIVERGENCE',
                        'signal': 'BUY',
                        'strength': 85,
                        'price': df['close'].iloc[i],
                        'reason': f'📈 RSI Bullish Divergence (RSI: {df["rsi"].iloc[i]:.1f})',
                        'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else datetime.utcnow()
                    })

                if (df['close'].iloc[i] > df['close'].iloc[i-lookback] and
                    df['rsi'].iloc[i] < df['rsi'].iloc[i-lookback] and
                    df['rsi'].iloc[i] > 60):

                    divergences.append({
                        'index': i,
                        'type': 'BEARISH_DIVERGENCE',
                        'signal': 'SELL',
                        'strength': 85,
                        'price': df['close'].iloc[i],
                        'reason': f'📉 RSI Bearish Divergence (RSI: {df["rsi"].iloc[i]:.1f})',
                        'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else datetime.utcnow()
                    })
            except:
                continue

        return divergences[-5:] if divergences else []

        @staticmethod
        def detect_whale_activity(df, std_multiplier=2.5):
            """تشخیص فعالیت نهنگها"""
            if len(df) < 60:
                return []

            df = df.copy()
            df['volume_mean'] = df['volume'].rolling(50).mean()
            df['volume_std'] = df['volume'].rolling(50).std()

            signals = []

            for i in range(50, len(df)):
                try:
                    if df['volume_std'].iloc[i] == 0 or pd.isna(df['volume_std'].iloc[i]):
                        continue

                    zscore = (df['volume'].iloc[i] - df['volume_mean'].iloc[i]) / df['volume_std'].iloc[i]

                    if zscore > std_multiplier:
                        price_change = ((df['close'].iloc[i] - df['open'].iloc[i]) / df['open'].iloc[i]) * 100

                        if price_change > 0.3:
                            signals.append({
                                'index': i,
                                'type': 'WHALE_BUYING',
                                'signal': 'BUY',
                                'strength': min(65 + int(zscore * 8), 95),
                                'price': df['close'].iloc[i],
                                'reason': f'🐋 Whale Buying (Vol Z: {zscore:.1f})',
                                'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else datetime.utcnow()
                            })
                        elif price_change < -0.3:
                            signals.append({
                                'index': i,
                                'type': 'WHALE_SELLING',
                                'signal': 'SELL',
                                'strength': min(65 + int(zscore * 8), 95),
                                'price': df['close'].iloc[i],
                                'reason': f'🐋 Whale Selling (Vol Z: {zscore:.1f})',
                                'timestamp': df['timestamp'].iloc[i] if 'timestamp' in df.columns else datetime.utcnow()
                            })
                except:
                    continue

            return signals[-5:] if signals else []


    class PumpDumpDetector:
        """تشخیص پامپ و دامپ"""

        @staticmethod
        def detect_pump(df, symbol, threshold=5, window=15):
            """تشخیص پامپ"""
            if len(df) < window + 50:
                return []

            alerts = []

            try:
                recent = df.tail(window)
                start_price = recent['close'].iloc[0]
                end_price = recent['close'].iloc[-1]
                price_change = ((end_price - start_price) / start_price) * 100

                avg_volume = df['volume'].tail(100).mean()
                recent_volume = recent['volume'].mean()
                volume_change = ((recent_volume - avg_volume) / avg_volume) * 100 if avg_volume > 0 else 0

                if price_change >= threshold and volume_change > 30:
                    alerts.append({
                        'symbol': symbol,
                        'alert_type': 'PUMP',
                        'signal': 'BUY',
                        'price': end_price,
                        'price_change': round(price_change, 2),
                        'volume_change': round(volume_change, 2),
                        'strength': min(70 + int(price_change * 2), 95),
                        'reason': f'🚀 PUMP! +{price_change:.1f}% | Vol +{volume_change:.0f}%',
                        'timestamp': datetime.utcnow()
                    })
            except:
                pass

            return alerts

    @staticmethod
    def detect_dump(df, symbol, threshold=5, window=15):
        """تشخیص دامپ"""
        if len(df) < window + 50:
            return []

        alerts = []

        try:
            recent = df.tail(window)
            start_price = recent['close'].iloc[0]
            end_price = recent['close'].iloc[-1]
            price_change = ((end_price - start_price) / start_price) * 100

            avg_volume = df['volume'].tail(100).mean()
            recent_volume = recent['volume'].mean()
            volume_change = ((recent_volume - avg_volume) / avg_volume) * 100 if avg_volume > 0 else 0

            if price_change <= -threshold and volume_change > 30:
                alerts.append({
                    'symbol': symbol,
                    'alert_type': 'DUMP',
                    'signal': 'SELL',
                    'price': end_price,
                    'price_change': round(price_change, 2),
                    'volume_change': round(volume_change, 2),
                    'strength': min(70 + int(abs(price_change) * 2), 95),
                    'reason': f'📉 DUMP! {price_change:.1f}% | Vol +{volume_change:.0f}%',
                    'timestamp': datetime.utcnow()
                })
        except:
            pass

        return alerts


class UltimateSignalGenerator:
    """ترکیب همه روشها"""

    def __init__(self):
        self.engine = AdvancedSignalEngine()
        self.pump_dump = PumpDumpDetector()
        self.indicators = TechnicalIndicators()

    def analyze(self, df, symbol):
        """تحلیل کامل"""
        all_signals = []

        try:
            # سیگنالهای پیشرفته
            smart_money = self.engine.detect_smart_money(df)
            order_blocks = self.engine.find_order_blocks(df)
            liquidity = self.engine.detect_liquidity_hunt(df)
            divergence = self.engine.find_divergences(df)
            whale = self.engine.detect_whale_activity(df)

            # UT Bot
            _, ut_alerts = self.indicators.ut_bot_alert(df)

            # MA/EMA Cross
            ma_crosses = self.indicators.detect_ma_ema_cross(df)

            # پامپ و دامپ
            pump = self.pump_dump.detect_pump(df, symbol)
            dump = self.pump_dump.detect_dump(df, symbol)

            for sig_list in [smart_money, order_blocks, liquidity, divergence, whale, ut_alerts, ma_crosses]:
                for sig in sig_list:
                    sig['symbol'] = symbol
                    all_signals.append(sig)

            all_signals.extend(pump)
            all_signals.extend(dump)

        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")

        return all_signals

    def get_best_signals(self, df, symbol, top_n=5):
        """بهترین سیگنالها"""
        signals = self.analyze(df, symbol)
        signals.sort(key=lambda x: x.get('strength', 0), reverse=True)
        return signals[:top_n]

signal_generator = UltimateSignalGenerator()
