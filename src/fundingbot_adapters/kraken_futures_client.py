import base64
import hashlib
import hmac
import time
from collections.abc import Sequence
from decimal import Decimal
from typing import Any, override
from urllib.parse import urlencode

from pydantic import TypeAdapter, ValidationError

from fundingbot_adapters.kraken_futures.kraken_futures_funding_rate_response import KrakenFuturesFundingRateResponse
from fundingbot_adapters.kraken_futures.kraken_futures_position_info_response import KrakenFuturesPositionInfoResponse
from fundingbot_adapters.kraken_futures.kraken_futures_symbol_converter import KrakenFuturesSymbolConverter
from fundingbot_sdk.contracts.errors import (
    FundingRateUnavailableError,
    OrderUnavailableError,
    TriggerOrdersUnavailableError,
    UnknownExchangeError,
    UnsupportedFeatureError,
)
from fundingbot_sdk.contracts.ports.cex_client import CexClientConfig
from fundingbot_sdk.contracts.protocols import FundingProtocol, OrderEntityProtocol, TriggerOrderProtocol
from fundingbot_sdk.toolkit.client_base import CcxtClient, rate_limited
from fundingbot_sdk.toolkit.error_mapper import map_sdk_errors

BASE_PATH = "/derivatives/api/v3"
KRAKEN_FUTURES_FUNDING_RATE_ADAPTER = TypeAdapter(KrakenFuturesFundingRateResponse)


class ExchangeUsesFiatQuoteCurrencies:
    """Биржа использует фиатные валюты в качестве котируемого символа.

    Пустой интерфейс, чтобы помечать реализации CcxtClient, что биржи, с которыми эти клиенты работают, используют
    фиатные валюты в качестве котируемого символа (USD место USDT).
    """


