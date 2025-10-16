## fundingbot-adapters

Каркас адаптеров бирж для FundingBot.

- Назначение: реализации клиентов бирж на базе `fundingbot-sdk`.
- Совместимость: namespace‑пакеты, без `__init__.py`.

### Требования

- Установленный Poetry.
- Python 3.12+.

### Установка и запуск

Клонирование репозитория сразу с сабмодулем SDK:

```bash
git clone --recurse-submodules <URL-репозитория-adapters> fundingbot-adapters
cd fundingbot-adapters
poetry install
```

Если репозиторий уже клонирован без сабмодуля:

```bash
git submodule update --init --recursive
poetry install
```

Обновить сабмодуль на актуальное состояние ветки по умолчанию:

```bash
git submodule update --remote --recursive
```

### Зависимость `fundingbot-sdk`

- В проекте `fundingbot-sdk` подключён как path‑зависимость через сабмодуль Git: см. `pyproject.toml` (`submodules/fundingbot-sdk`).
- При необходимости можно заменить на VCS‑зависимость, сохранив контракт импортов `fundingbot_sdk`.

### Примеры использования SDK

Базовый клиент на основе ccxt (`fundingbot_sdk.toolkit.client_base.CcxtClient`):

```python
import asyncio
from fundingbot_sdk.toolkit.client_base import CcxtClient
from fundingbot_sdk.contracts.ports.cex_client import CexClientConfig


async def main():
    cfg = CexClientConfig(
        api_key="...",
        api_secret="...",
        password=None,
        uid=None,
        default_type="swap",  # или "future"/"spot" при необходимости
        testnet=True,
        rate_limiter=None,    # можно передать реализацию RateLimiterPort
    )

    client = CcxtClient("bybit", cfg)
    await client.load_markets()
    ticker = await client.get_ticker("BTC/USDT:USDT")
    print(ticker)
    await client.close()


asyncio.run(main())
```

Расширение клиента под биржевые особенности:

```python
from fundingbot_sdk.toolkit.client_base import CcxtClient


class MyBybitClient(CcxtClient):
    # при необходимости переопределяйте методы под особенности биржи
    async def get_closed_position_report(self, **kwargs):
        return await super().get_closed_position_report(**kwargs)
```

### Тесты и полезные команды

```bash
# Запуск тестов
poetry run pytest -q

# Линтер/форматтер (ruff)
poetry run ruff check
poetry run ruff format
```
