from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast

from pydantic import Field, field_validator, model_validator
from pydantic.dataclasses import dataclass as pdc_dataclass

from fundingbot_adapters.kraken_futures.kraken_futures_utils import calculate_next_funding_timestamp
from fundingbot_sdk.schemas.base import ResponseBase


@pdc_dataclass(slots=True, frozen=True)
class KrakenFuturesFundingRateResponse(ResponseBase):
    """Нормализует и валидирует ставку финансирования Kraken Futures для USDT‑свопов."""

    symbol: str = Field(..., validation_alias="symbol", description="Символ инструмента в формате CCXT (:USD)")
    exchange: str = Field(..., description="Биржа")
    funding_rate: Decimal = Field(..., validation_alias="fundingRate", description="Ставка финансирования (доля)")
    funding_date: datetime = Field(..., validation_alias="fundingDate", description="Дата и время выплаты финансирования (UTC)")

    @model_validator(mode="before")
    @classmethod
    def pair_to_symbol_and_add_funding_timestamp(cls, data: object) -> object:
        """Приводит symbol к виду BASE/USDT:USDT и добавляет fundingDate."""
        if not isinstance(data, dict):
            return data

        item: dict[str, Any] = dict(cast("dict[str, Any]", data))

        # Конвертация символа
        pair = item.get("pair")
        if pair is not None:
            base_cur, quote_cur = pair.split(":")
            item["symbol"] = f"{base_cur}/{quote_cur}:{quote_cur}"

        # Добавление fundingDate если его нет
        item["fundingDate"] = calculate_next_funding_timestamp()

        return item

    @field_validator("funding_date", mode="before")
    @classmethod
    def to_datetime(cls, v: str | int | datetime) -> datetime:
        """Преобразует различные форматы к UTC‑aware datetime."""
        if isinstance(v, datetime):
            return v if v.tzinfo is not None else v.replace(tzinfo=UTC)
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(int(v) / 1000, tz=UTC)
        # Строка: допускаем суффикс Z
        iso = str(v).replace("Z", "+00:00")
        return datetime.fromisoformat(iso)
