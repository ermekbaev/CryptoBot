#!/usr/bin/env python3
# enhanced_main.py - ИСПРАВЛЕННАЯ ВЕРСИЯ с обработкой входящих сообщений

import asyncio
import logging
import sys
import signal
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List
import traceback
import aiohttp
import json

# Загружаем переменные окружения
from dotenv import load_dotenv
load_dotenv()

from persistent_config_system import EnhancedTradingConfig as TradingConfig
from bybit_api import BybitAPI
from signal_generator import SignalGenerator
from enhanced_telegram_bot import EnhancedTelegramBot
from simple_tp_tracker import SimpleTakeProfitTracker


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class TelegramPolling:
    """Класс для получения сообщений от Telegram через polling"""
    
    def __init__(self, bot_token: str, message_handler):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.message_handler = message_handler
        self.offset = 0
        self.is_running = False
        
        
    async def start_polling(self):
        """Запуск polling для получения сообщений"""
        self.is_running = True
        logger.info("📡 Запуск Telegram polling...")
        
        while self.is_running:
            try:
                # Получаем обновления от Telegram
                updates = await self._get_updates()
                
                if updates:
                    # Обрабатываем каждое обновление
                    for update in updates:
                        try:
                            await self._process_update(update)
                        except Exception as e:
                            logger.error(f"Ошибка обработки обновления: {e}")
                        
                        # Обновляем offset
                        self.offset = update.get('update_id', 0) + 1
                
                # Небольшая пауза между запросами
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Ошибка в polling: {e}")
                await asyncio.sleep(5)
    
    async def stop_polling(self):
        """Остановка polling"""
        self.is_running = False
        logger.info("⏹️ Остановка Telegram polling...")
    
    async def _get_updates(self):
        """Получение обновлений от Telegram API"""
        try:
            url = f"{self.base_url}/getUpdates"
            params = {
                'offset': self.offset,
                'timeout': 10,
                'allowed_updates': ['message']
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=15) as response: # type: ignore
                    if response.status == 200:
                        data = await response.json()
                        if data.get('ok'):
                            return data.get('result', [])
                    else:
                        logger.error(f"Ошибка Telegram API: {response.status}")
                        
        except asyncio.TimeoutError:
            # Таймаут - это нормально для long polling
            pass
        except Exception as e:
            logger.error(f"Ошибка получения обновлений: {e}")
        
        return []
    
    async def _process_update(self, update: Dict):
        """Обработка одного обновления"""
        try:
            message = update.get('message')
            if not message:
                return
            
            # Логируем входящее сообщение
            chat_id = message.get('chat', {}).get('id')
            text = message.get('text', '')
            username = message.get('from', {}).get('username', 'Unknown')
            
            logger.info(f"📱 Сообщение от {username} (ID: {chat_id}): {text}")
            
            # Передаем сообщение обработчику
            await self.message_handler(message)
            
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")

