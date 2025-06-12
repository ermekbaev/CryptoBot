# persistent_config_system.py - Система сохранения конфигурации

import json
import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
import asyncio
from pathlib import Path
import shutil

logger = logging.getLogger(__name__)

class PersistentConfigManager:
    """Менеджер для сохранения конфигурации чатов в файл"""
    
    def __init__(self, config_file: str = "chat_subscriptions.json"):
        self.config_file = Path(config_file)
        self.backup_dir = Path("config_backups")
        self.backup_dir.mkdir(exist_ok=True)
        
    def save_subscriptions(self, subscriptions: Dict) -> bool:
        """Сохранение подписок в файл"""
        try:
            # Создаем бэкап текущего файла
            if self.config_file.exists():
                backup_name = f"chat_subscriptions_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                backup_path = self.backup_dir / backup_name
                shutil.copy2(self.config_file, backup_path)
                
                # Оставляем только последние 10 бэкапов
                self._cleanup_backups()
            
            # Подготавливаем данные для сохранения
            save_data = {
                'last_updated': datetime.now().isoformat(),
                'version': '1.0',
                'subscriptions': subscriptions
            }
            
            # Сохраняем в файл
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Конфигурация сохранена в {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка сохранения конфигурации: {e}")
            return False
    
    def load_subscriptions(self) -> Dict:
        """Загрузка подписок из файла"""
        try:
            if not self.config_file.exists():
                logger.info("Файл конфигурации не найден, создаем новый")
                return {}
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Проверяем структуру файла
            if 'subscriptions' in data:
                subscriptions = data['subscriptions']
                logger.info(f"Загружено {len(subscriptions)} подписок из файла")
                return subscriptions
            else:
                # Старый формат файла
                logger.warning("Обнаружен старый формат файла конфигурации")
                return data if isinstance(data, dict) else {}
                
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}")
            return {}
    
    def _cleanup_backups(self):
        """Очистка старых бэкапов"""
        try:
            backup_files = list(self.backup_dir.glob("chat_subscriptions_backup_*.json"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Удаляем файлы старше 10
            for backup_file in backup_files[10:]:
                backup_file.unlink()
                logger.debug(f"Удален старый бэкап: {backup_file}")
                
        except Exception as e:
            logger.error(f"Ошибка очистки бэкапов: {e}")

class EnhancedTradingConfig:
    """Улучшенная конфигурация с автосохранением"""
    
    def __init__(self):
        # Базовые настройки из переменных окружения
        self.BYBIT_API_KEY = os.getenv('BYBIT_API_KEY', '')
        self.BYBIT_SECRET_KEY = os.getenv('BYBIT_SECRET_KEY', '')
        self.TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
        
        # Менеджер сохранения
        self.config_manager = PersistentConfigManager()
        
        # Торговые параметры
        self.MIN_CONFIDENCE_LEVEL = float(os.getenv('MIN_CONFIDENCE_LEVEL', '75.0'))
        self.MAX_RISK_PER_TRADE = float(os.getenv('MAX_RISK_PER_TRADE', '2.0'))
        self.MAX_LEVERAGE = int(os.getenv('MAX_LEVERAGE', '5'))
        self.MIN_VOLUME_USDT = float(os.getenv('MIN_VOLUME_USDT', '100000'))
        
        # Технические параметры
        self.RSI_PERIOD = 14
        self.MACD_FAST = 12
        self.MACD_SLOW = 26
        self.MACD_SIGNAL = 9
        self.BB_PERIOD = 20
        self.BB_STD = 2.0
        self.EMA_PERIODS = [9, 21, 50, 100, 200]
        
        # Временные рамки для анализа
        self.ANALYSIS_TIMEFRAMES = ['1h', '4h', '1d']
        self.PRIMARY_TIMEFRAME = os.getenv('PRIMARY_TIMEFRAME', '4h')
        
        # Торговые пары
        trading_pairs_env = os.getenv('TRADING_PAIRS', '')
        if trading_pairs_env:
            self.TRADING_PAIRS = [pair.strip() for pair in trading_pairs_env.split(',')]
        else:
            self.TRADING_PAIRS = [
                'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'SOLUSDT',
                'LINKUSDT', 'DOTUSDT', 'UNIUSDT', 'AAVEUSDT', 'MKRUSDT', 'SUSHIUSDT',
                'AVAXUSDT', 'MATICUSDT', 'FTMUSDT', 'ATOMUSDT', 'NEARUSDT', 'ALGOUSDT',
                'DOGEUSDT', 'SHIBUSDT', 'PEPEUSDT', '1000PEPEUSDT', 'FLOKIUSDT',
                'CETUSUSDT', 'OPUSDT', 'SLERFUSDT', 'SXTUSDT', 'APTUSDT', 'APEUSDT'
            ]
        
        # Категоризация пар
        self.PAIR_CATEGORIES = {
            'major': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'SOLUSDT'],
            'defi': ['LINKUSDT', 'UNIUSDT', 'AAVEUSDT', 'MKRUSDT', 'SUSHIUSDT', 'CRVUSDT'],
            'layer1': ['DOTUSDT', 'AVAXUSDT', 'MATICUSDT', 'FTMUSDT', 'ATOMUSDT', 'NEARUSDT', 'APTUSDT', 'SUIUSDT'],
            'meme': ['DOGEUSDT', 'SHIBUSDT', 'PEPEUSDT', '1000PEPEUSDT', 'FLOKIUSDT', 'MEMEUSDT'],
            'gaming_nft': ['APEUSDT', 'SANDUSDT', 'MANAUSDT', 'GALAUSDT', 'ENJUSDT', 'CHZUSDT', 'AXSUSDT'],
            'emerging': ['CETUSUSDT', 'SLERFUSDT', 'SXTUSDT', 'AUCTIONUSDT', 'TIAUSDT', 'FLMUSDT'],
            'altcoins': ['LTCUSDT', 'BCHUSDT', 'ETCUSDT', 'XLMUSDT', 'VETUSDT', 'ICPUSDT', 'LDOUSDT', 'ARBUSDT', 'OPUSDT']
        }
        
        # Минимальные объемы по категориям
        self.MIN_VOLUMES_BY_CATEGORY = {
            'major': 1000000000,
            'defi': 100000000,
            'layer1': 200000000,
            'meme': 50000000,
            'gaming_nft': 30000000,
            'emerging': 10000000,
            'altcoins': 50000000
        }
        
        # Система подписок
        self.SUBSCRIPTION_TIERS = {
            'FREE': {
                'max_signals_per_day': 3,
                'categories_allowed': ['major'],
                'features': ['basic_signals'],
                'cooldown_minutes': 120
            },
            'BASIC': {
                'max_signals_per_day': 10,
                'categories_allowed': ['major', 'defi', 'layer1', 'altcoins'],
                'features': ['basic_signals', 'technical_analysis'],
                'cooldown_minutes': 60
            },
            'PREMIUM': {
                'max_signals_per_day': 25,
                'categories_allowed': ['major', 'defi', 'layer1', 'gaming_nft', 'altcoins'],
                'features': ['basic_signals', 'technical_analysis', 'fundamental_analysis'],
                'cooldown_minutes': 30
            },
            'VIP': {
                'max_signals_per_day': -1,
                'categories_allowed': ['major', 'defi', 'layer1', 'meme', 'gaming_nft', 'emerging', 'altcoins'],
                'features': ['basic_signals', 'technical_analysis', 'fundamental_analysis', 'priority_support'],
                'cooldown_minutes': 15
            }
        }
        
        # Загружаем конфигурацию чатов
        self._load_chat_configuration()
        
        # Общие настройки
        self.SEND_ALERTS_ONLY = os.getenv('SEND_ALERTS_ONLY', 'False').lower() == 'true'
        self.DEFAULT_ALERT_COOLDOWN_MINUTES = int(os.getenv('ALERT_COOLDOWN_MINUTES', '60'))
    
    def _load_chat_configuration(self):
        """Загрузка конфигурации чатов"""
        
        # Сначала загружаем из файла (приоритет)
        file_subscriptions = self.config_manager.load_subscriptions()
        
        # Затем дополняем из переменных окружения
        env_subscriptions = self._load_from_env()
        
        # Объединяем (файл имеет приоритет)
        self.CHAT_SUBSCRIPTIONS = {**env_subscriptions, **file_subscriptions}
        
        logger.info(f"Загружено {len(self.CHAT_SUBSCRIPTIONS)} подписок чатов")
        
        # Если есть подписки, которых нет в файле, сохраняем
        if env_subscriptions and not file_subscriptions:
            self._save_chat_configuration()
    
    def _load_from_env(self) -> Dict:
        """Загрузка из переменных окружения (для обратной совместимости)"""
        subscriptions = {}
        
        # Основной чат администратора
        admin_chat = os.getenv('TELEGRAM_CHAT_ID', '')
        if admin_chat:
            subscriptions[admin_chat] = {
                'tier': 'VIP',
                'is_admin': True,
                'active': True,
                'signals_sent_today': 0,
                'last_signal_time': None,
                'allowed_features': self.SUBSCRIPTION_TIERS['VIP']['features'],
                'custom_settings': {},
                'source': 'env'
            }
        
        # Дополнительные чаты
        additional_chats_str = os.getenv('TELEGRAM_ADDITIONAL_CHATS', '')
        if additional_chats_str:
            additional_chats = [chat.strip() for chat in additional_chats_str.split(',') if chat.strip()]
            for chat in additional_chats:
                if chat not in subscriptions:
                    subscriptions[chat] = {
                        'tier': 'BASIC',
                        'is_admin': False,
                        'active': True,
                        'signals_sent_today': 0,
                        'last_signal_time': None,
                        'allowed_features': self.SUBSCRIPTION_TIERS['BASIC']['features'],
                        'custom_settings': {},
                        'source': 'env'
                    }
        
        # JSON конфигурация из .env
        custom_subscriptions_str = os.getenv('TELEGRAM_SUBSCRIPTIONS', '')
        if custom_subscriptions_str:
            try:
                custom_subscriptions = json.loads(custom_subscriptions_str)
                for chat_id, settings in custom_subscriptions.items():
                    if chat_id in subscriptions:
                        subscriptions[chat_id].update(settings)
                    else:
                        subscriptions[chat_id] = {
                            **settings,
                            'signals_sent_today': 0,
                            'last_signal_time': None,
                            'allowed_features': self.SUBSCRIPTION_TIERS.get(settings.get('tier', 'FREE'), {}).get('features', []),
                            'custom_settings': {},
                            'source': 'env'
                        }
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка парсинга TELEGRAM_SUBSCRIPTIONS: {e}")
        
        return subscriptions
    
    def _save_chat_configuration(self) -> bool:
        """Сохранение конфигурации чатов в файл"""
        return self.config_manager.save_subscriptions(self.CHAT_SUBSCRIPTIONS)
    
    # ===== МЕТОДЫ ДЛЯ РАБОТЫ С ЧАТАМИ (с автосохранением) =====
    
    def add_chat(self, chat_id: str, tier: str = 'FREE', is_admin: bool = False) -> bool:
        """Добавление нового чата с автосохранением"""
        if tier not in self.SUBSCRIPTION_TIERS:
            return False
        
        self.CHAT_SUBSCRIPTIONS[chat_id] = {
            'tier': tier,
            'is_admin': is_admin,
            'active': True,
            'signals_sent_today': 0,
            'last_signal_time': None,
            'allowed_features': self.SUBSCRIPTION_TIERS[tier]['features'],
            'custom_settings': {},
            'added_at': datetime.now().isoformat(),
            'source': 'admin_command'
        }
        
        # АВТОСОХРАНЕНИЕ
        success = self._save_chat_configuration()
        if success:
            logger.info(f"Чат {chat_id} добавлен с тарифом {tier} и сохранен в файл")
        else:
            logger.error(f"Чат {chat_id} добавлен, но не удалось сохранить в файл")
        
        return True
    
    def remove_chat(self, chat_id: str) -> bool:
        """Удаление чата с автосохранением"""
        if chat_id in self.CHAT_SUBSCRIPTIONS:
            del self.CHAT_SUBSCRIPTIONS[chat_id]
            
            # АВТОСОХРАНЕНИЕ
            success = self._save_chat_configuration()
            if success:
                logger.info(f"Чат {chat_id} удален и изменения сохранены")
            else:
                logger.error(f"Чат {chat_id} удален, но не удалось сохранить изменения")
            
            return True
        return False
    
    def upgrade_chat(self, chat_id: str, new_tier: str) -> bool:
        """Обновление уровня подписки с автосохранением"""
        if chat_id not in self.CHAT_SUBSCRIPTIONS:
            return False
        
        if new_tier not in self.SUBSCRIPTION_TIERS:
            return False
        
        self.CHAT_SUBSCRIPTIONS[chat_id]['tier'] = new_tier
        self.CHAT_SUBSCRIPTIONS[chat_id]['allowed_features'] = self.SUBSCRIPTION_TIERS[new_tier]['features']
        self.CHAT_SUBSCRIPTIONS[chat_id]['upgraded_at'] = datetime.now().isoformat()
        
        # АВТОСОХРАНЕНИЕ
        success = self._save_chat_configuration()
        if success:
            logger.info(f"Тариф чата {chat_id} изменен на {new_tier} и сохранен")
        else:
            logger.error(f"Тариф чата {chat_id} изменен, но не удалось сохранить")
        
        return True
    
    def update_chat_signal_count(self, chat_id: str):
        """Обновление счетчика сигналов с автосохранением"""
        if chat_id in self.CHAT_SUBSCRIPTIONS:
            if not self.CHAT_SUBSCRIPTIONS[chat_id].get('is_admin', False):
                self.CHAT_SUBSCRIPTIONS[chat_id]['signals_sent_today'] = \
                    self.CHAT_SUBSCRIPTIONS[chat_id].get('signals_sent_today', 0) + 1
                self.CHAT_SUBSCRIPTIONS[chat_id]['last_signal_time'] = datetime.now().isoformat()
                
                # Сохраняем только каждые 5 сигналов, чтобы не перегружать диск
                signal_count = self.CHAT_SUBSCRIPTIONS[chat_id]['signals_sent_today']
                if signal_count % 5 == 0:
                    self._save_chat_configuration()
    
    # ===== МЕТОДЫ ДЛЯ ЧТЕНИЯ (без изменений) =====
    
    def get_authorized_chats(self) -> List[str]:
        """Получение списка авторизованных чатов"""
        return [chat_id for chat_id, settings in self.CHAT_SUBSCRIPTIONS.items() 
                if settings.get('active', False)]
    
    def get_chat_tier(self, chat_id: str) -> str:
        """Получение уровня подписки чата"""
        return self.CHAT_SUBSCRIPTIONS.get(chat_id, {}).get('tier', 'FREE')
    
    def is_chat_authorized(self, chat_id: str) -> bool:
        """Проверка авторизации чата"""
        return chat_id in self.CHAT_SUBSCRIPTIONS and \
               self.CHAT_SUBSCRIPTIONS[chat_id].get('active', False)
    
    def can_receive_signal(self, chat_id: str, category: str) -> tuple[bool, str]:
        """Проверка возможности получения сигнала для чата"""
        if not self.is_chat_authorized(chat_id):
            return False, "Чат не авторизован"
        
        chat_settings = self.CHAT_SUBSCRIPTIONS[chat_id]
        
        if chat_settings.get('is_admin', False):
            return True, "OK (Admin - unlimited access)"
        
        tier = chat_settings['tier']
        tier_settings = self.SUBSCRIPTION_TIERS.get(tier, self.SUBSCRIPTION_TIERS['FREE'])
        
        if category == 'other':
            if tier in ['VIP', 'PREMIUM']:
                return True, f"OK (Category 'other' allowed for {tier})"
            else:
                return False, f"Категория 'other' доступна только для PREMIUM/VIP"
        
        if category not in tier_settings['categories_allowed']:
            return False, f"Категория '{category}' недоступна для уровня '{tier}'"
        
        max_signals = tier_settings['max_signals_per_day']
        if max_signals > 0:
            signals_today = chat_settings.get('signals_sent_today', 0)
            if signals_today >= max_signals:
                return False, f"Достигнут дневной лимит сигналов ({max_signals})"
        
        return True, "OK"
    
    def get_cooldown_minutes(self, chat_id: str) -> int:
        """Получение времени ожидания для чата"""
        if not self.is_chat_authorized(chat_id):
            return self.DEFAULT_ALERT_COOLDOWN_MINUTES
        
        if self.CHAT_SUBSCRIPTIONS[chat_id].get('is_admin', False):
            return 0
        
        tier = self.get_chat_tier(chat_id)
        tier_settings = self.SUBSCRIPTION_TIERS.get(tier, self.SUBSCRIPTION_TIERS['FREE'])
        return tier_settings.get('cooldown_minutes', self.DEFAULT_ALERT_COOLDOWN_MINUTES)

# Инструкция по интеграции
"""
ЗАМЕНИТЕ в enhanced_main.py:

БЫЛО:
from config import TradingConfig

СТАЛО:
from persistent_config_system import EnhancedTradingConfig as TradingConfig

Теперь все изменения через админские команды будут сохраняться в файл chat_subscriptions.json
и восстанавливаться после перезапуска бота!
"""