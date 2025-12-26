"""
محاسبه اندیکاتورهای تکنیکال
MA, EMA, RSI, MACD, Bollinger Bands, ATR, UT Bot Alert
"""
import pandas as pd
import numpy as np
from ta.trend import EMAIndicator, SMAIndicator, MACD
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange

class TechnicalIndicators:
    """محاسبه تمام اندیکاتورها"""

    @staticmethod
    def calculate_all(df):
        """محاسبه همه اندیکاتورها"""
        if len(df) < 50:
            return df

        df = df.copy()

        # Moving Averages
        df['ma_7'] = SMAIndicator(df['close'], window=7).sma_indicator()
        df['ma_20'] = SMAIndicator(df['close'], window=20).sma_indicator()
        df['ma_50'] = SMAIndicator(df['close'], window=50).sma_indicator()
        df['ma_100'] = SMAIndicator(df['close'], window=100).sma_indicator()
        df['ma_200'] = SMAIndicator(df['close'], window=200).sma_indicator()

        # EMA
        df['ema_9'] = EMAIndicator(df['close'], window=9).ema_indicator()
        df['ema_12'] = EMAIndicator(df['close'], window=12).ema_indicator()
        df['ema_21'] = EMAIndicator(df['close'], window=21).ema_indicator()
        df['ema_26'] = EMAIndicator(df['close'], window=26).ema_indicator()
        df['ema_50'] = EMAIndicator(df['close'], window=50).ema_indicator()

        # RSI
        df['rsi'] = RSIIndicator(df['close'], window=14).rsi()
        df['rsi_7'] = RSIIndicator(df['close'], window=7).rsi()

        # MACD
        macd = MACD(df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_histogram'] = macd.macd_diff()

        # Bollinger Bands
        bb = BollingerBands(df['close'], window=20, window_dev=2)
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_middle'] = bb.bollinger_mavg()
        df['bb_lower'] = bb.bollinger_lband()
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']

        # ATR
        atr = AverageTrueRange(df['high'], df['low'], df['close'], window=14)
        df['atr'] = atr.average_true_range()
        df['atr_percent'] = (df['atr'] / df['close']) * 100

        # Stochastic
        stoch = StochasticOscillator(df['high'], df['low'], df['close'])
        df['stoch_k'] = stoch.stoch()
        df['stoch_d'] = stoch.stoch_signal()

        return df

    @staticmethod
    def ut_bot_alert(df, sensitivity=1, atr_period=10):
        """
        UT Bot Alert - مشابه تریدینگ ویو
        """
        if len(df) < atr_period + 10:
            return df, []

        df = df.copy()

        # محاسبه ATR
        atr = AverageTrueRange(df['high'], df['low'], df['close'], window=atr_period)
        df['ut_atr'] = atr.average_true_range()
        df['ut_nLoss'] = sensitivity * df['ut_atr']

        # محاسبه Trailing Stop
        df['ut_xATRTrailingStop'] = 0.0

        for i in range(1, len(df)):
            nLoss = df['ut_nLoss'].iloc[i]
            prev_stop = df['ut_xATRTrailingStop'].iloc[i-1]
            close = df['close'].iloc[i]
            prev_close = df['close'].iloc[i-1]

            if close > prev_stop and prev_close > prev_stop:
                df.loc[df.index[i], 'ut_xATRTrailingStop'] = max(prev_stop, close - nLoss)
            elif close < prev_stop and prev_close < prev_stop:
                df.loc[df.index[i], 'ut_xATRTrailingStop'] = min(prev_stop, close + nLoss)
            elif close > prev_stop:
                df.loc[df.index[i], 'ut_xATRTrailingStop'] = close - nLoss
            else:
                df.loc[df.index[i], 'ut_xATRTrailingStop'] = close + nLoss

        # تشخیص سیگنال
        df['ut_pos'] = 0
        df.loc[df['close'] > df['ut_xATRTrailingStop'], 'ut_pos'] = 1
        df.loc[df['close'] < df['ut_xATRTrailingStop'], 'ut_pos'] = -1

        # سیگنالهای ورود
        df['ut_signal'] = df['ut_pos'].diff()

        alerts = []
        for i in range(1, len(df)):
            if df['ut_signal'].iloc[i] == 2:  # Buy
                alerts.append({
                    'index': i,
                    'type': 'UT_BOT_BUY',
                    'signal': 'BUY',
                    'price': df['close'].iloc[i],
                    'stop': df['ut_xATRTrailingStop'].iloc[i],
                    'strength': 80,
                    'reason': f'📈 UT Bot Buy Signal (Stop: {df["ut_xATRTrailingStop"].iloc[i]:.4f})'
                })
            elif df['ut_signal'].iloc[i] == -2:  # Sell
                alerts.append({
                    'index': i,
                    'type': 'UT_BOT_SELL',
                    'signal': 'SELL',
                    'price': df['close'].iloc[i],
                    'stop': df['ut_xATRTrailingStop'].iloc[i],
                    'strength': 80,
                    'reason': f'📉 UT Bot Sell Signal (Stop: {df["ut_xATRTrailingStop"].iloc[i]:.4f})'
                })

        return df, alerts[-5:] if alerts else []

    @staticmethod
    def detect_ma_ema_cross(df):
        """تشخیص تقاطع MA و EMA"""
        if len(df) < 55:
            return []

        df = df.copy()

        if 'ema_9' not in df.columns:
            df = TechnicalIndicators.calculate_all(df)

        crosses = []

        # EMA 9/21 Cross
        for i in range(1, len(df)):
            # Golden Cross EMA
            if (df['ema_9'].iloc[i] > df['ema_21'].iloc[i] and
                df['ema_9'].iloc[i-1] <= df['ema_21'].iloc[i-1]):
                crosses.append({
                    'index': i,
                    'type': 'EMA_GOLDEN_CROSS',
                    'signal': 'BUY',
                    'strength': 75,
                    'price': df['close'].iloc[i],
                    'reason': '🔀 EMA 9/21 Golden Cross (BUY)'
                })

            # Death Cross EMA
            elif (df['ema_9'].iloc[i] < df['ema_21'].iloc[i] and
                  df['ema_9'].iloc[i-1] >= df['ema_21'].iloc[i-1]):
                crosses.append({
                    'index': i,
                    'type': 'EMA_DEATH_CROSS',
                    'signal': 'SELL',
                    'strength': 75,
                    'price': df['close'].iloc[i],
                    'reason': '🔀 EMA 9/21 Death Cross (SELL)'
                })

            # MA 20/50 Cross
            if pd.notna(df['ma_50'].iloc[i]) and pd.notna(df['ma_50'].iloc[i-1]):
                if (df['ma_20'].iloc[i] > df['ma_50'].iloc[i] and
                    df['ma_20'].iloc[i-1] <= df['ma_50'].iloc[i-1]):
                    crosses.append({
                        'index': i,
                        'type': 'MA_GOLDEN_CROSS',
                        'signal': 'BUY',
                        'strength': 85,
                        'price': df['close'].iloc[i],
                        'reason': '🌟 MA 20/50 Golden Cross (Strong BUY)'
                    })

                elif (df['ma_20'].iloc[i] < df['ma_50'].iloc[i] and
                      df['ma_20'].iloc[i-1] >= df['ma_50'].iloc[i-1]):
                    crosses.append({
                        'index': i,
                        'type': 'MA_DEATH_CROSS',
                        'signal': 'SELL',
                        'strength': 85,
                        'price': df['close'].iloc[i],
                        'reason': '💀 MA 20/50 Death Cross (Strong SELL)'
                    })

        return crosses[-10:] if crosses else []

    @staticmethod
    def get_indicator_summary(df):
        """خلاصه وضعیت اندیکاتورها"""
        if len(df) < 50:
            return {}

        df = TechnicalIndicators.calculate_all(df)
        latest = df.iloc[-1]

        summary = {
            'price': latest['close'],
            'rsi': round(latest['rsi'], 2) if pd.notna(latest['rsi']) else None,
            'macd': round(latest['macd'], 6) if pd.notna(latest['macd']) else None,
            'macd_signal': round(latest['macd_signal'], 6) if pd.notna(latest['macd_signal']) else None,
            'bb_position': None,
            'ma_trend': None,
            'atr_percent': round(latest['atr_percent'], 2) if pd.notna(latest['atr_percent']) else None
        }

        # موقعیت در بولینگر
        if pd.notna(latest['bb_upper']) and pd.notna(latest['bb_lower']):
            bb_range = latest['bb_upper'] - latest['bb_lower']
            if bb_range > 0:
                bb_pos = (latest['close'] - latest['bb_lower']) / bb_range * 100
                summary['bb_position'] = round(bb_pos, 1)

        # ترند MA
        if pd.notna(latest['ma_20']) and pd.notna(latest['ma_50']):
            if latest['close'] > latest['ma_20'] > latest['ma_50']:
                summary['ma_trend'] = 'BULLISH'
            elif latest['close'] < latest['ma_20'] < latest['ma_50']:
                summary['ma_trend'] = 'BEARISH'
            else:
                summary['ma_trend'] = 'NEUTRAL'

        return summary

indicators = TechnicalIndicators()
