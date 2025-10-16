from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import override

from pydantic import Field, TypeAdapter, ValidationError, field_validator
from pydantic.dataclasses import dataclass as pdc_dataclass

from fundingbot_sdk.contracts.errors import FundingRateUnavailableError
from fundingbot_sdk.contracts.ports.cex_client import CexClientConfig
from fundingbot_sdk.contracts.protocols import FundingProtocol
from fundingbot_sdk.schemas.base import ResponseBase
from fundingbot_sdk.toolkit.client_base import CcxtClient, rate_limited
from fundingbot_sdk.toolkit.error_mapper import map_sdk_errors


# Так как в fetch_funding_rates() мы получаем данные не от ccxt, а raw данные от конкретного биржевого API,
# то мы не можем использовать FundingRateResponse из fundingbot-sdk,
# поэтому создаем свой класс для нормализации и валидации данных запроса финансирования для Bitget.
# Не забываем наследоваться от ResponseBase из fundingbot-sdk и использовать pydantic.dataclasses.
@pdc_dataclass(slots=True, frozen=True)
class BitgetFundingRateResponse(ResponseBase):
    """Нормализует и валидирует ставку финансирования Bitget для USDT‑свопов."""

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


BITGET_FUNDING_RATE_ADAPTER = TypeAdapter(BitgetFundingRateResponse)


class BitgetClient(CcxtClient):
    """клиент Bitget на базе ccxt для USDT‑свопов."""

    EXCHANGE_ID = "bitget"

    def __init__(self, config: CexClientConfig, *, verbose: bool = False) -> None:
        self._leverage = None
        super().__init__(exchange_name=BitgetClient.EXCHANGE_ID, config=config, verbose=verbose)

    @rate_limited(10)
    @map_sdk_errors
    @override
    # В ccxt нет реализации fetch_funding_rates() для biget, поэтому реализуем руками,
    # переопределяя метод базового класса.
    async def get_funding_usdt_rates(self, *, is_active: bool = True) -> Sequence[FundingProtocol]:
        await self._exchange.load_markets()

        # Фильтр доступных своп‑инструментов (:USDT) по состоянию рынка.
        active_symbols: set[str] | None = None
        if is_active:
            active_symbols = {
                m.get("symbol")
                for m in self._exchange.markets.values()
                if (m.get("swap") is True) and m.get("symbol").endswith(":USDT") and (m.get("active") is True)
            }

        raw_data = await self._exchange.request(
            "/v2/mix/market/current-fund-rate",
            ["public", "mix"],
            "GET",
            {"productType": "usdt-futures"},
        )

        now_utc = datetime.now(UTC)
        parsed: list[BitgetFundingRateResponse] = []
        for item in raw_data["data"]:
            try:
                model = BITGET_FUNDING_RATE_ADAPTER.validate_python({**item, "exchange": self.EXCHANGE_ID})
            except ValidationError as e:
                raise FundingRateUnavailableError(symbol=item.get("symbol"), exchange=self.EXCHANGE_ID) from e
            if model.funding_date < now_utc:
                continue
            if active_symbols is not None and model.symbol not in active_symbols:
                continue
            parsed.append(model)

        if not parsed:
            raise FundingRateUnavailableError(symbol="*/USDT", exchange=self.EXCHANGE_ID)

        return parsed
