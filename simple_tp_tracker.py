# simple_tp_tracker.py - Простое отслеживание времени достижения TP

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import aiohttp

logger = logging.getLogger(__name__)

@dataclass
class TPTrackingData:
    """Данные для отслеживания Take Profit"""
    signal_id: str
    symbol: str
    signal_type: str  # BUY/SELL
    entry_price: float
    take_profit_1: float
    take_profit_2: Optional[float]
    stop_loss: float
    confidence: float
    start_time: datetime
    
    # Результаты отслеживания
    tp1_reached: bool = False
    tp2_reached: bool = False
    sl_hit: bool = False
    
    tp1_time: Optional[datetime] = None
    tp2_time: Optional[datetime] = None
    sl_time: Optional[datetime] = None
    
    max_profit_reached: float = 0.0
    max_loss_reached: float = 0.0
    
    # Статус
    is_active: bool = True
    final_result: str = "PENDING"  # PENDING, TP1_HIT, TP2_HIT, SL_HIT, EXPIRED

class SimpleTakeProfitTracker:
    """Простой трекер времени достижения Take Profit"""
    
    def __init__(self, config, bybit_api):
        self.config = config
        self.bybit_api = bybit_api
        self.tracking_signals = {}  # Dict[signal_id, TPTrackingData]
        self.check_interval = 60  # Проверяем каждую минуту
        self.max_tracking_hours = 72  # Отслеживаем максимум 72 часа
        
        # Файл для сохранения результатов
        self.results_file = "tp_tracking_results.json"
        self.completed_signals = []
        
        # Запускаем фоновую задачу
        self.tracking_task = None
        
    async def start_tracking(self):
        """Запуск фонового отслеживания"""
        if self.tracking_task is None:
            self.tracking_task = asyncio.create_task(self._tracking_loop())
            logger.info("📊 Запуск отслеживания Take Profit")
    
    async def stop_tracking(self):
        """Остановка отслеживания"""
        if self.tracking_task:
            self.tracking_task.cancel()
            await self._save_results()
            logger.info("⏹️ Остановка отслеживания Take Profit")
    
    def add_signal_for_tracking(self, signal):
        """Добавление сигнала для отслеживания"""
        
        try:
            signal_id = f"{signal.symbol}_{int(signal.timestamp.timestamp())}"
            
            tracking_data = TPTrackingData(
                signal_id=signal_id,
                symbol=signal.symbol,
                signal_type=signal.signal_type,
                entry_price=signal.entry_price,
                take_profit_1=signal.take_profit_1,
                take_profit_2=signal.take_profit_2,
                stop_loss=signal.stop_loss,
                confidence=signal.confidence,
                start_time=signal.timestamp
            )
            
            self.tracking_signals[signal_id] = tracking_data
            
            logger.info(f"📊 Начато отслеживание {signal_id}: "
                       f"{signal.signal_type} {signal.symbol} @ {signal.entry_price}")
            
            return signal_id
            
        except Exception as e:
            logger.error(f"Ошибка добавления сигнала для отслеживания: {e}")
            return None
    
    async def _tracking_loop(self):
        """Основной цикл отслеживания"""
        
        while True:
            try:
                if self.tracking_signals:
                    await self._check_all_signals()
                
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в цикле отслеживания: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _check_all_signals(self):
        """Проверка всех активных сигналов"""
        
        signals_to_remove = []
        
        for signal_id, tracking_data in self.tracking_signals.items():
            try:
                # Проверяем не истек ли срок отслеживания
                elapsed_time = datetime.now() - tracking_data.start_time
                if elapsed_time.total_seconds() > self.max_tracking_hours * 3600:
                    tracking_data.is_active = False
                    tracking_data.final_result = "EXPIRED"
                    signals_to_remove.append(signal_id)
                    continue
                
                # Получаем текущую цену
                current_price = await self._get_current_price(tracking_data.symbol)
                
                if current_price is None:
                    continue
                
                # Проверяем достижение целей
                result_changed = await self._check_targets(tracking_data, current_price)
                
                # Если сигнал завершен, перемещаем в completed
                if not tracking_data.is_active:
                    signals_to_remove.append(signal_id)
                
                # Если есть изменения, логируем
                if result_changed:
                    await self._log_progress(tracking_data, current_price)
                
            except Exception as e:
                logger.error(f"Ошибка проверки сигнала {signal_id}: {e}")
        
        # Убираем завершенные сигналы
        for signal_id in signals_to_remove:
            completed_signal = self.tracking_signals.pop(signal_id)
            self.completed_signals.append(completed_signal)
            await self._log_completion(completed_signal)
        
        # Периодически сохраняем результаты
        if len(self.completed_signals) % 5 == 0 and signals_to_remove:
            await self._save_results()
    
    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Получение текущей цены через API"""
        
        try:
            ticker = self.bybit_api.get_ticker_24hr(symbol)
            
            if ticker and 'lastPrice' in ticker:
                return float(ticker['lastPrice'])
            
            return None
            
        except Exception as e:
            logger.debug(f"Ошибка получения цены {symbol}: {e}")
            return None
    
    async def _check_targets(self, tracking_data: TPTrackingData, current_price: float) -> bool:
        """Проверка достижения целей"""
        
        result_changed = False
        now = datetime.now()
        
        # Рассчитываем прибыль/убыток в процентах
        if tracking_data.signal_type == 'BUY':
            profit_pct = (current_price - tracking_data.entry_price) / tracking_data.entry_price
        else:  # SELL
            profit_pct = (tracking_data.entry_price - current_price) / tracking_data.entry_price
        
        # Обновляем максимальные значения
        if profit_pct > tracking_data.max_profit_reached:
            tracking_data.max_profit_reached = profit_pct
        elif profit_pct < tracking_data.max_loss_reached:
            tracking_data.max_loss_reached = profit_pct
        
        # Проверяем Stop Loss
        if not tracking_data.sl_hit:
            sl_hit = False
            
            if tracking_data.signal_type == 'BUY':
                sl_hit = current_price <= tracking_data.stop_loss
            else:  # SELL
                sl_hit = current_price >= tracking_data.stop_loss
            
            if sl_hit:
                tracking_data.sl_hit = True
                tracking_data.sl_time = now
                tracking_data.is_active = False
                tracking_data.final_result = "SL_HIT"
                result_changed = True
        
        # Проверяем Take Profit 1
        if not tracking_data.tp1_reached and not tracking_data.sl_hit:
            tp1_hit = False
            
            if tracking_data.signal_type == 'BUY':
                tp1_hit = current_price >= tracking_data.take_profit_1
            else:  # SELL
                tp1_hit = current_price <= tracking_data.take_profit_1
            
            if tp1_hit:
                tracking_data.tp1_reached = True
                tracking_data.tp1_time = now
                tracking_data.final_result = "TP1_HIT"
                result_changed = True
        
        # Проверяем Take Profit 2
        if (tracking_data.tp1_reached and 
            tracking_data.take_profit_2 and 
            not tracking_data.tp2_reached and 
            not tracking_data.sl_hit):
            
            tp2_hit = False
            
            if tracking_data.signal_type == 'BUY':
                tp2_hit = current_price >= tracking_data.take_profit_2
            else:  # SELL
                tp2_hit = current_price <= tracking_data.take_profit_2
            
            if tp2_hit:
                tracking_data.tp2_reached = True
                tracking_data.tp2_time = now
                tracking_data.is_active = False
                tracking_data.final_result = "TP2_HIT"
                result_changed = True
        
        # Если достигли только TP1 и нет TP2, закрываем сигнал
        if (tracking_data.tp1_reached and 
            not tracking_data.take_profit_2 and 
            tracking_data.is_active):
            tracking_data.is_active = False
            result_changed = True
        
        return result_changed
    
    async def _log_progress(self, tracking_data: TPTrackingData, current_price: float):
        """Логирование прогресса"""
        
        profit_pct = 0
        if tracking_data.signal_type == 'BUY':
            profit_pct = (current_price - tracking_data.entry_price) / tracking_data.entry_price
        else:
            profit_pct = (tracking_data.entry_price - current_price) / tracking_data.entry_price
        
        elapsed_time = datetime.now() - tracking_data.start_time
        
        logger.info(f"📊 {tracking_data.signal_id}: {profit_pct*100:+.2f}% "
                   f"за {self._format_duration(elapsed_time)}")
    
    async def _log_completion(self, tracking_data: TPTrackingData):
        """Логирование завершения отслеживания"""
        
        total_time = None
        result_msg = ""
        
        if tracking_data.final_result == "TP1_HIT":
            total_time = tracking_data.tp1_time - tracking_data.start_time # type: ignore
            result_msg = f"✅ TP1 достигнут за {self._format_duration(total_time)}"
            
        elif tracking_data.final_result == "TP2_HIT":
            tp1_time = tracking_data.tp1_time - tracking_data.start_time # type: ignore
            tp2_time = tracking_data.tp2_time - tracking_data.start_time # type: ignore
            result_msg = f"🎯 TP1 за {self._format_duration(tp1_time)}, TP2 за {self._format_duration(tp2_time)}"
            
        elif tracking_data.final_result == "SL_HIT":
            total_time = tracking_data.sl_time - tracking_data.start_time # type: ignore
            result_msg = f"❌ Stop Loss за {self._format_duration(total_time)}"
            
        elif tracking_data.final_result == "EXPIRED":
            total_time = timedelta(hours=self.max_tracking_hours)
            result_msg = f"⏱️ Истекло время отслеживания ({self.max_tracking_hours}ч)"
        
        logger.info(f"🏁 {tracking_data.signal_id} завершен: {result_msg}")
        
        # Также можно отправить в Telegram (опционально)
        # await self._send_completion_notification(tracking_data, result_msg)
    
    def _format_duration(self, duration: timedelta) -> str:
        """Форматирование длительности"""
        
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours}ч {minutes}м"
        else:
            return f"{minutes}м"
    
    async def _save_results(self):
        """Сохранение результатов в файл"""
        
        try:
            # Подготавливаем данные для сохранения
            results_data = {
                'saved_at': datetime.now().isoformat(),
                'completed_signals': [],
                'active_signals': []
            }
            
            # Завершенные сигналы
            for signal in self.completed_signals:
                signal_dict = asdict(signal)
                # Конвертируем datetime в строки
                for key, value in signal_dict.items():
                    if isinstance(value, datetime):
                        signal_dict[key] = value.isoformat()
                results_data['completed_signals'].append(signal_dict)
            
            # Активные сигналы
            for signal in self.tracking_signals.values():
                signal_dict = asdict(signal)
                for key, value in signal_dict.items():
                    if isinstance(value, datetime):
                        signal_dict[key] = value.isoformat()
                results_data['active_signals'].append(signal_dict)
            
            # Сохраняем в файл
            with open(self.results_file, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Результаты сохранены: {len(self.completed_signals)} завершенных, "
                       f"{len(self.tracking_signals)} активных")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения результатов: {e}")
    
    def load_results(self):
        """Загрузка результатов из файла"""
        
        try:
            with open(self.results_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Загружаем завершенные сигналы
            self.completed_signals = []
            for signal_data in data.get('completed_signals', []):
                # Конвертируем строки обратно в datetime
                for key, value in signal_data.items():
                    if key.endswith('_time') or key == 'start_time':
                        if value:
                            signal_data[key] = datetime.fromisoformat(value)
                
                signal = TPTrackingData(**signal_data)
                self.completed_signals.append(signal)
            
            # Загружаем активные сигналы
            self.tracking_signals = {}
            for signal_data in data.get('active_signals', []):
                # Конвертируем строки обратно в datetime
                for key, value in signal_data.items():
                    if key.endswith('_time') or key == 'start_time':
                        if value:
                            signal_data[key] = datetime.fromisoformat(value)
                
                signal = TPTrackingData(**signal_data)
                self.tracking_signals[signal.signal_id] = signal
            
            logger.info(f"📂 Загружено: {len(self.completed_signals)} завершенных, "
                       f"{len(self.tracking_signals)} активных сигналов")
            
        except FileNotFoundError:
            logger.info("Файл результатов не найден, начинаем с чистого листа")
        except Exception as e:
            logger.error(f"Ошибка загрузки результатов: {e}")
    
    def get_statistics(self) -> Dict:
        """Получение статистики по времени достижения TP"""
        
        if not self.completed_signals:
            return {
                'total_completed': 0,
                'message': 'Нет завершенных сигналов для анализа'
            }
        
        # Анализ завершенных сигналов
        tp1_times = []
        tp2_times = []
        sl_times = []
        
        results_count = {
            'TP1_HIT': 0,
            'TP2_HIT': 0,
            'SL_HIT': 0,
            'EXPIRED': 0
        }
        
        for signal in self.completed_signals:
            results_count[signal.final_result] += 1
            
            if signal.tp1_time:
                tp1_duration = signal.tp1_time - signal.start_time
                tp1_times.append(tp1_duration.total_seconds() / 60)  # в минутах
            
            if signal.tp2_time:
                tp2_duration = signal.tp2_time - signal.start_time
                tp2_times.append(tp2_duration.total_seconds() / 60)
            
            if signal.sl_time:
                sl_duration = signal.sl_time - signal.start_time
                sl_times.append(sl_duration.total_seconds() / 60)
        
        # Рассчитываем статистику
        stats = {
            'total_completed': len(self.completed_signals),
            'active_tracking': len(self.tracking_signals),
            'results_breakdown': results_count,
            'success_rate': (results_count['TP1_HIT'] + results_count['TP2_HIT']) / len(self.completed_signals) * 100,
        }
        
        if tp1_times:
            stats['tp1_avg_time_minutes'] = sum(tp1_times) / len(tp1_times)
            stats['tp1_fastest_minutes'] = min(tp1_times)
            stats['tp1_slowest_minutes'] = max(tp1_times)
        
        if tp2_times:
            stats['tp2_avg_time_minutes'] = sum(tp2_times) / len(tp2_times)
            stats['tp2_fastest_minutes'] = min(tp2_times)
            stats['tp2_slowest_minutes'] = max(tp2_times)
        
        if sl_times:
            stats['sl_avg_time_minutes'] = sum(sl_times) / len(sl_times)
        
        return stats
    
    def format_statistics_message(self) -> str:
        """Форматирование статистики для отправки в Telegram"""
        
        stats = self.get_statistics()
        
        if stats['total_completed'] == 0:
            return "📊 <b>Статистика Take Profit</b>\n\n❌ Пока нет завершенных сигналов"
        
        message = f"""📊 <b>Статистика времени достижения Take Profit</b>

