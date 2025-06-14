# market_sentiment_analyzer.py - Анализатор общего состояния рынка

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MarketSentiment:
    """Структура для хранения настроения рынка"""
    overall_sentiment: str  # 'BULLISH', 'BEARISH', 'NEUTRAL'
    strength: float  # 0-1
    btc_trend: str  # 'UP', 'DOWN', 'SIDEWAYS'
    volatility_level: str  # 'LOW', 'MEDIUM', 'HIGH', 'EXTREME'
    risk_level: str  # 'LOW', 'MEDIUM', 'HIGH', 'EXTREME'
    altcoin_season: bool
    fear_greed_estimate: int  # 0-100 (упрощенная оценка)
    recommendation: str  # 'TRADE', 'CAUTIOUS', 'AVOID'
    details: Dict

class MarketSentimentAnalyzer:
    """Анализатор общего состояния криптовалютного рынка"""
    
    def __init__(self, config):
        self.config = config
        self.last_analysis = None
        self.btc_cache = {}
        
    def analyze_market_sentiment(self, btc_data: Dict, eth_data: Dict = None) -> MarketSentiment: # type: ignore
        """Основной метод анализа настроения рынка"""
        
        try:
            # Анализируем Bitcoin как основной индикатор
            btc_analysis = self._analyze_btc_sentiment(btc_data)
            
            # Анализируем Ethereum для подтверждения (если доступен)
            eth_analysis = self._analyze_eth_sentiment(eth_data) if eth_data else None
            
            # Определяем общее настроение
            overall_sentiment = self._determine_overall_sentiment(btc_analysis, eth_analysis) # type: ignore
            
            # Определяем уровень риска
            risk_level = self._calculate_risk_level(btc_analysis, eth_analysis) # type: ignore
            
            # Определяем сезон альткоинов
            altcoin_season = self._detect_altcoin_season(btc_analysis, eth_analysis) # type: ignore
            
            # Оценка страха/жадности
            fear_greed = self._estimate_fear_greed(btc_analysis)
            
            # Рекомендация для торговли
            recommendation = self._get_trading_recommendation(
                overall_sentiment, risk_level, btc_analysis
            )
            
            sentiment = MarketSentiment(
                overall_sentiment=overall_sentiment['sentiment'],
                strength=overall_sentiment['strength'],
                btc_trend=btc_analysis['trend'],
                volatility_level=btc_analysis['volatility_level'],
                risk_level=risk_level,
                altcoin_season=altcoin_season,
                fear_greed_estimate=fear_greed,
                recommendation=recommendation,
                details={
                    'btc_analysis': btc_analysis,
                    'eth_analysis': eth_analysis,
                    'timestamp': datetime.now()
                }
            )
            
            self.last_analysis = sentiment
            logger.info(f"Анализ рынка: {sentiment.overall_sentiment} ({sentiment.strength:.2f}), "
                       f"BTC: {sentiment.btc_trend}, Risk: {sentiment.risk_level}, "
                       f"Рекомендация: {sentiment.recommendation}")
            
            return sentiment
            
        except Exception as e:
            logger.error(f"Ошибка анализа настроения рынка: {e}")
            # Возвращаем нейтральное настроение при ошибке
            return MarketSentiment(
                overall_sentiment='NEUTRAL',
                strength=0.5,
                btc_trend='SIDEWAYS',
                volatility_level='MEDIUM',
                risk_level='MEDIUM',
                altcoin_season=False,
                fear_greed_estimate=50,
                recommendation='CAUTIOUS',
                details={'error': str(e)}
            )
    
    def _analyze_btc_sentiment(self, btc_data: Dict) -> Dict:
        """Анализ настроения по Bitcoin"""
        
        analysis = {
            'trend': 'SIDEWAYS',
            'trend_strength': 0.5,
            'volatility': 0.0,
            'volatility_level': 'MEDIUM',
            'volume_trend': 'NEUTRAL',
            'price_momentum': 0.0,
            'support_resistance': 'NEUTRAL'
        }
        
        try:
            # Анализ данных свечей
            if 'klines' in btc_data and not btc_data['klines'].empty:
                klines = btc_data['klines']
                analysis.update(self._analyze_price_action(klines, 'BTC'))
            
            # Анализ тикера
            if 'ticker' in btc_data:
                ticker = btc_data['ticker']
                analysis.update(self._analyze_ticker_sentiment(ticker, 'BTC'))
            
            # Анализ фандинга
            if 'funding' in btc_data:
                funding = btc_data['funding']
                analysis.update(self._analyze_funding_sentiment(funding))
            
            # Анализ открытого интереса
            if 'open_interest' in btc_data and not btc_data['open_interest'].empty:
                oi = btc_data['open_interest']
                analysis.update(self._analyze_oi_sentiment(oi))
                
        except Exception as e:
            logger.error(f"Ошибка анализа BTC данных: {e}")
        
        return analysis
    
    def _analyze_eth_sentiment(self, eth_data: Dict) -> Dict:
        """Анализ настроения по Ethereum"""
        
        analysis = {
            'trend': 'SIDEWAYS',
            'trend_strength': 0.5,
            'volatility': 0.0,
            'btc_correlation': 0.8  # Предполагаемая корреляция
        }
        
        try:
            if 'klines' in eth_data and not eth_data['klines'].empty:
                klines = eth_data['klines']
                analysis.update(self._analyze_price_action(klines, 'ETH'))
            
            if 'ticker' in eth_data:
                ticker = eth_data['ticker']
                analysis.update(self._analyze_ticker_sentiment(ticker, 'ETH'))
                
        except Exception as e:
            logger.error(f"Ошибка анализа ETH данных: {e}")
        
        return analysis
    
    def _analyze_price_action(self, klines: pd.DataFrame, asset: str) -> Dict:
        """Анализ ценового движения"""
        
        analysis = {}
        
        try:
            if len(klines) < 20:
                return analysis
                
            current_price = klines['close'].iloc[-1]
            
            # EMA анализ для определения тренда
            ema_9 = klines['close'].ewm(span=9).mean()
            ema_21 = klines['close'].ewm(span=21).mean()
            ema_50 = klines['close'].ewm(span=50).mean()
            
            # Определение тренда
            if current_price > ema_50.iloc[-1] and ema_9.iloc[-1] > ema_21.iloc[-1]:
                if ema_21.iloc[-1] > ema_50.iloc[-1]:
                    trend = 'UP'
                    trend_strength = min((current_price - ema_50.iloc[-1]) / ema_50.iloc[-1] * 10, 1.0)
                else:
                    trend = 'SIDEWAYS'
                    trend_strength = 0.3
            elif current_price < ema_50.iloc[-1] and ema_9.iloc[-1] < ema_21.iloc[-1]:
                if ema_21.iloc[-1] < ema_50.iloc[-1]:
                    trend = 'DOWN'
                    trend_strength = min((ema_50.iloc[-1] - current_price) / ema_50.iloc[-1] * 10, 1.0)
                else:
                    trend = 'SIDEWAYS'
                    trend_strength = 0.3
            else:
                trend = 'SIDEWAYS'
                trend_strength = 0.1
            
            # Анализ волатильности
            returns = klines['close'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(24)  # Дневная волатильность
            
            if volatility > 0.08:
                volatility_level = 'EXTREME'
            elif volatility > 0.05:
                volatility_level = 'HIGH'
            elif volatility > 0.03:
                volatility_level = 'MEDIUM'
            else:
                volatility_level = 'LOW'
            
            # Моментум
            price_change_24h = (current_price - klines['close'].iloc[-24]) / klines['close'].iloc[-24] if len(klines) >= 24 else 0
            
            analysis.update({
                'trend': trend,
                'trend_strength': trend_strength,
                'volatility': volatility,
                'volatility_level': volatility_level,
                'price_momentum': price_change_24h,
                'current_price': current_price,
                'ema_9': ema_9.iloc[-1],
                'ema_21': ema_21.iloc[-1],
                'ema_50': ema_50.iloc[-1]
            })
            
        except Exception as e:
            logger.error(f"Ошибка анализа price action для {asset}: {e}")
        
        return analysis
    
    def _analyze_ticker_sentiment(self, ticker: Dict, asset: str) -> Dict:
        """Анализ тикера для определения настроения"""
        
        analysis = {}
        
        try:
            # Изменение цены за 24 часа
            price_change_24h = float(ticker.get('price24hPcnt', 0))
            
            # Объем за 24 часа
            volume_24h = float(ticker.get('turnover24h', 0))
            
            # Определение объемного тренда (упрощенно)
            if volume_24h > 1000000000:  # > 1B для BTC, пропорционально для других
                volume_trend = 'HIGH'
            elif volume_24h > 500000000:
                volume_trend = 'MEDIUM'
            else:
                volume_trend = 'LOW'
            
            analysis.update({
                'price_change_24h': price_change_24h,
                'volume_24h': volume_24h,
                'volume_trend': volume_trend
            })
            
        except Exception as e:
            logger.error(f"Ошибка анализа тикера для {asset}: {e}")
        
        return analysis
    
    def _analyze_funding_sentiment(self, funding: Dict) -> Dict:
        """Анализ ставки финансирования"""
        
        analysis = {}
        
        try:
            funding_rate = float(funding.get('fundingRate', 0))
            
            if funding_rate > 0.001:  # > 0.1%
                funding_sentiment = 'EXTREME_BULLISH'  # Слишком много лонгов
            elif funding_rate > 0.0005:  # > 0.05%
                funding_sentiment = 'BULLISH'
            elif funding_rate < -0.001:  # < -0.1%
                funding_sentiment = 'EXTREME_BEARISH'  # Слишком много шортов
            elif funding_rate < -0.0005:  # < -0.05%
                funding_sentiment = 'BEARISH'
            else:
                funding_sentiment = 'NEUTRAL'
            
            analysis.update({
                'funding_rate': funding_rate,
                'funding_sentiment': funding_sentiment
            })
            
        except Exception as e:
            logger.error(f"Ошибка анализа фандинга: {e}")
        
        return analysis
    
    def _analyze_oi_sentiment(self, oi_df: pd.DataFrame) -> Dict:
        """Анализ открытого интереса"""
        
        analysis = {}
        
        try:
            if len(oi_df) < 10:
                return analysis
            
            current_oi = oi_df['openInterest'].iloc[-1]
            
            # Тренд OI за последние 24 часа
            if len(oi_df) >= 24:
                oi_24h_ago = oi_df['openInterest'].iloc[-24]
                oi_change = (current_oi - oi_24h_ago) / oi_24h_ago
                
                if oi_change > 0.1:
                    oi_trend = 'GROWING'
                elif oi_change < -0.1:
                    oi_trend = 'DECLINING'
                else:
                    oi_trend = 'STABLE'
            else:
                oi_trend = 'UNKNOWN'
            
            analysis.update({
                'current_oi': current_oi,
                'oi_trend': oi_trend,
                'oi_change_24h': oi_change if 'oi_change' in locals() else 0
            })
            
        except Exception as e:
            logger.error(f"Ошибка анализа OI: {e}")
        
        return analysis
    
    def _determine_overall_sentiment(self, btc_analysis: Dict, eth_analysis: Dict = None) -> Dict: # type: ignore
        """Определение общего настроения рынка"""
        
        sentiment_score = 0.0
        factors = []
        
        # BTC тренд (50% веса)
        btc_trend = btc_analysis.get('trend', 'SIDEWAYS')
        btc_strength = btc_analysis.get('trend_strength', 0.0)
        
        if btc_trend == 'UP':
            sentiment_score += 0.5 * btc_strength
            factors.append(f"BTC растет (+{btc_strength:.2f})")
        elif btc_trend == 'DOWN':
            sentiment_score -= 0.5 * btc_strength
            factors.append(f"BTC падает (-{btc_strength:.2f})")
        
        # Волатильность (отрицательный фактор)
        volatility_level = btc_analysis.get('volatility_level', 'MEDIUM')
        if volatility_level == 'EXTREME':
            sentiment_score -= 0.3
            factors.append("Экстремальная волатильность (-0.3)")
        elif volatility_level == 'HIGH':
            sentiment_score -= 0.15
            factors.append("Высокая волатильность (-0.15)")
        
        # Фандинг (индикатор перегрева)
        funding_sentiment = btc_analysis.get('funding_sentiment', 'NEUTRAL')
        if funding_sentiment == 'EXTREME_BULLISH':
            sentiment_score -= 0.2  # Перегрев лонгов
            factors.append("Перегрев лонгов (-0.2)")
        elif funding_sentiment == 'EXTREME_BEARISH':
            sentiment_score += 0.15  # Избыток шортов = возможный отскок
            factors.append("Избыток шортов (+0.15)")
        
        # Объемы
        volume_trend = btc_analysis.get('volume_trend', 'MEDIUM')
        if volume_trend == 'HIGH':
            if btc_trend == 'UP':
                sentiment_score += 0.1
                factors.append("Высокие объемы на росте (+0.1)")
            elif btc_trend == 'DOWN':
                sentiment_score -= 0.1
                factors.append("Высокие объемы на падении (-0.1)")
        
        # ETH подтверждение (если доступно)
        if eth_analysis:
            eth_trend = eth_analysis.get('trend', 'SIDEWAYS')
            if eth_trend == btc_trend:
                sentiment_score += 0.1 if btc_trend == 'UP' else -0.1 if btc_trend == 'DOWN' else 0
                factors.append(f"ETH подтверждает тренд BTC")
        
        # Нормализация и определение настроения
        sentiment_score = max(-1.0, min(1.0, sentiment_score))
        
        if sentiment_score > 0.3:
            overall_sentiment = 'BULLISH'
        elif sentiment_score < -0.3:
            overall_sentiment = 'BEARISH'
        else:
            overall_sentiment = 'NEUTRAL'
        
        return {
            'sentiment': overall_sentiment,
            'strength': abs(sentiment_score),
            'score': sentiment_score,
            'factors': factors
        }
    
    def _calculate_risk_level(self, btc_analysis: Dict, eth_analysis: Dict = None) -> str: # type: ignore
        """Расчет уровня риска для торговли"""
        
        risk_score = 0
        
        # Волатильность
        volatility_level = btc_analysis.get('volatility_level', 'MEDIUM')
        volatility_points = {
            'LOW': 0,
            'MEDIUM': 1,
            'HIGH': 2,
            'EXTREME': 3
        }
        risk_score += volatility_points.get(volatility_level, 1)
        
        # Скорость изменения цены
        price_momentum = abs(btc_analysis.get('price_momentum', 0))
        if price_momentum > 0.1:  # > 10% за 24ч
            risk_score += 2
        elif price_momentum > 0.05:  # > 5% за 24ч
            risk_score += 1
        
        # Экстремальные значения фандинга
        funding_sentiment = btc_analysis.get('funding_sentiment', 'NEUTRAL')
        if 'EXTREME' in funding_sentiment:
            risk_score += 2
        elif funding_sentiment in ['BULLISH', 'BEARISH']:
            risk_score += 1
        
        # Определение уровня риска
        if risk_score >= 6:
            return 'EXTREME'
        elif risk_score >= 4:
            return 'HIGH'
        elif risk_score >= 2:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _detect_altcoin_season(self, btc_analysis: Dict, eth_analysis: Dict = None) -> bool: # type: ignore
        """Определение сезона альткоинов"""
        
        # Упрощенная логика определения altcoin season
        btc_trend = btc_analysis.get('trend', 'SIDEWAYS')
        btc_volatility = btc_analysis.get('volatility_level', 'MEDIUM')
        
        # Альткоин сезон обычно наступает когда:
        # 1. BTC в боковике или слабо растет
        # 2. Волатильность BTC не экстремальная
        # 3. ETH показывает силу относительно BTC
        
        conditions_met = 0
        
        if btc_trend in ['SIDEWAYS'] or (btc_trend == 'UP' and btc_analysis.get('trend_strength', 0) < 0.5):
            conditions_met += 1
        
        if btc_volatility in ['LOW', 'MEDIUM']:
            conditions_met += 1
        
        if eth_analysis:
            eth_trend = eth_analysis.get('trend', 'SIDEWAYS')
            if eth_trend == 'UP' and btc_trend != 'UP':
                conditions_met += 1
            elif eth_trend == 'UP' and btc_trend == 'UP':
                conditions_met += 0.5
        
        # Если выполнено 2+ условий из 3, считаем что может быть altcoin season
        return conditions_met >= 2
    
    def _estimate_fear_greed(self, btc_analysis: Dict) -> int:
        """Упрощенная оценка индекса страха/жадности"""
        
        score = 50  # Нейтральное значение
        
        # На основе тренда BTC
        trend = btc_analysis.get('trend', 'SIDEWAYS')
        trend_strength = btc_analysis.get('trend_strength', 0)
        
        if trend == 'UP':
            score += int(trend_strength * 30)  # До +30
        elif trend == 'DOWN':
            score -= int(trend_strength * 40)  # До -40
        
        # На основе волатильности (высокая волатильность = страх)
        volatility_level = btc_analysis.get('volatility_level', 'MEDIUM')
        volatility_penalty = {
            'LOW': 5,      # Низкая волатильность = больше жадности
            'MEDIUM': 0,
            'HIGH': -15,   # Высокая = страх
            'EXTREME': -25 # Экстремальная = паника
        }
        score += volatility_penalty.get(volatility_level, 0)
        
        # На основе фандинга
        funding_sentiment = btc_analysis.get('funding_sentiment', 'NEUTRAL')
        if funding_sentiment == 'EXTREME_BULLISH':
            score += 20  # Жадность лонгов
        elif funding_sentiment == 'EXTREME_BEARISH':
            score -= 20  # Страх, много шортов
        
        # На основе изменения цены
        price_change = btc_analysis.get('price_change_24h', 0)
        score += int(price_change * 100)  # Прямая зависимость от % изменения
        
        # Ограничиваем диапазоном 0-100
        return max(0, min(100, score))
    
    def _get_trading_recommendation(self, overall_sentiment: Dict, risk_level: str, btc_analysis: Dict) -> str:
        """Рекомендация для торговли"""
        
        sentiment = overall_sentiment['sentiment']
        strength = overall_sentiment['strength']
        
        # Очень высокий риск = избегать торговли
        if risk_level == 'EXTREME':
            return 'AVOID'
        
        # Экстремальная волатильность = осторожность
        if btc_analysis.get('volatility_level') == 'EXTREME':
            return 'AVOID'
        
        # Высокий риск = осторожная торговля
        if risk_level == 'HIGH':
            return 'CAUTIOUS'
        
        # Слабые сигналы = осторожность
        if strength < 0.3:
            return 'CAUTIOUS'
        
        # Хорошие условия для торговли
        if risk_level in ['LOW', 'MEDIUM'] and strength >= 0.4:
            return 'TRADE'
        
        # По умолчанию - осторожность
        return 'CAUTIOUS'
    
    def should_trade_altcoin(self, symbol: str, category: str) -> Tuple[bool, str]:
        """Определение, стоит ли торговать альткоин в текущих условиях"""
        
        if not self.last_analysis:
            return True, "Нет данных о рынке"
        
        sentiment = self.last_analysis
        
        # Проверяем общую рекомендацию
        if sentiment.recommendation == 'AVOID':
            return False, f"Рыночные условия неблагоприятны: {sentiment.risk_level} риск"
        
        # Для мемкоинов и новых проектов - менее строгие ограничения
        if category in ['meme', 'emerging']:
            if sentiment.recommendation == 'CAUTIOUS' and sentiment.risk_level != 'EXTREME':
                return True, "Мемкоин/новый проект - разрешена осторожная торговля"
            elif sentiment.recommendation == 'TRADE':
                return True, "Хорошие условия для мемкоина/нового проекта"
            else:
                return False, f"Слишком рискованно даже для {category}"
        
        # Для основных активов
        if category == 'major':
            # Топовые активы можно торговать даже при осторожности
            if sentiment.recommendation in ['TRADE', 'CAUTIOUS']:
                return True, f"Разрешена торговля топового актива ({sentiment.recommendation})"
            else:
                return False, "Неблагоприятные условия даже для топовых активов"
        
        # Для остальных категорий
        if sentiment.recommendation == 'TRADE':
            return True, "Хорошие рыночные условия"
        elif sentiment.recommendation == 'CAUTIOUS':
            # В осторожном режиме торгуем только при низком риске и не медвежьем рынке
            if sentiment.risk_level in ['LOW', 'MEDIUM'] and sentiment.overall_sentiment != 'BEARISH':
                return True, "Осторожная торговля разрешена"
            else:
                return False, "Осторожный режим + дополнительные риски"
        else:
            return False, f"Общая рекомендация: {sentiment.recommendation}"
    
    def get_market_summary(self) -> str:
        """Получение краткой сводки о состоянии рынка"""
        
        if not self.last_analysis:
            return "❓ Данные о рынке отсутствуют"
        
        sentiment = self.last_analysis
        
        # Эмодзи для настроения
        sentiment_emoji = {
            'BULLISH': '🟢',
            'BEARISH': '🔴', 
            'NEUTRAL': '🟡'
        }
        
        # Эмодзи для риска
        risk_emoji = {
            'LOW': '🟢',
            'MEDIUM': '🟡',
            'HIGH': '🟠',
            'EXTREME': '🔴'
        }
        
        # Эмодзи для рекомендации
        rec_emoji = {
            'TRADE': '✅',
            'CAUTIOUS': '⚠️',
            'AVOID': '❌'
        }
        
        altcoin_status = "🎯 Сезон альткоинов" if sentiment.altcoin_season else "🔵 Доминация BTC"
        
        summary = f"""📊 <b>Состояние рынка</b>

{sentiment_emoji.get(sentiment.overall_sentiment, '❓')} <b>Настроение:</b> {sentiment.overall_sentiment} ({sentiment.strength:.2f})
📈 <b>BTC тренд:</b> {sentiment.btc_trend}
🌊 <b>Волатильность:</b> {sentiment.volatility_level}
{risk_emoji.get(sentiment.risk_level, '❓')} <b>Риск:</b> {sentiment.risk_level}
😨 <b>Страх/Жадность:</b> {sentiment.fear_greed_estimate}/100
{altcoin_status}

{rec_emoji.get(sentiment.recommendation, '❓')} <b>Рекомендация:</b> {sentiment.recommendation}"""

        return summary
    
    def is_market_data_fresh(self, max_age_minutes: int = 30) -> bool:
        """Проверка актуальности данных о рынке"""
        
        if not self.last_analysis:
            return False
        
        analysis_time = self.last_analysis.details.get('timestamp')
        if not analysis_time:
            return False
        
        age = datetime.now() - analysis_time
        return age.total_seconds() < (max_age_minutes * 60)