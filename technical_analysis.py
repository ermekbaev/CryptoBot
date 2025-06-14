# technical_analysis.py - ИСПРАВЛЕННАЯ ВЕРСИЯ v2.0
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
    """Исправленный класс для технического анализа"""
    
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
        
        # Валидация данных перед анализом
        if not self._validate_data(df_finta):
            logger.warning(f"Данные для {symbol} не прошли валидацию")
            return self._create_empty_result(symbol, timeframe)
        
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
    
    def _validate_data(self, df: pd.DataFrame) -> bool:
        """Валидация качества данных"""
        try:
            # Проверяем наличие необходимых колонок
            required_cols = ['Open', 'High', 'Low', 'Close']
            if not all(col in df.columns for col in required_cols):
                logger.error("Отсутствуют необходимые колонки")
                return False
            
            # Проверяем на NaN
            if df[required_cols].isnull().any().any():
                logger.warning("Обнаружены NaN значения в данных")
                return False
            
            # Проверяем логичность цен (High >= Low, Close между High и Low)
            invalid_rows = (
                (df['High'] < df['Low']) |
                (df['Close'] > df['High']) |
                (df['Close'] < df['Low']) |
                (df['Open'] > df['High']) |
                (df['Open'] < df['Low'])
            )
            
            if invalid_rows.any():
                logger.warning(f"Обнаружено {invalid_rows.sum()} строк с некорректными ценами")
                return False
            
            # Проверяем на аномальные значения (скачки более 50%)
            price_changes = df['Close'].pct_change().abs()
            if (price_changes > 0.5).any():
                logger.warning("Обнаружены аномальные скачки цен > 50%")
                # Не блокируем анализ, только предупреждаем
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка валидации данных: {e}")
            return False
    
    def _analyze_trend_indicators_finta(self, df: pd.DataFrame) -> List[IndicatorSignal]:
        """ИСПРАВЛЕННЫЙ анализ трендовых индикаторов с FINTA"""
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
                            
                            # Улучшенная логика EMA с учетом наклона
                            if len(ema) >= 3:
                                ema_slope = (ema.iloc[-1] - ema.iloc[-3]) / ema.iloc[-3]
                                price_distance = (current_price - ema_value) / ema_value
                                
                                if current_price > ema_value and ema_slope > 0:
                                    signal = 'BUY'
                                    strength = min(abs(price_distance) * 20 + abs(ema_slope) * 10, 0.9)
                                elif current_price < ema_value and ema_slope < 0:
                                    signal = 'SELL'
                                    strength = min(abs(price_distance) * 20 + abs(ema_slope) * 10, 0.9)
                                else:
                                    signal = 'NEUTRAL'
                                    strength = 0.2
                            else:
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
                                description=f'EMA{period}: {ema_value:.6f} (наклон: {ema_slope:.4f})' if len(ema) >= 3 else f'EMA{period}: {ema_value:.6f}'
                            ))
                    except Exception as e:
                        logger.debug(f"Ошибка EMA{period}: {e}")
                        continue
            
            # ИСПРАВЛЕННЫЙ MACD - КРИТИЧНО!
            if len(df) > self.config.MACD_SLOW + self.config.MACD_SIGNAL:
                try:
                    # Правильный расчет MACD с FINTA
                    macd_data = TA.MACD(df, 
                                      period_fast=self.config.MACD_FAST, 
                                      period_slow=self.config.MACD_SLOW, 
                                      signal=self.config.MACD_SIGNAL)
                    
                    if isinstance(macd_data, pd.DataFrame) and len(macd_data) > 1:
                        # FINTA возвращает DataFrame с колонками MACD, SIGNAL, HISTOGRAM
                        macd_line = macd_data['MACD'].iloc[-1]
                        signal_line = macd_data['SIGNAL'].iloc[-1]
                        histogram = macd_data['HISTOGRAM'].iloc[-1]
                        
                        # Предыдущие значения для определения пересечения
                        prev_macd = macd_data['MACD'].iloc[-2]
                        prev_signal = macd_data['SIGNAL'].iloc[-2]
                        
                        # Правильная логика MACD
                        macd_signal = 'NEUTRAL'
                        macd_strength = 0.1
                        description = f'MACD: {macd_line:.6f}, Signal: {signal_line:.6f}, Hist: {histogram:.6f}'
                        
                        # Пересечение линий (основной сигнал)
                        if prev_macd <= prev_signal and macd_line > signal_line:
                            # Бычье пересечение MACD выше сигнальной линии
                            macd_signal = 'BUY'
                            macd_strength = 0.8
                            description += ' (Бычье пересечение)'
                        elif prev_macd >= prev_signal and macd_line < signal_line:
                            # Медвежье пересечение MACD ниже сигнальной линии
                            macd_signal = 'SELL'
                            macd_strength = 0.8
                            description += ' (Медвежье пересечение)'
                        else:
                            # Текущее положение без пересечения
                            if macd_line > signal_line and histogram > 0:
                                macd_signal = 'BUY'
                                macd_strength = min(abs(histogram) * 1000 + 0.3, 0.6)
                            elif macd_line < signal_line and histogram < 0:
                                macd_signal = 'SELL'
                                macd_strength = min(abs(histogram) * 1000 + 0.3, 0.6)
                        
                        # Усиление сигнала при пересечении нулевой линии
                        if abs(macd_line) < 0.0001:  # Близко к нулю
                            if macd_line > 0 and prev_macd <= 0:
                                macd_strength = min(macd_strength + 0.2, 0.9)
                                description += ' (Пересечение нуля вверх)'
                            elif macd_line < 0 and prev_macd >= 0:
                                macd_strength = min(macd_strength + 0.2, 0.9)
                                description += ' (Пересечение нуля вниз)'
                        
                        signals.append(IndicatorSignal(
                            name='MACD',
                            value=macd_line,
                            signal=macd_signal,
                            strength=macd_strength,
                            description=description
                        ))
                        
                    elif isinstance(macd_data, pd.Series) and len(macd_data) > 1:
                        # Если FINTA возвращает только Series (старая версия)
                        macd_value = macd_data.iloc[-1]
                        prev_macd = macd_data.iloc[-2]
                        
                        # Упрощенная логика для Series
                        if macd_value > 0 and prev_macd <= 0:
                            macd_signal = 'BUY'
                            macd_strength = 0.7
                        elif macd_value < 0 and prev_macd >= 0:
                            macd_signal = 'SELL'
                            macd_strength = 0.7
                        elif macd_value > 0:
                            macd_signal = 'BUY'
                            macd_strength = min(abs(macd_value) * 1000, 0.5)
                        elif macd_value < 0:
                            macd_signal = 'SELL'
                            macd_strength = min(abs(macd_value) * 1000, 0.5)
                        else:
                            macd_signal = 'NEUTRAL'
                            macd_strength = 0.1
                        
                        signals.append(IndicatorSignal(
                            name='MACD',
                            value=macd_value,
                            signal=macd_signal,
                            strength=macd_strength,
                            description=f'MACD: {macd_value:.6f} (Series mode)'
                        ))
                        
                except Exception as e:
                    logger.debug(f"Ошибка MACD: {e}")
                    # Fallback к простому MACD
                    try:
                        ema_fast = df['Close'].ewm(span=self.config.MACD_FAST).mean()
                        ema_slow = df['Close'].ewm(span=self.config.MACD_SLOW).mean()
                        macd_line = ema_fast - ema_slow
                        signal_line = macd_line.ewm(span=self.config.MACD_SIGNAL).mean()
                        
                        if len(macd_line) > 1:
                            current_macd = macd_line.iloc[-1]
                            current_signal = signal_line.iloc[-1]
                            prev_macd = macd_line.iloc[-2]
                            prev_signal = signal_line.iloc[-2]
                            
                            if prev_macd <= prev_signal and current_macd > current_signal:
                                macd_signal = 'BUY'
                                macd_strength = 0.6
                            elif prev_macd >= prev_signal and current_macd < current_signal:
                                macd_signal = 'SELL'
                                macd_strength = 0.6
                            else:
                                macd_signal = 'NEUTRAL'
                                macd_strength = 0.2
                            
                            signals.append(IndicatorSignal(
                                name='MACD',
                                value=current_macd,
                                signal=macd_signal,
                                strength=macd_strength,
                                description=f'MACD (fallback): {current_macd:.6f}'
                            ))
                    except Exception as e2:
                        logger.error(f"Ошибка fallback MACD: {e2}")
            
            # SMA индикаторы с улучшенной логикой
            for period in [20, 50, 100]:
                if len(df) > period:
                    try:
                        sma = TA.SMA(df, period=period)
                        if not sma.empty and not pd.isna(sma.iloc[-1]):
                            sma_value = sma.iloc[-1]
                            
                            # Анализ наклона SMA
                            if len(sma) >= 5:
                                sma_slope = (sma.iloc[-1] - sma.iloc[-5]) / sma.iloc[-5]
                                price_distance = (current_price - sma_value) / sma_value
                                
                                if current_price > sma_value and sma_slope > 0.001:
                                    signal = 'BUY'
                                    strength = min(abs(price_distance) * 30 + abs(sma_slope) * 20, 0.7)
                                elif current_price < sma_value and sma_slope < -0.001:
                                    signal = 'SELL'
                                    strength = min(abs(price_distance) * 30 + abs(sma_slope) * 20, 0.7)
                                else:
                                    signal = 'NEUTRAL'
                                    strength = 0.1
                            else:
                                if current_price > sma_value:
                                    signal = 'BUY'
                                    strength = min((current_price - sma_value) / sma_value * 50, 0.6)
                                else:
                                    signal = 'SELL'
                                    strength = min((sma_value - current_price) / sma_value * 50, 0.6)
                            
                            signals.append(IndicatorSignal(
                                name=f'SMA{period}',
                                value=sma_value,
                                signal=signal,
                                strength=abs(strength),
                                description=f'SMA{period}: {sma_value:.6f}'
                            ))
                    except Exception as e:
                        logger.debug(f"Ошибка SMA{period}: {e}")
                        continue
            
        except Exception as e:
            logger.error(f"Ошибка в анализе трендовых индикаторов FINTA: {e}")
        
        return signals
    
    def _analyze_oscillators_finta(self, df: pd.DataFrame) -> List[IndicatorSignal]:
        """Анализ осцилляторов с FINTA"""
        signals = []
        
        try:
            # RSI с улучшенной логикой
            if len(df) > self.config.RSI_PERIOD:
                try:
                    rsi = TA.RSI(df, period=self.config.RSI_PERIOD)
                    if not rsi.empty and not pd.isna(rsi.iloc[-1]):
                        rsi_val = rsi.iloc[-1]
                        
                        # Анализ дивергенции RSI (если достаточно данных)
                        divergence_signal = ''
                        if len(rsi) >= 10 and len(df) >= 10:
                            # Простая проверка дивергенции за последние 10 периодов
                            recent_rsi = rsi.tail(10)
                            recent_price = df['Close'].tail(10)
                            
                            rsi_trend = (recent_rsi.iloc[-1] - recent_rsi.iloc[0]) / recent_rsi.iloc[0]
                            price_trend = (recent_price.iloc[-1] - recent_price.iloc[0]) / recent_price.iloc[0]
                            
                            if rsi_trend > 0.05 and price_trend < -0.02:
                                divergence_signal = ' (Бычья дивергенция)'
                            elif rsi_trend < -0.05 and price_trend > 0.02:
                                divergence_signal = ' (Медвежья дивергенция)'
                        
                        # Основная логика RSI
                        if rsi_val < 30:
                            signal = 'BUY'
                            strength = (30 - rsi_val) / 30 * 0.8
                            if divergence_signal == ' (Бычья дивергенция)':
                                strength = min(strength + 0.2, 0.9)
                        elif rsi_val > 70:
                            signal = 'SELL'
                            strength = (rsi_val - 70) / 30 * 0.8
                            if divergence_signal == ' (Медвежья дивергенция)':
                                strength = min(strength + 0.2, 0.9)
                        elif rsi_val < 40:
                            signal = 'BUY'
                            strength = (40 - rsi_val) / 40 * 0.4
                        elif rsi_val > 60:
                            signal = 'SELL'
                            strength = (rsi_val - 60) / 40 * 0.4
                        else:
                            signal = 'NEUTRAL'
                            strength = 0.1
                        
                        signals.append(IndicatorSignal(
                            name='RSI',
                            value=rsi_val,
                            signal=signal,
                            strength=min(strength, 0.9),
                            description=f'RSI: {rsi_val:.2f}{divergence_signal}'
                        ))
                except Exception as e:
                    logger.debug(f"Ошибка RSI: {e}")
            
            # Улучшенный Stochastic
            if len(df) > 14:
                try:
                    stoch = TA.STOCH(df)
                    if not stoch.empty and not pd.isna(stoch.iloc[-1]):
                        stoch_val = stoch.iloc[-1]
                        
                        # Дополнительная проверка %D (если доступна)
                        stoch_d = None
                        try:
                            stoch_d = TA.STOCHD(df)
                            if not stoch_d.empty:
                                stoch_d_val = stoch_d.iloc[-1]
                        except:
                            pass
                        
                        if stoch_val < 20:
                            signal = 'BUY'
                            strength = (20 - stoch_val) / 20 * 0.7
                        elif stoch_val > 80:
                            signal = 'SELL'
                            strength = (stoch_val - 80) / 20 * 0.7
                        else:
                            signal = 'NEUTRAL'
                            strength = 0.1
                        
                        # Усиление сигнала при подтверждении %D
                        if stoch_d is not None:
                            if signal == 'BUY' and stoch_d_val < 20:
                                strength = min(strength + 0.2, 0.9)
                            elif signal == 'SELL' and stoch_d_val > 80:
                                strength = min(strength + 0.2, 0.9)
                        
                        signals.append(IndicatorSignal(
                            name='Stochastic',
                            value=stoch_val,
                            signal=signal,
                            strength=min(strength, 0.9),
                            description=f'Stoch: {stoch_val:.2f}' + (f', %D: {stoch_d_val:.2f}' if stoch_d is not None else '')
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
                            strength = (-80 - willr_val) / 20 * 0.6
                        elif willr_val > -20:
                            signal = 'SELL'
                            strength = (willr_val + 20) / 20 * 0.6
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
            # Улучшенные Bollinger Bands
            if len(df) > self.config.BB_PERIOD:
                try:
                    bb_data = TA.BBANDS(df, period=self.config.BB_PERIOD, std_multiplier=self.config.BB_STD)
                    
                    if isinstance(bb_data, pd.DataFrame) and not bb_data.empty:
                        bb_upper = bb_data['BB_UPPER'].iloc[-1]
                        bb_lower = bb_data['BB_LOWER'].iloc[-1]
                        bb_middle = bb_data['BB_MIDDLE'].iloc[-1] if 'BB_MIDDLE' in bb_data.columns else (bb_upper + bb_lower) / 2
                    else:
                        # Fallback к ручному расчету
                        sma = df['Close'].rolling(window=self.config.BB_PERIOD).mean()
                        std = df['Close'].rolling(window=self.config.BB_PERIOD).std()
                        bb_upper = (sma + (std * self.config.BB_STD)).iloc[-1]
                        bb_lower = (sma - (std * self.config.BB_STD)).iloc[-1]
                        bb_middle = sma.iloc[-1]
                    
                    current_price = df['Close'].iloc[-1]
                    
                    if not (pd.isna(bb_upper) or pd.isna(bb_lower)):
                        bb_position = (current_price - bb_lower) / (bb_upper - bb_lower)
                        bb_width = (bb_upper - bb_lower) / bb_middle
                        
                        # Анализ сжатия/расширения полос
                        if len(df) >= self.config.BB_PERIOD + 5:
                            prev_sma = df['Close'].rolling(window=self.config.BB_PERIOD).mean().iloc[-6]
                            prev_std = df['Close'].rolling(window=self.config.BB_PERIOD).std().iloc[-6]
                            prev_width = (prev_std * 2 * self.config.BB_STD) / prev_sma
                            
                            width_change = (bb_width - prev_width) / prev_width
                            squeeze_info = ''
                            
                            if width_change < -0.1:
                                squeeze_info = ' (Сжатие полос - готовность к движению)'
                            elif width_change > 0.1:
                                squeeze_info = ' (Расширение полос - волатильность)'
                        else:
                            squeeze_info = ''
                        
                        if bb_position < 0.1:  # Близко к нижней границе
                            signal = 'BUY'
                            strength = (0.1 - bb_position) * 5
                        elif bb_position > 0.9:  # Близко к верхней границе
                            signal = 'SELL'
                            strength = (bb_position - 0.9) * 5
                        elif bb_position < 0.2:
                            signal = 'BUY'
                            strength = (0.2 - bb_position) * 2
                        elif bb_position > 0.8:
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
                            description=f'BB Position: {bb_position:.3f}, Width: {bb_width:.4f}{squeeze_info}'
                        ))
                        
                except Exception as e:
                    logger.debug(f"Ошибка Bollinger Bands: {e}")
            
            # ИСПРАВЛЕННЫЙ ATR (Average True Range)
            if len(df) > 14:
                try:
                    # Правильный расчет ATR
                    high_low = df['High'] - df['Low']
                    high_close = np.abs(df['High'] - df['Close'].shift())
                    low_close = np.abs(df['Low'] - df['Close'].shift())
                    
                    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1) # type: ignore
                    atr = true_range.rolling(window=14).mean()
                    
                    if not atr.empty and not pd.isna(atr.iloc[-1]):
                        atr_value = atr.iloc[-1]
                        current_price = df['Close'].iloc[-1]
                        atr_percent = (atr_value / current_price) * 100
                        
                        # Анализ изменения волатильности
                        if len(atr) >= 7:
                            atr_change = (atr.iloc[-1] - atr.iloc[-7]) / atr.iloc[-7]
                            
                            if atr_percent > 5:  # Высокая волатильность
                                signal = 'SELL'  # Осторожность при высокой волатильности
                                strength = min((atr_percent - 5) / 10, 0.6)
                            elif atr_percent < 1:  # Очень низкая волатильность
                                signal = 'NEUTRAL'  # Низкая волатильность - ожидание движения
                                strength = 0.3
                            elif atr_change > 0.2:  # Растущая волатильность
                                signal = 'BUY'  # Может предвещать движение
                                strength = min(atr_change * 2, 0.5)
                            else:
                                signal = 'NEUTRAL'
                                strength = 0.1
                            
                            signals.append(IndicatorSignal(
                                name='ATR',
                                value=atr_value,
                                signal=signal,
                                strength=strength,
                                description=f'ATR: {atr_value:.6f} ({atr_percent:.2f}%), изменение: {atr_change:.2%}'
                            ))
                        else:
                            signals.append(IndicatorSignal(
                                name='ATR',
                                value=atr_value,
                                signal='NEUTRAL',
                                strength=0.1,
                                description=f'ATR: {atr_value:.6f} ({atr_percent:.2f}%)'
                            ))
                            
                except Exception as e:
                    logger.debug(f"Ошибка ATR: {e}")
                    
        except Exception as e:
            logger.error(f"Ошибка в анализе индикаторов волатильности FINTA: {e}")
        
        return signals
    
    def _analyze_volume_indicators_finta(self, df: pd.DataFrame) -> List[IndicatorSignal]:
        """Улучшенный анализ объемных индикаторов"""
        signals = []
        
        try:
            if 'Volume' in df.columns and len(df) > 20:
                current_volume = df['Volume'].iloc[-1]
                
                # Средний объем за разные периоды
                avg_volume_10 = df['Volume'].rolling(10).mean().iloc[-1]
                avg_volume_20 = df['Volume'].rolling(20).mean().iloc[-1]
                
                if not (pd.isna(avg_volume_10) or pd.isna(avg_volume_20)) and avg_volume_20 > 0:
                    volume_ratio_10 = current_volume / avg_volume_10
                    volume_ratio_20 = current_volume / avg_volume_20
                    
                    # Анализ ценового движения с объемом
                    price_change = (df['Close'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2]
                    
                    # OBV (On Balance Volume) упрощенный
                    obv_data = []
                    obv = 0
                    for i in range(len(df)):
                        if i == 0:
                            obv_data.append(df['Volume'].iloc[i])
                        else:
                            if df['Close'].iloc[i] > df['Close'].iloc[i-1]:
                                obv += df['Volume'].iloc[i]
                            elif df['Close'].iloc[i] < df['Close'].iloc[i-1]:
                                obv -= df['Volume'].iloc[i]
                            obv_data.append(obv)
                    
                    obv_series = pd.Series(obv_data)
                    obv_trend = (obv_series.iloc[-1] - obv_series.iloc[-5]) / abs(obv_series.iloc[-5]) if len(obv_series) >= 5 and obv_series.iloc[-5] != 0 else 0
                    
                    # Основная логика объемного анализа
                    if volume_ratio_20 > 2.0:  # Очень высокий объем
                        if price_change > 0.02:  # Рост цены + высокий объем
                            signal = 'BUY'
                            strength = min(volume_ratio_20 / 5, 0.8)
                        elif price_change < -0.02:  # Падение цены + высокий объем
                            signal = 'SELL'
                            strength = min(volume_ratio_20 / 5, 0.8)
                        else:
                            signal = 'NEUTRAL'
                            strength = 0.4
                    elif volume_ratio_20 > 1.5:  # Повышенный объем
                        if price_change > 0:
                            signal = 'BUY'
                            strength = min((volume_ratio_20 - 1) / 2, 0.6)
                        else:
                            signal = 'NEUTRAL'
                            strength = 0.2
                    elif volume_ratio_20 < 0.5:  # Низкий объем
                        signal = 'NEUTRAL'
                        strength = 0.1
                    else:
                        signal = 'NEUTRAL'
                        strength = 0.1
                    
                    # Коррекция на основе OBV
                    if abs(obv_trend) > 0.1:
                        if obv_trend > 0 and signal != 'SELL':
                            signal = 'BUY' if signal != 'BUY' else signal
                            strength = min(strength + abs(obv_trend), 0.9)
                        elif obv_trend < 0 and signal != 'BUY':
                            signal = 'SELL' if signal != 'SELL' else signal
                            strength = min(strength + abs(obv_trend), 0.9)
                    
                    signals.append(IndicatorSignal(
                        name='Volume',
                        value=current_volume,
                        signal=signal,
                        strength=strength,
                        description=f'Volume Ratio 20: {volume_ratio_20:.2f}, OBV Trend: {obv_trend:.3f}, Price Change: {price_change:.3%}'
                    ))
                    
        except Exception as e:
            logger.error(f"Ошибка в анализе объемных индикаторов: {e}")
        
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
                        description=f'EMA{period}: {ema_value:.6f}'
                    ))
                    
            # Простой RSI
            if len(df) > 14:
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean() # type: ignore
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean() # type: ignore
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                
                if not pd.isna(rsi.iloc[-1]):
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
            logger.error(f"Ошибка в упрощенных индикаторах: {e}")
        
        return signals
    
    def _analyze_candlestick_patterns(self, df: pd.DataFrame) -> List[IndicatorSignal]:
        """Улучшенный анализ свечных паттернов"""
        signals = []
        
        try:
            if len(df) < 3:
                return signals
            
            # Получаем последние 3 свечи для анализа паттернов
            current = df.iloc[-1]
            prev1 = df.iloc[-2]
            prev2 = df.iloc[-3] if len(df) >= 3 else None
            
            patterns_found = []
            
            # Размеры тел и теней
            current_body = abs(current['close'] - current['open'])
            current_total = current['high'] - current['low']
            current_upper_shadow = current['high'] - max(current['open'], current['close'])
            current_lower_shadow = min(current['open'], current['close']) - current['low']
            
            prev1_body = abs(prev1['close'] - prev1['open'])
            prev1_total = prev1['high'] - prev1['low']
            
            if current_total > 0:
                # Hammer (молот)
                if (current_lower_shadow > current_body * 2 and 
                    current_upper_shadow < current_body * 0.5 and
                    current_body > current_total * 0.1):
                    patterns_found.append(('Hammer', 'BUY', 0.6))
                
                # Hanging Man (висящий)
                elif (current_lower_shadow > current_body * 2 and 
                      current_upper_shadow < current_body * 0.5 and
                      current['close'] < prev1['close']):
                    patterns_found.append(('Hanging Man', 'SELL', 0.5))
                
                # Shooting Star (падающая звезда)
                elif (current_upper_shadow > current_body * 2 and 
                      current_lower_shadow < current_body * 0.5 and
                      current_body > current_total * 0.1):
                    patterns_found.append(('Shooting Star', 'SELL', 0.6))
                
                # Inverted Hammer (перевернутый молот)
                elif (current_upper_shadow > current_body * 2 and 
                      current_lower_shadow < current_body * 0.5 and
                      current['close'] > prev1['close']):
                    patterns_found.append(('Inverted Hammer', 'BUY', 0.5))
                
                # Doji
                elif current_body < current_total * 0.1:
                    if current_upper_shadow > current_total * 0.4 and current_lower_shadow > current_total * 0.4:
                        patterns_found.append(('Doji', 'NEUTRAL', 0.4))
                
                # Engulfing patterns (требуют предыдущую свечу)
                if prev1_total > 0:
                    # Bullish Engulfing
                    if (current['close'] > current['open'] and  # Текущая зеленая
                        prev1['close'] < prev1['open'] and     # Предыдущая красная
                        current['close'] > prev1['open'] and   # Закрытие выше открытия предыдущей
                        current['open'] < prev1['close'] and   # Открытие ниже закрытия предыдущей
                        current_body > prev1_body * 1.2):     # Тело больше предыдущего
                        patterns_found.append(('Bullish Engulfing', 'BUY', 0.7))
                    
                    # Bearish Engulfing
                    elif (current['close'] < current['open'] and  # Текущая красная
                          prev1['close'] > prev1['open'] and     # Предыдущая зеленая
                          current['close'] < prev1['open'] and   # Закрытие ниже открытия предыдущей
                          current['open'] > prev1['close'] and   # Открытие выше закрытия предыдущей
                          current_body > prev1_body * 1.2):     # Тело больше предыдущего
                        patterns_found.append(('Bearish Engulfing', 'SELL', 0.7))
            
            # Трехсвечные паттерны
            if prev2 is not None:
                prev2_body = abs(prev2['close'] - prev2['open'])
                
                # Morning Star (утренняя звезда)
                if (prev2['close'] < prev2['open'] and      # Первая красная
                    prev1_body < prev2_body * 0.5 and      # Вторая маленькая
                    current['close'] > current['open'] and  # Третья зеленая
                    current['close'] > (prev2['open'] + prev2['close']) / 2):  # Закрытие выше середины первой
                    patterns_found.append(('Morning Star', 'BUY', 0.8))
                
                # Evening Star (вечерняя звезда)
                elif (prev2['close'] > prev2['open'] and      # Первая зеленая
                      prev1_body < prev2_body * 0.5 and      # Вторая маленькая
                      current['close'] < current['open'] and  # Третья красная
                      current['close'] < (prev2['open'] + prev2['close']) / 2):  # Закрытие ниже середины первой
                    patterns_found.append(('Evening Star', 'SELL', 0.8))
            
            # Добавляем найденные паттерны в сигналы
            for pattern_name, signal_type, strength in patterns_found:
                signals.append(IndicatorSignal(
                    name=f'Pattern_{pattern_name}',
                    value=1.0,
                    signal=signal_type,
                    strength=strength,
                    description=f'Свечной паттерн: {pattern_name}'
                ))
                        
        except Exception as e:
            logger.error(f"Ошибка в анализе свечных паттернов: {e}")
        
        return signals
    
    def _find_support_resistance(self, df: pd.DataFrame) -> Tuple[List[float], List[float]]:
        """Улучшенный поиск уровней поддержки и сопротивления"""
        try:
            if len(df) < 20:
                return [], []
            
            window = 5
            support_levels = []
            resistance_levels = []
            
            # Локальные минимумы (поддержка)
            for i in range(window, len(df) - window):
                if df['low'].iloc[i] == df['low'].iloc[i-window:i+window+1].min():
                    # Дополнительная проверка на значимость уровня
                    touches = 0
                    level = df['low'].iloc[i]
                    tolerance = level * 0.005  # 0.5% толерантность
                    
                    # Считаем количество касаний этого уровня
                    for j in range(len(df)):
                        if abs(df['low'].iloc[j] - level) <= tolerance:
                            touches += 1
                    
                    if touches >= 2:  # Уровень должен быть протестирован минимум 2 раза
                        support_levels.append(level)
            
            # Локальные максимумы (сопротивление)
            for i in range(window, len(df) - window):
                if df['high'].iloc[i] == df['high'].iloc[i-window:i+window+1].max():
                    touches = 0
                    level = df['high'].iloc[i]
                    tolerance = level * 0.005
                    
                    for j in range(len(df)):
                        if abs(df['high'].iloc[j] - level) <= tolerance:
                            touches += 1
                    
                    if touches >= 2:
                        resistance_levels.append(level)
            
            current_price = df['close'].iloc[-1]
            
            # Фильтруем и сортируем уровни
            support_levels = [level for level in set(support_levels) 
                            if level < current_price and (current_price - level) / current_price < 0.15]
            resistance_levels = [level for level in set(resistance_levels) 
                               if level > current_price and (level - current_price) / current_price < 0.15]
            
            # Сортируем: поддержка по убыванию (ближайшие сверху), сопротивление по возрастанию (ближайшие снизу)
            support_levels = sorted(support_levels, reverse=True)[:5]
            resistance_levels = sorted(resistance_levels)[:5]
            
            return support_levels, resistance_levels
            
        except Exception as e:
            logger.error(f"Ошибка поиска уровней: {e}")
            return [], []
    
    def _calculate_overall_signal(self, signals: List[IndicatorSignal]) -> Tuple[str, float]:
        """Улучшенный расчет общего сигнала"""
        if not signals:
            return 'NEUTRAL', 0.0
        
        # Веса для разных типов индикаторов
        indicator_weights = {
            'MACD': 1.5,        # Высокий вес для MACD
            'RSI': 1.2,         # Высокий вес для RSI
            'EMA9': 1.0,        # Краткосрочная EMA
            'EMA21': 1.3,       # Среднесрочная EMA
            'EMA50': 1.5,       # Долгосрочная EMA
            'Bollinger Bands': 1.1,
            'Volume': 1.0,
            'Pattern_': 0.8,    # Свечные паттерны (префикс)
            'Stochastic': 0.9,
            'Williams': 0.7,
            'ATR': 0.5,         # Низкий вес для ATR (индикатор волатильности)
            'SMA': 0.8
        }
        
        buy_score = 0.0
        sell_score = 0.0
        total_weight = 0.0
        
        # Подсчет взвешенных сигналов
        for signal in signals:
            # Определяем вес индикатора
            weight = 0.5  # Базовый вес
            for key, w in indicator_weights.items():
                if key in signal.name:
                    weight = w
                    break
            
            adjusted_strength = signal.strength * weight
            
            if signal.signal == 'BUY':
                buy_score += adjusted_strength
            elif signal.signal == 'SELL':
                sell_score += adjusted_strength
            
            total_weight += weight
        
        # Нормализация
        if total_weight == 0:
            return 'NEUTRAL', 50.0
        
        buy_score = (buy_score / total_weight) * 100
        sell_score = (sell_score / total_weight) * 100
        
        # Определение сигнала с адаптивными порогами
        signal_threshold = 20  # Базовый порог 20%
        
        # Адаптивные пороги на основе количества сигналов
        if len(signals) >= 8:
            signal_threshold = 15  # Снижаем порог при большом количестве индикаторов
        elif len(signals) <= 4:
            signal_threshold = 25  # Повышаем порог при малом количестве
        
        # Определение итогового сигнала
        if buy_score > sell_score + signal_threshold:
            overall_signal = 'BUY'
            confidence = min(buy_score, 95)
        elif sell_score > buy_score + signal_threshold:
            overall_signal = 'SELL'
            confidence = min(sell_score, 95)
        else:
            overall_signal = 'NEUTRAL'
            confidence = max(60 - abs(buy_score - sell_score) / 2, 30)
        
        return overall_signal, confidence
    
    def _calculate_price_targets(self, df: pd.DataFrame, signal: str, 
                               support_levels: List[float], 
                               resistance_levels: List[float]) -> Tuple[Dict[str, float], float]:
        """Улучшенный расчет целей и стоп-лосса"""
        current_price = df['close'].iloc[-1]
        price_targets = {}
        
        # Правильный ATR
        try:
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = true_range.rolling(14).mean().iloc[-1]
            
            if pd.isna(atr) or atr <= 0:
                atr = current_price * 0.02
        except:
            atr = current_price * 0.02
        
        # Динамические мультипликаторы на основе волатильности
        volatility = atr / current_price
        if volatility > 0.05:  # Высокая волатильность
            stop_multiplier = 2.5
            target_multiplier_1 = 2.0
            target_multiplier_2 = 3.5
        elif volatility < 0.02:  # Низкая волатильность
            stop_multiplier = 1.5
            target_multiplier_1 = 2.5
            target_multiplier_2 = 4.0
        else:  # Средняя волатильность
            stop_multiplier = 2.0
            target_multiplier_1 = 2.5
            target_multiplier_2 = 4.0
        
        if signal == 'BUY':
            # Стоп-лосс для покупки
            stop_loss = current_price - (atr * stop_multiplier)
            
            # Используем ближайший уровень поддержки
            if support_levels:
                nearest_support = support_levels[0]  # Первый в списке = ближайший
                stop_loss = max(stop_loss, nearest_support - atr * 0.5)
            
            # Цели для покупки
            target1 = current_price + (atr * target_multiplier_1)
            target2 = current_price + (atr * target_multiplier_2)
            
            # Корректируем цели на основе уровней сопротивления
            if resistance_levels:
                if len(resistance_levels) >= 1:
                    target1 = min(target1, resistance_levels[0] * 0.995)
                if len(resistance_levels) >= 2:
                    target2 = min(target2, resistance_levels[1] * 0.995)
                elif len(resistance_levels) == 1:
                    target2 = min(target2, resistance_levels[0] * 1.02)
            
            price_targets['target1'] = max(target1, current_price + atr)  # Минимум ATR прибыли
            price_targets['target2'] = max(target2, current_price + atr * 2)
            
        elif signal == 'SELL':
            # Стоп-лосс для продажи
            stop_loss = current_price + (atr * stop_multiplier)
            
            # Используем ближайший уровень сопротивления
            if resistance_levels:
                nearest_resistance = resistance_levels[0]
                stop_loss = min(stop_loss, nearest_resistance + atr * 0.5)
            
            # Цели для продажи
            target1 = current_price - (atr * target_multiplier_1)
            target2 = current_price - (atr * target_multiplier_2)
            
            # Корректируем цели на основе уровней поддержки
            if support_levels:
                if len(support_levels) >= 1:
                    target1 = max(target1, support_levels[0] * 1.005)
                if len(support_levels) >= 2:
                    target2 = max(target2, support_levels[1] * 1.005)
                elif len(support_levels) == 1:
                    target2 = max(target2, support_levels[0] * 0.98)
            
            price_targets['target1'] = min(target1, current_price - atr)
            price_targets['target2'] = min(target2, current_price - atr * 2)
            
        else:
            # NEUTRAL
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