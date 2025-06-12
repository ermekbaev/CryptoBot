# enhanced_telegram_bot.py - Улучшенный Telegram бот с поддержкой множественных чатов
import asyncio
import aiohttp
import json
import logging
from typing import Dict, Optional, List, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
from command_troubleshooting import CommandTroubleshooter
from config import TradingConfig
from technical_analysis import TechnicalAnalysisResult
from fundamental_analysis import FundamentalAnalysisResult

logger = logging.getLogger(__name__)

@dataclass
class TradingSignal:
    """Структура торгового сигнала"""
    symbol: str
    signal_type: str  # 'BUY', 'SELL'
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: Optional[float]
    leverage: int
    confidence: float
    risk_amount: float
    position_size: float
    technical_summary: str
    fundamental_summary: str
    risk_factors: list
    timestamp: datetime
    category: str = 'other'  # Категория торговой пары

class EnhancedTelegramBot:
    """Улучшенный класс для отправки сигналов в множественные Telegram чаты"""
    
    def __init__(self, config: TradingConfig):
        self.config = config
        self.base_url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"
        self.last_signals = {}  # Кэш последних сигналов по чатам
        self.daily_stats = {}   # Дневная статистика по чатам
        
    async def send_trading_signal(self, signal: TradingSignal) -> Dict[str, bool]:
        """Отправка торгового сигнала во все авторизованные чаты"""
        results = {}
        authorized_chats = self.config.get_authorized_chats()
        
        if not authorized_chats:
            logger.warning("Нет авторизованных чатов для отправки сигналов")
            return results
        
        for chat_id in authorized_chats:
            try:
                # Проверяем, может ли чат получить этот сигнал
                can_receive, reason = self.config.can_receive_signal(chat_id, signal.category)
                
                if not can_receive:
                    logger.info(f"Чат {chat_id} не может получить сигнал {signal.symbol}: {reason}")
                    results[chat_id] = False
                    continue
                
                # Проверяем дублирование
                if self._is_signal_duplicate(signal, chat_id):
                    logger.info(f"Пропуск дублирующего сигнала {signal.symbol} для чата {chat_id}")
                    results[chat_id] = False
                    continue
                
                # Форматируем сообщение в зависимости от уровня подписки
                message = self._format_signal_message(signal, chat_id)
                
                # Отправляем сообщение
                success = await self._send_message(message, chat_id)
                results[chat_id] = success
                
                if success:
                    # Обновляем статистику и кэш
                    self._cache_signal(signal, chat_id)
                    self.config.update_chat_signal_count(chat_id)
                    logger.info(f"Сигнал {signal.symbol} отправлен в чат {chat_id}")
                else:
                    logger.error(f"Ошибка отправки сигнала {signal.symbol} в чат {chat_id}")
                    
            except Exception as e:
                logger.error(f"Ошибка при отправке сигнала в чат {chat_id}: {e}")
                results[chat_id] = False
        
        return results
    
    async def send_alert(self, message: str, priority: str = "INFO", 
                        admin_only: bool = False) -> Dict[str, bool]:
        """Отправка уведомления"""
        results = {}
        
        try:
            emoji_map = {
                "INFO": "ℹ️",
                "WARNING": "⚠️", 
                "ERROR": "❌",
                "SUCCESS": "✅"
            }
            
            formatted_message = f"{emoji_map.get(priority, 'ℹ️')} {message}"
            
            # Определяем получателей
            if admin_only:
                # Только администраторы
                target_chats = [chat_id for chat_id, settings in self.config.CHAT_SUBSCRIPTIONS.items()
                              if settings.get('is_admin', False) and settings.get('active', False)]
            else:
                # Все авторизованные чаты
                target_chats = self.config.get_authorized_chats()
            
            for chat_id in target_chats:
                success = await self._send_message(formatted_message, chat_id)
                results[chat_id] = success
                
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления: {e}")
        
        return results
    
    async def send_market_analysis(self, symbol: str, 
                                 technical_result: TechnicalAnalysisResult,
                                 fundamental_result: FundamentalAnalysisResult) -> Dict[str, bool]:
        """Отправка анализа рынка"""
        results = {}
        
        try:
            # Определяем, кто может получить детальный анализ
            for chat_id in self.config.get_authorized_chats():
                chat_tier = self.config.get_chat_tier(chat_id)
                chat_features = self.config.SUBSCRIPTION_TIERS[chat_tier]['features']
                
                # Проверяем доступ к техническому анализу
                if 'technical_analysis' not in chat_features:
                    continue
                
                message = self._format_analysis_message(
                    symbol, technical_result, fundamental_result, chat_id
                )
                success = await self._send_message(message, chat_id)
                results[chat_id] = success
                
        except Exception as e:
            logger.error(f"Ошибка при отправке анализа: {e}")
        
        return results
    
    async def send_subscription_info(self, chat_id: str) -> bool:
        """Отправка информации о подписке"""
        try:
            if not self.config.is_chat_authorized(chat_id):
                message = """❌ <b>Доступ запрещен</b>

🔐 Данный чат не авторизован для получения торговых сигналов.

💎 <b>Доступные тарифы:</b>
🆓 FREE - 3 сигнала/день, только топ криптовалюты
⭐ BASIC - 10 сигналов/день, DeFi + Layer 1
💎 PREMIUM - 25 сигналов/день, включая Gaming/NFT
👑 VIP - безлимитные сигналы, все категории

📞 Для подключения обратитесь к администратору"""
                return await self._send_message(message, chat_id)
            
            chat_settings = self.config.CHAT_SUBSCRIPTIONS[chat_id]
            tier = chat_settings['tier']
            tier_info = self.config.SUBSCRIPTION_TIERS[tier]
            
            # Счетчики
            signals_today = chat_settings.get('signals_sent_today', 0)
            max_signals = tier_info['max_signals_per_day']
            max_signals_text = str(max_signals) if max_signals > 0 else "∞"
            
            message = f"""📊 <b>Информация о подписке</b>

👤 <b>Уровень:</b> {tier}
📈 <b>Сигналы сегодня:</b> {signals_today}/{max_signals_text}
⏱️ <b>Кулдаун:</b> {tier_info['cooldown_minutes']} мин

🎯 <b>Доступные категории:</b>"""
            
            category_names = {
                'major': '🔵 Топ криптовалюты',
                'defi': '🟣 DeFi токены', 
                'layer1': '🟢 Layer 1 блокчейны',
                'meme': '🟡 Мемкоины',
                'gaming_nft': '🎮 Gaming/NFT',
                'emerging': '🆕 Новые проекты'
            }
            
            for category in tier_info['categories_allowed']:
                message += f"\n• {category_names.get(category, category)}"
            
            message += f"""

🛠️ <b>Доступные функции:</b>"""
            
            feature_names = {
                'basic_signals': '📊 Базовые сигналы',
                'technical_analysis': '📈 Технический анализ',
                'fundamental_analysis': '💰 Фундаментальный анализ',
                'priority_support': '👑 Приоритетная поддержка'
            }
            
            for feature in tier_info['features']:
                message += f"\n• {feature_names.get(feature, feature)}"
            
            if chat_settings.get('is_admin', False):
                message += f"\n\n👑 <b>Статус:</b> Администратор"
            
            return await self._send_message(message, chat_id)
            
        except Exception as e:
            logger.error(f"Ошибка при отправке информации о подписке: {e}")
            return False
    
    async def handle_command(self, chat_id: str, command: str, args: List[str] = None) -> bool:
        """Обработка команд от пользователей"""
        if args is None:
            args = []
            
        try:
            # Проверяем авторизацию для большинства команд
            if command not in ['start', 'help'] and not self.config.is_chat_authorized(chat_id):
                return await self.send_subscription_info(chat_id)
            
            if command == 'start':
                message = """🤖 <b>Добро пожаловать в торгового бота!</b>

🎯 Я предоставляю профессиональные торговые сигналы для криптовалют на основе технического и фундаментального анализа.

📋 <b>Доступные команды:</b>
/status - информация о подписке
/help - помощь
/stats - статистика сигналов"""
                
                return await self._send_message(message, chat_id)
            
            elif command == 'help':
                message = """❓ <b>Помощь по боту</b>

🤖 <b>Основные команды:</b>
/start - запуск бота
/status - информация о подписке
/stats - статистика сигналов
/help - эта справка

📊 <b>Как работают сигналы:</b>
• Анализирую рынок каждые 15 минут
• Использую 20+ технических индикаторов
• Учитываю фундаментальные факторы
• Предоставляю точки входа, стоп-лосс и тейк-профиты

⚠️ <b>Важно:</b>
• Это не финансовые советы
• Всегда управляйте рисками
• Не рискуйте больше чем можете потерять

💎 <b>Уровни подписок:</b>
🆓 FREE - базовые сигналы
⭐ BASIC - расширенный анализ
💎 PREMIUM - приоритетные сигналы
👑 VIP - полный доступ"""
                
                return await self._send_message(message, chat_id)
            
            elif command == 'status':
                return await self.send_subscription_info(chat_id)
            
            elif command == 'stats':
                return await self._send_stats(chat_id)
            
            # Админские команды
            elif command == 'admin' and self.config.CHAT_SUBSCRIPTIONS.get(chat_id, {}).get('is_admin', False):
                return await self._handle_admin_command(chat_id, args)
            
            else:
                message = "❓ Неизвестная команда. Используйте /help для справки."
                return await self._send_message(message, chat_id)
                
        except Exception as e:
            logger.error(f"Ошибка при обработке команды {command}: {e}")
            return False
    
    async def _send_stats(self, chat_id: str) -> bool:
        """Отправка статистики"""
        try:
            chat_settings = self.config.CHAT_SUBSCRIPTIONS.get(chat_id, {})
            signals_today = chat_settings.get('signals_sent_today', 0)
            tier = chat_settings.get('tier', 'FREE')
            
            message = f"""📈 <b>Статистика сигналов</b>

📊 <b>Сегодня получено:</b> {signals_today}
🎯 <b>Текущий тариф:</b> {tier}

⏰ <b>Последние сигналы:</b>"""
            
            # Показываем последние сигналы для этого чата
            chat_signals = []
            for key, signal_data in self.last_signals.items():
                if key.endswith(f"_{chat_id}"):
                    chat_signals.append(signal_data)
            
            chat_signals = sorted(chat_signals, key=lambda x: x['timestamp'], reverse=True)[:5]
            
            if chat_signals:
                for signal in chat_signals:
                    symbol = signal['symbol']
                    signal_type = signal['signal_type']
                    confidence = signal['confidence']
                    time_str = signal['timestamp'].strftime('%H:%M')
                    message += f"\n• {time_str} - {symbol} {signal_type} ({confidence:.0f}%)"
            else:
                message += "\n• Пока нет сигналов"
            
            return await self._send_message(message, chat_id)
            
        except Exception as e:
            logger.error(f"Ошибка при отправке статистики: {e}")
            return False
    
    # ===============================================
    # АДМИНСКИЕ КОМАНДЫ (ДОПИСАНО)
    # ===============================================
    
    async def _handle_admin_command(self, chat_id: str, args: List[str]) -> bool:
        """Обработка админских команд"""
        
        if not self.config.CHAT_SUBSCRIPTIONS.get(chat_id, {}).get('is_admin', False):
            await self._send_message("❌ У вас нет прав администратора", chat_id)
            return False
        
        if not args:
            await self._send_admin_help(chat_id)
            return True
        
        admin_command = args[0].lower()
        admin_args = args[1:] if len(args) > 1 else []
        
        logger.info(f"Админская команда от {chat_id}: {admin_command} {admin_args}")
        
        # Роутинг админских команд
        if admin_command == 'add_chat':
            return await self._admin_add_chat(chat_id, admin_args)
        elif admin_command == 'remove_chat':
            return await self._admin_remove_chat(chat_id, admin_args)
        elif admin_command == 'upgrade_chat':
            return await self._admin_upgrade_chat(chat_id, admin_args)
        elif admin_command == 'list_chats':
            return await self._admin_list_chats(chat_id, admin_args)
        elif admin_command == 'broadcast':
            return await self._admin_broadcast(chat_id, admin_args)
        elif admin_command == 'diagnose':
            return await self._admin_diagnose(chat_id, admin_args)
        elif admin_command == 'test_bot':
            return await self._admin_test_bot(chat_id, admin_args)
        elif admin_command == 'help':
            return await self._send_admin_help(chat_id)
        else:
            await self._send_message(f"❓ Неизвестная админская команда: {admin_command}\nИспользуйте /admin help", chat_id)
            return False
    
    async def _admin_add_chat(self, admin_chat: str, args: List[str]) -> bool: # type: ignore
        """Добавление нового чата"""
        
        if len(args) < 2:
            help_text = """💡 <b>Команда: /admin add_chat</b>

📝 <b>Формат:</b>
<code>/admin add_chat CHAT_ID TIER [NOTES]</code>

🎯 <b>Параметры:</b>
• <code>CHAT_ID</code> - ID чата (число)
• <code>TIER</code> - Уровень (FREE/BASIC/PREMIUM/VIP)
• <code>NOTES</code> - Заметки (опционально)

📋 <b>Пример:</b>
<code>/admin add_chat 1857921803 BASIC Тестовый пользователь</code>"""
            
            await self._send_message(help_text, admin_chat)
            return False
        
        target_chat = args[0].strip()
        tier = args[1].upper().strip()
        notes = " ".join(args[2:]) if len(args) > 2 else ""
        
        # Валидация chat_id
        try:
            validated_chat_id = str(int(target_chat))
        except ValueError:
            await self._send_message(f"❌ Неверный формат Chat ID: {target_chat}\nИспользуйте числовой ID", admin_chat)
            return False
        
        # Валидация тарифа
        if tier not in self.config.SUBSCRIPTION_TIERS:
            available_tiers = ", ".join(self.config.SUBSCRIPTION_TIERS.keys())
            await self._send_message(f"❌ Неверный тариф: {tier}\nДоступные тарифы: {available_tiers}", admin_chat)
            return False
        
        # Проверяем, не существует ли уже
        if validated_chat_id in self.config.CHAT_SUBSCRIPTIONS:
            current_tier = self.config.CHAT_SUBSCRIPTIONS[validated_chat_id]['tier']
            await self._send_message(
                f"⚠️ Чат {validated_chat_id} уже существует с тарифом {current_tier}\n"
                f"Используйте /admin upgrade_chat для изменения тарифа", 
                admin_chat
            )
            return False
        
        # Добавляем чат
        try:
            success = self.config.add_chat(validated_chat_id, tier, is_admin=False)
            
            if success:
                # Добавляем дополнительную информацию
                self.config.CHAT_SUBSCRIPTIONS[validated_chat_id].update({
                    'admin_notes': notes,
                    'added_by': admin_chat,
                    'added_at': datetime.now().isoformat()
                })
                
                # Формируем сообщение об успехе
                tier_info = self.config.SUBSCRIPTION_TIERS[tier]
                success_message = f"""✅ <b>Чат успешно добавлен!</b>

        👤 <b>Chat ID:</b> <code>{validated_chat_id}</code>
        💎 <b>Тариф:</b> {tier}
        📊 <b>Лимит сигналов:</b> {tier_info['max_signals_per_day'] if tier_info['max_signals_per_day'] > 0 else '∞'}/день
        ⏱️ <b>Кулдаун:</b> {tier_info['cooldown_minutes']} мин
        📝 <b>Заметки:</b> {notes or 'Нет'}
        🕐 <b>Добавлен:</b> {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}
        👑 <b>Администратор:</b> {admin_chat}
        💡 <b>Осталось чатов в системе:</b> {len(self.config.CHAT_SUBSCRIPTIONS)}"""
                
                await self._send_message(success_message, admin_chat)
                
                # Уведомляем удаленного пользователя (возможно, это должно быть добавление нового пользователя, а не удаление?)
                try:
                    welcome_message = """👋 <b>Вы были подключены к торговому боту</b>

        Добро пожаловать!
        📈 Следите за сигналами и соблюдайте правила.
        """
                    await self._send_message(welcome_message, validated_chat_id)
                except Exception as e:
                    logger.warning(f"Не удалось уведомить нового пользователя {validated_chat_id}: {e}")
                
                logger.info(f"Админ {admin_chat} добавил чат {validated_chat_id}")
                return True

        except Exception as e:
            logger.error(f"Ошибка при добавлении чата: {e}")
            await self._send_message("❌ Произошла ошибка при добавлении чата.", admin_chat)
            return False

    async def _admin_broadcast(self, admin_chat: str, args: List[str]) -> bool:
        """Рассылка сообщения всем пользователям"""
        
        if len(args) < 1:
            await self._send_message(
                "📝 Формат: /admin broadcast СООБЩЕНИЕ\n"
                "Пример: /admin broadcast Внимание! Завтра техническое обслуживание", 
                admin_chat
            )
            return False
        
        broadcast_message = " ".join(args)
        
        # Подтверждение рассылки
        confirmation_text = f"""📢 <b>Подтверждение рассылки</b>

📝 <b>Сообщение:</b>
{broadcast_message}

👥 <b>Получателей:</b> {len(self.config.get_authorized_chats())} чатов

⚠️ <b>Внимание!</b> Сообщение будет отправлено всем активным пользователям.

🔄 Отправьте команду еще раз с параметром 'confirm' для подтверждения:
<code>/admin broadcast confirm {broadcast_message}</code>"""
        
        # Проверяем подтверждение
        if args[0].lower() != 'confirm':
            await self._send_message(confirmation_text, admin_chat)
            return False
        
        # Убираем 'confirm' из сообщения
        actual_message = " ".join(args[1:])
        
        if not actual_message.strip():
            await self._send_message("❌ Пустое сообщение для рассылки", admin_chat)
            return False
        
        # Форматируем сообщение для рассылки
        formatted_message = f"""📢 <b>УВЕДОМЛЕНИЕ</b>

{actual_message}

<i>— Администрация торгового бота</i>"""
        
        # Отправляем во все чаты
        results = {}
        authorized_chats = self.config.get_authorized_chats()
        
        for chat_id in authorized_chats:
            try:
                success = await self._send_message(formatted_message, chat_id)
                results[chat_id] = success
            except Exception as e:
                logger.error(f"Ошибка рассылки в чат {chat_id}: {e}")
                results[chat_id] = False
        
        # Отчет о рассылке
        success_count = sum(results.values())
        total_count = len(results)
        failed_chats = [chat_id for chat_id, success in results.items() if not success]
        
        report = f"""📊 <b>Отчет о рассылке</b>

✅ <b>Успешно:</b> {success_count}/{total_count} чатов
⏰ <b>Время:</b> {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}"""
        
        if failed_chats:
            report += f"\n\n❌ <b>Не доставлено ({len(failed_chats)}):</b>"
            for chat_id in failed_chats[:5]:  # Показываем первые 5
                report += f"\n• <code>{chat_id}</code>"
            if len(failed_chats) > 5:
                report += f"\n... и еще {len(failed_chats) - 5}"
        
        await self._send_message(report, admin_chat)
        logger.info(f"Админ {admin_chat} выполнил рассылку: {success_count}/{total_count} доставлено")
        
        return True
    
    async def _admin_diagnose(self, admin_chat: str, args: List[str]) -> bool:
        """Диагностика команды добавления чата"""
        
        if len(args) < 3:
            await self._send_message(
                "📝 Формат: /admin diagnose add_chat CHAT_ID TIER\n"
                "Пример: /admin diagnose add_chat 1857921803 BASIC", 
                admin_chat
            )
            return False
        
        # Восстанавливаем полную команду для диагностики
        full_command = f"/admin {' '.join(args)}"
        
        # Создаем диагностику
        troubleshooter = CommandTroubleshooter(self.config, self)
        
        # Запускаем диагностику
        await troubleshooter.diagnose_add_chat_command(admin_chat, full_command)
        
        return True
    
    async def _admin_test_bot(self, admin_chat: str, args: List[str]) -> bool:
        """Тест работы бота"""
        
        troubleshooter = CommandTroubleshooter(self.config, self)
        await troubleshooter.test_bot_responsiveness(admin_chat)
        
        return True
    
    async def _send_admin_help(self, chat_id: str) -> bool:
        """Справка по админским командам"""
        
        help_text = """👑 <b>АДМИНСКИЕ КОМАНДЫ</b>

👥 <b>Управление чатами:</b>
/admin add_chat CHAT_ID TIER [NOTES] - добавить чат
/admin remove_chat CHAT_ID - удалить чат  
/admin upgrade_chat CHAT_ID TIER - изменить тариф
/admin list_chats - список всех чатов

🔧 <b>Диагностика:</b>
/admin test_bot - тест работы бота
/admin diagnose add_chat CHAT_ID TIER - диагностика команды

📢 <b>Рассылка:</b>
/admin broadcast MESSAGE - отправить во все чаты

💡 <b>Доступные тарифы:</b>
🆓 FREE, ⭐ BASIC, 💎 PREMIUM, 👑 VIP

🛠️ <b>Если команда не работает:</b>
1. Используйте /admin test_bot для проверки
2. Используйте /admin diagnose add_chat для диагностики
3. Проверьте логи бота

📋 <b>Примеры:</b>
<code>/admin add_chat 1857921803 BASIC Тестовый пользователь</code>
<code>/admin test_bot</code>
<code>/admin diagnose add_chat 1857921803 BASIC</code>
<code>/admin broadcast confirm Внимание! Обновление системы</code>"""
        
        await self._send_message(help_text, chat_id)
        return True
    
    # ===============================================
    # ФОРМАТИРОВАНИЕ СООБЩЕНИЙ
    # ===============================================
    
    def _format_signal_message(self, signal: TradingSignal, chat_id: str) -> str:
        """Форматирование сообщения с учетом уровня подписки"""
        
        tier = self.config.get_chat_tier(chat_id)
        tier_features = self.config.SUBSCRIPTION_TIERS[tier]['features']
        
        # Базовое сообщение для всех уровней
        signal_emoji = "🟢" if signal.signal_type == "BUY" else "🔴"
        confidence_emoji = self._get_confidence_emoji(signal.confidence)
        
        message = f"""🤖 <b>ТОРГОВЫЙ СИГНАЛ</b> {signal_emoji}

📊 <b>Пара:</b> {signal.symbol}
🎯 <b>Тип:</b> {signal.signal_type}
💰 <b>Цена входа:</b> {signal.entry_price:.6f}"""

        # Для FREE показываем минимум информации
        if tier == 'FREE':
            message += f"""
🛡️ <b>Stop Loss:</b> {signal.stop_loss:.6f}
🎯 <b>Take Profit:</b> {signal.take_profit_1:.6f}

{confidence_emoji} <b>Уверенность:</b> {signal.confidence:.1f}%

⏰ {signal.timestamp.strftime('%H:%M:%S')}

<i>⭐ Получите BASIC подписку для полного анализа!</i>"""
            
        else:
            # Для BASIC и выше - полная информация
            message += f"""
📈 <b>Плечо:</b> {signal.leverage}x
💵 <b>Размер позиции:</b> ${signal.position_size:.2f}

🛡️ <b>Управление рисками:</b>
⛔ Stop Loss: {signal.stop_loss:.6f}
🎯 Take Profit 1: {signal.take_profit_1:.6f}"""

            if signal.take_profit_2:
                message += f"\n🎯 Take Profit 2: {signal.take_profit_2:.6f}"
            
            message += f"""

{confidence_emoji} <b>Уверенность:</b> {signal.confidence:.1f}%
💎 <b>Риск на сделку:</b> ${signal.risk_amount:.2f}"""

            # Технический анализ для BASIC+
            if 'technical_analysis' in tier_features:
                message += f"""

📈 <b>Технический анализ:</b>
{signal.technical_summary}"""
            
            # Фундаментальный анализ для PREMIUM+
            if 'fundamental_analysis' in tier_features:
                message += f"""

📊 <b>Фундаментальный анализ:</b>
{signal.fundamental_summary}"""
                
                if signal.risk_factors:
                    message += f"\n\n⚠️ <b>Факторы риска:</b>\n"
                    for risk in signal.risk_factors[:3]:
                        message += f"• {risk}\n"
            
            message += f"""

⏰ <b>Время:</b> {signal.timestamp.strftime('%H:%M:%S %d.%m.%Y')}"""
        
        message += "\n\n<i>⚠️ Не является финансовой консультацией!</i>"
        
        return message
    
    def _format_analysis_message(self, symbol: str,
                               technical_result: TechnicalAnalysisResult,
                               fundamental_result: FundamentalAnalysisResult,
                               chat_id: str) -> str:
        """Форматирование анализа с учетом подписки"""
        
        tier = self.config.get_chat_tier(chat_id)
        
        message = f"""📊 <b>АНАЛИЗ: {symbol}</b>

🔧 <b>Технический анализ:</b>
• Сигнал: {technical_result.overall_signal}
• Уверенность: {technical_result.confidence:.1f}%"""

        if tier in ['PREMIUM', 'VIP']:
            message += f"""

📈 <b>Ключевые уровни:</b>"""
            
            if technical_result.support_levels:
                message += f"\n🟢 Поддержка: {', '.join([f'{level:.6f}' for level in technical_result.support_levels[:2]])}"
            
            if technical_result.resistance_levels:
                message += f"\n🔴 Сопротивление: {', '.join([f'{level:.6f}' for level in technical_result.resistance_levels[:2]])}"
            
            message += f"""

💡 <b>Фундаментальный анализ:</b>
• Сигнал: {fundamental_result.overall_signal}
• Уверенность: {fundamental_result.confidence:.1f}%
• Настроение: {fundamental_result.market_sentiment}"""
        
        if tier == 'VIP':
            # Детальная информация только для VIP
            strong_signals = sorted(
                [s for s in technical_result.signals if s.strength > 0.5],
                key=lambda x: x.strength, reverse=True
            )[:3]
            
            if strong_signals:
                message += f"\n\n📋 <b>Активные индикаторы:</b>"
                for signal in strong_signals:
                    message += f"\n• {signal.name}: {signal.signal} ({signal.strength:.2f})"
        
        message += f"\n\n⏰ {datetime.now().strftime('%H:%M:%S')}"
        
        return message
    
    def _get_confidence_emoji(self, confidence: float) -> str:
        """Эмодзи для уровня уверенности"""
        if confidence >= 85:
            return "🔥"
        elif confidence >= 75:
            return "💎"
        elif confidence >= 65:
            return "⭐"
        else:
            return "⚡"
    
    # ===============================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ===============================================
    
    async def _send_message(self, message: str, chat_id: str) -> bool:
        """Отправка сообщения в конкретный чат"""
        try:
            url = f"{self.base_url}/sendMessage"
            
            payload = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Ошибка Telegram API для чата {chat_id}: {response.status} - {error_text}")
                        return False
                        
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения в чат {chat_id}: {e}")
            return False
    
    def _is_signal_duplicate(self, signal: TradingSignal, chat_id: str) -> bool:
        """Проверка дублирования с учетом кулдауна для чата"""
        key = f"{signal.symbol}_{signal.signal_type}_{chat_id}"
        
        if key in self.last_signals:
            last_time = self.last_signals[key]['timestamp']
            cooldown_minutes = self.config.get_cooldown_minutes(chat_id)
            cooldown = timedelta(minutes=cooldown_minutes)
            
            if datetime.now() - last_time < cooldown:
                return True
        
        return False
    
    def _cache_signal(self, signal: TradingSignal, chat_id: str):
        """Кэширование сигнала для чата"""
        key = f"{signal.symbol}_{signal.signal_type}_{chat_id}"
        self.last_signals[key] = {
            'timestamp': signal.timestamp,
            'confidence': signal.confidence,
            'symbol': signal.symbol,
            'signal_type': signal.signal_type
        }
        
        # Очистка старых записей
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.last_signals = {
            k: v for k, v in self.last_signals.items() 
            if v['timestamp'] > cutoff_time
        }
    
    async def test_connection(self) -> bool:
        """Тестирование всех авторизованных чатов"""
        try:
            results = await self.send_alert("🤖 Тест подключения - OK!", "SUCCESS")
            success_count = sum(results.values())
            total_count = len(results)
            
            logger.info(f"Тест подключения: {success_count}/{total_count} чатов доступны")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Ошибка тестирования Telegram: {e}")
            return False

