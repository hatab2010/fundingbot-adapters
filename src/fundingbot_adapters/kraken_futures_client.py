import base64
import hashlib
import hmac
import time
from decimal import Decimal
from typing import Any, Sequence, override
from urllib.parse import urlencode

from pydantic import ValidationError

from fundingbot_sdk.contracts.errors import UnknownExchangeError, UnsupportedFeatureError, OrderUnavailableError
from fundingbot_sdk.contracts.ports.cex_client import CexClientConfig
from fundingbot_sdk.contracts.protocols import PositionProtocol, OrderEntityProtocol
from fundingbot_sdk.toolkit.client_base import CcxtClient
from fundingbot_sdk.toolkit.symbol_converter import SymbolConverter

BASE_PATH = "/derivatives/api/v3"


class KrakenFuturesSymbolConverter(SymbolConverter):
    def from_standard_to_native(self, symbol: str) -> str:
        """Convert CCXT symbol format to Kraken native symbol format.

        Examples:
        'XRP/USDT:USD' -> 'PF_XRPUSD'
        'BTC/USDT:USD' -> 'PF_XBTUSD'
        'ETH/USDT:USD' -> 'PF_ETHUSD'

        """
        if ":" not in symbol:
            raise ValueError(f"Invalid CCXT swap symbol format: {symbol}. Expected format: BASE/QUOTE:SETTLE")

        # Split the symbol to get base/quote part
        base_quote_part = symbol.split(":")[0]  # 'XRP/USD' from 'XRP/USD:USD'

        if "/" not in base_quote_part:
            raise ValueError(f"Invalid CCXT symbol format: {symbol}. Expected format: BASE/QUOTE:SETTLE")

        base, quote = base_quote_part.split("/")

        if quote == "USDT":
            quote = "USD"

        # Handle special case: BTC -> XBT conversion for Kraken
        if base == "BTC":
            base = "XBT"

        # Construct Kraken native symbol with PF_ prefix for perpetual futures
        native_symbol = f"PF_{base}{quote}"
        return native_symbol

    def quote_from_stable_coin_to_fiat_if_needed(self, symbol: str) -> str:
        """
        Examples:
        'XRP/USDT:USDT' -> 'XRP/USD:USD'
        """
        if ":" not in symbol:
            raise ValueError(f"Invalid CCXT swap symbol format: {symbol}. Expected format: BASE/QUOTE:SETTLE")

        # Split the symbol to get base/quote part
        base_quote_part, settle = symbol.split(":")  # 'XRP/USD' from 'XRP/USD:USD'

        if "/" not in base_quote_part:
            raise ValueError(f"Invalid CCXT symbol format: {symbol}. Expected format: BASE/QUOTE:SETTLE")

        base, quote = base_quote_part.split("/")

        if quote == "USDT":
            quote = "USD"

        if settle == "USDT":
            settle = "USD"

        return f"{base}/{quote}:{settle}"

    def quote_from_fiat_to_stable_coin_if_needed(self, symbol: str) -> str:
        """
        Examples:
        'XRP/USDT:USDT' -> 'XRP/USD:USD'
        """
        if ":" not in symbol:
            raise ValueError(f"Invalid CCXT swap symbol format: {symbol}. Expected format: BASE/QUOTE:SETTLE")

        # Split the symbol to get base/quote part
        base_quote_part, settle = symbol.split(":")  # 'XRP/USD' from 'XRP/USD:USD'

        if "/" not in base_quote_part:
            raise ValueError(f"Invalid CCXT symbol format: {symbol}. Expected format: BASE/QUOTE:SETTLE")

        base, quote = base_quote_part.split("/")

        if quote == "USD":
            quote = "USDT"

        if settle == "USD":
            settle = "USDT"

        return f"{base}/{quote}:{settle}"


KRAKEN_FUTURES_SYMBOL_CONVERTER = KrakenFuturesSymbolConverter()