class KrakenFuturesClient(CcxtClient, ExchangeUsesFiatQuoteCurrencies):
    """клиент Kraken на базе ccxt для USD‑свопов."""

    EXCHANGE_ID = "krakenfutures"

    _position_info_adapter = TypeAdapter(KrakenFuturesPositionInfoResponse)

    def __init__(self, config: CexClientConfig, *, verbose: bool = False) -> None:
        self._leverage = None
        super().__init__(exchange_name=KrakenFuturesClient.EXCHANGE_ID, config=config, verbose=verbose)

        # Kraken Futures API configuration
        self.futures_base_url = "https://futures.kraken.com/derivatives/api/v3"
        if config.testnet:
            self.futures_base_url = "https://demo-futures.kraken.com/derivatives/api/v3"

    @map_sdk_errors
    @override
    async def get_trigger_orders(self, symbol: str) -> Sequence[TriggerOrderProtocol]:
        native_symbol = KrakenFuturesSymbolConverter.from_ccxt_to_kraken(symbol)
        all_orders = await self._exchange.fetch_open_orders(symbol=native_symbol)
        tpsl_orders = [o for o in all_orders if o["type"] == "stop"]
        try:
            return self._trigger_order_list_adapter.validate_python(tpsl_orders)
        except ValidationError as e:
            raise TriggerOrdersUnavailableError(symbol=symbol, exchange=self.cex_id) from e

    @map_sdk_errors
    @override
    async def get_funding_rate(self, symbol: str) -> FundingProtocol:
        # Получаем данные через tickers API
        params_dict: dict[str, Any] = {}
        headers = await self._create_request_headers("tickers", params_dict)
        raw_data = await self._exchange.request("tickers", "public", method="GET", params=params_dict, headers=headers)

        # Ищем нужный символ в ответе
        # Нужно искать по полю pair, которое имеет формат "XRP:USD"
        target_pair = symbol.replace("/", ":").replace(":USD", ":USD")  # XRP/USD:USD -> XRP:USD
        target_pair = target_pair.split(":")[0] + ":" + target_pair.split(":")[1]  # XRP/USD:USD -> XRP:USD

        for item in raw_data["tickers"]:
            if item.get("pair") == target_pair and item.get("fundingRate") is not None:
                try:
                    model = KRAKEN_FUTURES_FUNDING_RATE_ADAPTER.validate_python({**item, "exchange": self.EXCHANGE_ID})
                    if model.symbol == symbol:
                        return model
                except ValidationError as e:
                    raise FundingRateUnavailableError(symbol=symbol, exchange=self.EXCHANGE_ID) from e

        raise FundingRateUnavailableError(symbol=symbol, exchange=self.EXCHANGE_ID)

    @rate_limited(10)
    @map_sdk_errors
    @override
    # В ccxt нет реализации fetch_funding_rates() для bitget, поэтому реализуем руками,
    # переопределяя метод базового класса.
    async def get_funding_usdt_rates(self, *, is_active: bool = True) -> Sequence[FundingProtocol]:
        await self._exchange.load_markets()

        # Фильтр доступных своп‑инструментов (:USDT) по состоянию рынка.
        active_symbols: set[str] | None = None
        if is_active:
            active_symbols = {
                m.get("symbol")
                for m in self._exchange.markets.values()
                if (m.get("swap") is True) and m.get("symbol").endswith(":USD") and (m.get("active") is True)
            }

        params_dict: dict[str, Any] = {}
        headers = await self._create_request_headers("tickers", params_dict)
        raw_data = await self._exchange.request("tickers", "public", method="GET", params=params_dict, headers=headers)

        # now_utc = datetime.now(UTC)
        parsed: list[KrakenFuturesFundingRateResponse] = []
        for item in raw_data["tickers"]:
            if item.get("fundingRate") is None:
                continue
            try:
                model = KRAKEN_FUTURES_FUNDING_RATE_ADAPTER.validate_python({**item, "exchange": self.EXCHANGE_ID})
            except ValidationError as e:
                raise FundingRateUnavailableError(symbol=item.get("symbol"), exchange=self.EXCHANGE_ID) from e
            # if model.funding_date < now_utc:
            #     continue
            if active_symbols is not None and model.symbol not in active_symbols:
                continue
            parsed.append(model)

        if not parsed:
            raise FundingRateUnavailableError(symbol="*/USDT:USDT", exchange=self.EXCHANGE_ID)

        return parsed

    @map_sdk_errors
    @override
    async def set_position_mode(self, *, hedged: bool, symbol: str | None = None, params: dict[str, Any] | None = None) -> None:
        raise UnsupportedFeatureError(self.EXCHANGE_ID, "setPositionMode", params={})

    @map_sdk_errors
    @override
    async def set_margin_mode(self, *, margin_mode: str, symbol: str | None = None, params: dict[str, Any] | None = None) -> None:
        if symbol is None:
            raise UnsupportedFeatureError(self.EXCHANGE_ID, "setMarginMode(symbol=None)", params={})

        # Согласно docs: можно задать symbol, marginMode и/или maxLeverage.[web:1]
        native_symbol = KrakenFuturesSymbolConverter.from_ccxt_to_kraken(symbol)
        params_dict = {"symbol": native_symbol}
        # params = {"symbol": symbol}

        # Если явно указать режим
        if margin_mode.lower() == "cross":
            pass  # Не указываем maxLeverage
        elif margin_mode.lower() == "isolated":
            if params is None or "leverage" not in params:
                exception_message = "params should contain 'leverage'"
                raise ValueError(exception_message)
            params_dict["maxLeverage"] = params["leverage"]
        else:
            error_message = "mode must be 'cross' or 'isolated'"
            raise ValueError(error_message)

        headers = await self._create_request_headers("leveragepreferences", params_dict)

        resp = await self._exchange.request("leveragepreferences", "public", method="PUT", params=params_dict, headers=headers)
        if resp["result"] != "success":
            raise UnknownExchangeError

    @map_sdk_errors
    @override
    async def set_leverage(self, *, leverage: int, symbol: str | None = None, params: dict[str, Any] | None = None) -> None:
        if symbol is None:
            raise UnsupportedFeatureError(self.EXCHANGE_ID, "setMarginMode(symbol=None)", params={})

        return await super().set_leverage(leverage=leverage, symbol=symbol, params=params)

    @rate_limited(3)
    @map_sdk_errors
    @override
    async def create_tpsl_position(
        self,
        *,
        symbol: str,
        side: str,
        order_type: str,
        amount: Decimal,
        take_profit: Decimal,
        stop_loss: Decimal,
        margin_mode: str = "isolated",
    ) -> OrderEntityProtocol:
        data = await self._exchange.create_order(symbol=symbol, side=side, type=order_type, amount=amount)

        await self._exchange.create_order(
            symbol, "stp", self._against_side(side), amount=amount, params={"stopPrice": stop_loss, "reduceOnly": True}
        )

        await self._exchange.create_order(
            symbol, "take_profit", self._against_side(side), amount=amount, params={"stopPrice": take_profit, "reduceOnly": True}
        )

        try:
            return self._create_order_response_adapter.validate_python(data)
        except ValidationError as e:
            raise OrderUnavailableError(symbol=symbol, exchange=self.cex_id) from e

    @staticmethod
    def _against_side(side: str) -> str:
        if side == "buy":
            return "sell"
        if side == "sell":
            return "buy"
        error_message = "Side must be 'buy' or 'sell'."
        raise ValueError(error_message)

    async def _create_request_headers(self, short_url_path: str, params_dict: dict[str, Any]) -> dict[str, str]:
        nonce = str(int(time.time() * 1000))
        return {
            "APIKey": self._exchange.apiKey,
            "Nonce": nonce,
            "Authent": self._create_futures_signature("/api/v3/" + short_url_path, nonce, urlencode(params_dict)),
            "Content-Type": "application/json",
        }

    def _create_futures_signature(self, endpoint: str, nonce: str, postdata: str) -> str:
        message = postdata + nonce + endpoint
        sha256_hash = hashlib.sha256(message.encode("utf-8")).digest()
        signature = hmac.new(base64.b64decode(self._exchange.secret), sha256_hash, hashlib.sha512).digest()
        return base64.b64encode(signature).decode("utf-8")
