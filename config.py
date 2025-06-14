# config.py - ИСПРАВЛЕННАЯ ФИНАЛЬНАЯ ВЕРСИЯ
import os
from typing import List, Dict, Set
import json

class TradingConfig:
    """Конфигурация торгового бота с поддержкой множественных чатов"""
    
    def __init__(self):
        # API ключи
        self.BYBIT_API_KEY = os.getenv('BYBIT_API_KEY', '')
        self.BYBIT_SECRET_KEY = os.getenv('BYBIT_SECRET_KEY', '')
        self.TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
        
        # Система чатов и подписок
        self._setup_chat_system()
        
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
        
        # Торговые пары для анализа
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
                
                # ===== DEFI ЛИДЕРЫ (топ DeFi протоколы) =====
                'LINKUSDT',     # Chainlink - оракулы №1
                'UNIUSDT',      # Uniswap - ведущий DEX
                'AAVEUSDT',     # Aave - лидер DeFi кредитования
                'MKRUSDT',      # Maker - создатель DAI
                'CRVUSDT',      # Curve - стейблкоин ликвидность
                'GRTUSDT',      # The Graph - Web3 индексирование данных
                'COMPUSDT',     # Compound - автономное кредитование  
                'SNXUSDT',      # Synthetix - синтетические активы
                'YFIUSDT',      # Yearn Finance - yield оптимизация
                '1INCHUSDT',    # 1inch - DEX агрегатор
                'SUSHIUSDT',    # SushiSwap - мультичейн DEX

                # ===== LAYER 1 БЛОКЧЕЙНЫ (проверенные сети) =====
                'DOTUSDT',      # Polkadot - парачейны
                'AVAXUSDT',     # Avalanche - быстрые транзакции
                'MATICUSDT',    # Polygon - L2 для Ethereum
                'ATOMUSDT',     # Cosmos - интернет блокчейнов
                'NEARUSDT',     # Near Protocol - масштабируемая сеть
                'FTMUSDT',      # Fantom - DAG платформа
                'XTZUSDT',      # Tezos - самообновляемая сеть
                'ALGOUSDT',     # Algorand - чистый PoS

                # ===== ТРАДИЦИОННЫЕ АЛЬТКОИНЫ (проверенные временем) =====
                'LTCUSDT',      # Litecoin - цифровое серебро
                'BCHUSDT',      # Bitcoin Cash - быстрые платежи
                'ETCUSDT',      # Ethereum Classic - оригинальный ETH
                'XLMUSDT',      # Stellar - трансграничные платежи
                'TRXUSDT',      # Tron - контент платформа
                'EOSUSDT',      # EOS - смарт-контракты
                
                # ===== УТИЛИТАРНЫЕ ТОКЕНЫ (реальное применение) =====
                'VETUSDT',      # VeChain - supply chain
                'ICPUSDT',      # Internet Computer - веб3 вычисления
                'FILUSDT',      # Filecoin - децентрализованное хранение
                'THETAUSDT',    # Theta - видео стриминг
            ]
        # ИСПРАВЛЕНО: Убрали лишний отступ!
        # Категоризация торговых пар для умного анализа
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
                'KLAYUSDT', 'STXUSDT', 'XTZUSDT', 'ALGOUSDT'
            ],
            'altcoins': [
                'LTCUSDT', 'BCHUSDT', 'ETCUSDT', 'XLMUSDT', 'VETUSDT', 'ICPUSDT',
                'FILUSDT', 'INJUSDT', 'RUNEUSDT', 'LDOUSDT', 'ARBUSDT', 'OPUSDT'
            ]
        }
        
        # Минимальные объемы для разных категорий (в USDT)
        # self.MIN_VOLUMES_BY_CATEGORY = {
        #     'major': 1000000000,      # 1B для топовых
        #     'defi': 100000000,        # 100M для DeFi
        #     'layer1': 200000000,      # 200M для Layer 1
        #     'meme': 50000000,         # 50M для мемов
        #     'gaming_nft': 30000000,   # 30M для игровых
        #     'emerging': 10000000,     # 10M для новых проектов
        #     'altcoins': 50000000      # 50M для альткоинов
        # }

        self.MIN_VOLUMES_BY_CATEGORY = {
            'major': 1000000000,        # 1B для топовых (строже)
            'defi': 150000000,          # 150M для DeFi (строже)
            'layer1': 200000000,        # 200M для Layer 1 (строже)
            'altcoins': 100000000       # 100M для альткоинов (строже)
        }

    
    def _setup_chat_system(self):
        """Настройка системы чатов и подписок"""
        
        # Основной чат администратора (обратная совместимость)
        admin_chat = os.getenv('TELEGRAM_CHAT_ID', '')
        
        # Дополнительные чаты из переменной окружения
        additional_chats_str = os.getenv('TELEGRAM_ADDITIONAL_CHATS', '')
        additional_chats = []
        if additional_chats_str:
            try:
                # Поддерживаем как JSON, так и простой список через запятую
                if additional_chats_str.startswith('['):
                    additional_chats = json.loads(additional_chats_str)
                else:
                    additional_chats = [chat.strip() for chat in additional_chats_str.split(',') if chat.strip()]
            except json.JSONDecodeError:
                additional_chats = [chat.strip() for chat in additional_chats_str.split(',') if chat.strip()]
        
        # Объединяем все чаты
        all_chats = []
        if admin_chat:
            all_chats.append(admin_chat)
        all_chats.extend(additional_chats)
        
        # Система подписок и уровней доступа
        self.SUBSCRIPTION_TIERS = {
            'FREE': {
                'max_signals_per_day': 3,
                'categories_allowed': ['major'],  
                'features': ['basic_signals'],
                'cooldown_minutes': 120
            },
            'BASIC': {
                'max_signals_per_day': 8,        
                'categories_allowed': ['major', 'defi'],  # DeFi теперь включает больше токенов
                'features': ['basic_signals', 'technical_analysis'],
                'cooldown_minutes': 90           
            },
            'PREMIUM': {
                'max_signals_per_day': 15,       
                'categories_allowed': ['major', 'defi', 'layer1'],  
                'features': ['basic_signals', 'technical_analysis', 'fundamental_analysis'],
                'cooldown_minutes': 60           
            },
            'VIP': {
                'max_signals_per_day': 25,       
                'categories_allowed': ['major', 'defi', 'layer1', 'altcoins'],  
                'features': ['basic_signals', 'technical_analysis', 'fundamental_analysis', 'priority_support'],
                'cooldown_minutes': 30           
            }
        }
        
        # Настройка пользователей/чатов
        self.CHAT_SUBSCRIPTIONS = self._load_chat_subscriptions(all_chats, admin_chat)
        
        # Общие настройки уведомлений
        self.SEND_ALERTS_ONLY = os.getenv('SEND_ALERTS_ONLY', 'False').lower() == 'true'
        self.DEFAULT_ALERT_COOLDOWN_MINUTES = int(os.getenv('ALERT_COOLDOWN_MINUTES', '60'))
    
    def _load_chat_subscriptions(self, all_chats: List[str], admin_chat: str) -> Dict:
        """Загрузка подписок чатов"""
        subscriptions = {}
        
        # Настройки по умолчанию для администратора
        if admin_chat:
            subscriptions[admin_chat] = {
                'tier': 'VIP',
                'is_admin': True,
                'active': True,
                'signals_sent_today': 0,
                'last_signal_time': None,
                'allowed_features': self.SUBSCRIPTION_TIERS['VIP']['features'],
                'custom_settings': {}
            }
        
        # Загружаем дополнительные настройки из файла или переменных окружения
        custom_subscriptions_str = os.getenv('TELEGRAM_SUBSCRIPTIONS', '')
        if custom_subscriptions_str:
            try:
                custom_subscriptions = json.loads(custom_subscriptions_str)
                subscriptions.update(custom_subscriptions)
            except json.JSONDecodeError:
                pass
        
        # Добавляем базовые настройки для дополнительных чатов
        for chat in all_chats:
            if chat not in subscriptions:
                subscriptions[chat] = {
                    'tier': 'BASIC',  # По умолчанию BASIC для новых чатов
                    'is_admin': False,
                    'active': True,
                    'signals_sent_today': 0,
                    'last_signal_time': None,
                    'allowed_features': self.SUBSCRIPTION_TIERS['BASIC']['features'],
                    'custom_settings': {}
                }
        
        return subscriptions
    
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
        """ИСПРАВЛЕНО: Проверка возможности получения сигнала для чата"""
        if not self.is_chat_authorized(chat_id):
            return False, "Чат не авторизован"
        
        chat_settings = self.CHAT_SUBSCRIPTIONS[chat_id]
        
        # КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: Администраторы получают ВСЕ сигналы без ограничений
        if chat_settings.get('is_admin', False):
            return True, "OK (Admin - unlimited access)"
        
        tier = chat_settings['tier']
        tier_settings = self.SUBSCRIPTION_TIERS.get(tier, self.SUBSCRIPTION_TIERS['FREE'])
        
        # ИСПРАВЛЕНИЕ: Специальная обработка категории 'other'
        if category == 'other':
            if tier in ['VIP', 'PREMIUM']:
                return True, f"OK (Category 'other' allowed for {tier})"
            else:
                return False, f"Категория 'other' доступна только для PREMIUM/VIP"
        
        # Проверяем категорию
        if category not in tier_settings['categories_allowed']:
            return False, f"Категория '{category}' недоступна для уровня '{tier}'"
        
        # Проверяем лимит сигналов
        max_signals = tier_settings['max_signals_per_day']
        if max_signals > 0:  # -1 означает безлимитно
            signals_today = chat_settings.get('signals_sent_today', 0)
            if signals_today >= max_signals:
                return False, f"Достигнут дневной лимит сигналов ({max_signals})"
        
        return True, "OK"
    
    def update_chat_signal_count(self, chat_id: str):
        """ИСПРАВЛЕНО: Обновление счетчика сигналов (не для админов)"""
        if chat_id in self.CHAT_SUBSCRIPTIONS:
            # Не считаем сигналы для администраторов
            if not self.CHAT_SUBSCRIPTIONS[chat_id].get('is_admin', False):
                self.CHAT_SUBSCRIPTIONS[chat_id]['signals_sent_today'] = \
                    self.CHAT_SUBSCRIPTIONS[chat_id].get('signals_sent_today', 0) + 1
    
    def get_cooldown_minutes(self, chat_id: str) -> int:
        """Получение времени ожидания для чата"""
        if not self.is_chat_authorized(chat_id):
            return self.DEFAULT_ALERT_COOLDOWN_MINUTES
        
        # Администраторы без кулдауна
        if self.CHAT_SUBSCRIPTIONS[chat_id].get('is_admin', False):
            return 0
        
        tier = self.get_chat_tier(chat_id)
        tier_settings = self.SUBSCRIPTION_TIERS.get(tier, self.SUBSCRIPTION_TIERS['FREE'])
        return tier_settings.get('cooldown_minutes', self.DEFAULT_ALERT_COOLDOWN_MINUTES)
    
    def add_chat(self, chat_id: str, tier: str = 'FREE', is_admin: bool = False) -> bool:
        """Добавление нового чата"""
        if tier not in self.SUBSCRIPTION_TIERS:
            return False
        
        self.CHAT_SUBSCRIPTIONS[chat_id] = {
            'tier': tier,
            'is_admin': is_admin,
            'active': True,
            'signals_sent_today': 0,
            'last_signal_time': None,
            'allowed_features': self.SUBSCRIPTION_TIERS[tier]['features'],
            'custom_settings': {}
        }
        return True
    
    def remove_chat(self, chat_id: str) -> bool:
        """Удаление чата"""
        if chat_id in self.CHAT_SUBSCRIPTIONS:
            del self.CHAT_SUBSCRIPTIONS[chat_id]
            return True
        return False
    
    def upgrade_chat(self, chat_id: str, new_tier: str) -> bool:
        """Обновление уровня подписки чата"""
        if chat_id not in self.CHAT_SUBSCRIPTIONS:
            return False
        
        if new_tier not in self.SUBSCRIPTION_TIERS:
            return False
        
        self.CHAT_SUBSCRIPTIONS[chat_id]['tier'] = new_tier
        self.CHAT_SUBSCRIPTIONS[chat_id]['allowed_features'] = \
            self.SUBSCRIPTION_TIERS[new_tier]['features']
        return True

