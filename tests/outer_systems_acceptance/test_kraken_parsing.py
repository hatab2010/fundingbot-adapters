#!/usr/bin/env python3
"""
Простой тест для проверки парсинга данных Kraken API без сетевых запросов.
"""

from datetime import datetime, UTC
from decimal import Decimal

from fundingbot_adapters.futures_kraken_client import FUTURES_KRAKEN_FUNDING_RATE_ADAPTER


def test_kraken_funding_rate_parsing():
    """Тестирует парсинг данных funding rate из Kraken API."""
    
    # Пример данных из Kraken API (из исследования)
    sample_data = {
        "symbol": "PF_BTCUSD",
        "fundingRate": -0.00048532027671,
        "serverTime": "2026-01-31T12:39:49.595Z",
        "exchange": "kraken",
        "tag": "perpetual",
        "suspended": False
    }
    
    # Парсим данные
    model = FUTURES_KRAKEN_FUNDING_RATE_ADAPTER.validate_python(sample_data)
    
    # Проверяем результат
    print(f"Исходный символ: {sample_data['symbol']}")
    print(f"Нормализованный символ: {model.symbol}")
    print(f"Exchange: {model.exchange}")
    print(f"Funding rate: {model.funding_rate}")
    print(f"Funding date: {model.funding_date}")
    
    # Проверяем конвертацию символа
    assert model.symbol == "BTC/USD:USD", f"Ожидался BTC/USD:USD, получен {model.symbol}"
    assert model.exchange == "kraken"
    assert model.funding_rate == Decimal("-0.00048532027671")
    assert isinstance(model.funding_date, datetime)
    assert model.funding_date.tzinfo == UTC
    
    print("✅ Тест парсинга прошел успешно!")


def test_symbol_conversion():
    """Тестирует различные варианты конвертации символов."""
    
    test_cases = [
        ("PF_BTCUSD", "BTC/USD:USD"),
        ("PF_ETHUSD", "ETH/USD:USD"),
        ("PF_AUCTIONUSD", "AUCTION/USD:USD"),
        ("PF_ALTUSD", "ALT/USD:USD"),
    ]
    
    for input_symbol, expected_output in test_cases:
        sample_data = {
            "symbol": input_symbol,
            "fundingRate": 0.001,
            "serverTime": "2026-01-31T12:39:49.595Z",
            "exchange": "kraken"
        }
        
        model = FUTURES_KRAKEN_FUNDING_RATE_ADAPTER.validate_python(sample_data)
        
        print(f"{input_symbol} -> {model.symbol}")
        assert model.symbol == expected_output, f"Ожидался {expected_output}, получен {model.symbol}"
    
    print("✅ Тест конвертации символов прошел успешно!")


def test_datetime_parsing():
    """Тестирует парсинг различных форматов времени."""
    
    test_cases = [
        "2026-01-31T12:39:49.595Z",
        "2026-01-31T12:39:49Z",
        "2026-01-31T12:39:49.123456Z",
    ]
    
    for time_str in test_cases:
        sample_data = {
            "symbol": "PF_BTCUSD",
            "fundingRate": 0.001,
            "serverTime": time_str,
            "exchange": "kraken"
        }
        
        model = FUTURES_KRAKEN_FUNDING_RATE_ADAPTER.validate_python(sample_data)
        
        print(f"Время: {time_str} -> {model.funding_date}")
        assert isinstance(model.funding_date, datetime)
        assert model.funding_date.tzinfo == UTC
    
    print("✅ Тест парсинга времени прошел успешно!")


if __name__ == "__main__":
    print("🧪 Запуск тестов парсинга Kraken API...")
    print()
    
    test_kraken_funding_rate_parsing()
    print()
    
    test_symbol_conversion()
    print()
    
    test_datetime_parsing()
    print()
    
    print("🎉 Все тесты прошли успешно!")
    print()
    print("📋 Резюме изменений:")
    print("1. ✅ Обновлена структура KrakenFundingRateResponse")
    print("2. ✅ Изменен API endpoint на /derivatives/api/v3/tickers")
    print("3. ✅ Реализована конвертация символов PF_BTCUSD -> BTC/USD:USD")
    print("4. ✅ Добавлена фильтрация perpetual контрактов")
    print("5. ✅ Обновлена обработка времени из serverTime")
    print("6. ✅ Протестирована логика парсинга данных")