class EnhancedTradingBot:
    """Расширенный торговый бот с поддержкой множественных чатов"""
    
    def __init__(self):
        self.config = TradingConfig()
        self.bybit_api = BybitAPI(self.config) # type: ignore
        self.signal_generator = SignalGenerator(self.config) # type: ignore
        self.telegram_bot = EnhancedTelegramBot(self.config) # type: ignore
        self.is_running = False
        self.last_analysis_time = {}
        self.tp_tracker = SimpleTakeProfitTracker(self.config, self.bybit_api)
        
        # ДОБАВЛЕНО: Инициализация polling
        self.telegram_polling = TelegramPolling(
            self.config.TELEGRAM_BOT_TOKEN,
            self.handle_telegram_message
        )
        
        # Статистика
        self.daily_stats = {
            'signals_generated': 0,
            'signals_sent': 0,
            'analysis_cycles': 0,
            'errors': 0,
            'messages_received': 0,  # ДОБАВЛЕНО
            'commands_processed': 0,   # ДОБАВЛЕНО
            'tp_tracking_started': 0
        }
        
    async def start(self):
        """Запуск бота"""
        logger.info("🚀 Запуск расширенного торгового бота...")
        
        # Проверяем конфигурацию
        if not await self._validate_configuration():
            logger.error("❌ Ошибка конфигурации")
            return
        
        # Проверяем подключения
        if not await self._validate_connections():
            logger.error("❌ Ошибка подключения к сервисам")
            return
        
        try:
            self.tp_tracker.load_results()
            await self.tp_tracker.start_tracking()
            logger.info("📊 TP трекер запущен")
        except Exception as e:
            logger.error(f"Ошибка запуска TP трекера: {e}")

        # Отправляем уведомление о запуске
        await self.telegram_bot.send_alert(
            f"🚀 Торговый бот запущен!\n📊 Мониторинг {len(self.config.TRADING_PAIRS)} торговых пар\n👥 Подключено {len(self.config.get_authorized_chats())} чатов\n\n💬 Теперь бот принимает команды!",
            "SUCCESS"
        )
        
        # Показываем информацию о подписках
        await self._send_startup_info()
        
        self.is_running = True
        
        try:
            # ИСПРАВЛЕНИЕ: Запускаем polling и анализ параллельно
            await asyncio.gather(
                self.telegram_polling.start_polling(),  # Обработка сообщений
                self._analysis_loop()                    # Анализ рынка
            )
                
        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки")
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
            await self.telegram_bot.send_alert(f"🚨 Критическая ошибка бота: {e}", "ERROR", admin_only=True)
        finally:
            await self.stop()
    
    async def _analysis_loop(self):
        """Основной цикл анализа"""
        while self.is_running:
            try:
                await self._analysis_cycle()
                await asyncio.sleep(60)  # Пауза между циклами
            except Exception as e:
                logger.error(f"Ошибка в цикле анализа: {e}")
                await asyncio.sleep(10)
    
    async def stop(self):
        """Остановка бота"""
        logger.info("⏹️ Остановка торгового бота...")
        self.is_running = False
        
        # Останавливаем polling
        await self.telegram_polling.stop_polling()

        # Останавливаем TP трекер
        try:
            await self.tp_tracker.stop_tracking()
            logger.info("📊 TP трекер остановлен")
        except Exception as e:
            logger.error(f"Ошибка остановки TP трекера: {e}")
        
        # Отправляем статистику за день
        stats_message = f"""📊 Статистика за сессию:
🔄 Циклов анализа: {self.daily_stats['analysis_cycles']}
📈 Сигналов сгенерировано: {self.daily_stats['signals_generated']}
📤 Сигналов отправлено: {self.daily_stats['signals_sent']}
📊 TP отслеживаний: {self.daily_stats['tp_tracking_started']}
📱 Сообщений получено: {self.daily_stats['messages_received']}
⌨️ Команд обработано: {self.daily_stats['commands_processed']}
❌ Ошибок: {self.daily_stats['errors']}"""
        
        await self.telegram_bot.send_alert(f"⏹️ Торговый бот остановлен\n\n{stats_message}", "WARNING")
    
    # НОВЫЙ МЕТОД: Обработка входящих сообщений Telegram
    async def handle_telegram_message(self, message: Dict):
        """Обработка входящих сообщений от Telegram"""
        try:
            self.daily_stats['messages_received'] += 1
            
            chat_id = str(message.get('chat', {}).get('id', ''))
            text = message.get('text', '').strip()
            
            if not chat_id or not text:
                logger.warning("Пустое сообщение или chat_id")
                return
            
            # Обработка команд
            if text.startswith('/'):
                self.daily_stats['commands_processed'] += 1
                
                parts = text[1:].split()
                command = parts[0].lower()
                args = parts[1:] if len(parts) > 1 else []
                
                logger.info(f"🔧 Обработка команды /{command} от {chat_id}")

                # Обработка команд TP трекера
                if command == 'tp_stats':
                    await self._handle_tp_stats_command(chat_id)
                    return
                elif command == 'tp_active':
                    await self._handle_tp_active_command(chat_id)
                    return
                
                await self.telegram_bot.handle_command(chat_id, command, args)

                
            
            # Обработка запросов анализа (например, "BTC" или "анализ ETHUSDT")
            elif text.upper() in self.config.TRADING_PAIRS:
                symbol = text.upper()
                if self.config.is_chat_authorized(chat_id):
                    await self.send_manual_analysis(symbol, chat_id)
                else:
                    await self.telegram_bot.send_subscription_info(chat_id)
            
            # Обработка текстовых запросов
            elif any(symbol in text.upper() for symbol in self.config.TRADING_PAIRS):
                # Ищем символ в тексте
                for symbol in self.config.TRADING_PAIRS:
                    if symbol in text.upper():
                        if self.config.is_chat_authorized(chat_id):
                            await self.send_manual_analysis(symbol, chat_id)
                        else:
                            await self.telegram_bot.send_subscription_info(chat_id)
                        break
            
            # Если пользователь не авторизован и пишет что-то не команду
            elif not self.config.is_chat_authorized(chat_id):
                await self.telegram_bot.send_subscription_info(chat_id)
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения: {e}")
            self.daily_stats['errors'] += 1
    
    async def _validate_configuration(self) -> bool:
        """Валидация конфигурации"""
        logger.info("🔧 Проверка конфигурации...")
        
        # Проверяем API ключи
        if not self.config.BYBIT_API_KEY or not self.config.BYBIT_SECRET_KEY:
            logger.error("❌ Не заданы API ключи Bybit")
            return False
        
        if not self.config.TELEGRAM_BOT_TOKEN:
            logger.error("❌ Не задан токен Telegram бота")
            return False
        
        # Проверяем наличие чатов
        authorized_chats = self.config.get_authorized_chats()
        if not authorized_chats:
            logger.warning("⚠️ Нет авторизованных чатов - бот будет работать в режиме только для новых пользователей")
        else:
            logger.info(f"✅ Настроено {len(authorized_chats)} авторизованных чатов")
            
            # Показываем информацию о чатах
            for chat_id in authorized_chats:
                tier = self.config.get_chat_tier(chat_id)
                is_admin = self.config.CHAT_SUBSCRIPTIONS.get(chat_id, {}).get('is_admin', False)
                admin_mark = " (Админ)" if is_admin else ""
                logger.info(f"  📱 Чат {chat_id}: {tier}{admin_mark}")
        
        logger.info(f"✅ Будет анализироваться {len(self.config.TRADING_PAIRS)} торговых пар")
        return True
    
    async def _validate_connections(self) -> bool:
        """Проверка подключений"""
        logger.info("🌐 Проверка подключений...")
        
        # Проверка Bybit API
        try:
            if not self.bybit_api.validate_connection():
                logger.error("❌ Не удалось подключиться к Bybit API")
                return False
            logger.info("✅ Bybit API подключен")
        except Exception as e:
            logger.error(f"❌ Ошибка Bybit API: {e}")
            return False
        
        # Проверка Telegram
        try:
            if not await self.telegram_bot.test_connection():
                logger.error("❌ Не удалось подключиться к Telegram")
                return False
            logger.info("✅ Telegram подключен")
        except Exception as e:
            logger.error(f"❌ Ошибка Telegram: {e}")
            return False
        
        return True
    
    async def _send_startup_info(self):
        """Отправка информации о запуске в чаты"""
        try:
            # Информация для администраторов
            admin_chats = [chat_id for chat_id, settings in self.config.CHAT_SUBSCRIPTIONS.items()
                          if settings.get('is_admin', False)]
            
            if admin_chats:
                admin_message = f"""👑 <b>Информация для администраторов</b>

🤖 <b>Статус бота:</b> Запущен и готов к работе
📊 <b>Торговых пар:</b> {len(self.config.TRADING_PAIRS)}
👥 <b>Активных чатов:</b> {len(self.config.get_authorized_chats())}
💬 <b>Прием команд:</b> Включен

💎 <b>Распределение по тарифам:</b>"""
                
                tier_counts = {}
                for settings in self.config.CHAT_SUBSCRIPTIONS.values():
                    tier = settings.get('tier', 'FREE')
                    tier_counts[tier] = tier_counts.get(tier, 0) + 1
                
                for tier, count in tier_counts.items():
                    admin_message += f"\n• {tier}: {count} чатов"
                
                admin_message += f"""

🔧 <b>Админские команды:</b>
/admin help - полная справка
/admin list_chats - список всех чатов
/admin add_chat [chat_id] [tier] - добавить чат
/admin test_bot - проверка работы

💡 <b>Теперь команды работают!</b>"""
                
                for admin_chat in admin_chats:
                    await self.telegram_bot._send_message(admin_message, admin_chat)
        
        except Exception as e:
            logger.error(f"Ошибка отправки стартовой информации: {e}")
    
    async def _analysis_cycle(self):
        """Цикл анализа рынка"""
        cycle_start = datetime.now()
        
        try:
            logger.info("🔍 Начало цикла анализа рынка...")
            self.daily_stats['analysis_cycles'] += 1
            
            # ДОБАВЛЕНО: Отправляем тестовое сообщение каждые 10 циклов
            if self.daily_stats['analysis_cycles'] % 10 == 0:
                test_message = f"""🤖 <b>Бот работает!</b>

📊 Цикл анализа: #{self.daily_stats['analysis_cycles']}
📱 Получено сообщений: {self.daily_stats['messages_received']}
⌨️ Обработано команд: {self.daily_stats['commands_processed']}

💡 Попробуйте команду /admin help"""
                
                await self.telegram_bot.send_alert(test_message, "INFO", admin_only=True)
            
            # Получаем баланс аккаунта
            account_data = self.bybit_api.get_account_balance()
            balance = self._extract_usdt_balance(account_data)
            
            if balance <= 0:
                logger.warning("⚠️ Не удалось получить баланс аккаунта")
                balance = 1000.0  # Используем тестовое значение
            
            signals_generated = 0
            signals_sent = 0
            
            # Анализируем каждую торговую пару
            for symbol in self.config.TRADING_PAIRS:
                try:
                    # Проверяем, нужно ли анализировать эту пару
                    if not self._should_analyze_symbol(symbol):
                        continue
                    
                    logger.info(f"📊 Анализ {symbol}...")
                    
                    # Собираем рыночные данные
                    market_data = await self._collect_market_data(symbol)
                    
                    if not market_data:
                        logger.warning(f"⚠️ Не удалось получить данные для {symbol}")
                        continue
                    
                    # Генерируем сигнал
                    signal = self.signal_generator.generate_signal(symbol, market_data, balance)
                    
                    if signal:
                        signals_generated += 1
                        self.daily_stats['signals_generated'] += 1
                        
                        # Определяем категорию пары для сигнала
                        signal.category = self._get_pair_category(symbol) # type: ignore
                        
                        # Отправляем сигнал во все подходящие чаты
                        send_results = await self.telegram_bot.send_trading_signal(signal) # type: ignore
                        
                        successful_sends = sum(send_results.values())
                        if successful_sends > 0:
                            signals_sent += successful_sends
                            self.daily_stats['signals_sent'] += successful_sends
                            try:
                                signal_id = self.tp_tracker.add_signal_for_tracking(signal)
                                if signal_id:
                                    self.daily_stats['tp_tracking_started'] += 1
                                    logger.info(f"📊 Начато отслеживание TP для {signal_id}")
                            except Exception as e:
                                logger.error(f"Ошибка добавления TP отслеживания: {e}")
                            logger.info(f"✅ Сигнал {signal.signal_type} для {symbol} отправлен в {successful_sends} чатов")
                        else:
                            logger.warning(f"⚠️ Сигнал для {symbol} не был отправлен ни в один чат")
                    
                    # Обновляем время последнего анализа
                    self.last_analysis_time[symbol] = datetime.now()
                    
                    # Небольшая пауза между анализами
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка анализа {symbol}: {e}")
                    self.daily_stats['errors'] += 1
                    continue
            
            cycle_duration = (datetime.now() - cycle_start).total_seconds()
            
            logger.info(f"✅ Цикл анализа завершен за {cycle_duration:.1f}с. Сгенерировано сигналов: {signals_generated}, отправлено: {signals_sent}")
            
            # Отправляем периодическую сводку (каждые 10 циклов)
            if self.daily_stats['analysis_cycles'] % 10 == 0:
                await self._send_periodic_summary()
                
        except Exception as e:
            logger.error(f"❌ Ошибка в цикле анализа: {e}")
            logger.error(traceback.format_exc())
            self.daily_stats['errors'] += 1
    
    # Остальные методы остаются без изменений
    async def _collect_market_data(self, symbol: str) -> Dict:
        """Сбор рыночных данных"""
        try:
            market_data = {}
            
            # Получаем исторические данные (свечи)
            klines = self.bybit_api.get_klines(symbol, self.config.PRIMARY_TIMEFRAME, 200)
            if not klines.empty:
                market_data['klines'] = klines
            
            # Получаем данные тикера
            ticker = self.bybit_api.get_ticker_24hr(symbol)
            if ticker:
                market_data['ticker'] = ticker
            
            # Получаем ставку финансирования
            funding = self.bybit_api.get_funding_rate(symbol)
            if funding:
                market_data['funding'] = funding
            
            # Получаем открытый интерес
            oi_data = self.bybit_api.get_open_interest(symbol, '1h', 48)
            if not oi_data.empty:
                market_data['open_interest'] = oi_data
            
            return market_data if market_data else None # type: ignore
            
        except Exception as e:
            logger.error(f"❌ Ошибка сбора данных для {symbol}: {e}")
            return None # type: ignore
    
    def _extract_usdt_balance(self, account_data: Dict) -> float:
        """Извлечение USDT баланса из данных аккаунта"""
        try:
            if not account_data or 'list' not in account_data:
                return 0.0
            
            for account in account_data['list']:
                if account.get('accountType') == 'UNIFIED':
                    coins = account.get('coin', [])
                    for coin in coins:
                        if coin.get('coin') == 'USDT':
                            return float(coin.get('walletBalance', 0))
            
            return 0.0
            
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения баланса: {e}")
            return 0.0
    
    def _should_analyze_symbol(self, symbol: str) -> bool:
        """Проверка, нужно ли анализировать символ"""
        
        # Проверяем временной интервал
        last_analysis = self.last_analysis_time.get(symbol)
        
        if last_analysis:
            time_since_last = datetime.now() - last_analysis
            # Анализируем каждые 15 минут
            if time_since_last < timedelta(minutes=15):
                return False
        
        return True
    
    def _get_pair_category(self, symbol: str) -> str:
        """Определение категории торговой пары"""
        for category, pairs in self.config.PAIR_CATEGORIES.items():
            if symbol in pairs:
                return category
        return 'other'
    
    async def _send_periodic_summary(self):
        """Отправка периодической сводки"""
        try:
            summary = f"""📊 <b>Периодическая сводка</b>

🔄 Циклов анализа: {self.daily_stats['analysis_cycles']}
📈 Сигналов сгенерировано: {self.daily_stats['signals_generated']}
📤 Сигналов отправлено: {self.daily_stats['signals_sent']}
📱 Сообщений получено: {self.daily_stats['messages_received']}
⌨️ Команд обработано: {self.daily_stats['commands_processed']}
❌ Ошибок: {self.daily_stats['errors']}

⏰ Время: {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}"""
            
            # Отправляем только администраторам
            await self.telegram_bot.send_alert(summary, "INFO", admin_only=True)
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки периодической сводки: {e}")
    
    async def send_manual_analysis(self, symbol: str, chat_id: str = None): # type: ignore
        """Ручной запуск анализа для конкретной пары"""
        try:
            logger.info(f"🔍 Ручной анализ {symbol}...")
            
            market_data = await self._collect_market_data(symbol)
            
            if not market_data:
                message = f"❌ Не удалось получить данные для {symbol}"
                if chat_id:
                    await self.telegram_bot._send_message(message, chat_id)
                else:
                    await self.telegram_bot.send_alert(message, "ERROR", admin_only=True)
                return
            
            # Проводим анализ без генерации сигнала
            from technical_analysis import TechnicalAnalyzer
            from fundamental_analysis import FundamentalAnalyzer
            
            tech_analyzer = TechnicalAnalyzer(self.config) # type: ignore
            fund_analyzer = FundamentalAnalyzer(self.config) # type: ignore
            
            tech_result = tech_analyzer.analyze(
                market_data['klines'], symbol, self.config.PRIMARY_TIMEFRAME
            )
            
            fund_result = fund_analyzer.analyze(
                symbol, 
                market_data.get('ticker', {}),
                market_data.get('funding', {}),
                market_data.get('open_interest', pd.DataFrame())
            )
            
            # Отправляем анализ
            if chat_id:
                # В конкретный чат
                message = self.telegram_bot._format_analysis_message(
                    symbol, tech_result, fund_result, chat_id
                )
                await self.telegram_bot._send_message(message, chat_id)
            else:
                # Во все подходящие чаты
                await self.telegram_bot.send_market_analysis(symbol, tech_result, fund_result)
            
        except Exception as e:
            logger.error(f"❌ Ошибка ручного анализа {symbol}: {e}")
            error_message = f"❌ Ошибка анализа {symbol}: {e}"
            if chat_id:
                await self.telegram_bot._send_message(error_message, chat_id)
            else:
                await self.telegram_bot.send_alert(error_message, "ERROR", admin_only=True)

    async def _handle_tp_stats_command(self, chat_id: str):
            """Обработка команды /tp_stats"""
            try:
                if not self.config.is_chat_authorized(chat_id):
                    await self.telegram_bot.send_subscription_info(chat_id)
                    return
                
                stats_message = self.tp_tracker.format_statistics_message()
                await self.telegram_bot._send_message(stats_message, chat_id)
                
            except Exception as e:
                logger.error(f"Ошибка обработки /tp_stats: {e}")
                await self.telegram_bot._send_message("❌ Ошибка получения статистики TP", chat_id)
        
    async def _handle_tp_active_command(self, chat_id: str):
        """Обработка команды /tp_active"""
        try:
            if not self.config.is_chat_authorized(chat_id):
                await self.telegram_bot.send_subscription_info(chat_id)
                return
            
            active_signals = self.tp_tracker.tracking_signals
            
            if not active_signals:
                message = "📊 <b>Активные отслеживания TP</b>\n\n❌ Нет активных отслеживаний"
            else:
                message = f"📊 <b>Активные отслеживания TP</b>\n\n👀 Отслеживается: {len(active_signals)} сигналов\n\n"
                
                for signal_id, signal_data in list(active_signals.items())[:5]:
                    elapsed = datetime.now() - signal_data.start_time
                    elapsed_str = self._format_duration(elapsed)
                    message += f"• {signal_data.symbol} {signal_data.signal_type} - {elapsed_str}\n"
                
                if len(active_signals) > 5:
                    message += f"... и еще {len(active_signals) - 5} сигналов"
            
            await self.telegram_bot._send_message(message, chat_id)
            
        except Exception as e:
            logger.error(f"Ошибка обработки /tp_active: {e}")
            await self.telegram_bot._send_message("❌ Ошибка получения активных отслеживаний", chat_id)
    
    def _format_duration(self, duration):
        """Форматирование длительности"""
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours}ч {minutes}м"
        else:
            return f"{minutes}м"

