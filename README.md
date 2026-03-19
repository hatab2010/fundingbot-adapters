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
```

Если репозиторий уже клонирован без сабмодуля:

```bash
git submodule update --init --recursive

```

Обновить сабмодуль на актуальное состояние ветки по умолчанию:

```bash
git submodule update --remote --recursive
```

### Активация виртуального окружения (PowerShell)

Перед запуском ruff убедитесь, что активировано виртуальное окружение:

```powershell
# Активация виртуального окружения
.\venv\Scripts\Activate.ps1

# Проверка активации (должен показать путь к venv)
Get-Command python
```

Если виртуальное окружение не создано, создайте и активируйте его:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Установка пакетов

```
pip install poetry
poetry install
pip uninstall aiodns
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
```

### Code Quality and Linting

Проект использует [ruff](https://docs.astral.sh/ruff/) для линтинга и форматирования кода. Ruff — это быстрый линтер и форматтер для Python, который заменяет множество инструментов (flake8, isort, black и др.).

#### Основные команды ruff

Проверка кода на ошибки

```powershell
# Проверка всего проекта
poetry run ruff check

# Проверка конкретного файла
poetry run ruff check src/fundingbot_adapters/kraken_futures_client.py

# Проверка с подробным выводом
poetry run ruff check --verbose

# Показать только ошибки (без предупреждений)
poetry run ruff check --select E
```

Автоматическое исправление ошибок

```powershell
# Исправить все автоматически исправимые ошибки
poetry run ruff check --fix

# Исправить ошибки в конкретном файле
poetry run ruff check --fix src/fundingbot_adapters/kraken_futures_client.py

# Предварительный просмотр изменений (без применения)
poetry run ruff check --fix --diff
```

Форматирование кода

```powershell
# Форматировать весь проект
poetry run ruff format

# Форматировать конкретный файл
poetry run ruff format src/fundingbot_adapters/kraken_futures_client.py

# Предварительный просмотр форматирования
poetry run ruff format --diff

# Проверить, нужно ли форматирование (без изменений)
poetry run ruff format --check
```

#### Работа с большим количеством ошибок

В проекте обнаружено **197 ошибок линтинга**. Рекомендуемый подход для их исправления:

##### Шаг 1: Автоматические исправления

```powershell
# Исправить все автоматически исправимые ошибки
poetry run ruff check --fix

# Применить форматирование
poetry run ruff format

# Типизация (pyright)
poetry run pyright
```

### Git-хуки (проверки перед commit и push)

```bash
# Установить хуки pre-commit и pre-push
poetry run pre-commit install --hook-type pre-commit --hook-type pre-push

# Прогнать все проверки вручную по всему репозиторию
poetry run pre-commit run --all-files
```

##### Шаг 2: Исправление по категориям

```powershell
# Исправить только импорты
poetry run ruff check --select I --fix

# Исправить только неиспользуемые импорты
poetry run ruff check --select F401 --fix

# Исправить только проблемы с длиной строк
poetry run ruff check --select E501 --fix
```

##### Шаг 3: Работа с конкретными файлами

```powershell
# Сначала исправить основной файл клиента
poetry run ruff check --fix src/fundingbot_adapters/kraken_futures_client.py
poetry run ruff format src/fundingbot_adapters/kraken_futures_client.py

# Затем тесты
poetry run ruff check --fix tests/
poetry run ruff format tests/
```

#### Настройка переменных окружения

Перед запуском тестов убедитесь, что настроены переменные окружения:

```powershell
# Применить переменные из .env файла
.\scripts\ApplyDotEnv.ps1

# Проверить, что KRAKEN_API_KEY установлен
$env:KRAKEN_API_KEY
```

#### Интеграция в рабочий процесс

Рекомендуемый рабочий процесс:

```powershell
# Активировать окружение
.\venv\Scripts\Activate.ps1

# Проверить код
poetry run ruff check

# Исправить автоматически исправимые ошибки
poetry run ruff check --fix

# Отформатировать код
poetry run ruff format

# Запустить тесты
poetry run pytest -q

# Финальная проверка
poetry run ruff check
```

### Type Checking with Pyright

Проект использует [pyright](https://github.com/microsoft/pyright) для статической проверки типов. Pyright — это быстрый и точный анализатор типов для Python, который помогает выявлять ошибки типизации на этапе разработки.

Pyright настроен в **strict режиме** через [`pyrightconfig.json`](pyrightconfig.json), что обеспечивает максимально строгую проверку типов и помогает поддерживать высокое качество кода.

#### Основные команды pyright

Проверка типов во всем проекте:

```powershell
# Проверка всего проекта
poetry run pyright

# Проверка конкретного файла
poetry run pyright src/fundingbot_adapters/kraken_futures_client.py

# Проверка с подробным выводом
poetry run pyright --verbose

# Проверка только ошибок (без предупреждений)
poetry run pyright --level error
```