📈 <b>Общие результаты:</b>
• Завершено сигналов: {stats['total_completed']}
• Активно отслеживается: {stats['active_tracking']}
• Успешность: {stats['success_rate']:.1f}%

🎯 <b>Разбивка результатов:</b>
• TP1 достигнуто: {stats['results_breakdown']['TP1_HIT']}
• TP2 достигнуто: {stats['results_breakdown']['TP2_HIT']}  
• Stop Loss: {stats['results_breakdown']['SL_HIT']}
• Истекло время: {stats['results_breakdown']['EXPIRED']}"""
        
        # Добавляем временную статистику
        if 'tp1_avg_time_minutes' in stats:
            avg_time = stats['tp1_avg_time_minutes']
            fastest = stats['tp1_fastest_minutes'] 
            slowest = stats['tp1_slowest_minutes']
            
            message += f"""

⏱️ <b>Время достижения TP1:</b>
• Среднее: {self._format_minutes(avg_time)}
• Быстрейшее: {self._format_minutes(fastest)}
• Медленнейшее: {self._format_minutes(slowest)}"""
        
        if 'tp2_avg_time_minutes' in stats:
            avg_time = stats['tp2_avg_time_minutes']
            
            message += f"""

🎯 <b>Время достижения TP2:</b>
• Среднее: {self._format_minutes(avg_time)}"""
        
        message += f"\n\n⏰ {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}"
        
        return message
    
    def _format_minutes(self, minutes: float) -> str:
        """Форматирование минут в читаемый вид"""
        
        if minutes < 60:
            return f"{int(minutes)}м"
        elif minutes < 1440:  # меньше суток
            hours = int(minutes // 60)
            mins = int(minutes % 60)
            return f"{hours}ч {mins}м"
        else:  # больше суток
            days = int(minutes // 1440)
            hours = int((minutes % 1440) // 60)
            return f"{days}д {hours}ч"

# ИНТЕГРАЦИЯ В ОСНОВНОЙ БОТ
"""
В enhanced_main.py:

1. В __init__:
   from simple_tp_tracker import SimpleTakeProfitTracker
   
   self.tp_tracker = SimpleTakeProfitTracker(self.config, self.bybit_api)
   
   # Загружаем предыдущие результаты
   self.tp_tracker.load_results()

2. В start():
   # Запускаем отслеживание TP
   await self.tp_tracker.start_tracking()

3. В stop():
   # Останавливаем отслеживание
   await self.tp_tracker.stop_tracking()

4. После генерации сигнала в _analysis_cycle():
   if signal:
       # Отправляем сигнал...
       
       # Добавляем для отслеживания TP
       signal_id = self.tp_tracker.add_signal_for_tracking(signal)

5. Добавить команду для статистики в handle_command():
   elif command == 'tp_stats':
       stats_message = self.tp_tracker.format_statistics_message()
       return await self._send_message(stats_message, chat_id)

Теперь бот будет показывать такие сообщения:
- "📊 ETHUSDT_123456 завершен: ✅ TP1 достигнут за 2ч 15м"
- "🎯 BTCUSDT_789012 завершен: TP1 за 45м, TP2 за 3ч 20м"
- "❌ ADAUSDT_345678 завершен: Stop Loss за 1ч 5м"

И команда /tp_stats покажет общую статистику времени достижения целей!
"""