def signal_handler(signum, frame):
    """Обработчик сигналов системы"""
    logger.info(f"Получен сигнал {signum}, завершаем работу...")
    sys.exit(0)

async def main():
    """Главная функция"""
    
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Создаем и запускаем бота
    bot = EnhancedTradingBot()
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("⏹️ Прерывание работы пользователем")
    except Exception as e:
        logger.error(f"💥 Неожиданная ошибка: {e}")
        logger.error(traceback.format_exc())
    finally:
        await bot.stop()

if __name__ == "__main__":
    # Проверяем наличие необходимых переменных окружения
    config = TradingConfig()
    
    if not config.BYBIT_API_KEY or not config.BYBIT_SECRET_KEY:
        print("❌ ОШИБКА: Не заданы API ключи Bybit")
        print("Создайте файл .env и добавьте:")
        print("BYBIT_API_KEY=ваш_ключ")
        print("BYBIT_SECRET_KEY=ваш_секрет")
        sys.exit(1)
    
    if not config.TELEGRAM_BOT_TOKEN:
        print("❌ ОШИБКА: Не задан токен Telegram бота")
        print("Добавьте в .env файл:")
        print("TELEGRAM_TOKEN=ваш_токен")
        sys.exit(1)
    
    # Проверяем наличие чатов
    authorized_chats = config.get_authorized_chats()
    if not authorized_chats:
        print("⚠️ ВНИМАНИЕ: Не настроены чаты для уведомлений")
        print("Добавьте в .env файл:")
        print("TELEGRAM_CHAT_ID=ваш_chat_id")
        print("или")
        print("TELEGRAM_ADDITIONAL_CHATS=chat1,chat2,chat3")
        
        response = input("Продолжить без настроенных чатов? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    print(f"🚀 Запуск расширенного торгового бота...")
    print(f"📊 Мониторинг {len(config.TRADING_PAIRS)} торговых пар")
    print(f"👥 Подключено {len(authorized_chats)} авторизованных чатов")
    print(f"💬 Режим: Polling (прием команд включен)")
    
    # Запускаем основной цикл
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⏹️ Работа завершена")
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")
        sys.exit(1)