class KrakenFuturesClient(CcxtClient):
    """клиент Kraken на базе ccxt для USD‑свопов."""

    EXCHANGE_ID = "krakenfutures"

    def __init__(self, config: CexClientConfig, *, verbose: bool = False) -> None:
        self._leverage = None
        super().__init__(exchange_name=KrakenFuturesClient.EXCHANGE_ID, config=config, verbose=verbose)

        # Kraken Futures API configuration
        self.futures_base_url = "https://futures.kraken.com/derivatives/api/v3"
        if config.testnet:
            self.futures_base_url = "https://demo-futures.kraken.com/derivatives/api/v3"

    @override
    def get_symbol_converter(self) -> SymbolConverter:
        return KRAKEN_FUTURES_SYMBOL_CONVERTER

    @override
    async def set_position_mode(self, *, hedged: bool, symbol: str | None = None, params: dict[str, Any] | None = None) -> None:
        raise UnsupportedFeatureError(self.EXCHANGE_ID, "setPositionMode", params={})

    @override
    async def set_margin_mode(self, *, margin_mode: str, symbol: str | None = None, params: dict[str, Any] | None = None):
        # Согласно docs: можно задать symbol, marginMode и/или maxLeverage.[web:1]
        symbol_converter = self.get_symbol_converter()
        native_symbol = symbol_converter.from_standard_to_native(symbol_converter.quote_from_stable_coin_to_fiat_if_needed(symbol))
        params_dict = {"symbol": native_symbol}
        # params = {"symbol": symbol}

        # Если явно указать режим
        if margin_mode.lower() == "cross":
            pass  # Не указываем maxLeverage
        elif margin_mode.lower() == "isolated":
            if "leverage" not in params:
                raise ValueError("params should contain 'leverage'")
            params_dict["maxLeverage"] = params["leverage"]
        else:
            raise ValueError("mode must be 'cross' or 'isolated'")

        headers = await self.create_request_headers("leveragepreferences", params_dict)

        resp = await self._exchange.request("leveragepreferences", "public", method="PUT", params=params_dict, headers=headers)
        if resp["result"] != "success":
            raise UnknownExchangeError()
    #
    # @override
    # async def get_positions(self, symbols: list[str], params: dict[str, Any] | None = None) -> Sequence[PositionProtocol]:
    #     positions = await super().get_positions(symbols, params)
    #     for position in positions:
    #         if position.hedged is None:
    #             position.hedged = False
    #     return positions

    async def create_request_headers(self, short_url_path: str, params_dict: dict[str, Any]) -> dict[str, str]:
        nonce = str(int(time.time() * 1000))
        headers = {
            "APIKey": self._exchange.apiKey,
            "Nonce": nonce,
            "Authent": self.create_futures_signature("/api/v3/" + short_url_path, nonce, urlencode(params_dict)),
            "Content-Type": "application/json",
        }
        return headers

    def create_futures_signature(self, endpoint: str, nonce: str, postdata: str) -> str:
        message = postdata + nonce + endpoint
        sha256_hash = hashlib.sha256(message.encode("utf-8")).digest()
        signature = hmac.new(base64.b64decode(self._exchange.secret), sha256_hash, hashlib.sha512).digest()
        return base64.b64encode(signature).decode("utf-8")

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
        fiat_quote_symbol = self.get_symbol_converter().quote_from_stable_coin_to_fiat_if_needed(symbol)
        data = await self._exchange.create_order(symbol=fiat_quote_symbol, side=side, type=order_type, amount=amount)

        await self._exchange.create_order(
            fiat_quote_symbol,
            "stp",
            self.against_side(side),
            amount=amount,
            params={'stopPrice': stop_loss, 'reduceOnly': True},
        )

        await self._exchange.create_order(
            fiat_quote_symbol,
            "take_profit",
            self.against_side(side),
            amount=amount,
            params={'stopPrice': take_profit, 'reduceOnly': True},
        )

        try:
            return self._create_order_response_adapter.validate_python(data)
        except ValidationError as e:
            raise OrderUnavailableError(symbol=symbol, exchange=self.cex_id) from e

    @staticmethod
    def against_side(side):
        if side == "buy":
            return "sell"
        elif side == "sell":
            return "buy"
        else:
            raise ValueError("Side must be 'buy' or 'sell'.")


