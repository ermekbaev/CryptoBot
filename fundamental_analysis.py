# fundamental_analysis.py
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging
from dataclasses import dataclass
from config import TradingConfig

logger = logging.getLogger(__name__)

@dataclass
class FundamentalSignal:
    """Структура фундаментального сигнала"""
    name: str
    value: float
    signal: str  # 'BUY', 'SELL', 'NEUTRAL'
    strength: float  # 0-1
    description: str
    impact: str  # 'HIGH', 'MEDIUM', 'LOW'

@dataclass
class FundamentalAnalysisResult:
    """Результат фундаментального анализа"""
    symbol: str
    timestamp: pd.Timestamp
    signals: List[FundamentalSignal]
    overall_signal: str
    confidence: float
    risk_factors: List[str]
    market_sentiment: str

class FundamentalAnalyzer:
    """Класс для фундаментального анализа"""
    
    def __init__(self, config: TradingConfig):
        self.config = config
        
    def analyze(self, symbol: str, ticker_data: Dict, 
                funding_rate: Dict, open_interest_df: pd.DataFrame) -> FundamentalAnalysisResult:
        """Основной метод фундаментального анализа"""
        signals = []
        risk_factors = []
        
        try:
            # Анализ объемов и ликвидности
            volume_signals = self._analyze_volume_metrics(ticker_data)
            signals.extend(volume_signals)
            
            # Анализ ставки финансирования
            funding_signals = self._analyze_funding_rate(funding_rate, symbol)
            signals.extend(funding_signals)
            
            # Анализ открытого интереса
            oi_signals = self._analyze_open_interest(open_interest_df, symbol)
            signals.extend(oi_signals)
            
            # Анализ цены и волатильности
            price_signals = self._analyze_price_metrics(ticker_data)
            signals.extend(price_signals)
            
            # Анализ рыночных условий
            market_signals = self._analyze_market_conditions(ticker_data)
            signals.extend(market_signals)
            
            # Определение рисков
            risk_factors = self._identify_risk_factors(signals, ticker_data)
            
            # Общий сигнал и настроение рынка
            overall_signal, confidence = self._calculate_overall_fundamental_signal(signals)
            market_sentiment = self._determine_market_sentiment(signals)
            
        except Exception as e:
            logger.error(f"Ошибка в фундаментальном анализе для {symbol}: {e}")
            signals = []
            risk_factors = ["Ошибка получения данных"]
            overall_signal = 'NEUTRAL'
            confidence = 0.0
            market_sentiment = 'UNKNOWN'
        
        return FundamentalAnalysisResult(
            symbol=symbol,
            timestamp=pd.Timestamp.now(),
            signals=signals,
            overall_signal=overall_signal,
            confidence=confidence,
            risk_factors=risk_factors,
            market_sentiment=market_sentiment
        )
    
    def _analyze_volume_metrics(self, ticker_data: Dict) -> List[FundamentalSignal]:
        """Анализ объемных метрик"""
        signals = []
        
        try:
            if not ticker_data:
                return signals
            
            # 24-часовой объем в USDT
            volume_24h = float(ticker_data.get('turnover24h', 0))
            
            if volume_24h >= self.config.MIN_VOLUME_USDT:
                # Высокий объем - хороший сигнал для ликвидности
                if volume_24h >= self.config.MIN_VOLUME_USDT * 10:
                    signal = 'BUY'
                    strength = 0.8
                    impact = 'HIGH'
                    description = f"Очень высокий объем: ${volume_24h:,.0f}"
                elif volume_24h >= self.config.MIN_VOLUME_USDT * 5:
                    signal = 'BUY'
                    strength = 0.6
                    impact = 'MEDIUM'
                    description = f"Высокий объем: ${volume_24h:,.0f}"
                else:
                    signal = 'NEUTRAL'
                    strength = 0.3
                    impact = 'LOW'
                    description = f"Достаточный объем: ${volume_24h:,.0f}"
            else:
                signal = 'SELL'
                strength = 0.7
                impact = 'HIGH'
                description = f"Низкий объем: ${volume_24h:,.0f}"
            
            signals.append(FundamentalSignal(
                name='Volume_24h',
                value=volume_24h,
                signal=signal,
                strength=strength,
                description=description,
                impact=impact
            ))
            
            # Изменение цены за 24 часа
            price_change_24h = float(ticker_data.get('price24hPcnt', 0))
            
            if abs(price_change_24h) > 0.05:  # Более 5% изменения
                if price_change_24h > 0.1:  # Рост более 10%
                    signal = 'SELL'  # Возможная коррекция
                    strength = min(price_change_24h / 0.2, 1.0)
                    impact = 'HIGH'
                elif price_change_24h < -0.1:  # Падение более 10%
                    signal = 'BUY'  # Возможная покупка на падении
                    strength = min(abs(price_change_24h) / 0.2, 1.0)
                    impact = 'HIGH'
                else:
                    signal = 'NEUTRAL'
                    strength = 0.3
                    impact = 'MEDIUM'
            else:
                signal = 'NEUTRAL'
                strength = 0.1
                impact = 'LOW'
            
            signals.append(FundamentalSignal(
                name='Price_Change_24h',
                value=price_change_24h,
                signal=signal,
                strength=strength,
                description=f"Изменение за 24ч: {price_change_24h*100:.2f}%",
                impact=impact
            ))
            
        except Exception as e:
            logger.error(f"Ошибка в анализе объемных метрик: {e}")
        
        return signals
    
    def _analyze_funding_rate(self, funding_data: Dict, symbol: str) -> List[FundamentalSignal]:
        """Анализ ставки финансирования"""
        signals = []
        
        try:
            if not funding_data:
                return signals
            
            funding_rate = float(funding_data.get('fundingRate', 0))
            
            # Ставка финансирования показывает настроение трейдеров
            if funding_rate > 0.0001:  # Положительная ставка > 0.01%
                if funding_rate > 0.001:  # > 0.1%
                    signal = 'SELL'
                    strength = min(funding_rate / 0.002, 1.0)
                    impact = 'HIGH'
                    description = f"Очень высокая ставка финансирования: {funding_rate*100:.4f}%"
                else:
                    signal = 'SELL'
                    strength = min(funding_rate / 0.001, 1.0)
                    impact = 'MEDIUM'
                    description = f"Высокая ставка финансирования: {funding_rate*100:.4f}%"
                    
            elif funding_rate < -0.0001:  # Отрицательная ставка < -0.01%
                if funding_rate < -0.001:  # < -0.1%
                    signal = 'BUY'
                    strength = min(abs(funding_rate) / 0.002, 1.0)
                    impact = 'HIGH'
                    description = f"Очень низкая ставка финансирования: {funding_rate*100:.4f}%"
                else:
                    signal = 'BUY'
                    strength = min(abs(funding_rate) / 0.001, 1.0)
                    impact = 'MEDIUM'
                    description = f"Низкая ставка финансирования: {funding_rate*100:.4f}%"
            else:
                signal = 'NEUTRAL'
                strength = 0.1
                impact = 'LOW'
                description = f"Нейтральная ставка финансирования: {funding_rate*100:.4f}%"
            
            signals.append(FundamentalSignal(
                name='Funding_Rate',
                value=funding_rate,
                signal=signal,
                strength=strength,
                description=description,
                impact=impact
            ))
            
        except Exception as e:
            logger.error(f"Ошибка в анализе ставки финансирования: {e}")
        
        return signals
    
    def _analyze_open_interest(self, oi_df: pd.DataFrame, symbol: str) -> List[FundamentalSignal]:
        """Анализ открытого интереса"""
        signals = []
        
        try:
            if oi_df.empty or len(oi_df) < 10:
                return signals
            
            # Текущий открытый интерес
            current_oi = oi_df['openInterest'].iloc[-1]
            
            # Тренд открытого интереса за последние 24 часа
            if len(oi_df) >= 24:  # Если есть данные за 24 часа
                oi_24h_ago = oi_df['openInterest'].iloc[-24]
                oi_change = (current_oi - oi_24h_ago) / oi_24h_ago
                
                if oi_change > 0.1:  # Рост OI > 10%
                    signal = 'BUY'
                    strength = min(oi_change / 0.3, 1.0)
                    impact = 'HIGH'
                    description = f"Рост открытого интереса: {oi_change*100:.2f}%"
                elif oi_change < -0.1:  # Падение OI > 10%
                    signal = 'SELL'
                    strength = min(abs(oi_change) / 0.3, 1.0)
                    impact = 'HIGH'
                    description = f"Падение открытого интереса: {oi_change*100:.2f}%"
                else:
                    signal = 'NEUTRAL'
                    strength = 0.2
                    impact = 'MEDIUM'
                    description = f"Стабильный открытый интерес: {oi_change*100:.2f}%"
                
                signals.append(FundamentalSignal(
                    name='Open_Interest_Trend',
                    value=oi_change,
                    signal=signal,
                    strength=strength,
                    description=description,
                    impact=impact
                ))
            
            # Абсолютный размер открытого интереса
            # Высокий OI означает высокий интерес к инструменту
            if current_oi > 0:
                # Нормализуем по размеру (это примерная логика)
                if 'BTC' in symbol:
                    threshold_high = 1000000000  # 1B для BTC
                    threshold_medium = 500000000  # 500M для BTC
                elif 'ETH' in symbol:
                    threshold_high = 500000000   # 500M для ETH
                    threshold_medium = 200000000 # 200M для ETH
                else:
                    threshold_high = 100000000   # 100M для альткоинов
                    threshold_medium = 50000000  # 50M для альткоинов
                
                if current_oi > threshold_high:
                    signal = 'BUY'
                    strength = 0.6
                    impact = 'MEDIUM'
                    description = f"Высокий открытый интерес: ${current_oi:,.0f}"
                elif current_oi > threshold_medium:
                    signal = 'NEUTRAL'
                    strength = 0.3
                    impact = 'LOW'
                    description = f"Средний открытый интерес: ${current_oi:,.0f}"
                else:
                    signal = 'NEUTRAL'
                    strength = 0.1
                    impact = 'LOW'
                    description = f"Низкий открытый интерес: ${current_oi:,.0f}"
                
                signals.append(FundamentalSignal(
                    name='Open_Interest_Size',
                    value=current_oi,
                    signal=signal,
                    strength=strength,
                    description=description,
                    impact=impact
                ))
            
        except Exception as e:
            logger.error(f"Ошибка в анализе открытого интереса: {e}")
        
        return signals
    
    def _analyze_price_metrics(self, ticker_data: Dict) -> List[FundamentalSignal]:
        """Анализ ценовых метрик"""
        signals = []
        
        try:
            if not ticker_data:
                return signals
            
            # Спред bid-ask
            bid = float(ticker_data.get('bid1Price', 0))
            ask = float(ticker_data.get('ask1Price', 0))
            
            if bid > 0 and ask > 0:
                spread = (ask - bid) / bid
                
                if spread < 0.001:  # Спред < 0.1%
                    signal = 'BUY'
                    strength = 0.5
                    impact = 'MEDIUM'
                    description = f"Узкий спред: {spread*100:.3f}%"
                elif spread > 0.005:  # Спред > 0.5%
                    signal = 'SELL'
                    strength = min(spread / 0.01, 1.0)
                    impact = 'HIGH'
                    description = f"Широкий спред: {spread*100:.3f}%"
                else:
                    signal = 'NEUTRAL'
                    strength = 0.2
                    impact = 'LOW'
                    description = f"Нормальный спред: {spread*100:.3f}%"
                
                signals.append(FundamentalSignal(
                    name='Bid_Ask_Spread',
                    value=spread,
                    signal=signal,
                    strength=strength,
                    description=description,
                    impact=impact
                ))
            
            # Максимум и минимум за 24 часа
            high_24h = float(ticker_data.get('highPrice24h', 0))
            low_24h = float(ticker_data.get('lowPrice24h', 0))
            last_price = float(ticker_data.get('lastPrice', 0))
            
            if high_24h > 0 and low_24h > 0 and last_price > 0:
                # Позиция цены в дневном диапазоне
                price_position = (last_price - low_24h) / (high_24h - low_24h)
                
                if price_position > 0.8:  # Цена в верхних 20%
                    signal = 'SELL'
                    strength = (price_position - 0.8) / 0.2
                    impact = 'MEDIUM'
                    description = f"Цена у максимума дня: {price_position*100:.1f}%"
                elif price_position < 0.2:  # Цена в нижних 20%
                    signal = 'BUY'
                    strength = (0.2 - price_position) / 0.2
                    impact = 'MEDIUM'
                    description = f"Цена у минимума дня: {price_position*100:.1f}%"
                else:
                    signal = 'NEUTRAL'
                    strength = 0.1
                    impact = 'LOW'
                    description = f"Цена в середине диапазона: {price_position*100:.1f}%"
                
                signals.append(FundamentalSignal(
                    name='Price_Position_24h',
                    value=price_position,
                    signal=signal,
                    strength=strength,
                    description=description,
                    impact=impact
                ))
            
        except Exception as e:
            logger.error(f"Ошибка в анализе ценовых метрик: {e}")
        
        return signals
    
    def _analyze_market_conditions(self, ticker_data: Dict) -> List[FundamentalSignal]:
        """Анализ рыночных условий"""
        signals = []
        
        try:
            if not ticker_data:
                return signals
            
            # Анализ волатильности на основе диапазона 24ч
            high_24h = float(ticker_data.get('highPrice24h', 0))
            low_24h = float(ticker_data.get('lowPrice24h', 0))
            last_price = float(ticker_data.get('lastPrice', 0))
            
            if high_24h > 0 and low_24h > 0 and last_price > 0:
                volatility = (high_24h - low_24h) / last_price
                
                if volatility > 0.1:  # Волатильность > 10%
                    signal = 'SELL'  # Высокий риск
                    strength = min(volatility / 0.2, 1.0)
                    impact = 'HIGH'
                    description = f"Высокая волатильность: {volatility*100:.2f}%"
                elif volatility < 0.02:  # Волатильность < 2%
                    signal = 'NEUTRAL'  # Низкая активность
                    strength = 0.3
                    impact = 'LOW'
                    description = f"Низкая волатильность: {volatility*100:.2f}%"
                else:
                    signal = 'BUY'  # Умеренная волатильность
                    strength = 0.5
                    impact = 'MEDIUM'
                    description = f"Умеренная волатильность: {volatility*100:.2f}%"
                
                signals.append(FundamentalSignal(
                    name='Market_Volatility',
                    value=volatility,
                    signal=signal,
                    strength=strength,
                    description=description,
                    impact=impact
                ))
            
            # Анализ объемной активности
            volume_24h = float(ticker_data.get('volume24h', 0))
            turnover_24h = float(ticker_data.get('turnover24h', 0))
            
            if volume_24h > 0 and turnover_24h > 0:
                avg_price = turnover_24h / volume_24h
                price_efficiency = abs(last_price - avg_price) / avg_price
                
                if price_efficiency < 0.01:  # Цена близка к средневзвешенной
                    signal = 'BUY'
                    strength = 0.6
                    impact = 'MEDIUM'
                    description = f"Эффективное ценообразование: {price_efficiency*100:.3f}%"
                elif price_efficiency > 0.05:  # Большое отклонение
                    signal = 'SELL'
                    strength = min(price_efficiency / 0.1, 1.0)
                    impact = 'HIGH'
                    description = f"Неэффективное ценообразование: {price_efficiency*100:.3f}%"
                else:
                    signal = 'NEUTRAL'
                    strength = 0.2
                    impact = 'LOW'
                    description = f"Нормальное ценообразование: {price_efficiency*100:.3f}%"
                
                signals.append(FundamentalSignal(
                    name='Price_Efficiency',
                    value=price_efficiency,
                    signal=signal,
                    strength=strength,
                    description=description,
                    impact=impact
                ))
            
        except Exception as e:
            logger.error(f"Ошибка в анализе рыночных условий: {e}")
        
        return signals
    
    def _identify_risk_factors(self, signals: List[FundamentalSignal], ticker_data: Dict) -> List[str]:
        """Определение факторов риска"""
        risk_factors = []
        
        try:
            # Проверка на низкую ликвидность
            volume_24h = float(ticker_data.get('turnover24h', 0))
            if volume_24h < self.config.MIN_VOLUME_USDT:
                risk_factors.append(f"Низкая ликвидность: ${volume_24h:,.0f}")
            
            # Проверка на высокую волатильность
            high_24h = float(ticker_data.get('highPrice24h', 0))
            low_24h = float(ticker_data.get('lowPrice24h', 0))
            last_price = float(ticker_data.get('lastPrice', 0))
            
            if high_24h > 0 and low_24h > 0 and last_price > 0:
                volatility = (high_24h - low_24h) / last_price
                if volatility > 0.15:  # Волатильность > 15%
                    risk_factors.append(f"Экстремальная волатильность: {volatility*100:.1f}%")
            
            # Проверка на экстремальные ставки финансирования
            for signal in signals:
                if signal.name == 'Funding_Rate':
                    if abs(signal.value) > 0.002:  # > 0.2%
                        risk_factors.append(f"Экстремальная ставка финансирования: {signal.value*100:.4f}%")
            
            # Проверка на широкий спред
            for signal in signals:
                if signal.name == 'Bid_Ask_Spread':
                    if signal.value > 0.01:  # > 1%
                        risk_factors.append(f"Широкий спред: {signal.value*100:.3f}%")
            
            # Проверка на резкие движения цены
            price_change_24h = float(ticker_data.get('price24hPcnt', 0))
            if abs(price_change_24h) > 0.2:  # > 20%
                risk_factors.append(f"Резкое движение цены: {price_change_24h*100:.1f}%")
            
        except Exception as e:
            logger.error(f"Ошибка при определении факторов риска: {e}")
            risk_factors.append("Ошибка анализа рисков")
        
        return risk_factors
    
    def _calculate_overall_fundamental_signal(self, signals: List[FundamentalSignal]) -> tuple[str, float]:
        """Расчет общего фундаментального сигнала"""
        if not signals:
            return 'NEUTRAL', 0.0
        
        # Веса для различных типов сигналов
        impact_weights = {
            'HIGH': 1.0,
            'MEDIUM': 0.6,
            'LOW': 0.3
        }
        
        buy_score = 0.0
        sell_score = 0.0
        total_weight = 0.0
        
        for signal in signals:
            weight = impact_weights.get(signal.impact, 0.3)
            adjusted_strength = signal.strength * weight
            
            if signal.signal == 'BUY':
                buy_score += adjusted_strength
            elif signal.signal == 'SELL':
                sell_score += adjusted_strength
            
            total_weight += weight
        
        # Нормализация
        if total_weight > 0:
            buy_score = (buy_score / total_weight) * 100
            sell_score = (sell_score / total_weight) * 100
        
        # Определение сигнала
        if buy_score > sell_score + 15:  # Разница минимум 15%
            overall_signal = 'BUY'
            confidence = min(buy_score, 90)
        elif sell_score > buy_score + 15:
            overall_signal = 'SELL'
            confidence = min(sell_score, 90)
        else:
            overall_signal = 'NEUTRAL'
            confidence = max(50 - abs(buy_score - sell_score), 10)
        
        return overall_signal, confidence
    
    def _determine_market_sentiment(self, signals: List[FundamentalSignal]) -> str:
        """Определение настроения рынка"""
        sentiment_scores = {
            'BULLISH': 0,
            'BEARISH': 0,
            'NEUTRAL': 0
        }
        
        for signal in signals:
            if signal.name in ['Funding_Rate', 'Open_Interest_Trend']:
                if signal.signal == 'BUY':
                    sentiment_scores['BULLISH'] += signal.strength # type: ignore
                elif signal.signal == 'SELL':
                    sentiment_scores['BEARISH'] += signal.strength # type: ignore
                else:
                    sentiment_scores['NEUTRAL'] += signal.strength # type: ignore
        
        # Определяем преобладающее настроение
        max_sentiment = max(sentiment_scores, key=sentiment_scores.get) # type: ignore
        
        if sentiment_scores[max_sentiment] > 0.5:
            return max_sentiment
        else:
            return 'NEUTRAL'