# Паттерны свечей для распознавания
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

# Дополнительные настройки для новых пар
PAIR_SPECIFIC_SETTINGS = {
    # Мемкоины - более агрессивная торговля
    'DOGEUSDT': {
        'max_leverage': 3,
        'min_confidence': 80.0,
        'volatility_threshold': 0.15
    },
    'SHIBUSDT': {
        'max_leverage': 3,
        'min_confidence': 80.0,
        'volatility_threshold': 0.15
    },
    'PEPEUSDT': {
        'max_leverage': 2,
        'min_confidence': 85.0,
        'volatility_threshold': 0.20
    },
    
    # Стейблкоины DeFi - консервативная торговля
    'LINKUSDT': {
        'max_leverage': 5,
        'min_confidence': 70.0,
        'volatility_threshold': 0.08
    },
    'AAVEUSDT': {
        'max_leverage': 5,
        'min_confidence': 70.0,
        'volatility_threshold': 0.08
    },
    
    # Новые проекты - осторожная торговля
    'CETUSUSDT': {
        'max_leverage': 2,
        'min_confidence': 85.0,
        'volatility_threshold': 0.25,
        'min_volume_multiplier': 2.0
    },
    'SLERFUSDT': {
        'max_leverage': 2,
        'min_confidence': 85.0,
        'volatility_threshold': 0.25,
        'min_volume_multiplier': 2.0
    }
}