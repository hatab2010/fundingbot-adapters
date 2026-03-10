import base64
import hashlib
import hmac
import time
from typing import Any, override
from urllib.parse import urlencode

from fundingbot_sdk.contracts.errors import UnknownExchangeError, UnsupportedFeatureError
from fundingbot_sdk.contracts.ports.cex_client import CexClientConfig
from fundingbot_sdk.toolkit.client_base import CcxtClient
from fundingbot_sdk.toolkit.symbol_converter import SymbolConverter

BASE_PATH = "/derivatives/api/v3"


class KrakenFuturesSymbolConverter(SymbolConverter):
    """клиент Kraken Futures на базе ccxt для USDT‑свопов."""

    def from_standard_to_native(self, symbol: str) -> str:  # noqa: PLR6301
        """Convert CCXT symbol format to Kraken native symbol format.

        Examples:
        'XRP/USDT:USD' -> 'PF_XRPUSD'
        'BTC/USDT:USD' -> 'PF_XBTUSD'
        'ETH/USDT:USD' -> 'PF_ETHUSD'

        Raises:
        ------
        ValueError
            If invalid CCXT symbol format.

        """
        if ":" not in symbol:
            error_message = f"Invalid CCXT swap symbol format: {symbol}. Expected format: BASE/QUOTE:SETTLE"
            raise ValueError(error_message)

        # Split the symbol to get base/quote part
        # 'XRP/USD' from 'XRP/USD:USD'
        base_quote_part = symbol.split(":")[0]  # noqa: PLC0207

        if "/" not in base_quote_part:
            error_message = f"Invalid CCXT symbol format: {symbol}. Expected format: BASE/QUOTE:SETTLE"
            raise ValueError(error_message)

        base, quote = base_quote_part.split("/")

        if quote == "USDT":
            quote = "USD"

        # Handle special case: BTC -> XBT conversion for Kraken
        if base == "BTC":
            base = "XBT"

        # Construct Kraken native symbol with PF_ prefix for perpetual futures
        return f"PF_{base}{quote}"

    def quote_from_stable_coin_to_fiat_if_needed(self, symbol: str) -> str:  # noqa: PLR6301
        """Конвертирует из пары с фиатной валютой в пару с крипто-.

        Examples:
        'XRP/USDT:USDT' -> 'XRP/USD:USD'

        Raises:
        ------
        ValueError
            If invalid CCXT symbol format.

        """
        if ":" not in symbol:
            error_message = f"Invalid CCXT swap symbol format: {symbol}. Expected format: BASE/QUOTE:SETTLE"
            raise ValueError(error_message)

        # Split the symbol to get base/quote part
        base_quote_part, settle = symbol.split(":")  # 'XRP/USD' from 'XRP/USD:USD'

        if "/" not in base_quote_part:
            error_message = f"Invalid CCXT symbol format: {symbol}. Expected format: BASE/QUOTE:SETTLE"
            raise ValueError(error_message)

        base, quote = base_quote_part.split("/")

        if quote == "USDT":
            quote = "USD"

        if settle == "USDT":
            settle = "USD"

        return f"{base}/{quote}:{settle}"

    def quote_from_fiat_to_stable_coin_if_needed(self, symbol: str) -> str:  # noqa: PLR6301
        """Конвертирует из пары с квотрованной криптовалютой в пару с фиатной.

        Examples:
        'XRP/USDT:USDT' -> 'XRP/USD:USD'

        Raises:
        ------
        ValueError
            If invalid CCXT symbol format.

        """
        if ":" not in symbol:
            error_message = f"Invalid CCXT swap symbol format: {symbol}. Expected format: BASE/QUOTE:SETTLE"
            raise ValueError(error_message)

        # Split the symbol to get base/quote part
        base_quote_part, settle = symbol.split(":")  # 'XRP/USD' from 'XRP/USD:USD'

        if "/" not in base_quote_part:
            error_message = f"Invalid CCXT symbol format: {symbol}. Expected format: BASE/QUOTE:SETTLE"
            raise ValueError(error_message)

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
    async def set_margin_mode(self, *, margin_mode: str, symbol: str | None = None, params: dict[str, Any] | None = None) -> None:
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
                exception_message = "params should contain 'leverage'"
                raise ValueError(exception_message)
            params_dict["maxLeverage"] = params["leverage"]
        else:
            error_message = "mode must be 'cross' or 'isolated'"
            raise ValueError(error_message)

        headers = await self._create_request_headers(params_dict)

        resp = await self._exchange.request("leveragepreferences", "public", method="PUT", params=params_dict, headers=headers)
        if resp["result"] != "success":
            raise UnknownExchangeError

    async def _create_request_headers(self, params_dict: dict[str, Any]) -> dict[str, str]:
        nonce = str(int(time.time() * 1000))
        return {
            "APIKey": self._exchange.apiKey,
            "Nonce": nonce,
            "Authent": self._create_futures_signature("/api/v3/leveragepreferences", nonce, urlencode(params_dict)),
            "Content-Type": "application/json",
        }

    def _create_futures_signature(self, endpoint: str, nonce: str, postdata: str) -> str:
        message = postdata + nonce + endpoint
        sha256_hash = hashlib.sha256(message.encode("utf-8")).digest()
        signature = hmac.new(base64.b64decode(self._exchange.secret), sha256_hash, hashlib.sha512).digest()
        return base64.b64encode(signature).decode("utf-8")
