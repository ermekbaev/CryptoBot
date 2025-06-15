# enhanced_persistent_config_system.py - ОБЪЕДИНЕННАЯ УЛУЧШЕННАЯ ВЕРСИЯ

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
                'version': '2.0',  # Обновленная версия
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
    """Улучшенная конфигурация с автосохранением - ОБЪЕДИНЕННАЯ ВЕРСИЯ"""
    
    def __init__(self):
        # Базовые настройки из переменных окружения
        self.BYBIT_API_KEY = os.getenv('BYBIT_API_KEY', '')
        self.BYBIT_SECRET_KEY = os.getenv('BYBIT_SECRET_KEY', '')
        self.TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
        
        # Менеджер сохранения
        self.config_manager = PersistentConfigManager()
        
        # Торговые параметры (с поддержкой тестового режима)
        test_mode = os.getenv('TEST_MODE', 'False').lower() == 'true'
        
        if test_mode:
            logger.info("🧪 ТЕСТОВЫЙ РЕЖИМ: Снижены требования для генерации сигналов")
            self.MIN_CONFIDENCE_LEVEL = float(os.getenv('MIN_CONFIDENCE_LEVEL', '45.0'))  # Снижено с 75
            self.MAX_RISK_PER_TRADE = float(os.getenv('MAX_RISK_PER_TRADE', '3.0'))      # Увеличено с 2
            self.MIN_VOLUME_USDT = float(os.getenv('MIN_VOLUME_USDT', '10000000'))       # 10M вместо 100M
        else:
            self.MIN_CONFIDENCE_LEVEL = float(os.getenv('MIN_CONFIDENCE_LEVEL', '70.0'))
            self.MAX_RISK_PER_TRADE = float(os.getenv('MAX_RISK_PER_TRADE', '2.0'))
            self.MIN_VOLUME_USDT = float(os.getenv('MIN_VOLUME_USDT', '50000000'))       # 50M вместо 100M
        
        self.MAX_LEVERAGE = int(os.getenv('MAX_LEVERAGE', '5'))
        
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
        
        # ОБЪЕДИНЕННЫЙ список торговых пар (лучшее из обеих версий)
        trading_pairs_env = os.getenv('TRADING_PAIRS', '')
        if trading_pairs_env:
            self.TRADING_PAIRS = [pair.strip() for pair in trading_pairs_env.split(',')]
        else:
            self.TRADING_PAIRS = [
                # ===== ТОП КРИПТОВАЛЮТЫ (проверенные временем) =====
                'BTCUSDT',      # Bitcoin - цифровое золото
                'ETHUSDT',      # Ethereum - лидер смарт-контрактов
                'BNBUSDT',      # Binance Coin - биржевой токен #1
                'XRPUSDT',      # Ripple - банковские решения
                'ADAUSDT',      # Cardano - академический подход
                'SOLUSDT',      # Solana - высокая производительность
                
                # ===== DEFI ЛИДЕРЫ (расширенный список) =====
                'LINKUSDT',     # Chainlink - оракулы №1
                'UNIUSDT',      # Uniswap - ведущий DEX
                'AAVEUSDT',     # Aave - лидер DeFi кредитования
                'MKRUSDT',      # Maker - создатель DAI
                'CRVUSDT',      # Curve - стейблкоин ликвидность
                'SUSHIUSDT',    # SushiSwap - мультичейн DEX
                'GRTUSDT',      # The Graph - Web3 индексирование данных
                'COMPUSDT',     # Compound - автономное кредитование  
                'SNXUSDT',      # Synthetix - синтетические активы
                'YFIUSDT',      # Yearn Finance - yield оптимизация
                '1INCHUSDT',    # 1inch - DEX агрегатор

                # ===== LAYER 1 БЛОКЧЕЙНЫ (расширенный список) =====
                'DOTUSDT',      # Polkadot - парачейны
                'AVAXUSDT',     # Avalanche - быстрые транзакции
                'MATICUSDT',    # Polygon - L2 для Ethereum
                'ATOMUSDT',     # Cosmos - интернет блокчейнов
                'NEARUSDT',     # Near Protocol - масштабируемая сеть
                'FTMUSDT',      # Fantom - DAG платформа
                'APTUSDT',      # Aptos - новый Layer 1
                'SUIUSDT',      # Sui - параллельный блокчейн
                'XTZUSDT',      # Tezos - самообновляемая сеть
                'ALGOUSDT',     # Algorand - чистый PoS
                'TRXUSDT',      # Tron - контент платформа
                'EOSUSDT',      # EOS - смарт-контракты
                'THETAUSDT',    # Theta - видео стриминг

                # ===== МЕМКОИНЫ (популярные) =====
                'DOGEUSDT',     # Dogecoin - оригинальный мем
                'SHIBUSDT',     # Shiba Inu - убийца Doge
                'PEPEUSDT',     # Pepe - мем 2023
                '1000PEPEUSDT', # Pepe альтернатива
                'FLOKIUSDT',    # Floki - мем с утилитой

                # ===== GAMING/NFT ТОКЕНЫ =====
                'APEUSDT',      # ApeCoin - Bored Apes
                'SANDUSDT',     # The Sandbox - метавселенная
                'MANAUSDT',     # Decentraland - виртуальный мир
                'GALAUSDT',     # Gala Games - игровая платформа
                'ENJUSDT',      # Enjin - NFT платформа
                'CHZUSDT',      # Chiliz - спортивные токены
                'AXSUSDT',      # Axie Infinity - игра

                # ===== НОВЫЕ ПРОЕКТЫ =====
                'CETUSUSDT',    # Cetus - DeFi на Sui
                'SLERFUSDT',    # Slerf - новый мем
                'SXTUSDT',      # Space and Time - децентрализованная БД
                'AUCTIONUSDT',  # Bounce - аукционная платформа
                'TIAUSDT',      # Celestia - модульный блокчейн
                'FLMUSDT',      # Flamingo - кросс-чейн протокол

                # ===== ТРАДИЦИОННЫЕ АЛЬТКОИНЫ =====
                'LTCUSDT',      # Litecoin - цифровое серебро
                'BCHUSDT',      # Bitcoin Cash - быстрые платежи
                'ETCUSDT',      # Ethereum Classic - оригинальный ETH
                'XLMUSDT',      # Stellar - трансграничные платежи
                'VETUSDT',      # VeChain - supply chain
                'ICPUSDT',      # Internet Computer - веб3 вычисления
                'FILUSDT',      # Filecoin - децентрализованное хранение
                'INJUSDT',      # Injective - деривативы
                'RUNEUSDT',     # THORChain - кросс-чейн DEX
                'LDOUSDT',      # Lido DAO - liquid staking
                'ARBUSDT',      # Arbitrum - L2 решение
                'OPUSDT',       # Optimism - L2 решение
            ]
        
        # УЛУЧШЕННАЯ категоризация (объединенная)
        self.PAIR_CATEGORIES = {
            'major': [
                'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'SOLUSDT'
            ],
            'defi': [
                'LINKUSDT', 'UNIUSDT', 'AAVEUSDT', 'MKRUSDT', 'SUSHIUSDT', 'CRVUSDT', 
                'GRTUSDT', 'COMPUSDT', 'SNXUSDT', 'YFIUSDT', '1INCHUSDT'
            ],
            'layer1': [
                'DOTUSDT', 'AVAXUSDT', 'MATICUSDT', 'FTMUSDT', 'ATOMUSDT', 'NEARUSDT',
                'APTUSDT', 'SUIUSDT', 'ALGOUSDT', 'TRXUSDT', 'EOSUSDT', 'THETAUSDT',
                'XTZUSDT'
            ],
            'meme': [
                'DOGEUSDT', 'SHIBUSDT', 'PEPEUSDT', '1000PEPEUSDT', 'FLOKIUSDT'
            ],
            'gaming_nft': [
                'APEUSDT', 'SANDUSDT', 'MANAUSDT', 'GALAUSDT', 'ENJUSDT', 'CHZUSDT', 'AXSUSDT'
            ],
            'emerging': [
                'CETUSUSDT', 'SLERFUSDT', 'SXTUSDT', 'AUCTIONUSDT', 'TIAUSDT', 'FLMUSDT'
            ],
            'altcoins': [
                'LTCUSDT', 'BCHUSDT', 'ETCUSDT', 'XLMUSDT', 'VETUSDT', 'ICPUSDT',
                'FILUSDT', 'INJUSDT', 'RUNEUSDT', 'LDOUSDT', 'ARBUSDT', 'OPUSDT'
            ]
        }
        
        # ИСПРАВЛЕННЫЕ минимальные объемы (снижены для лучшей генерации сигналов)
        if test_mode:
            logger.info("🧪 ТЕСТОВЫЙ РЕЖИМ: Минимальные объемы значительно снижены")
            self.MIN_VOLUMES_BY_CATEGORY = {
                'major': 100000000,     # 100M вместо 1B
                'defi': 25000000,       # 25M вместо 150M
                'layer1': 50000000,     # 50M вместо 200M
                'meme': 15000000,       # 15M вместо 50M
                'gaming_nft': 10000000, # 10M вместо 30M
                'emerging': 5000000,    # 5M вместо 10M
                'altcoins': 20000000    # 20M вместо 50M
            }
        else:
            logger.info("🎯 ПРОДАКШН РЕЖИМ: Оптимизированные объемы для стабильной генерации")
            self.MIN_VOLUMES_BY_CATEGORY = {
                'major': 100000000,     # 500M вместо 1B (в 2 раза меньше)
                'defi': 20000000,       # 75M вместо 150M (в 2 раза меньше)
                'layer1': 30000000,    # 100M вместо 200M (в 2 раза меньше)
                'meme': 10000000,       # 25M вместо 50M (в 2 раза меньше)
                'gaming_nft': 5000000, # 15M вместо 30M (в 2 раза меньше)
                'emerging': 3000000,    # 5M вместо 10M (в 2 раза меньше)
                'altcoins': 10000000    # 25M вместо 50M (в 2 раза меньше)
            }
        
        # УЛУЧШЕННАЯ система подписок (более гибкая)
        self.SUBSCRIPTION_TIERS = {
            'FREE': {
                'max_signals_per_day': 5,           # Увеличено с 3 до 5
                'categories_allowed': ['major'],
                'features': ['basic_signals'],
                'cooldown_minutes': 90              # Снижено со 120 до 90
            },
            'BASIC': {
                'max_signals_per_day': 15,          # Увеличено с 10 до 15
                'categories_allowed': ['major', 'defi', 'layer1', 'altcoins'],  # Добавлены altcoins
                'features': ['basic_signals', 'technical_analysis'],
                'cooldown_minutes': 45              # Снижено с 60 до 45
            },
            'PREMIUM': {
                'max_signals_per_day': 30,          # Увеличено с 25 до 30
                'categories_allowed': ['major', 'defi', 'layer1', 'gaming_nft', 'altcoins'],
                'features': ['basic_signals', 'technical_analysis', 'fundamental_analysis'],
                'cooldown_minutes': 20              # Снижено с 30 до 20
            },
            'VIP': {
                'max_signals_per_day': -1,          # Безлимитно
                'categories_allowed': ['major', 'defi', 'layer1', 'meme', 'gaming_nft', 'emerging', 'altcoins'],
                'features': ['basic_signals', 'technical_analysis', 'fundamental_analysis', 'priority_support'],
                'cooldown_minutes': 10              # Снижено с 15 до 10
            }
        }
        
        # Загружаем конфигурацию чатов
        self._load_chat_configuration()
        
        # Общие настройки
        self.SEND_ALERTS_ONLY = os.getenv('SEND_ALERTS_ONLY', 'False').lower() == 'true'
        self.DEFAULT_ALERT_COOLDOWN_MINUTES = int(os.getenv('ALERT_COOLDOWN_MINUTES', '45'))  # Снижено с 60
    
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
            try:
                # Поддерживаем как JSON, так и простой список через запятую
                if additional_chats_str.startswith('['):
                    additional_chats = json.loads(additional_chats_str)
                else:
                    additional_chats = [chat.strip() for chat in additional_chats_str.split(',') if chat.strip()]
            except json.JSONDecodeError:
                additional_chats = [chat.strip() for chat in additional_chats_str.split(',') if chat.strip()]
            
            for chat in additional_chats:
                if chat not in subscriptions:
                    subscriptions[chat] = {
                        'tier': 'BASIC',  # По умолчанию BASIC для дополнительных чатов
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
    
    # ===== МЕТОДЫ ДЛЯ ЧТЕНИЯ (улучшенные) =====
    
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
        """ИСПРАВЛЕННАЯ проверка возможности получения сигнала для чата"""
        if not self.is_chat_authorized(chat_id):
            return False, "Чат не авторизован"
        
        chat_settings = self.CHAT_SUBSCRIPTIONS[chat_id]
        
        # Администраторы получают ВСЕ сигналы без ограничений
        if chat_settings.get('is_admin', False):
            return True, "OK (Admin - unlimited access)"
        
        tier = chat_settings['tier']
        tier_settings = self.SUBSCRIPTION_TIERS.get(tier, self.SUBSCRIPTION_TIERS['FREE'])
        
        # УЛУЧШЕННАЯ обработка категории 'other' - разрешаем для всех BASIC+
        if category == 'other':
            if tier in ['VIP', 'PREMIUM', 'BASIC']:  # Добавили BASIC
                return True, f"OK (Category 'other' allowed for {tier})"
            else:
                return False, f"Категория 'other' доступна только для BASIC/PREMIUM/VIP"
        
        # Проверяем категорию
        if category not in tier_settings['categories_allowed']:
            return False, f"Категория '{category}' недоступна для уровня '{tier}'"
        
        # Проверяем лимит сигналов
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

# ===== ДОПОЛНИТЕЛЬНЫЕ КОНСТАНТЫ И НАСТРОЙКИ =====

# Паттерны свечей для распознавания (из config.py)
CANDLESTICK_PATTERNS = {
    'bullish': [
        'hammer', 'inverted_hammer', 'bullish_engulfing', 
        'piercing_line', 'morning_star', 'three_white_soldiers'
    ],
    'bearish': [
        'hanging_man', 'shooting_star', 'bearish_engulfing',
        'dark_cloud_cover', 'evening_star', 'three_black_crows'
    ]
}

# Веса для различных индикаторов при расчете общего сигнала
INDICATOR_WEIGHTS = {
    'trend_following': 0.25,    # Трендовые индикаторы (EMA, MACD)
    'momentum': 0.20,           # Моментум (RSI, Stochastic)
    'volatility': 0.15,         # Волатильность (Bollinger Bands)
    'volume': 0.15,             # Объемные индикаторы
    'candlestick': 0.15,        # Свечные паттерны
    'support_resistance': 0.10   # Уровни поддержки/сопротивления
}

# Настройки для различных типов рынка
MARKET_CONDITIONS = {
    'trending': {
        'min_trend_strength': 0.6,
        'preferred_indicators': ['MACD', 'EMA', 'ADX']
    },
    'ranging': {
        'max_trend_strength': 0.4,
        'preferred_indicators': ['RSI', 'Stochastic', 'BB']
    },
    'volatile': {
        'min_volatility': 0.02,
        'risk_multiplier': 0.5
    }
}

# УЛУЧШЕННЫЕ настройки для специфичных пар (расширенный список)
PAIR_SPECIFIC_SETTINGS = {
    # ===== МЕМКОИНЫ - агрессивная торговля =====
    'DOGEUSDT': {
        'max_leverage': 3,
        'min_confidence': 70.0,         # Снижено с 80
        'volatility_threshold': 0.15,
        'min_volume_multiplier': 0.8    # Снижен множитель
    },
    'SHIBUSDT': {
        'max_leverage': 3,
        'min_confidence': 70.0,         # Снижено с 80
        'volatility_threshold': 0.15,
        'min_volume_multiplier': 0.8
    },
    'PEPEUSDT': {
        'max_leverage': 2,
        'min_confidence': 75.0,         # Снижено с 85
        'volatility_threshold': 0.20,
        'min_volume_multiplier': 0.7
    },
    '1000PEPEUSDT': {
        'max_leverage': 2,
        'min_confidence': 75.0,
        'volatility_threshold': 0.20,
        'min_volume_multiplier': 0.7
    },
    'FLOKIUSDT': {
        'max_leverage': 3,
        'min_confidence': 70.0,
        'volatility_threshold': 0.18,
        'min_volume_multiplier': 0.8
    },
    
    # ===== DEFI ТОКЕНЫ - консервативная торговля =====
    'LINKUSDT': {
        'max_leverage': 5,
        'min_confidence': 65.0,         # Снижено с 70
        'volatility_threshold': 0.08,
        'min_volume_multiplier': 0.9
    },
    'AAVEUSDT': {
        'max_leverage': 5,
        'min_confidence': 65.0,
        'volatility_threshold': 0.08,
        'min_volume_multiplier': 0.9
    },
    'UNIUSDT': {
        'max_leverage': 4,
        'min_confidence': 65.0,
        'volatility_threshold': 0.10,
        'min_volume_multiplier': 0.9
    },
    'MKRUSDT': {
        'max_leverage': 4,
        'min_confidence': 68.0,
        'volatility_threshold': 0.12,
        'min_volume_multiplier': 1.0
    },
    
    # ===== НОВЫЕ ПРОЕКТЫ - осторожная торговля =====
    'CETUSUSDT': {
        'max_leverage': 2,
        'min_confidence': 75.0,         # Снижено с 85
        'volatility_threshold': 0.25,
        'min_volume_multiplier': 1.5    # Снижено с 2.0
    },
    'SLERFUSDT': {
        'max_leverage': 2,
        'min_confidence': 75.0,
        'volatility_threshold': 0.25,
        'min_volume_multiplier': 1.5
    },
    'SXTUSDT': {
        'max_leverage': 3,
        'min_confidence': 70.0,
        'volatility_threshold': 0.20,
        'min_volume_multiplier': 1.2
    },
    'TIAUSDT': {
        'max_leverage': 4,
        'min_confidence': 68.0,
        'volatility_threshold': 0.15,
        'min_volume_multiplier': 1.0
    },
    
    # ===== GAMING/NFT ТОКЕНЫ =====
    'APEUSDT': {
        'max_leverage': 3,
        'min_confidence': 68.0,
        'volatility_threshold': 0.15,
        'min_volume_multiplier': 0.9
    },
    'SANDUSDT': {
        'max_leverage': 4,
        'min_confidence': 65.0,
        'volatility_threshold': 0.12,
        'min_volume_multiplier': 0.9
    },
    'MANAUSDT': {
        'max_leverage': 4,
        'min_confidence': 65.0,
        'volatility_threshold': 0.12,
        'min_volume_multiplier': 0.9
    },
    
    # ===== LAYER 1 БЛОКЧЕЙНЫ =====
    'AVAXUSDT': {
        'max_leverage': 5,
        'min_confidence': 62.0,
        'volatility_threshold': 0.10,
        'min_volume_multiplier': 0.8
    },
    'DOTUSDT': {
        'max_leverage': 5,
        'min_confidence': 62.0,
        'volatility_threshold': 0.10,
        'min_volume_multiplier': 0.8
    },
    'MATICUSDT': {
        'max_leverage': 5,
        'min_confidence': 60.0,
        'volatility_threshold': 0.08,
        'min_volume_multiplier': 0.7
    },
    'ATOMUSDT': {
        'max_leverage': 4,
        'min_confidence': 65.0,
        'volatility_threshold': 0.12,
        'min_volume_multiplier': 0.9
    },
    'NEARUSDT': {
        'max_leverage': 4,
        'min_confidence': 65.0,
        'volatility_threshold': 0.12,
        'min_volume_multiplier': 0.9
    },
    'APTUSDT': {
        'max_leverage': 4,
        'min_confidence': 68.0,
        'volatility_threshold': 0.15,
        'min_volume_multiplier': 1.0
    },
    'SUIUSDT': {
        'max_leverage': 4,
        'min_confidence': 68.0,
        'volatility_threshold': 0.15,
        'min_volume_multiplier': 1.0
    }
}

# ===== UTILITY ФУНКЦИИ =====

def get_test_mode_status() -> bool:
    """Проверить статус тестового режима"""
    return os.getenv('TEST_MODE', 'False').lower() == 'true'

def log_config_status():
    """Логирование статуса конфигурации"""
    test_mode = get_test_mode_status()
    
    if test_mode:
        logger.info("🧪 ENHANCED CONFIG: Тестовый режим активен")
        logger.info("   • Минимальная уверенность: 45%")
        logger.info("   • Минимальные объемы снижены в 10 раз")
        logger.info("   • Максимальный риск: 3%")
    else:
        logger.info("🎯 ENHANCED CONFIG: Продакшн режим")
        logger.info("   • Минимальная уверенность: 70%")
        logger.info("   • Оптимизированные объемы (снижены в 2 раза)")
        logger.info("   • Максимальный риск: 2%")

