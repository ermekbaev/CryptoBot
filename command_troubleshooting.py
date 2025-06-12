# command_troubleshooting.py - Диагностика проблем с командами

import asyncio
import logging
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)

class CommandTroubleshooter:
    """Класс для диагностики проблем с командами"""
    
    def __init__(self, config, telegram_bot):
        self.config = config
        self.telegram_bot = telegram_bot
    
    async def diagnose_add_chat_command(self, admin_chat_id: str, command_text: str):
        """Полная диагностика команды add_chat"""
        
        diagnostic_report = []
        diagnostic_report.append("🔧 <b>ДИАГНОСТИКА КОМАНДЫ ADD_CHAT</b>")
        diagnostic_report.append(f"🕐 Время: {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}")
        diagnostic_report.append(f"👤 Админ: {admin_chat_id}")
        diagnostic_report.append(f"💬 Команда: <code>{command_text}</code>")
        diagnostic_report.append("")
        
        try:
            # Шаг 1: Проверка прав администратора
            diagnostic_report.append("1️⃣ <b>Проверка прав администратора</b>")
            
            is_admin = self.config.CHAT_SUBSCRIPTIONS.get(admin_chat_id, {}).get('is_admin', False)
            
            if is_admin:
                diagnostic_report.append("✅ У вас есть права администратора")
            else:
                diagnostic_report.append("❌ У вас НЕТ прав администратора!")
                diagnostic_report.append("")
                diagnostic_report.append("🔍 <b>Ваши настройки:</b>")
                
                if admin_chat_id in self.config.CHAT_SUBSCRIPTIONS:
                    settings = self.config.CHAT_SUBSCRIPTIONS[admin_chat_id]
                    diagnostic_report.append(f"• Тариф: {settings.get('tier', 'НЕТ')}")
                    diagnostic_report.append(f"• Активен: {settings.get('active', False)}")
                    diagnostic_report.append(f"• Админ: {settings.get('is_admin', False)}")
                else:
                    diagnostic_report.append("• Вы НЕ найдены в системе!")
                
                diagnostic_report.append("")
                diagnostic_report.append("🛠️ <b>Как исправить:</b>")
                diagnostic_report.append("1. Убедитесь, что ваш Chat ID в .env файле")
                diagnostic_report.append("2. Перезапустите бота")
                diagnostic_report.append("3. Или попросите другого админа добавить вас")
                
                await self._send_diagnostic_message(admin_chat_id, diagnostic_report)
                return False
            
            # Шаг 2: Парсинг команды
            diagnostic_report.append("")
            diagnostic_report.append("2️⃣ <b>Парсинг команды</b>")
            
            parts = command_text.strip().split()
            
            if len(parts) < 4:
                diagnostic_report.append(f"❌ Недостаточно аргументов: {len(parts)} из 4 минимум")
                diagnostic_report.append("✅ Правильный формат: /admin add_chat CHAT_ID TIER [NOTES]")
                await self._send_diagnostic_message(admin_chat_id, diagnostic_report)
                return False
            
            command = parts[0]
            subcommand = parts[1]
            target_chat = parts[2]
            tier = parts[3].upper()
            notes = " ".join(parts[4:]) if len(parts) > 4 else ""
            
            diagnostic_report.append(f"✅ Команда: {command}")
            diagnostic_report.append(f"✅ Подкоманда: {subcommand}")
            diagnostic_report.append(f"✅ Целевой чат: {target_chat}")
            diagnostic_report.append(f"✅ Тариф: {tier}")
            diagnostic_report.append(f"✅ Заметки: {notes or 'Нет'}")
            
            # Шаг 3: Валидация chat_id
            diagnostic_report.append("")
            diagnostic_report.append("3️⃣ <b>Валидация Chat ID</b>")
            
            try:
                validated_chat_id = str(int(target_chat))
                diagnostic_report.append(f"✅ Chat ID валиден: {validated_chat_id}")
            except ValueError:
                diagnostic_report.append(f"❌ Chat ID невалиден: {target_chat}")
                diagnostic_report.append("💡 Chat ID должен быть числом (например: 1857921803)")
                await self._send_diagnostic_message(admin_chat_id, diagnostic_report)
                return False
            
            # Шаг 4: Валидация тарифа
            diagnostic_report.append("")
            diagnostic_report.append("4️⃣ <b>Валидация тарифа</b>")
            
            if tier in self.config.SUBSCRIPTION_TIERS:
                diagnostic_report.append(f"✅ Тариф валиден: {tier}")
            else:
                available_tiers = ", ".join(self.config.SUBSCRIPTION_TIERS.keys())
                diagnostic_report.append(f"❌ Тариф невалиден: {tier}")
                diagnostic_report.append(f"💡 Доступные тарифы: {available_tiers}")
                await self._send_diagnostic_message(admin_chat_id, diagnostic_report)
                return False
            
            # Шаг 5: Проверка существования чата
            diagnostic_report.append("")
            diagnostic_report.append("5️⃣ <b>Проверка существования чата</b>")
            
            if validated_chat_id in self.config.CHAT_SUBSCRIPTIONS:
                current_tier = self.config.CHAT_SUBSCRIPTIONS[validated_chat_id]['tier']
                diagnostic_report.append(f"⚠️ Чат уже существует с тарифом {current_tier}")
                diagnostic_report.append("💡 Используйте /admin upgrade_chat для изменения тарифа")
                await self._send_diagnostic_message(admin_chat_id, diagnostic_report)
                return False
            else:
                diagnostic_report.append("✅ Чат не существует, можно добавлять")
            
            # Шаг 6: Попытка добавления
            diagnostic_report.append("")
            diagnostic_report.append("6️⃣ <b>Попытка добавления чата</b>")
            
            try:
                success = self.config.add_chat(validated_chat_id, tier, is_admin=False)
                
                if success:
                    # Дополнительная информация
                    self.config.CHAT_SUBSCRIPTIONS[validated_chat_id].update({
                        'admin_notes': notes,
                        'added_by': admin_chat_id,
                        'added_at': datetime.now().isoformat()
                    })
                    
                    diagnostic_report.append("✅ Чат успешно добавлен в конфигурацию!")
                    
                    # Проверяем сохранение в файл
                    if hasattr(self.config, '_save_chat_configuration'):
                        save_success = self.config._save_chat_configuration()
                        if save_success:
                            diagnostic_report.append("✅ Конфигурация сохранена в файл")
                        else:
                            diagnostic_report.append("⚠️ Ошибка сохранения в файл")
                    
                    diagnostic_report.append("")
                    diagnostic_report.append(f"📊 <b>Результат:</b>")
                    diagnostic_report.append(f"• Chat ID: {validated_chat_id}")
                    diagnostic_report.append(f"• Тариф: {tier}")
                    diagnostic_report.append(f"• Всего чатов: {len(self.config.CHAT_SUBSCRIPTIONS)}")
                    
                else:
                    diagnostic_report.append("❌ Ошибка добавления чата в конфигурацию")
                
            except Exception as e:
                diagnostic_report.append(f"❌ Исключение при добавлении: {e}")
                logger.error(f"Ошибка добавления чата: {e}")
            
            # Шаг 7: Тест отправки приветствия
            if success:
                diagnostic_report.append("")
                diagnostic_report.append("7️⃣ <b>Тест отправки приветствия</b>")
                
                try:
                    welcome_message = f"🎉 Добро пожаловать! Вы подключены с тарифом {tier}"
                    welcome_sent = await self.telegram_bot._send_message(welcome_message, validated_chat_id)
                    
                    if welcome_sent:
                        diagnostic_report.append("✅ Приветственное сообщение отправлено")
                    else:
                        diagnostic_report.append("⚠️ Не удалось отправить приветствие")
                        diagnostic_report.append("💡 Возможные причины:")
                        diagnostic_report.append("  • Бот заблокирован пользователем")
                        diagnostic_report.append("  • Неверный Chat ID")
                        diagnostic_report.append("  • Пользователь не начал диалог с ботом")
                        
                except Exception as e:
                    diagnostic_report.append(f"❌ Ошибка отправки приветствия: {e}")
            
            await self._send_diagnostic_message(admin_chat_id, diagnostic_report)
            return success
            
        except Exception as e:
            diagnostic_report.append("")
            diagnostic_report.append(f"💥 <b>КРИТИЧЕСКАЯ ОШИБКА: {e}</b>")
            logger.error(f"Критическая ошибка диагностики: {e}")
            await self._send_diagnostic_message(admin_chat_id, diagnostic_report)
            return False
    
    async def test_bot_responsiveness(self, admin_chat_id: str):
        """Тест отзывчивости бота"""
        
        test_report = []
        test_report.append("🧪 <b>ТЕСТ ОТЗЫВЧИВОСТИ БОТА</b>")
        test_report.append("")
        
        # Тест 1: Простая отправка сообщения
        test_report.append("1️⃣ <b>Тест отправки сообщения</b>")
        try:
            success = await self.telegram_bot._send_message("🤖 Тест-сообщение", admin_chat_id)
            if success:
                test_report.append("✅ Отправка работает")
            else:
                test_report.append("❌ Ошибка отправки")
        except Exception as e:
            test_report.append(f"❌ Исключение: {e}")
        
        # Тест 2: Проверка конфигурации
        test_report.append("")
        test_report.append("2️⃣ <b>Тест конфигурации</b>")
        test_report.append(f"• Всего чатов: {len(self.config.CHAT_SUBSCRIPTIONS)}")
        test_report.append(f"• Ваш статус: {'Админ' if self.config.CHAT_SUBSCRIPTIONS.get(admin_chat_id, {}).get('is_admin', False) else 'Пользователь'}")
        
        # Тест 3: Проверка доступных тарифов
        test_report.append("")
        test_report.append("3️⃣ <b>Доступные тарифы</b>")
        for tier in self.config.SUBSCRIPTION_TIERS.keys():
            test_report.append(f"• {tier}")
        
        await self._send_diagnostic_message(admin_chat_id, test_report)
    
    async def _send_diagnostic_message(self, chat_id: str, message_parts: List[str]):
        """Отправка диагностического сообщения"""
        message = "\n".join(message_parts)
        
        # Разбиваем длинные сообщения
        if len(message) > 4000:
            chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
            for chunk in chunks:
                await self.telegram_bot._send_message(chunk, chat_id)
                await asyncio.sleep(0.5)
        else:
            await self.telegram_bot._send_message(message, chat_id)

# Добавьте эти команды в enhanced_telegram_bot.py

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

# Обновленная справка админских команд
ADMIN_HELP_TEXT = """👑 <b>АДМИНСКИЕ КОМАНДЫ</b>

👥 <b>Управление чатами:</b>
/admin add_chat CHAT_ID TIER [NOTES] - добавить чат
/admin remove_chat CHAT_ID - удалить чат  
/admin upgrade_chat CHAT_ID TIER - изменить тариф
/admin list_chats - список всех чатов
/admin chat_info CHAT_ID - информация о чате

🔧 <b>Диагностика:</b>
/admin diagnose add_chat CHAT_ID TIER - диагностика команды
/admin test_bot - тест работы бота

📢 <b>Рассылка:</b>
/admin broadcast MESSAGE - отправить во все чаты

💡 <b>Если команда не работает:</b>
1. Используйте /admin test_bot для проверки
2. Используйте /admin diagnose add_chat для диагностики
3. Проверьте логи бота"""

# Инструкция по использованию
"""
Если команда /admin add_chat не работает:

1. Сначала проверьте работу бота:
   /admin test_bot

2. Затем продиагностируйте конкретную команду:
   /admin diagnose add_chat 1857921803 BASIC

3. Система покажет где именно проблема!
"""