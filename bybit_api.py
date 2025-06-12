# bybit_api.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
import hmac
import hashlib
import json
import time
import requests
import pandas as pd
from typing import Dict, List, Optional, Tuple
import logging
from config import TradingConfig

logger = logging.getLogger(__name__)

class BybitAPI:
    """Класс для работы с API Bybit"""
    
    def __init__(self, config: TradingConfig):
        self.config = config
        self.base_url = "https://api.bybit.com"
        self.session = requests.Session()
        
    def _generate_signature(self, params: str, timestamp: str) -> str:
        """Генерация подписи для API запроса"""
        param_str = timestamp + self.config.BYBIT_API_KEY + "5000" + params
        return hmac.new(
            self.config.BYBIT_SECRET_KEY.encode('utf-8'),
            param_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _make_request(self, endpoint: str, params: Dict = None, method: str = "GET") -> Dict: # type: ignore
        """Выполнение запроса к API"""
        if params is None:
            params = {}
            
        timestamp = str(int(time.time() * 1000))
        
        try:
            if method == "GET":
                query_string = "&".join([f"{k}={v}" for k, v in params.items()])
                signature = self._generate_signature(query_string, timestamp)
                
                headers = {
                    "X-BAPI-API-KEY": self.config.BYBIT_API_KEY,
                    "X-BAPI-SIGN": signature,
                    "X-BAPI-SIGN-TYPE": "2",
                    "X-BAPI-TIMESTAMP": timestamp,
                    "X-BAPI-RECV-WINDOW": "5000"
                }
                
                url = f"{self.base_url}{endpoint}"
                if query_string:
                    url += f"?{query_string}"
                    
                logger.debug(f"GET запрос: {url}")
                response = self.session.get(url, headers=headers, timeout=10)
                
            else:
                # Для POST запросов
                json_params = json.dumps(params) if params else ""
                signature = self._generate_signature(json_params, timestamp)
                
                headers = {
                    "X-BAPI-API-KEY": self.config.BYBIT_API_KEY,
                    "X-BAPI-SIGN": signature,
                    "X-BAPI-SIGN-TYPE": "2",
                    "X-BAPI-TIMESTAMP": timestamp,
                    "X-BAPI-RECV-WINDOW": "5000",
                    "Content-Type": "application/json"
                }
                
                logger.debug(f"POST запрос: {self.base_url}{endpoint}")
                response = self.session.post(
                    f"{self.base_url}{endpoint}", 
                    headers=headers, 
                    json=params,
                    timeout=10
                )
            
            response.raise_for_status()
            result = response.json()
            
            # Логируем ответ для отладки
            if result.get('retCode') != 0:
                logger.error(f"API ошибка для {endpoint}: {result.get('retMsg')} (код: {result.get('retCode')})")
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка HTTP запроса к {endpoint}: {e}")
            return {"retCode": -1, "retMsg": f"HTTP Error: {e}"}
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON для {endpoint}: {e}")
            return {"retCode": -1, "retMsg": f"JSON Error: {e}"}
        except Exception as e:
            logger.error(f"Неожиданная ошибка для {endpoint}: {e}")
            return {"retCode": -1, "retMsg": f"Unexpected Error: {e}"}
    
    def get_klines(self, symbol: str, interval: str, limit: int = 200) -> pd.DataFrame:
        """Получение исторических данных (свечи) - ИСПРАВЛЕНО"""
        try:
            # Нормализуем интервал для Bybit API
            interval_map = {
                '1m': '1', '3m': '3', '5m': '5', '15m': '15', '30m': '30',
                '1h': '60', '2h': '120', '4h': '240', '6h': '360', '12h': '720',
                '1d': 'D', '1D': 'D', 'd': 'D', 'D': 'D',
                '1w': 'W', '1W': 'W', 'w': 'W', 'W': 'W',
                '1M': 'M', 'M': 'M'
            }
            
            # Преобразуем интервал
            bybit_interval = interval_map.get(interval, interval)
            
            params = {
                "category": "linear",
                "symbol": symbol,
                "interval": bybit_interval,
                "limit": min(limit, 200)  # Bybit максимум 200 для kline
            }
            
            logger.info(f"Запрос свечей для {symbol}, интервал: {interval} -> {bybit_interval}, лимит: {limit}")
            response = self._make_request("/v5/market/kline", params)
            
            if response.get('retCode') != 0:
                logger.error(f"Ошибка получения свечей для {symbol}: код {response.get('retCode')}, сообщение: {response.get('retMsg')}")
                # Логируем дополнительную информацию для отладки
                logger.error(f"Параметры запроса: {params}")
                return pd.DataFrame()
            
            result = response.get('result', {})
            klines = result.get('list', [])
            
            if not klines:
                logger.warning(f"Пустой ответ свечей для {symbol}. Полный ответ: {result}")
                return pd.DataFrame()
            
            logger.info(f"Получено {len(klines)} raw свечей для {symbol}")
            
            # Преобразование в DataFrame
            df = pd.DataFrame(klines, columns=[
                'start_time', 'open', 'high', 'low', 'close', 'volume', 'turnover'
            ])
            
            if df.empty:
                logger.warning(f"Пустой DataFrame свечей для {symbol}")
                return pd.DataFrame()
            
            # Конвертация типов данных
            try:
                # Конвертируем timestamp - исправляем проблему с большими числами
                df['start_time'] = pd.to_datetime(df['start_time'].astype('int64'), unit='ms', errors='coerce')
                
                numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'turnover']
                for col in numeric_columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # Удаляем строки с NaN
                original_count = len(df)
                df = df.dropna()
                
                if len(df) != original_count:
                    logger.warning(f"Удалено {original_count - len(df)} строк с NaN для {symbol}")
                
                if df.empty:
                    logger.warning(f"DataFrame пуст после очистки NaN для {symbol}")
                    return pd.DataFrame()
                
                # Сортировка по времени (от старых к новым)
                df = df.sort_values('start_time').reset_index(drop=True)
                
                logger.info(f"✅ Получено {len(df)} обработанных свечей для {symbol}")
                return df
                
            except Exception as e:
                logger.error(f"Ошибка преобразования данных свечей для {symbol}: {e}")
                return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Ошибка при получении klines для {symbol}: {e}")
            return pd.DataFrame()
    
    def get_ticker_24hr(self, symbol: str) -> Dict:
        """Получение 24-часовой статистики тикера"""
        try:
            params = {
                "category": "linear",
                "symbol": symbol
            }
            
            logger.debug(f"Запрос тикера для {symbol}")
            response = self._make_request("/v5/market/tickers", params)
            
            if response.get('retCode') != 0:
                logger.error(f"Ошибка получения тикера для {symbol}: {response.get('retMsg')}")
                return {}
                
            result_list = response.get('result', {}).get('list', [])
            if result_list:
                ticker = result_list[0]
                logger.debug(f"Получен тикер для {symbol}: цена {ticker.get('lastPrice')}")
                return ticker
            
            logger.warning(f"Пустой ответ тикера для {symbol}")
            return {}
            
        except Exception as e:
            logger.error(f"Ошибка при получении тикера для {symbol}: {e}")
            return {}
    
    def get_orderbook(self, symbol: str, limit: int = 25) -> Dict:
        """Получение стакана заявок"""
        try:
            params = {
                "category": "linear",
                "symbol": symbol,
                "limit": min(limit, 200)  # Bybit лимит
            }
            
            response = self._make_request("/v5/market/orderbook", params)
            
            if response.get('retCode') != 0:
                logger.error(f"Ошибка получения стакана для {symbol}: {response.get('retMsg')}")
                return {}
                
            return response.get('result', {})
            
        except Exception as e:
            logger.error(f"Ошибка при получении стакана для {symbol}: {e}")
            return {}
    
    def get_account_balance(self) -> Dict:
        """Получение баланса аккаунта"""
        try:
            params = {
                "accountType": "UNIFIED"
            }
            
            response = self._make_request("/v5/account/wallet-balance", params)
            
            if response.get('retCode') != 0:
                logger.error(f"Ошибка получения баланса: {response.get('retMsg')}")
                return {}
                
            return response.get('result', {})
            
        except Exception as e:
            logger.error(f"Ошибка при получении баланса: {e}")
            return {}
    
    def get_instruments_info(self, symbol: str = None) -> List[Dict]: # type: ignore
        """Получение информации об инструментах"""
        try:
            params = {
                "category": "linear"
            }
            
            if symbol:
                params["symbol"] = symbol
            
            response = self._make_request("/v5/market/instruments-info", params)
            
            if response.get('retCode') != 0:
                logger.error(f"Ошибка получения информации об инструментах: {response.get('retMsg')}")
                return []
                
            return response.get('result', {}).get('list', [])
            
        except Exception as e:
            logger.error(f"Ошибка при получении информации об инструментах: {e}")
            return []
    
    def get_funding_rate(self, symbol: str) -> Dict:
        """Получение ставки финансирования"""
        try:
            params = {
                "category": "linear",
                "symbol": symbol,
                "limit": 1
            }
            
            response = self._make_request("/v5/market/funding/history", params)
            
            if response.get('retCode') != 0:
                logger.error(f"Ошибка получения ставки финансирования для {symbol}: {response.get('retMsg')}")
                return {}
                
            result_list = response.get('result', {}).get('list', [])
            if result_list:
                return result_list[0]
            
            return {}
            
        except Exception as e:
            logger.error(f"Ошибка при получении ставки финансирования для {symbol}: {e}")
            return {}
    
    def get_open_interest(self, symbol: str, interval: str = "1h", limit: int = 200) -> pd.DataFrame:
        """Получение открытого интереса - ИСПРАВЛЕНО"""
        try:
            params = {
                "category": "linear",
                "symbol": symbol,
                "intervalTime": interval,
                "limit": min(limit, 200)  # Bybit лимит
            }
            
            logger.debug(f"Запрос открытого интереса для {symbol}")
            response = self._make_request("/v5/market/open-interest", params)
            
            if response.get('retCode') != 0:
                logger.error(f"Ошибка получения открытого интереса для {symbol}: {response.get('retMsg')}")
                return pd.DataFrame()
            
            data = response.get('result', {}).get('list', [])
            
            if not data:
                logger.warning(f"Пустой ответ открытого интереса для {symbol}")
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            
            if df.empty:
                return pd.DataFrame()
            
            try:
                # ИСПРАВЛЕНИЕ: безопасное преобразование timestamp
                if 'timestamp' in df.columns:
                    # Конвертируем в строку, затем в int64, затем в datetime
                    df['timestamp'] = df['timestamp'].astype(str).astype('int64')
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', errors='coerce')
                
                if 'openInterest' in df.columns:
                    df['openInterest'] = pd.to_numeric(df['openInterest'], errors='coerce')
                
                # Удаляем строки с NaN
                df = df.dropna()
                
                if not df.empty:
                    df = df.sort_values('timestamp').reset_index(drop=True)
                    logger.debug(f"Получено {len(df)} записей открытого интереса для {symbol}")
                
                return df
                
            except Exception as e:
                logger.error(f"Ошибка преобразования данных открытого интереса для {symbol}: {e}")
                return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Ошибка при получении открытого интереса для {symbol}: {e}")
            return pd.DataFrame()
    
    def validate_connection(self) -> bool:
        """Проверка подключения к API"""
        try:
            logger.info("Проверка подключения к Bybit API...")
            response = self._make_request("/v5/market/time")
            
            if response.get('retCode') == 0:
                server_time = response.get('result', {}).get('timeSecond', 0)
                logger.info(f"Подключение к Bybit API успешно. Время сервера: {server_time}")
                return True
            else:
                logger.error(f"Ошибка подключения к Bybit API: {response.get('retMsg')}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка подключения к API: {e}")
            return False
    
    def test_symbol_data(self, symbol: str) -> Dict:
        """Тестирование получения данных для символа"""
        logger.info(f"=== ТЕСТИРОВАНИЕ ДАННЫХ ДЛЯ {symbol} ===")
        
        results = {}
        
        # Тест информации об инструменте
        try:
            instruments = self.get_instruments_info(symbol)
            results['instruments'] = len(instruments) > 0
            if instruments:
                instrument = instruments[0]
                logger.info(f"✅ Инструмент {symbol} найден")
                logger.info(f"   Статус: {instrument.get('status')}")
                logger.info(f"   Тип контракта: {instrument.get('contractType')}")
            else:
                logger.error(f"❌ Инструмент {symbol} не найден")
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации об инструменте: {e}")
            results['instruments'] = False
        
        # Тест тикера
        try:
            ticker = self.get_ticker_24hr(symbol)
            results['ticker'] = bool(ticker)
            if ticker:
                logger.info(f"✅ Тикер получен. Цена: {ticker.get('lastPrice')}")
                logger.info(f"   Объем 24ч: {ticker.get('turnover24h')}")
            else:
                logger.error(f"❌ Тикер не получен")
        except Exception as e:
            logger.error(f"❌ Ошибка получения тикера: {e}")
            results['ticker'] = False
        
        # Тест свечей с разными интервалами
        test_intervals = ['1h', '4h', '1d']
        results['klines'] = False
        
        for interval in test_intervals:
            try:
                logger.info(f"🕯️ Тестируем свечи с интервалом {interval}")
                klines = self.get_klines(symbol, interval, 10)
                if not klines.empty:
                    logger.info(f"✅ Свечи {interval} получены. Количество: {len(klines)}")
                    logger.info(f"   Последняя цена: {klines['close'].iloc[-1]}")
                    logger.info(f"   Временной диапазон: {klines['start_time'].iloc[0]} -> {klines['start_time'].iloc[-1]}")
                    results['klines'] = True
                    break
                else:
                    logger.warning(f"⚠️ Свечи {interval} пусты")
            except Exception as e:
                logger.error(f"❌ Ошибка получения свечей {interval}: {e}")
        
        if not results['klines']:
            logger.error(f"❌ Все интервалы свечей не получены")
        
        # Тест funding rate
        try:
            funding = self.get_funding_rate(symbol)
            results['funding'] = bool(funding)
            if funding:
                logger.info(f"✅ Ставка финансирования получена: {funding.get('fundingRate')}")
            else:
                logger.warning(f"⚠️ Ставка финансирования не получена")
        except Exception as e:
            logger.error(f"❌ Ошибка получения ставки финансирования: {e}")
            results['funding'] = False
        
        return results