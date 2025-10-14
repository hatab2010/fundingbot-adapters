# fundingbot-adapters

Каркас адаптеров бирж для FundingBot.

- Назначение: реализации клиентов бирж на базе `fundingbot-sdk`.
- Совместимость: namespace‑пакеты, без `__init__.py`.

## Зависимость `fundingbot-sdk`

- Проект зависит от `fundingbot-sdk`, подключённого как path‑зависимость (editable) в `pyproject.toml`.
- Для корректной установки необходимо расположить исходники `fundingbot-sdk` рядом с этим репозиторием на один уровень выше по пути.

Ожидаемая структура каталогов:

```text
../fundingbot-sdk/
../fundingbot-adapters/
```

Быстрый старт:

```bash
cd ..
git clone <URL-репозитория-fundingbot-sdk> fundingbot-sdk
cd fundingbot-adapters
poetry install
```

Альтернативно можно изменить путь в `pyproject.toml` или установить `fundingbot-sdk` другим способом (например, из VCS или из реестра пакетов), соблюдая контракт импортов `fundingbot_sdk`.

## Тесты

```bash
poetry run pytest -q
```
