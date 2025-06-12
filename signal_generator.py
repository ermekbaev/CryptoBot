# enhanced_signal_generator.py - Улучшенный генератор сигналов

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime
from dataclasses import dataclass

from config import TradingConfig, INDICATOR_WEIGHTS, PAIR_SPECIFIC_SETTINGS
from technical_analysis import TechnicalAnalyzer, TechnicalAnalysisResult
from fundamental_analysis import FundamentalAnalyzer, FundamentalAnalysisResult
from enhanced_telegram_bot import TradingSignal

logger = logging.getLogger(__name__)

class SignalGenerator:
    """Улучшенный генератор сигналов с поддержкой категорий"""
    
    def __init__(self, config: TradingConfig):
        self.config = config
        self.technical_analyzer = TechnicalAnalyzer(config)
        self.fundamental_analyzer = FundamentalAnalyzer(config)
        
    def generate_signal(self, 
                       symbol: str,
                       market_data: Dict,
                       account_balance: float) -> Optional[TradingSignal]:
        """Генерация торгового сигнала с учетом категории пары"""
        
        try:
            # Определяем категорию пары
            pair_category = self._get_pair_category(symbol)
            logger.info(f"Анализ {symbol} (категория: {pair_category})")
            
            # Получаем специфичные настройки для пары
            pair_settings = PAIR_SPECIFIC_SETTINGS.get(symbol, {})
            
            # Получаем данные для анализа
            klines_data = market_data.get('klines', pd.DataFrame())
            ticker_data = market_data.get('ticker', {})
            funding_data = market_data.get('funding', {})
            oi_data = market_data.get('open_interest', pd.DataFrame())
            
            if klines_data.empty:
                logger.warning(f"Нет данных для анализа {symbol}")
                return None
            
            # Проверяем минимальный объем для категории
            if not self._check_volume_requirements(symbol, ticker_data, pair_category):
                logger.info(f"Недостаточный объем для {symbol} в категории {pair_category}")
                return None
            
            # Проводим технический анализ
            tech_result = self.technical_analyzer.analyze(
                klines_data, symbol, self.config.PRIMARY_TIMEFRAME
            )
            
            # Проводим фундаментальный анализ
            fund_result = self.fundamental_analyzer.analyze(
                symbol, ticker_data, funding_data, oi_data
            )
            
            # Рассчитываем метрики сигнала с учетом категории
            metrics = self._calculate_enhanced_metrics(
                tech_result, fund_result, ticker_data, pair_category, pair_settings
            )
            
            # Проверяем условия для генерации сигнала
            if not self._should_generate_signal_enhanced(
                metrics, tech_result, fund_result, pair_category, pair_settings
            ):
                logger.info(f"Условия для сигнала {symbol} не выполнены")
                return None
            
            # Определяем тип сигнала
            signal_type = self._determine_signal_type_enhanced(
                metrics, tech_result, fund_result, pair_category
            )
            
            if signal_type == 'NEUTRAL':
                return None
            
            # Рассчитываем параметры сделки с учетом категории
            trade_params = self._calculate_trade_parameters_enhanced(
                signal_type, klines_data, tech_result, metrics, 
                account_balance, pair_category, pair_settings
            )
            
            if not trade_params:
                logger.warning(f"Не удалось рассчитать параметры сделки для {symbol}")
                return None
            
            # Создаем торговый сигнал
            signal = self._create_enhanced_trading_signal(
                symbol, signal_type, trade_params, tech_result, 
                fund_result, metrics, pair_category
            )
            
            logger.info(f"Сгенерирован сигнал {signal_type} для {symbol} ({pair_category}) с уверенностью {signal.confidence:.1f}%")
            return signal
            
        except Exception as e:
            logger.error(f"Ошибка при генерации сигнала для {symbol}: {e}")
            return None
    
    def _get_pair_category(self, symbol: str) -> str:
        """Определение категории торговой пары"""
        for category, pairs in self.config.PAIR_CATEGORIES.items():
            if symbol in pairs:
                return category
        return 'other'
    
    def _check_volume_requirements(self, symbol: str, ticker_data: Dict, category: str) -> bool:
        """Проверка минимального объема для категории"""
        if not ticker_data:
            return False
        
        volume_24h = float(ticker_data.get('turnover24h', 0))
        min_volume = self.config.MIN_VOLUMES_BY_CATEGORY.get(category, self.config.MIN_VOLUME_USDT)
        
        # Применяем мультипликатор для специфичных пар
        pair_settings = PAIR_SPECIFIC_SETTINGS.get(symbol, {})
        multiplier = pair_settings.get('min_volume_multiplier', 1.0)
        min_volume *= multiplier
        
        return volume_24h >= min_volume
    
    def _calculate_enhanced_metrics(self, 
                                  tech_result: TechnicalAnalysisResult,
                                  fund_result: FundamentalAnalysisResult,
                                  ticker_data: Dict,
                                  category: str,
                                  pair_settings: Dict) -> Dict:
        """Расчет улучшенных метрик с учетом категории"""
        
        # Базовые метрики
        tech_score = self._calculate_technical_score(tech_result)
        fund_score = self._calculate_fundamental_score(fund_result)
        
        # Весовые коэффициенты по категориям
        category_weights = {
            'major': {'technical': 0.6, 'fundamental': 0.4},      # Больше техники
            'defi': {'technical': 0.7, 'fundamental': 0.3},       # Техника важнее
            'layer1': {'technical': 0.65, 'fundamental': 0.35},   # Баланс
            'meme': {'technical': 0.8, 'fundamental': 0.2},       # Только техника
            'gaming_nft': {'technical': 0.75, 'fundamental': 0.25},
            'emerging': {'technical': 0.5, 'fundamental': 0.5},   # Равный вес
            'other': {'technical': 0.7, 'fundamental': 0.3}
        }
        
        weights = category_weights.get(category, category_weights['other'])
        combined_score = tech_score * weights['technical'] + fund_score * weights['fundamental']
        
        # Расчет специального риска для категории
        category_risk = self._calculate_category_risk(category, ticker_data)
        base_risk = self._calculate_base_risk(tech_result, fund_result, ticker_data)
        
        total_risk = base_risk + category_risk
        
        # Определение рыночных условий
        market_condition = self._determine_market_condition_enhanced(tech_result, ticker_data, category)
        
        # Фактор волатильности с учетом категории
        volatility_factor = self._calculate_volatility_factor_enhanced(ticker_data, category)
        
        return {
            'technical_score': tech_score,
            'fundamental_score': fund_score,
            'combined_score': combined_score,
            'risk_score': total_risk,
            'category_risk': category_risk,
            'market_condition': market_condition,
            'volatility_factor': volatility_factor,
            'category': category,
            'pair_settings': pair_settings
        }
    
    def _calculate_category_risk(self, category: str, ticker_data: Dict) -> float:
        """Расчет риска специфичного для категории"""
        base_risk = 0.0
        
        # Базовый риск по категориям
        category_risk_factors = {
            'major': 0.0,        # Минимальный риск
            'defi': 10.0,        # Средний риск
            'layer1': 15.0,      # Средний+ риск  
            'meme': 40.0,        # Высокий риск
            'gaming_nft': 25.0,  # Средний+ риск
            'emerging': 35.0,    # Высокий риск
            'other': 20.0
        }
        
        base_risk = category_risk_factors.get(category, 20.0)
        
        # Дополнительные факторы риска
        try:
            price_change_24h = abs(float(ticker_data.get('price24hPcnt', 0)))
            
            # Для мемкоинов высокая волатильность - норма
            if category == 'meme':
                if price_change_24h > 0.5:  # > 50%
                    base_risk += 30
                elif price_change_24h > 0.3:  # > 30%
                    base_risk += 15
            else:
                # Для остальных - риск
                if price_change_24h > 0.2:  # > 20%
                    base_risk += 25
                elif price_change_24h > 0.1:  # > 10%
                    base_risk += 10
            
        except Exception:
            base_risk += 10  # Риск неопределенности
        
        return min(base_risk, 100)
    
    def _should_generate_signal_enhanced(self, 
                                       metrics: Dict,
                                       tech_result: TechnicalAnalysisResult,
                                       fund_result: FundamentalAnalysisResult,
                                       category: str,
                                       pair_settings: Dict) -> bool:
        """Улучшенная проверка условий генерации сигнала"""
        
        # Минимальный уровень уверенности по категориям
        category_min_confidence = {
            'major': 70.0,
            'defi': 75.0,
            'layer1': 75.0,
            'meme': 85.0,       # Выше требования для мемов
            'gaming_nft': 80.0,
            'emerging': 85.0,   # Выше для новых проектов
            'other': 75.0
        }
        
        # Используем настройки пары или категории
        min_confidence = pair_settings.get(
            'min_confidence', 
            category_min_confidence.get(category, self.config.MIN_CONFIDENCE_LEVEL)
        )
        
        # Проверяем уверенность
        max_confidence = max(tech_result.confidence, fund_result.confidence)
        if max_confidence < min_confidence:
            logger.debug(f"Недостаточная уверенность: {max_confidence} < {min_confidence}")
            return False
        
        # Максимальный риск по категориям
        category_max_risk = {
            'major': 60.0,
            'defi': 70.0,
            'layer1': 70.0,
            'meme': 80.0,       # Допускаем больший риск для мемов
            'gaming_nft': 75.0,
            'emerging': 80.0,
            'other': 70.0
        }
        
        max_risk = category_max_risk.get(category, 70.0)
        if metrics['risk_score'] > max_risk:
            logger.debug(f"Слишком высокий риск: {metrics['risk_score']} > {max_risk}")
            return False
        
        # Проверяем силу сигнала
        min_signal_strength = 25 if category in ['meme', 'emerging'] else 20
        if abs(metrics['combined_score']) < min_signal_strength:
            logger.debug(f"Слабый сигнал: {abs(metrics['combined_score'])} < {min_signal_strength}")
            return False
        
        # Проверяем волатильность
        volatility_threshold = pair_settings.get('volatility_threshold', 0.15)
        if category == 'meme':
            volatility_threshold = 0.25  # Для мемов выше порог
        
        if metrics['volatility_factor'] > volatility_threshold * 100:
            logger.debug(f"Слишком высокая волатильность: {metrics['volatility_factor']}")
            return False
        
        return True
    
    def _calculate_trade_parameters_enhanced(self, 
                                           signal_type: str,
                                           klines_data: pd.DataFrame,
                                           tech_result: TechnicalAnalysisResult,
                                           metrics: Dict,
                                           account_balance: float,
                                           category: str,
                                           pair_settings: Dict) -> Optional[Dict]:
        """Улучшенный расчет параметров сделки"""
        
        try:
            current_price = klines_data['close'].iloc[-1]
            
            # Определяем плечо с учетом категории
            max_leverage_by_category = {
                'major': 10,
                'defi': 5,
                'layer1': 5,
                'meme': 3,      # Ограничиваем плечо для мемов
                'gaming_nft': 5,
                'emerging': 2,  # Минимальное плечо для новых
                'other': 5
            }
            
            category_max_leverage = max_leverage_by_category.get(category, 5)
            pair_max_leverage = pair_settings.get('max_leverage', category_max_leverage)
            
            leverage = min(
                self._calculate_optimal_leverage(metrics),
                pair_max_leverage,
                self.config.MAX_LEVERAGE
            )
            
            # Рассчитываем размер позиции с учетом категории
            category_risk_multipliers = {
                'major': 1.0,
                'defi': 0.8,
                'layer1': 0.8,
                'meme': 0.5,      # Уменьшаем позицию для мемов
                'gaming_nft': 0.7,
                'emerging': 0.4,  # Минимальная позиция для новых
                'other': 0.8
            }
            
            risk_multiplier = category_risk_multipliers.get(category, 0.8)
            risk_amount = account_balance * (self.config.MAX_RISK_PER_TRADE / 100) * risk_multiplier
            
            # Определяем стоп-лосс
            stop_loss = self._calculate_stop_loss_enhanced(
                signal_type, current_price, tech_result, klines_data, category
            )
            
            if stop_loss == 0:
                return None
            
            # Рассчитываем размер позиции на основе стоп-лосса
            if signal_type == 'BUY':
                stop_distance = current_price - stop_loss
            else:
                stop_distance = stop_loss - current_price
            
            stop_distance_pct = stop_distance / current_price
            
            # Проверяем разумность стоп-лосса
            max_stop_distance = {
                'major': 0.08,    # 8% для топовых
                'defi': 0.10,     # 10% для DeFi
                'layer1': 0.10,   # 10% для Layer 1
                'meme': 0.15,     # 15% для мемов
                'gaming_nft': 0.12,
                'emerging': 0.15, # 15% для новых
                'other': 0.10
            }
            
            if stop_distance_pct <= 0 or stop_distance_pct > max_stop_distance.get(category, 0.10):
                logger.debug(f"Неподходящий стоп-лосс: {stop_distance_pct*100:.2f}%")
                return None
            
            # Размер позиции с учетом плеча
            position_size = (risk_amount / stop_distance_pct) * leverage
            
            # Ограничиваем размер позиции
            max_position_pct = {
                'major': 0.15,    # 15% депозита с плечом
                'defi': 0.12,
                'layer1': 0.12,
                'meme': 0.08,     # 8% для мемов
                'gaming_nft': 0.10,
                'emerging': 0.06, # 6% для новых
                'other': 0.10
            }
            
            max_position = account_balance * leverage * max_position_pct.get(category, 0.10)
            position_size = min(position_size, max_position)
            
            # Рассчитываем тейк-профиты
            take_profits = self._calculate_take_profits_enhanced(
                signal_type, current_price, tech_result, stop_distance, category
            )
            
            return {
                'entry_price': current_price,
                'stop_loss': stop_loss,
                'take_profit_1': take_profits[0],
                'take_profit_2': take_profits[1] if len(take_profits) > 1 else None,
                'leverage': leverage,
                'position_size': position_size,
                'risk_amount': risk_amount,
                'stop_distance_pct': stop_distance_pct,
                'category': category,
                'risk_multiplier': risk_multiplier
            }
            
        except Exception as e:
            logger.error(f"Ошибка при расчете параметров сделки: {e}")
            return None
    
    def _create_enhanced_trading_signal(self, 
                                      symbol: str,
                                      signal_type: str,
                                      trade_params: Dict,
                                      tech_result: TechnicalAnalysisResult,
                                      fund_result: FundamentalAnalysisResult,
                                      metrics: Dict,
                                      category: str) -> TradingSignal:
        """Создание улучшенного торгового сигнала"""
        
        # Комбинированная уверенность с учетом категории
        weights = self._get_category_weights(category)
        combined_confidence = (
            tech_result.confidence * weights['technical'] + 
            fund_result.confidence * weights['fundamental']
        )
        
        # Корректируем уверенность на основе риска
        risk_penalty = metrics['risk_score'] * 0.2
        final_confidence = max(combined_confidence - risk_penalty, 50)
        
        # Создаем описания с учетом категории
        tech_summary = self._create_enhanced_technical_summary(tech_result, category)
        fund_summary = self._create_enhanced_fundamental_summary(fund_result, category)
        
        # Объединяем факторы риска
        all_risk_factors = fund_result.risk_factors.copy()
        
        # Добавляем категориальные риски
        if category == 'meme':
            all_risk_factors.append("⚠️ Мемкоин: высокая волатильность")
        elif category == 'emerging':
            all_risk_factors.append("⚠️ Новый проект: повышенный риск")
        elif category == 'gaming_nft':
            all_risk_factors.append("⚠️ Gaming/NFT: зависимость от трендов")
        
        if metrics['volatility_factor'] > 15:
            all_risk_factors.append(f"⚠️ Высокая волатильность: {metrics['volatility_factor']:.1f}%")
        if metrics['risk_score'] > 40:
            all_risk_factors.append("⚠️ Повышенный уровень риска")
        
        # Добавляем категорию в описание
        category_names = {
            'major': '🔵 Топ криптовалюта',
            'defi': '🟣 DeFi токен',
            'layer1': '🟢 Layer 1 блокчейн',
            'meme': '🟡 Мемкоин',
            'gaming_nft': '🎮 Gaming/NFT',
            'emerging': '🆕 Новый проект',
            'other': '⚪ Альткоин'
        }
        
        category_description = category_names.get(category, '⚪ Альткоин')
        
        return TradingSignal(
            symbol=symbol,
            signal_type=signal_type,
            entry_price=trade_params['entry_price'],
            stop_loss=trade_params['stop_loss'],
            take_profit_1=trade_params['take_profit_1'],
            take_profit_2=trade_params['take_profit_2'],
            leverage=trade_params['leverage'],
            confidence=final_confidence,
            risk_amount=trade_params['risk_amount'],
            position_size=trade_params['position_size'],
            technical_summary=tech_summary,
            fundamental_summary=f"{category_description} | {fund_summary}",
            risk_factors=all_risk_factors,
            timestamp=datetime.now()
        )
    
    def _get_category_weights(self, category: str) -> Dict[str, float]:
        """Получение весов для категории"""
        category_weights = {
            'major': {'technical': 0.6, 'fundamental': 0.4},
            'defi': {'technical': 0.7, 'fundamental': 0.3},
            'layer1': {'technical': 0.65, 'fundamental': 0.35},
            'meme': {'technical': 0.8, 'fundamental': 0.2},
            'gaming_nft': {'technical': 0.75, 'fundamental': 0.25},
            'emerging': {'technical': 0.5, 'fundamental': 0.5},
            'other': {'technical': 0.7, 'fundamental': 0.3}
        }
        return category_weights.get(category, category_weights['other'])
    
    def _calculate_stop_loss_enhanced(self, 
                                    signal_type: str,
                                    current_price: float,
                                    tech_result: TechnicalAnalysisResult,
                                    klines_data: pd.DataFrame,
                                    category: str) -> float:
        """Улучшенный расчет стоп-лосса с учетом категории"""
        
        # Базовый ATR
        try:
            high_low = klines_data['high'] - klines_data['low']
            atr = high_low.rolling(14).mean().iloc[-1]
            if pd.isna(atr):
                atr = current_price * 0.02
        except:
            atr = current_price * 0.02
        
        # Мультипликаторы ATR по категориям
        atr_multipliers = {
            'major': 1.5,      # Консервативно
            'defi': 2.0,       # Средне
            'layer1': 2.0,     # Средне
            'meme': 3.0,       # Широко для мемов
            'gaming_nft': 2.5, # Широко
            'emerging': 3.0,   # Широко для новых
            'other': 2.0
        }
        
        atr_multiplier = atr_multipliers.get(category, 2.0)
        
        # Базовый стоп-лосс
        if signal_type == 'BUY':
            stop_loss = current_price - (atr * atr_multiplier)
            
            # Используем ближайший уровень поддержки
            if tech_result.support_levels:
                nearest_support = max([s for s in tech_result.support_levels if s < current_price], default=0)
                if nearest_support > 0:
                    support_stop = nearest_support - (atr * 0.5)
                    stop_loss = max(stop_loss, support_stop)
                    
        else:  # SELL
            stop_loss = current_price + (atr * atr_multiplier)
            
            # Используем ближайший уровень сопротивления
            if tech_result.resistance_levels:
                nearest_resistance = min([r for r in tech_result.resistance_levels if r > current_price], default=float('inf'))
                if nearest_resistance != float('inf'):
                    resistance_stop = nearest_resistance + (atr * 0.5)
                    stop_loss = min(stop_loss, resistance_stop)
        
        return stop_loss
        
    def _calculate_take_profits_enhanced(self, 
                                    signal_type: str,
                                    current_price: float,
                                    tech_result: TechnicalAnalysisResult,
                                    stop_distance: float,
                                    category: str) -> List[float]:
        """ИСПРАВЛЕННЫЙ расчет тейк-профитов с учетом категории"""
        
        # Соотношения риск/прибыль по категориям
        risk_reward_ratios = {
            'major': (2.0, 3.5),      # Консервативно
            'defi': (2.5, 4.0),       # Средне
            'layer1': (2.5, 4.0),     # Средне
            'meme': (1.5, 2.5),       # Быстрые прибыли для мемов
            'gaming_nft': (2.0, 3.0), # Средне-быстро
            'emerging': (1.8, 3.0),   # Осторожно
            'other': (2.0, 3.5)
        }
        
        rr1, rr2 = risk_reward_ratios.get(category, (2.0, 3.5))
        
        take_profits = []
        
        if signal_type == 'BUY':
            # ДЛЯ ПОКУПКИ: TP должен быть ВЫШЕ цены входа
            tp1 = current_price + (stop_distance * rr1)
            tp2 = current_price + (stop_distance * rr2)
            
            # Корректируем на основе уровней сопротивления
            if tech_result.resistance_levels:
                available_resistances = [r for r in tech_result.resistance_levels if r > current_price]
                if available_resistances:
                    available_resistances = sorted(available_resistances)
                    
                    # Первый TP - ближайшее сопротивление или расчетное значение
                    if len(available_resistances) >= 1:
                        nearest_resistance = available_resistances[0]
                        # Используем минимум из расчетного TP и сопротивления (с небольшим отступом)
                        take_profits.append(min(tp1, nearest_resistance * 0.995))
                    else:
                        take_profits.append(tp1)
                    
                    # Второй TP - следующее сопротивление или расчетное значение
                    if len(available_resistances) >= 2:
                        second_resistance = available_resistances[1]
                        take_profits.append(min(tp2, second_resistance * 0.995))
                    elif len(take_profits) == 1:
                        take_profits.append(tp2)
                else:
                    take_profits = [tp1, tp2]
            else:
                take_profits = [tp1, tp2]
                
        else:  # SELL
            # ДЛЯ ПРОДАЖИ: TP должен быть НИЖЕ цены входа
            tp1 = current_price - (stop_distance * rr1)
            tp2 = current_price - (stop_distance * rr2)
            
            # Корректируем на основе уровней поддержки
            if tech_result.support_levels:
                available_supports = [s for s in tech_result.support_levels if s < current_price]
                if available_supports:
                    available_supports = sorted(available_supports, reverse=True)
                    
                    # Первый TP - ближайшая поддержка или расчетное значение
                    if len(available_supports) >= 1:
                        nearest_support = available_supports[0]
                        take_profits.append(max(tp1, nearest_support * 1.005))
                    else:
                        take_profits.append(tp1)
                    
                    # Второй TP - следующая поддержка или расчетное значение
                    if len(available_supports) >= 2:
                        second_support = available_supports[1]
                        take_profits.append(max(tp2, second_support * 1.005))
                    elif len(take_profits) == 1:
                        take_profits.append(tp2)
                else:
                    take_profits = [tp1, tp2]
            else:
                take_profits = [tp1, tp2]
        
        # ПРОВЕРКА КОРРЕКТНОСТИ (важно!)
        if signal_type == 'BUY':
            # Для покупки все TP должны быть выше цены входа
            take_profits = [tp for tp in take_profits if tp > current_price]
            if not take_profits:
                # Если после фильтрации ничего не осталось, используем простые расчетные значения
                take_profits = [
                    current_price + (stop_distance * rr1),
                    current_price + (stop_distance * rr2)
                ]
        else:
            # Для продажи все TP должны быть ниже цены входа
            take_profits = [tp for tp in take_profits if tp < current_price]
            if not take_profits:
                take_profits = [
                    current_price - (stop_distance * rr1),
                    current_price - (stop_distance * rr2)
                ]
        
        # Убеждаемся что есть минимум 2 TP
        if len(take_profits) == 1:
            if signal_type == 'BUY':
                take_profits.append(current_price + (stop_distance * rr2))
            else:
                take_profits.append(current_price - (stop_distance * rr2))
        elif len(take_profits) == 0:
            if signal_type == 'BUY':
                take_profits = [
                    current_price + (stop_distance * rr1),
                    current_price + (stop_distance * rr2)
                ]
            else:
                take_profits = [
                    current_price - (stop_distance * rr1),
                    current_price - (stop_distance * rr2)
                ]
        
        # Сортируем TP правильно
        if signal_type == 'BUY':
            take_profits = sorted(take_profits)  # По возрастанию для покупки
        else:
            take_profits = sorted(take_profits, reverse=True)  # По убыванию для продажи
        
        return take_profits[:2]  # Возвращаем только первые 2
    
    def _create_enhanced_technical_summary(self, tech_result: TechnicalAnalysisResult, category: str) -> str:
        """Создание улучшенного описания технического анализа"""
        
        strong_signals = [s for s in tech_result.signals if s.strength > 0.6]
        
        if not strong_signals:
            return f"Слабые технические сигналы ({category})"
        
        summary_parts = []
        
        # Группируем сигналы по типам
        trend_signals = [s for s in strong_signals if any(ind in s.name for ind in ['EMA', 'MACD', 'ADX'])]
        momentum_signals = [s for s in strong_signals if any(ind in s.name for ind in ['RSI', 'Stochastic', 'Williams'])]
        pattern_signals = [s for s in strong_signals if 'Pattern' in s.name]
        
        if trend_signals:
            trend_direction = 'бычий' if trend_signals[0].signal == 'BUY' else 'медвежий'
            summary_parts.append(f"{trend_direction} тренд")
        
        if momentum_signals:
            momentum_count = len([s for s in momentum_signals if s.signal != 'NEUTRAL'])
            if momentum_count > 0:
                summary_parts.append(f"моментум ({momentum_count} инд.)")
        
        if pattern_signals:
            summary_parts.append("свечные паттерны")
        
        # Добавляем специфику категории
        category_specifics = {
            'meme': "волатильный актив",
            'emerging': "новый проект", 
            'defi': "DeFi протокол",
            'gaming_nft': "Gaming токен"
        }
        
        if category in category_specifics:
            summary_parts.append(category_specifics[category])
        
        return "; ".join(summary_parts) if summary_parts else f"Технические индикаторы ({category})"
    
    def _create_enhanced_fundamental_summary(self, fund_result: FundamentalAnalysisResult, category: str) -> str:
        """Создание улучшенного описания фундаментального анализа"""
        
        strong_signals = [s for s in fund_result.signals if s.strength > 0.5]
        
        if not strong_signals:
            return f"Нейтральные фундаментальные факторы"
        
        summary_parts = []
        
        # Анализируем ключевые факторы
        for signal in strong_signals[:3]:  # Берем топ-3
            if 'Volume' in signal.name:
                summary_parts.append("объемы")
            elif 'Funding' in signal.name:
                funding_direction = 'положительный' if signal.signal == 'BUY' else 'отрицательный'
                summary_parts.append(f"{funding_direction} фандинг")
            elif 'Open_Interest' in signal.name:
                oi_direction = 'растущий' if signal.signal == 'BUY' else 'падающий'
                summary_parts.append(f"{oi_direction} OI")
            elif 'Spread' in signal.name:
                summary_parts.append("ликвидность")
        
        sentiment = fund_result.market_sentiment.lower()
        if sentiment != 'neutral':
            summary_parts.append(f"{sentiment} настроение")
        
        return "; ".join(summary_parts) if summary_parts else "Фундаментальные факторы"
    
    # Вспомогательные методы из оригинального класса
    def _calculate_technical_score(self, tech_result: TechnicalAnalysisResult) -> float:
        """Расчет технического счета"""
        if not tech_result.signals:
            return 0.0
        
        total_score = 0.0
        total_weight = 0.0
        
        for signal in tech_result.signals:
            weight = self._get_signal_weight(signal.name)
            
            if signal.signal == 'BUY':
                signal_value = signal.strength
            elif signal.signal == 'SELL':
                signal_value = -signal.strength
            else:
                signal_value = 0.0
            
            total_score += signal_value * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        normalized_score = (total_score / total_weight) * 100
        return max(-100, min(100, normalized_score))
    
    def _calculate_fundamental_score(self, fund_result: FundamentalAnalysisResult) -> float:
        """Расчет фундаментального счета"""
        if not fund_result.signals:
            return 0.0
        
        total_score = 0.0
        total_weight = 0.0
        
        impact_weights = {'HIGH': 1.0, 'MEDIUM': 0.6, 'LOW': 0.3}
        
        for signal in fund_result.signals:
            weight = impact_weights.get(signal.impact, 0.3)
            
            if signal.signal == 'BUY':
                signal_value = signal.strength
            elif signal.signal == 'SELL':
                signal_value = -signal.strength
            else:
                signal_value = 0.0
            
            total_score += signal_value * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        normalized_score = (total_score / total_weight) * 100
        return max(-100, min(100, normalized_score))
    
    def _calculate_base_risk(self, tech_result: TechnicalAnalysisResult,
                           fund_result: FundamentalAnalysisResult, 
                           ticker_data: Dict) -> float:
        """Базовый расчет риска"""
        risk_factors = 0.0
        
        # Проверяем волатильность
        try:
            high_24h = float(ticker_data.get('highPrice24h', 0))
            low_24h = float(ticker_data.get('lowPrice24h', 0))
            last_price = float(ticker_data.get('lastPrice', 0))
            
            if high_24h > 0 and low_24h > 0 and last_price > 0:
                volatility = (high_24h - low_24h) / last_price
                if volatility > 0.1:
                    risk_factors += volatility * 50
                elif volatility > 0.05:
                    risk_factors += volatility * 25
        except:
            risk_factors += 10
        
        # Проверяем противоречия в сигналах
        if tech_result.confidence > 0 and fund_result.confidence > 0:
            confidence_diff = abs(tech_result.confidence - fund_result.confidence)
            if confidence_diff > 30:
                risk_factors += confidence_diff * 0.5
        
        # Проверяем количество факторов риска
        risk_factors += len(fund_result.risk_factors) * 8
        
        return min(risk_factors, 100)
    
    def _determine_market_condition_enhanced(self, tech_result: TechnicalAnalysisResult, 
                                           ticker_data: Dict, category: str) -> str:
        """Определение рыночных условий с учетом категории"""
        
        # Базовое определение
        trend_signals = [s for s in tech_result.signals if 'EMA' in s.name]
        
        if trend_signals:
            buy_signals = sum(1 for s in trend_signals if s.signal == 'BUY')
            sell_signals = sum(1 for s in trend_signals if s.signal == 'SELL')
            
            if buy_signals > sell_signals * 1.5:
                base_condition = 'TRENDING_UP'
            elif sell_signals > buy_signals * 1.5:
                base_condition = 'TRENDING_DOWN'
            else:
                base_condition = 'RANGING'
        else:
            base_condition = 'NEUTRAL'
        
        # Корректируем для категории
        try:
            high_24h = float(ticker_data.get('highPrice24h', 0))
            low_24h = float(ticker_data.get('lowPrice24h', 0))
            last_price = float(ticker_data.get('lastPrice', 0))
            
            if high_24h > 0 and low_24h > 0 and last_price > 0:
                volatility = (high_24h - low_24h) / last_price
                
                # Для мемкоинов высокая волатильность - норма
                if category == 'meme':
                    if volatility > 0.3:
                        return 'MEME_VOLATILE'
                    elif volatility < 0.05:
                        return 'MEME_QUIET'
                # Для новых проектов
                elif category == 'emerging':
                    if volatility > 0.2:
                        return 'EMERGING_VOLATILE'
                
                # Для остальных
                if volatility > 0.15:
                    return 'VOLATILE'
                elif volatility < 0.03:
                    return 'RANGING'
        except:
            pass
        
        return base_condition
    
    def _calculate_volatility_factor_enhanced(self, ticker_data: Dict, category: str) -> float:
        """Расчет фактора волатильности с учетом категории"""
        try:
            high_24h = float(ticker_data.get('highPrice24h', 0))
            low_24h = float(ticker_data.get('lowPrice24h', 0))
            last_price = float(ticker_data.get('lastPrice', 0))
            
            if high_24h > 0 and low_24h > 0 and last_price > 0:
                volatility = (high_24h - low_24h) / last_price
                
                # Нормализуем по категориям
                category_normalizers = {
                    'major': 2.0,        # Низкая базовая волатильность
                    'defi': 3.0,         # Средняя
                    'layer1': 3.0,       # Средняя
                    'meme': 5.0,         # Высокая базовая волатильность
                    'gaming_nft': 4.0,   # Выше средней
                    'emerging': 5.0,     # Высокая
                    'other': 3.0
                }
                
                normalizer = category_normalizers.get(category, 3.0)
                return min(volatility * 100 / normalizer, 50)
            
            return 5.0
            
        except Exception:
            return 5.0
    
    def _get_signal_weight(self, signal_name: str) -> float:
        """Получение веса для сигнала"""
        for category, weight in INDICATOR_WEIGHTS.items():
            if category.lower() in signal_name.lower():
                return weight
        
        # Специфичные веса для индикаторов
        if 'EMA' in signal_name:
            return 0.15
        elif 'MACD' in signal_name:
            return 0.20
        elif 'RSI' in signal_name:
            return 0.15
        elif 'Pattern' in signal_name:
            return 0.10
        else:
            return 0.05
    
    def _calculate_optimal_leverage(self, metrics: Dict) -> int:
        """Расчет оптимального плеча"""
        base_leverage = 2
        
        # Снижаем плечо при высоком риске
        if metrics['risk_score'] > 50:
            base_leverage = 1
        elif metrics['risk_score'] > 30:
            base_leverage = 2
        else:
            base_leverage = 3
        
        # Снижаем плечо при высокой волатильности
        if metrics['volatility_factor'] > 15:
            base_leverage = max(1, base_leverage - 1)
        
        # Увеличиваем плечо при сильном сигнале
        if abs(metrics['combined_score']) > 60:
            base_leverage = min(5, base_leverage + 1)
        
        return base_leverage
    
    def _determine_signal_type_enhanced(self, 
                                      metrics: Dict,
                                      tech_result: TechnicalAnalysisResult,
                                      fund_result: FundamentalAnalysisResult,
                                      category: str) -> str:
        """Определение типа сигнала с учетом категории"""
        
        # Пороги для разных категорий
        category_thresholds = {
            'major': 15,        # Консервативно
            'defi': 18,         # Средне
            'layer1': 18,       # Средне
            'meme': 22,         # Требуем сильный сигнал
            'gaming_nft': 20,   # Выше среднего
            'emerging': 22,     # Требуем сильный сигнал
            'other': 18
        }
        
        threshold = category_thresholds.get(category, 25)
        
        if metrics['combined_score'] > threshold:
            return 'BUY'
        elif metrics['combined_score'] < -threshold:
            return 'SELL'
        else:
            return 'NEUTRAL'