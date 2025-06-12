#!/usr/bin/env python3
# test_api.py - Скрипт для тестирования API

import sys
from dotenv import load_dotenv
load_dotenv()

from config import TradingConfig
from bybit_api import BybitAPI
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_bybit_api():
    """Тестирование Bybit API"""
    print("🚀 НАЧАЛО ТЕСТИРОВАНИЯ BYBIT API")
    print("=" * 50)
    
    config = TradingConfig()
    
    # Проверяем наличие API ключей
    if not config.BYBIT_API_KEY or not config.BYBIT_SECRET_KEY:
        print("❌ API ключи не настроены!")
        print("Создайте файл .env со следующими переменными:")
        print("BYBIT_API_KEY=ваш_ключ")
        print("BYBIT_SECRET_KEY=ваш_секрет")
        return False
    
    print(f"✅ API ключ найден: {config.BYBIT_API_KEY[:8]}...")
    
    api = BybitAPI(config)
    
    # Тест подключения
    print("\n📡 Тестирование подключения...")
    if not api.validate_connection():
        print("❌ Не удалось подключиться к API")
        return False
    
    print("✅ Подключение успешно")
    
    # Тестирование символов
    test_symbols = ['BTCUSDT', 'ETHUSDT']
    
    for symbol in test_symbols:
        print(f"\n🔍 Тестирование {symbol}:")
        results = api.test_symbol_data(symbol)
        
        success_count = sum(results.values())
        total_tests = len(results)
        
        print(f"📊 Результат: {success_count}/{total_tests} тестов пройдено")
        
        if success_count == total_tests:
            print(f"✅ {symbol} - ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
            return True
        else:
            print(f"⚠️ {symbol} - есть проблемы")
    
    return False

def test_specific_endpoints():
    """Тестирование конкретных эндпоинтов"""
    print("\n🔧 ДЕТАЛЬНОЕ ТЕСТИРОВАНИЕ ЭНДПОИНТОВ")
    print("=" * 50)
    
    config = TradingConfig()
    api = BybitAPI(config)
    
    # Тест времени сервера (публичный эндпоинт)
    print("\n⏰ Тест времени сервера:")
    response = api._make_request("/v5/market/time")
    print(f"Ответ: {response}")
    
    # Тест инструментов (публичный эндпоинт)
    print("\n📋 Тест списка инструментов:")
    response = api._make_request("/v5/market/instruments-info", {
        "category": "linear",
        "limit": 5
    })
    
    if response.get('retCode') == 0:
        instruments = response.get('result', {}).get('list', [])
        print(f"✅ Получено {len(instruments)} инструментов")
        for inst in instruments[:3]:
            print(f"  - {inst.get('symbol')}: {inst.get('status')}")
    else:
        print(f"❌ Ошибка: {response}")
    
    # Тест тикеров
    print("\n📈 Тест тикеров:")
    response = api._make_request("/v5/market/tickers", {
        "category": "linear",
        "symbol": "BTCUSDT"
    })
    
    if response.get('retCode') == 0:
        tickers = response.get('result', {}).get('list', [])
        if tickers:
            ticker = tickers[0]
            print(f"✅ BTC цена: {ticker.get('lastPrice')}")
            print(f"  Объем 24ч: {ticker.get('turnover24h')}")
        else:
            print("❌ Тикер не найден")
    else:
        print(f"❌ Ошибка тикера: {response}")
    
    # НОВОЕ: Детальный тест свечей
    print("\n🕯️ ДЕТАЛЬНЫЙ ТЕСТ СВЕЧЕЙ:")
    test_intervals = ['1', '60', 'D']  # 1 минута, 1 час, 1 день
    
    for interval in test_intervals:
        print(f"\n  Тестируем интервал: {interval}")
        response = api._make_request("/v5/market/kline", {
            "category": "linear",
            "symbol": "BTCUSDT",
            "interval": interval,
            "limit": 5
        })
        
        if response.get('retCode') == 0:
            result = response.get('result', {})
            klines = result.get('list', [])
            print(f"  ✅ Получено {len(klines)} свечей для интервала {interval}")
            
            if klines:
                latest = klines[0]  # Последняя свеча
                print(f"    Последняя свеча: время={latest[0]}, цена={latest[4]}")
            else:
                print(f"  ⚠️ Список свечей пуст для интервала {interval}")
        else:
            print(f"  ❌ Ошибка получения свечей {interval}: {response.get('retMsg')}")

def test_raw_requests():
    """Тест через обычные HTTP запросы без авторизации"""
    print("\n🌐 ТЕСТ ПУБЛИЧНЫХ ЭНДПОИНТОВ (БЕЗ АВТОРИЗАЦИИ)")
    print("=" * 50)
    
    import requests
    
    base_url = "https://api.bybit.com"
    
    # Публичный эндпоинт времени
    print("\n⏰ Публичное время сервера:")
    try:
        response = requests.get(f"{base_url}/v5/market/time", timeout=10)
        print(f"Статус: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Время сервера: {data}")
        else:
            print(f"❌ Ошибка: {response.text}")
    except Exception as e:
        print(f"❌ Исключение: {e}")
    
    # Публичный эндпоинт тикера
    print("\n📈 Публичный тикер BTC:")
    try:
        response = requests.get(f"{base_url}/v5/market/tickers?category=linear&symbol=BTCUSDT", timeout=10)
        print(f"Статус: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data.get('retCode') == 0:
                tickers = data.get('result', {}).get('list', [])
                if tickers:
                    print(f"✅ BTC цена: {tickers[0].get('lastPrice')}")
                else:
                    print("❌ Пустой список тикеров")
            else:
                print(f"❌ API ошибка: {data}")
        else:
            print(f"❌ HTTP ошибка: {response.text}")
    except Exception as e:
        print(f"❌ Исключение: {e}")
    
    # Публичные свечи
    print("\n🕯️ Публичные свечи BTC (1 час):")
    try:
        response = requests.get(f"{base_url}/v5/market/kline?category=linear&symbol=BTCUSDT&interval=60&limit=5", timeout=10)
        print(f"Статус: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data.get('retCode') == 0:
                klines = data.get('result', {}).get('list', [])
                print(f"✅ Получено {len(klines)} свечей")
                if klines:
                    latest = klines[0]
                    print(f"  Последняя: время={latest[0]}, open={latest[1]}, close={latest[4]}")
                else:
                    print("  ⚠️ Список свечей пуст")
            else:
                print(f"❌ API ошибка: {data}")
        else:
            print(f"❌ HTTP ошибка: {response.text}")
    except Exception as e:
        print(f"❌ Исключение: {e}")

if __name__ == "__main__":
    print("🤖 ТЕСТИРОВАНИЕ API BYBIT")
    print("=" * 50)
    
    # Основное тестирование
    if test_bybit_api():
        print("\n🎉 ОСНОВНЫЕ ТЕСТЫ ПРОЙДЕНЫ!")
    else:
        print("\n⚠️ ЕСТЬ ПРОБЛЕМЫ С API")
        
        # Детальное тестирование
        test_specific_endpoints()
        
        # Тест без авторизации
        test_raw_requests()
    
    print("\n" + "=" * 50)
    print("Тестирование завершено")