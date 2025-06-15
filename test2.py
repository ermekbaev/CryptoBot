# technical_analysis.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass
from config import TradingConfig, CANDLESTICK_PATTERNS

# Импорт FINTA индикаторов
try:
    from finta import TA
    FINTA_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("✅ FINTA успешно импортирована")
except ImportError:
    FINTA_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ FINTA не найдена, используем упрощенные индикаторы")

@dataclass
class IndicatorSignal:
    """Структура сигнала от индикатора"""
    name: str
    value: float
    signal: str  # 'BUY', 'SELL', 'NEUTRAL'
    strength: float  # 0-1
    description: str

@dataclass
class TechnicalAnalysisResult:
    """Результат технического анализа"""
    symbol: str
    timeframe: str
    timestamp: pd.Timestamp
    signals: List[IndicatorSignal]
    overall_signal: str
    confidence: float
    price_targets: Dict[str, float]
    stop_loss: float
    support_levels: List[float]
    resistance_levels: List[float]

class TechnicalAnalyzer:
    """Класс для технического анализа с исправленной FINTA"""
    
    def __init__(self, config: TradingConfig):
        self.config = config
        
    def analyze(self, df: pd.DataFrame, symbol: str, timeframe: str) -> TechnicalAnalysisResult:
        """Основной метод анализа"""
        if df.empty or len(df) < 50:
            logger.warning(f"Недостаточно данных для анализа {symbol}")
            return self._create_empty_result(symbol, timeframe)
        
        # Переименовываем колонки для FINTA (нужны заглавные буквы)
        df_finta = df.copy()
        df_finta.columns = [col.title() if col in ['open', 'high', 'low', 'close', 'volume'] else col for col in df_finta.columns]
        
        signals = []
        
        if FINTA_AVAILABLE:
            # Используем FINTA индикаторы
            signals.extend(self._analyze_trend_indicators_finta(df_finta))
            signals.extend(self._analyze_oscillators_finta(df_finta))
            signals.extend(self._analyze_volatility_indicators_finta(df_finta))
            signals.extend(self._analyze_volume_indicators_finta(df_finta))
        else:
            # Упрощенные индикаторы
            signals.extend(self._analyze_simple_indicators(df))
        
        # Свечные паттерны (собственная реализация)
        signals.extend(self._analyze_candlestick_patterns(df))
        
        # Уровни поддержки и сопротивления
        support_levels, resistance_levels = self._find_support_resistance(df)
        
        # Общий сигнал и уровень уверенности
        overall_signal, confidence = self._calculate_overall_signal(signals)
        
        # Целевые уровни и стоп-лосс
        price_targets, stop_loss = self._calculate_price_targets(
            df, overall_signal, support_levels, resistance_levels
        )
        
        return TechnicalAnalysisResult(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=df.iloc[-1]['start_time'],
            signals=signals,
            overall_signal=overall_signal,
            confidence=confidence,
            price_targets=price_targets,
            stop_loss=stop_loss,
            support_levels=support_levels,
            resistance_levels=resistance_levels
        )
    
    def _analyze_trend_indicators_finta(self, df: pd.DataFrame) -> List[IndicatorSignal]:
        """Анализ трендовых индикаторов с FINTA - ИСПРАВЛЕНО"""
        signals = []
        
        try:
            current_price = df['Close'].iloc[-1]
            
            # EMA индикаторы
            for period in self.config.EMA_PERIODS:
                if len(df) > period:
                    try:
                        ema = TA.EMA(df, period=period)
                        if not ema.empty and not pd.isna(ema.iloc[-1]):
                            ema_value = ema.iloc[-1]
                            
                            if current_price > ema_value:
                                signal = 'BUY'
                                strength = min((current_price - ema_value) / ema_value * 50, 0.8)
                            else:
                                signal = 'SELL'
                                strength = min((ema_value - current_price) / ema_value * 50, 0.8)
                            
                            signals.append(IndicatorSignal(
                                name=f'EMA{period}',
                                value=ema_value,
                                signal=signal,
                                strength=abs(strength),
                                description=f'EMA{period}: {ema_value:.4f}'
                            ))
                    except Exception as e:
                        logger.debug(f"Ошибка EMA{period}: {e}")
                        continue
            
            # SMA индикаторы
            for period in [20, 50, 100]:
                if len(df) > period:
                    try:
                        sma = TA.SMA(df, period=period)
                        if not sma.empty and not pd.isna(sma.iloc[-1]):
                            sma_value = sma.iloc[-1]
                            
                            if current_price > sma_value:
                                signal = 'BUY'
                                strength = min((current_price - sma_value) / sma_value * 50, 0.8)
                            else:
                                signal = 'SELL'
                                strength = min((sma_value - current_price) / sma_value * 50, 0.8)
                            
                            signals.append(IndicatorSignal(
                                name=f'SMA{period}',
                                value=sma_value,
                                signal=signal,
                                strength=abs(strength),
                                description=f'SMA{period}: {sma_value:.4f}'
                            ))
                    except Exception as e:
                        logger.debug(f"Ошибка SMA{period}: {e}")
                        continue
            
            # MACD - ИСПРАВЛЕНО
            if len(df) > self.config.MACD_SLOW:
                try:
                    macd_result = TA.MACD(df)
                    if not macd_result.empty and len(macd_result) > 0:
                        # FINTA возвращает Series, а не DataFrame
                        macd_value = macd_result.iloc[-1]
                        
                        # Простая логика MACD
                        if macd_value > 0: # type: ignore
                            signal = 'BUY'
                            strength = min(abs(macd_value) * 1000, 0.8) # type: ignore
                        elif macd_value < 0: # type: ignore
                            signal = 'SELL'
                            strength = min(abs(macd_value) * 1000, 0.8) # type: ignore
                        else:
                            signal = 'NEUTRAL'
                            strength = 0.1
                        
                        signals.append(IndicatorSignal(
                            name='MACD',
                            value=macd_value, # type: ignore
                            signal=signal,
                            strength=strength,
                            description=f'MACD: {macd_value:.6f}'
                        ))
                except Exception as e:
                    logger.debug(f"Ошибка MACD: {e}")
            
        except Exception as e:
            logger.error(f"Ошибка в анализе трендовых индикаторов FINTA: {e}")
        
        return signals
    
    def _analyze_oscillators_finta(self, df: pd.DataFrame) -> List[IndicatorSignal]:
        """Анализ осцилляторов с FINTA - ИСПРАВЛЕНО"""
        signals = []
        
        try:
            # RSI
            if len(df) > self.config.RSI_PERIOD:
                try:
                    rsi = TA.RSI(df, period=self.config.RSI_PERIOD)
                    if not rsi.empty and not pd.isna(rsi.iloc[-1]):
                        rsi_val = rsi.iloc[-1]
                        
                        if rsi_val < 30:
                            signal = 'BUY'
                            strength = (30 - rsi_val) / 30
                        elif rsi_val > 70:
                            signal = 'SELL'
                            strength = (rsi_val - 70) / 30
                        else:
                            signal = 'NEUTRAL'
                            strength = 0.1
                        
                        signals.append(IndicatorSignal(
                            name='RSI',
                            value=rsi_val,
                            signal=signal,
                            strength=min(strength, 0.9),
                            description=f'RSI: {rsi_val:.2f}'
                        ))
                except Exception as e:
                    logger.debug(f"Ошибка RSI: {e}")
            
            # Stochastic
            if len(df) > 14:
                try:
                    stoch = TA.STOCH(df)
                    if not stoch.empty and not pd.isna(stoch.iloc[-1]):
                        stoch_val = stoch.iloc[-1]
                        
                        if stoch_val < 20:
                            signal = 'BUY'
                            strength = (20 - stoch_val) / 20
                        elif stoch_val > 80:
                            signal = 'SELL'
                            strength = (stoch_val - 80) / 20
                        else:
                            signal = 'NEUTRAL'
                            strength = 0.1
                        
                        signals.append(IndicatorSignal(
                            name='Stochastic',
                            value=stoch_val,
                            signal=signal,
                            strength=min(strength, 0.9),
                            description=f'Stoch: {stoch_val:.2f}'
                        ))
                except Exception as e:
                    logger.debug(f"Ошибка Stochastic: {e}")
            
            # Williams %R
            if len(df) > 14:
                try:
                    willr = TA.WILLIAMS(df, period=14)
                    if not willr.empty and not pd.isna(willr.iloc[-1]):
                        willr_val = willr.iloc[-1]
                        
                        if willr_val < -80:
                            signal = 'BUY'
                            strength = (-80 - willr_val) / 20
                        elif willr_val > -20:
                            signal = 'SELL'
                            strength = (willr_val + 20) / 20
                        else:
                            signal = 'NEUTRAL'
                            strength = 0.1
                        
                        signals.append(IndicatorSignal(
                            name='Williams %R',
                            value=willr_val,
                            signal=signal,
                            strength=min(strength, 0.9),
                            description=f'Williams %R: {willr_val:.2f}'
                        ))
                except Exception as e:
                    logger.debug(f"Ошибка Williams: {e}")
                    
        except Exception as e:
            logger.error(f"Ошибка в анализе осцилляторов FINTA: {e}")
        
        return signals
    
    def _analyze_volatility_indicators_finta(self, df: pd.DataFrame) -> List[IndicatorSignal]:
        """Анализ индикаторов волатильности с FINTA"""
        signals = []
        
        try:
            # Bollinger Bands
            if len(df) > self.config.BB_PERIOD:
                try:
                    bb_upper = TA.BBANDS(df, period=self.config.BB_PERIOD)['BB_UPPER']
                    bb_lower = TA.BBANDS(df, period=self.config.BB_PERIOD)['BB_LOWER']
                    
                    if not bb_upper.empty and not bb_lower.empty:
                        current_price = df['Close'].iloc[-1]
                        upper_val = bb_upper.iloc[-1]
                        lower_val = bb_lower.iloc[-1]
                        
                        if not (pd.isna(upper_val) or pd.isna(lower_val)):
                            bb_position = (current_price - lower_val) / (upper_val - lower_val)
                            
                            if bb_position < 0.2:  # Близко к нижней границе
                                signal = 'BUY'
                                strength = (0.2 - bb_position) * 2
                            elif bb_position > 0.8:  # Близко к верхней границе
                                signal = 'SELL'
                                strength = (bb_position - 0.8) * 2
                            else:
                                signal = 'NEUTRAL'
                                strength = 0.1
                            
                            signals.append(IndicatorSignal(
                                name='Bollinger Bands',
                                value=bb_position,
                                signal=signal,
                                strength=min(strength, 0.8),
                                description=f'BB Position: {bb_position:.3f}'
                            ))
                except Exception as e:
                    logger.debug(f"Ошибка Bollinger Bands: {e}")
                    
        except Exception as e:
            logger.error(f"Ошибка в анализе индикаторов волатильности FINTA: {e}")
        
        return signals
    
    def _analyze_volume_indicators_finta(self, df: pd.DataFrame) -> List[IndicatorSignal]:
        """Анализ объемных индикаторов с FINTA"""
        signals = []
        
        try:
            if 'Volume' in df.columns and len(df) > 20:
                # Простой анализ объема
                current_volume = df['Volume'].iloc[-1]
                avg_volume = df['Volume'].rolling(20).mean().iloc[-1]
                
                if not pd.isna(avg_volume) and avg_volume > 0:
                    volume_ratio = current_volume / avg_volume
                    
                    if volume_ratio > 1.5:
                        signal = 'BUY'
                        strength = min((volume_ratio - 1) / 2, 0.6)
                    else:
                        signal = 'NEUTRAL'
                        strength = 0.1
                    
                    signals.append(IndicatorSignal(
                        name='Volume',
                        value=current_volume,
                        signal=signal,
                        strength=strength,
                        description=f'Volume Ratio: {volume_ratio:.2f}'
                    ))
                    
        except Exception as e:
            logger.error(f"Ошибка в анализе объемных индикаторов FINTA: {e}")
        
        return signals
    
    def _analyze_simple_indicators(self, df: pd.DataFrame) -> List[IndicatorSignal]:
        """Упрощенные индикаторы без FINTA"""
        signals = []
        
        try:
            current_price = df['close'].iloc[-1]
            
            # Простая EMA
            for period in [9, 21, 50]:
                if len(df) > period:
                    ema = df['close'].ewm(span=period).mean()
                    ema_value = ema.iloc[-1]
                    
                    if current_price > ema_value:
                        signal = 'BUY'
                        strength = min((current_price - ema_value) / ema_value * 50, 0.8)
                    else:
                        signal = 'SELL'
                        strength = min((ema_value - current_price) / ema_value * 50, 0.8)
                    
                    signals.append(IndicatorSignal(
                        name=f'EMA{period}',
                        value=ema_value,
                        signal=signal,
                        strength=abs(strength),
                        description=f'EMA{period}: {ema_value:.4f}'
                    ))
        except Exception as e:
            logger.error(f"Ошибка в упрощенных индикаторах: {e}")
        
        return signals
    
    def _analyze_candlestick_patterns(self, df: pd.DataFrame) -> List[IndicatorSignal]:
        """Анализ свечных паттернов"""
        signals = []
        
        try:
            if len(df) < 3:
                return signals
            
            # Простые паттерны
            last_candle = df.iloc[-1]
            body_size = abs(last_candle['close'] - last_candle['open'])
            total_size = last_candle['high'] - last_candle['low']
            
            if total_size > 0:
                upper_shadow = last_candle['high'] - max(last_candle['open'], last_candle['close'])
                lower_shadow = min(last_candle['open'], last_candle['close']) - last_candle['low']
                
                # Hammer
                if lower_shadow > body_size * 2 and upper_shadow < body_size:
                    signals.append(IndicatorSignal(
                        name='Bullish_Pattern',
                        value=lower_shadow / total_size,
                        signal='BUY',
                        strength=0.5,
                        description='Bullish hammer pattern'
                    ))
                # Shooting star
                elif upper_shadow > body_size * 2 and lower_shadow < body_size:
                    signals.append(IndicatorSignal(
                        name='Bearish_Pattern',
                        value=upper_shadow / total_size,
                        signal='SELL',
                        strength=0.5,
                        description='Bearish shooting star pattern'
                    ))
                        
        except Exception as e:
            logger.error(f"Ошибка в анализе свечных паттернов: {e}")
        
        return signals
    
    def _find_support_resistance(self, df: pd.DataFrame) -> Tuple[List[float], List[float]]:
        """Поиск уровней поддержки и сопротивления"""
        try:
            if len(df) < 20:
                return [], []
            
            window = 5
            support_levels = []
            resistance_levels = []
            
            # Локальные минимумы
            for i in range(window, len(df) - window):
                if df['low'].iloc[i] == df['low'].iloc[i-window:i+window+1].min():
                    support_levels.append(df['low'].iloc[i])
            
            # Локальные максимумы
            for i in range(window, len(df) - window):
                if df['high'].iloc[i] == df['high'].iloc[i-window:i+window+1].max():
                    resistance_levels.append(df['high'].iloc[i])
            
            current_price = df['close'].iloc[-1]
            
            # Фильтруем
            support_levels = [level for level in set(support_levels) 
                            if level < current_price and (current_price - level) / current_price < 0.1]
            resistance_levels = [level for level in set(resistance_levels) 
                               if level > current_price and (level - current_price) / current_price < 0.1]
            
            return sorted(support_levels, reverse=True)[:3], sorted(resistance_levels)[:3]
            
        except Exception as e:
            logger.error(f"Ошибка поиска уровней: {e}")
            return [], []
    
    def _calculate_overall_signal(self, signals: List[IndicatorSignal]) -> Tuple[str, float]:
        """Расчет общего сигнала"""
        if not signals:
            return 'NEUTRAL', 0.0
        
        buy_score = sum(s.strength for s in signals if s.signal == 'BUY')
        sell_score = sum(s.strength for s in signals if s.signal == 'SELL')
        total_signals = len([s for s in signals if s.signal != 'NEUTRAL'])
        
        if total_signals == 0:
            return 'NEUTRAL', 50.0
        
        total_score = buy_score + sell_score
        if total_score == 0:
            return 'NEUTRAL', 50.0
        
        buy_pct = (buy_score / total_score) * 100
        sell_pct = (sell_score / total_score) * 100
        
        if buy_pct > sell_pct + 15:
            return 'BUY', min(buy_pct, 90)
        elif sell_pct > buy_pct + 15:
            return 'SELL', min(sell_pct, 90)
        else:
            return 'NEUTRAL', 50.0
    
    def _calculate_price_targets(self, df: pd.DataFrame, signal: str, 
                               support_levels: List[float], 
                               resistance_levels: List[float]) -> Tuple[Dict[str, float], float]:
        """Расчет целей и стоп-лосса"""
        current_price = df['close'].iloc[-1]
        price_targets = {}
        
        # Простой ATR
        try:
            high_low = df['high'] - df['low']
            atr = high_low.rolling(14).mean().iloc[-1]
            if pd.isna(atr):
                atr = current_price * 0.02
        except:
            atr = current_price * 0.02
        
        if signal == 'BUY':
            price_targets['target1'] = current_price + atr * 2
            price_targets['target2'] = current_price + atr * 3
            stop_loss = current_price - atr * 1.5
        elif signal == 'SELL':
            price_targets['target1'] = current_price - atr * 2  
            price_targets['target2'] = current_price - atr * 3
            stop_loss = current_price + atr * 1.5
        else:
            price_targets['target1'] = current_price
            price_targets['target2'] = current_price
            stop_loss = current_price
        
        return price_targets, stop_loss
    
    def _create_empty_result(self, symbol: str, timeframe: str) -> TechnicalAnalysisResult:
        """Пустой результат"""
        return TechnicalAnalysisResult(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=pd.Timestamp.now(),
            signals=[],
            overall_signal='NEUTRAL',
            confidence=0.0,
            price_targets={},
            stop_loss=0.0,
            support_levels=[],
            resistance_levels=[]
        )