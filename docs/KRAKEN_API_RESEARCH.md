# Детальное исследование Kraken Spot REST API для реализации KrakenClient

## 1. Базовая структура Kraken Spot REST API

### 1.1 Архитектура API
Kraken Spot REST API организован по функциональным группам:

- **Market Data** (публичные endpoints) - тикеры, ордербуки, торговые данные
- **Account Data** (приватные endpoints) - балансы, позиции, история
- **Trading** (приватные endpoints) - создание/изменение/отмена ордеров
- **Funding** - операции с фондированием
- **Subaccounts** - управление субаккаунтами
- **Earn** - стейкинг и доходные продукты
- **Websocket Authentication** - аутентификация для WebSocket

### 1.2 Базовые URL
- **REST API**: `https://api.kraken.com/0/`
- **Публичные endpoints**: `https://api.kraken.com/0/public/`
- **Приватные endpoints**: `https://api.kraken.com/0/private/`

## 2. Публичные endpoints (Market Data)

### 2.1 Ключевые endpoints для fundingbot
```
GET /0/public/Time - серверное время
GET /0/public/SystemStatus - статус системы
GET /0/public/AssetPairs - информация о торговых парах
GET /0/public/Ticker - тикеры (цены, объемы)
GET /0/public/Depth - ордербук
GET /0/public/Trades - последние сделки
GET /0/public/OHLC - OHLC данные
```

### 2.2 Формат данных
- **Параметры**: через query string для GET запросов
- **Символы**: в формате `XBTUSD`, `ETHUSD` (без разделителей)
- **Ответы**: JSON с полями `error` и `result`

### 2.3 Особенности символов Kraken
- **Spot формат**: `XBTUSD`, `ETHUSD`, `ADAUSD`
- **CCXT формат**: `BTC/USD`, `ETH/USD`, `ADA/USD`
- **Требуется конвертация** между форматами

## 3. Приватные endpoints (Account Data & Trading)

### 3.1 Account Data endpoints
```
POST /0/private/Balance - баланс аккаунта
POST /0/private/BalanceEx - расширенный баланс
POST /0/private/TradeBalance - торговый баланс
POST /0/private/OpenOrders - открытые ордера
POST /0/private/ClosedOrders - закрытые ордера
POST /0/private/QueryOrders - информация об ордерах
POST /0/private/TradesHistory - история сделок
POST /0/private/QueryTrades - информация о сделках
POST /0/private/OpenPositions - открытые позиции
POST /0/private/Ledgers - история операций
```

### 3.2 Trading endpoints
```
POST /0/private/AddOrder - создать ордер
POST /0/private/AddOrderBatch - создать несколько ордеров
POST /0/private/EditOrder - изменить ордер
POST /0/private/CancelOrder - отменить ордер
POST /0/private/CancelAll - отменить все ордера
POST /0/private/CancelAllOrdersAfter - отменить ордера через время
```

### 3.3 Особенности приватных endpoints
- **Метод**: только POST
- **Аутентификация**: обязательна для всех
- **Nonce**: требуется уникальный nonce для каждого запроса
- **Rate limits**: применяются к приватным endpoints

## 4. Система аутентификации Kraken API

### 4.1 Параметры аутентификации
```
API-Key: публичный ключ из API key-pair
API-Sign: зашифрованная подпись сообщения
nonce: всегда увеличивающееся 64-битное целое число
otp: одноразовый пароль (только если настроена 2FA)
```

### 4.2 Создание подписи API-Sign
```
API-Sign = HMAC-SHA512(URI path + SHA256(nonce + POST data), base64_decoded_secret_API_key)
```

### 4.3 Особенности аутентификации
- **URI path**: должен начинаться с "/0/private/" для приватных endpoints
- **Private key**: используется только для создания подписи, никогда не передается
- **Public key**: передается в заголовке API-Key
- **Nonce**: должен быть больше предыдущего значения

## 5. Rate Limits и ограничения

### 5.1 REST Specific Limits
```
Tier        Max API Counter    API Counter Decay
Starter     15                 -0.33/sec
Intermediate 20                -0.5/sec  
Pro         20                 -1/sec
```

### 5.2 Весовая система
- **Стандартные вызовы**: вес 1 (кроме AddOrder, CancelOrder)
- **Ledger/trade history**: вес 2
- **Счетчик**: уменьшается каждые несколько секунд в зависимости от tier
- **Превышение лимита**: HTTP 429 или rate limit ошибки

