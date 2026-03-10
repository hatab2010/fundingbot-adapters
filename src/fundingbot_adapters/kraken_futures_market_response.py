"""Схемы рынка (market) SDK.

Определяют компактные pydantic dataclass‑модели метаданных инструмента: точности,
граничные лимиты и идентификацию символа. Схемы согласованы с контрактами
``fundingbot_sdk.contracts.protocols.InstrumentProtocol`` и предназначены для
нормализации данных поставщиков (например, биржевых API).

Модели принимают избыточные входные ключи и игнорируют их (см. базовый ``BaseDTO``),
что упрощает интеграцию с различными источниками. Состав полей может расширяться
в минорных релизах без нарушения обратной совместимости.
"""

from pydantic import field_validator
from pydantic.dataclasses import dataclass as pdc_dataclass

from fundingbot_adapters.kraken_futures_symbol_converter import KRAKEN_FUTURES_SYMBOL_CONVERTER
from fundingbot_sdk.schemas.market import MarketResponse


@pdc_dataclass(slots=True, frozen=True)
class KrakenFuturesMarketResponse(MarketResponse):
    """Нормализованная модель метаданных инструмента.

    Контракт совпадает с ``MarketResponse``. Дополнительно нормализуются:
    - поле symbol - конвертируется из символа с фиатной quote-частью в соответствующий символ со стейблкоином.
    """

    @field_validator("symbol", mode="before")
    @classmethod
    def stable_coin_quote_symbol(cls, v: str) -> str:
        return KRAKEN_FUTURES_SYMBOL_CONVERTER.quote_from_fiat_to_stable_coin_if_needed(v)
