import base64
import hashlib
import hmac
import time
from decimal import Decimal
from typing import Any, override, Sequence
from urllib.parse import urlencode

from pydantic import ValidationError, TypeAdapter

from fundingbot_adapters.kraken_futures_market_response import KrakenFuturesMarketResponse
from fundingbot_adapters.kraken_futures_position_info_response import KrakenFuturesPositionInfoResponse
from fundingbot_adapters.kraken_futures_symbol_converter import KRAKEN_FUTURES_SYMBOL_CONVERTER
from fundingbot_sdk.contracts.errors import OrderUnavailableError, UnknownExchangeError, UnsupportedFeatureError, \
    TriggerOrdersUnavailableError
from fundingbot_sdk.contracts.ports.cex_client import CexClientConfig
from fundingbot_sdk.contracts.protocols import OrderEntityProtocol, TickerProtocol, PositionProtocol, InstrumentProtocol, \
    TriggerOrderProtocol, FundingProtocol, BalanceProtocol
from fundingbot_sdk.toolkit.client_base import CcxtClient, rate_limited
from fundingbot_sdk.toolkit.error_mapper import map_sdk_errors

BASE_PATH = "/derivatives/api/v3"


class KrakenFuturesClient(CcxtClient):
    """клиент Kraken на базе ccxt для USD‑свопов."""

    EXCHANGE_ID = "krakenfutures"

    _position_info_adapter = TypeAdapter(KrakenFuturesPositionInfoResponse)
    _market_response_adapter = TypeAdapter(KrakenFuturesMarketResponse)

    def __init__(self, config: CexClientConfig, *, verbose: bool = False) -> None:
        self._leverage = None
        super().__init__(exchange_name=KrakenFuturesClient.EXCHANGE_ID, config=config, verbose=verbose)

        # Kraken Futures API configuration
        self.futures_base_url = "https://futures.kraken.com/derivatives/api/v3"
        if config.testnet:
            self.futures_base_url = "https://demo-futures.kraken.com/derivatives/api/v3"

    @map_sdk_errors
    @override
    async def get_market_symbols(self) -> list[str]:
        super_result = await super().get_market_symbols()
        return [KRAKEN_FUTURES_SYMBOL_CONVERTER.quote_from_fiat_to_stable_coin_if_needed(symbol) for symbol in super_result]

    @map_sdk_errors
    @override
    async def get_ticker(self, symbol: str) -> TickerProtocol:
        fiat_quote_symbol = KRAKEN_FUTURES_SYMBOL_CONVERTER.quote_from_stable_coin_to_fiat_if_needed(symbol)
        native_symbol = KRAKEN_FUTURES_SYMBOL_CONVERTER.from_standard_to_native(fiat_quote_symbol)
        return await super().get_ticker(native_symbol)

    @map_sdk_errors
    @override
    async def get_positions(self, symbols: list[str], params: dict[str, Any] | None = None) -> Sequence[
        PositionProtocol]:
        fiat_quote_symbols = [KRAKEN_FUTURES_SYMBOL_CONVERTER.quote_from_stable_coin_to_fiat_if_needed(symbol) for symbol in symbols]
        return await super().get_positions(fiat_quote_symbols, params)

    @map_sdk_errors
    @override
    async def close_trigger_orders(self, symbol: str, ids: list[str], params: dict[str, Any] | None = None) -> None:
        fiat_quote_symbol = KRAKEN_FUTURES_SYMBOL_CONVERTER.quote_from_stable_coin_to_fiat_if_needed(symbol)
        return await super().close_trigger_orders(fiat_quote_symbol, ids, params)

    @map_sdk_errors
    @override
    async def get_instrument_info(self, symbol: str) -> InstrumentProtocol:
        fiat_quote_symbol = KRAKEN_FUTURES_SYMBOL_CONVERTER.quote_from_stable_coin_to_fiat_if_needed(symbol)
        return await super().get_instrument_info(fiat_quote_symbol)

    @map_sdk_errors
    @override
    async def get_trigger_orders(self, symbol: str) -> Sequence[TriggerOrderProtocol]:
        fiat_quote_symbol = KRAKEN_FUTURES_SYMBOL_CONVERTER.quote_from_stable_coin_to_fiat_if_needed(symbol)
        native_symbol = KRAKEN_FUTURES_SYMBOL_CONVERTER.from_standard_to_native(fiat_quote_symbol)
        tpsl_orders = await self._exchange.fetch_open_orders(symbol=native_symbol)
        try:
            return self._trigger_order_list_adapter.validate_python(tpsl_orders)
        except ValidationError as e:
            raise TriggerOrdersUnavailableError(symbol=symbol, exchange=self.cex_id) from e

    @map_sdk_errors
    @override
    async def get_funding_rate(self, symbol: str) -> FundingProtocol:
        fiat_quote_symbol = KRAKEN_FUTURES_SYMBOL_CONVERTER.quote_from_stable_coin_to_fiat_if_needed(symbol)
        return await super().get_funding_rate(fiat_quote_symbol)

    @map_sdk_errors
    @override
    async def set_position_mode(self, *, hedged: bool, symbol: str | None = None, params: dict[str, Any] | None = None) -> None:
        raise UnsupportedFeatureError(self.EXCHANGE_ID, "setPositionMode", params={})

    @map_sdk_errors
    @override
    async def set_margin_mode(self, *, margin_mode: str, symbol: str | None = None, params: dict[str, Any] | None = None) -> None:
        # Согласно docs: можно задать symbol, marginMode и/или maxLeverage.[web:1]
        fiat_quote_symbol = KRAKEN_FUTURES_SYMBOL_CONVERTER.quote_from_stable_coin_to_fiat_if_needed(symbol)
        native_symbol = KRAKEN_FUTURES_SYMBOL_CONVERTER.from_standard_to_native(fiat_quote_symbol)
        params_dict = {"symbol": native_symbol}
        # params = {"symbol": symbol}

        # Если явно указать режим
        if margin_mode.lower() == "cross":
            pass  # Не указываем maxLeverage
        elif margin_mode.lower() == "isolated":
            if "leverage" not in params:
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
    async def set_leverage(self, *, leverage: int, symbol: str | None = None,
                           params: dict[str, Any] | None = None) -> None:
        fiat_quote_symbol = KRAKEN_FUTURES_SYMBOL_CONVERTER.quote_from_stable_coin_to_fiat_if_needed(symbol)
        return await super().set_leverage(leverage=leverage, symbol=fiat_quote_symbol, params=params)

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
        fiat_quote_symbol = KRAKEN_FUTURES_SYMBOL_CONVERTER.quote_from_stable_coin_to_fiat_if_needed(symbol)
        data = await self._exchange.create_order(symbol=fiat_quote_symbol, side=side, type=order_type, amount=amount)

        await self._exchange.create_order(
            fiat_quote_symbol,
            "stp",
            self._against_side(side),
            amount=amount,
            params={"stopPrice": stop_loss, "reduceOnly": True},
        )

        await self._exchange.create_order(
            fiat_quote_symbol,
            "take_profit",
            self._against_side(side),
            amount=amount,
            params={"stopPrice": take_profit, "reduceOnly": True},
        )

        try:
            return self._create_order_response_adapter.validate_python(data)
        except ValidationError as e:
            raise OrderUnavailableError(symbol=symbol, exchange=self.cex_id) from e

    @map_sdk_errors
    @override
    async def create_order(self, symbol: str, order_type: str, side: str, amount: Decimal, price: Decimal | None = None,
                           params: dict[str, Any] | None = None, margin_mode: str = "isolated") -> OrderEntityProtocol:
        fiat_quote_symbol = KRAKEN_FUTURES_SYMBOL_CONVERTER.quote_from_stable_coin_to_fiat_if_needed(symbol)
        return await super().create_order(fiat_quote_symbol, order_type, side, amount, price, params, margin_mode)

    @map_sdk_errors
    @override
    def price_to_precision(self, symbol: str, price: Decimal) -> Decimal:
        fiat_quote_symbol = KRAKEN_FUTURES_SYMBOL_CONVERTER.quote_from_stable_coin_to_fiat_if_needed(symbol)
        return super().price_to_precision(fiat_quote_symbol, price)

    @map_sdk_errors
    @override
    async def get_balance(self, coin: str) -> BalanceProtocol:
        if coin == "USD":
            coin = "USDT"
        return await super().get_balance(coin)

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