### 5.3 Рекомендации по rate limiting
- Использовать внешний rate limiter в fundingbot
- Учитывать вес операций при планировании запросов
- Обрабатывать ошибки 429 с exponential backoff

## 6. Форматы данных и структуры ответов

### 6.1 Общая структура ответа
```json
{
  "error": [],
  "result": {
    // данные ответа
  }
}
```

### 6.2 Формат ошибок
```json
{
  "error": ["EService:Unavailable", "EGeneral:Internal error"]
}
```

### 6.3 Типы данных
- **Цены**: строки с фиксированной точностью
- **Объемы**: строки с фиксированной точностью  
- **Время**: Unix timestamp в секундах
- **Символы**: строки без разделителей

## 7. Endpoints для реализации CexClientPort интерфейса

### 7.1 Обязательные методы и соответствующие endpoints

| CexClientPort метод | Kraken endpoint | Тип | Примечания |
|-------------------|----------------|-----|------------|
| [`load_markets()`](submodules/fundingbot-sdk/src/fundingbot_sdk/contracts/ports/cex_client.py:93) | `/0/public/AssetPairs` | GET | Загрузка справочника рынков |
| [`get_market_symbols()`](submodules/fundingbot-sdk/src/fundingbot_sdk/contracts/ports/cex_client.py:103) | `/0/public/AssetPairs` | GET | Фильтрация по типу рынка |
| [`get_ticker()`](submodules/fundingbot-sdk/src/fundingbot_sdk/contracts/ports/cex_client.py:108) | `/0/public/Ticker` | GET | Тикер для символа |
| [`get_positions()`](submodules/fundingbot-sdk/src/fundingbot_sdk/contracts/ports/cex_client.py:113) | `/0/private/OpenPositions` | POST | Открытые позиции |
| [`get_funding_usdt_rates()`](submodules/fundingbot-sdk/src/fundingbot_sdk/contracts/ports/cex_client.py:118) | **НЕ ПОДДЕРЖИВАЕТСЯ** | - | Kraken Spot не имеет funding rates |
| [`create_order()`](submodules/fundingbot-sdk/src/fundingbot_sdk/contracts/ports/cex_client.py:183) | `/0/private/AddOrder` | POST | Создание ордера |
| [`get_trigger_orders()`](submodules/fundingbot-sdk/src/fundingbot_sdk/contracts/ports/cex_client.py:130) | `/0/private/OpenOrders` | POST | Фильтрация условных ордеров |
| [`close_trigger_orders()`](submodules/fundingbot-sdk/src/fundingbot_sdk/contracts/ports/cex_client.py:135) | `/0/private/CancelOrder` | POST | Отмена ордеров по ID |
| [`get_instrument_info()`](submodules/fundingbot-sdk/src/fundingbot_sdk/contracts/ports/cex_client.py:140) | `/0/public/AssetPairs` | GET | Метаданные инструмента |
| [`get_funding_rate()`](submodules/fundingbot-sdk/src/fundingbot_sdk/contracts/ports/cex_client.py:145) | **НЕ ПОДДЕРЖИВАЕТСЯ** | - | Только для futures |
| [`set_take_profit()`](submodules/fundingbot-sdk/src/fundingbot_sdk/contracts/ports/cex_client.py:150) | **НЕ ПОДДЕРЖИВАЕТСЯ** | - | Через условные ордера |
| [`set_stop_loss()`](submodules/fundingbot-sdk/src/fundingbot_sdk/contracts/ports/cex_client.py:157) | **НЕ ПОДДЕРЖИВАЕТСЯ** | - | Через условные ордера |
| [`set_position_mode()`](submodules/fundingbot-sdk/src/fundingbot_sdk/contracts/ports/cex_client.py:162) | **НЕ ПОДДЕРЖИВАЕТСЯ** | - | Spot торговля |
| [`set_margin_mode()`](submodules/fundingbot-sdk/src/fundingbot_sdk/contracts/ports/cex_client.py:169) | **НЕ ПОДДЕРЖИВАЕТСЯ** | - | Spot торговля |
| [`set_leverage()`](submodules/fundingbot-sdk/src/fundingbot_sdk/contracts/ports/cex_client.py:176) | **НЕ ПОДДЕРЖИВАЕТСЯ** | - | Spot торговля |
| [`create_tpsl_position()`](submodules/fundingbot-sdk/src/fundingbot_sdk/contracts/ports/cex_client.py:123) | `/0/private/AddOrder` | POST | Через условные ордера |
| [`get_balance()`](submodules/fundingbot-sdk/src/fundingbot_sdk/contracts/ports/cex_client.py:197) | `/0/private/Balance` | POST | Баланс по валюте |

