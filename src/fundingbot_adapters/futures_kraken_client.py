import base64
import hashlib
import hmac
import time
import urllib.parse
from datetime import UTC, datetime
from decimal import Decimal
from typing import override

import aiohttp
from pydantic import Field, TypeAdapter, field_validator
from pydantic.dataclasses import dataclass as pdc_dataclass

from fundingbot_sdk.contracts.ports.cex_client import CexClientConfig
from fundingbot_sdk.schemas.base import ResponseBase
from fundingbot_sdk.toolkit.client_base import CcxtClient


# Так как в fetch_funding_rates() мы получаем данные не от ccxt, а raw данные от конкретного биржевого API,
# то мы не можем использовать FundingRateResponse из fundingbot-sdk,
# поэтому создаем свой класс для нормализации и валидации данных запроса финансирования для Kraken.
# Не забываем наследоваться от ResponseBase из fundingbot-sdk и использовать pydantic.dataclasses.
@pdc_dataclass(slots=True, frozen=True)
class FuturesKrakenFundingRateResponse(ResponseBase):
    """Нормализует и валидирует ставку финансирования Kraken для USDT‑свопов."""

    symbol: str = Field(..., validation_alias="symbol", description="Символ инструмента в формате CCXT (:USDT)")
    exchange: str = Field(..., description="Биржа")
    funding_rate: Decimal = Field(..., validation_alias="fundingRate", description="Ставка финансирования (доля)")
    funding_date: datetime = Field(..., validation_alias="nextUpdate", description="Дата и время выплаты финансирования (UTC)")

    @field_validator("symbol", mode="before")
    def normalize_symbol(cls, v: str) -> str:
        """Приводит symbol к виду BASE/USDT:USDT."""
        raw = str(v)
        if ":" in raw:
            return raw if raw.endswith(":USDT") else f"{raw}:USDT"
        if raw.endswith("USDT"):
            base = raw[:-4]
            return f"{base}/USDT:USDT"
        return f"{raw}:USDT"

    @field_validator("funding_date", mode="before")
    def to_datetime(cls, v: str | int | datetime) -> datetime:
        """Преобразует мс Unix к UTC‑aware datetime."""
        if isinstance(v, datetime):
            return v
        return datetime.fromtimestamp(int(v) / 1000, tz=UTC)


FUTURES_KRAKEN_FUNDING_RATE_ADAPTER = TypeAdapter(FuturesKrakenFundingRateResponse)


class FuturesKrakenClient(CcxtClient):
    """клиент Kraken на базе ccxt для USDT‑свопов."""

    EXCHANGE_ID = "krakenfutures"

    def __init__(self, config: CexClientConfig, *, verbose: bool = False) -> None:
        self._leverage = None
        super().__init__(exchange_name=FuturesKrakenClient.EXCHANGE_ID, config=config, verbose=verbose)
        
        # Kraken Futures API configuration
        self.futures_base_url = 'https://futures.kraken.com/derivatives/api/v3'
        if config.testnet:
            self.futures_base_url = 'https://demo-futures.kraken.com/derivatives/api/v3'