### 7.2 Критические ограничения Kraken Spot API

**🚨 ВАЖНО**: Kraken Spot REST API **НЕ ПОДДЕРЖИВАЕТ**:
- Funding rates (только для futures)
- Позиции (только spot торговля)
- Leverage/margin режимы (только spot)
- Прямые TP/SL операции (только через условные ордера)

## 8. Сравнение с возможностями CCXT для Kraken

### 8.1 Поддержка CCXT
- ✅ **Базовая поддержка**: Kraken поддерживается в CCXT
- ✅ **Spot торговля**: полная поддержка
- ❌ **fetch_funding_rates()**: НЕ реализован
- ❌ **Futures**: требует отдельной реализации
- ✅ **Стандартные операции**: балансы, ордера, тикеры

### 8.2 Ограничения CCXT для Kraken
```python
# НЕ РАБОТАЕТ для Kraken в CCXT:
await exchange.fetch_funding_rates()  # NotSupported
await exchange.fetch_positions()      # Только для futures
await exchange.set_leverage()         # Только для futures
```

### 8.3 Рабочие методы CCXT
```python
# РАБОТАЕТ для Kraken в CCXT:
await exchange.load_markets()
await exchange.fetch_ticker(symbol)
await exchange.fetch_balance()
await exchange.create_order(...)
await exchange.fetch_open_orders()
```

## 9. Определение необходимых endpoints для fundingbot

### 9.1 Критический анализ совместимости

**Проблема**: Kraken Spot REST API **НЕ СОВМЕСТИМ** с требованиями fundingbot:

1. **Отсутствуют funding rates** - основная функция fundingbot
2. **Нет позиций** - только spot торговля
3. **Нет leverage/margin** - только spot торговля
4. **Нет futures контрактов** - только spot пары

### 9.2 Альтернативное решение: Kraken Futures API

Для полной совместимости с fundingbot требуется **Kraken Futures API**:
- **URL**: `https://futures.kraken.com/derivatives/api/v3/`
- **Funding rates**: `/tickers` endpoint содержит funding rates
- **Позиции**: поддерживаются futures позиции
- **Leverage**: поддерживается для futures

### 9.3 Рекомендация по реализации

**Вариант 1**: Реализовать [`KrakenClient`](src/fundingbot_adapters/kraken_client.py:55) для Kraken Futures API
```python
# Использовать Kraken Futures API вместо Spot
base_url = "https://futures.kraken.com/derivatives/api/v3/"
# Реализовать funding rates через /tickers
# Поддержать futures позиции и leverage
```

**Вариант 2**: Адаптировать fundingbot для spot-only бирж
```python
# Добавить поддержку spot-only режима
# Исключить funding rates для spot бирж
# Адаптировать логику для spot торговли
```

## 10. Заключение и рекомендации

### 10.1 Ключевые выводы

1. **Kraken Spot REST API хорошо документирован** и стабилен
2. **Аутентификация понятна** и реализуема
3. **Rate limits разумные** и управляемые
4. **CCXT поддержка достаточна** для spot операций
5. **НЕ СОВМЕСТИМ с fundingbot** из-за отсутствия funding rates

### 10.2 Архитектурные решения

**Для реализации [`KrakenClient`](src/fundingbot_adapters/kraken_client.py:55) рекомендуется**:

1. **Использовать Kraken Futures API** вместо Spot API
2. **Наследоваться от [`CcxtClient`](submodules/fundingbot-sdk/src/fundingbot_sdk/toolkit/client_base.py:115)** с переопределением специфичных методов
3. **Реализовать прямые API вызовы** для funding rates через `exchange.request()`
4. **Адаптировать символы** между Kraken и CCXT форматами
5. **Интегрировать rate limiter** для соблюдения ограничений

### 10.3 Следующие шаги

1. **Переключиться на Kraken Futures API** в текущей реализации
2. **Обновить endpoints** согласно исследованию в [`KRAKEN_API_RESEARCH.md`](docs/KRAKEN_API_RESEARCH.md)
3. **Протестировать funding rates** с реальными данными
4. **Запустить интеграционные тесты** для проверки совместимости
5. **Документировать ограничения** и особенности реализации

**Статус**: Исследование завершено. Kraken Spot REST API изучен, но для fundingbot требуется Kraken Futures API.