import base64
import hashlib
import hmac
import time
from typing import Any
from urllib.parse import urlencode

from fundingbot_sdk.contracts.errors import UnknownExchangeError, UnsupportedFeatureError
from fundingbot_sdk.contracts.ports.cex_client import CexClientConfig
from fundingbot_sdk.toolkit.client_base import CcxtClient

BASE_PATH = "/derivatives/api/v3"


class KrakenFuturesNormalizationUtils:
    def ccxt_to_pf(self, ccxt_symbol: str) -> str:
        """Convert CCXT symbol format to Kraken native symbol format.

        Examples:
        'XRP/USD:USD' -> 'PF_XRPUSD'
        'BTC/USD:USD' -> 'PF_XBTUSD'
        'ETH/USD:USD' -> 'PF_ETHUSD'

        """
        if ":" not in ccxt_symbol:
            raise ValueError(f"Invalid CCXT swap symbol format: {ccxt_symbol}. Expected format: BASE/QUOTE:SETTLE")

        # Split the symbol to get base/quote part
        base_quote_part = ccxt_symbol.split(":")[0]  # 'XRP/USD' from 'XRP/USD:USD'

        if "/" not in base_quote_part:
            raise ValueError(f"Invalid CCXT symbol format: {ccxt_symbol}. Expected format: BASE/QUOTE:SETTLE")

        base, quote = base_quote_part.split("/")

        # Handle special case: BTC -> XBT conversion for Kraken
        if base == "BTC":
            base = "XBT"

        # Construct Kraken native symbol with PF_ prefix for perpetual futures
        native_symbol = f"PF_{base}{quote}"
        return native_symbol


NORMALIZATION_UTILS = KrakenFuturesNormalizationUtils()


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

    async def set_position_mode(self, *, hedged: bool, symbol: str | None = None,
                                params: dict[str, Any] | None = None) -> None:
        raise UnsupportedFeatureError(self.EXCHANGE_ID, "setPositionMode", params={})

    async def set_margin_mode(self, *, margin_mode: str, symbol: str | None = None, params: dict[str, Any] | None = None):
        # Согласно docs: можно задать symbol, marginMode и/или maxLeverage.[web:1]
        params_dict = {"symbol": NORMALIZATION_UTILS.ccxt_to_pf(symbol)}
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

        headers = await self.create_request_headers(params_dict)

        resp = await self._exchange.request(
            "leveragepreferences",
            "public",
            method="PUT",
            params=params_dict,
            headers=headers,
        )
        if resp["result"] != "success":
            raise UnknownExchangeError()

    async def create_request_headers(self, params_dict: dict[str, Any]) -> dict[str, str]:
        nonce = str(int(time.time() * 1000))
        headers = {
            "APIKey": self._exchange.apiKey,
            "Nonce": nonce,
            "Authent": self.create_futures_signature("/api/v3/leveragepreferences", nonce, urlencode(params_dict)),
            "Content-Type": "application/json",
        }
        return headers

    def create_futures_signature(self, endpoint: str, nonce: str, postdata: str) -> str:
        message = postdata + nonce + endpoint
        sha256_hash = hashlib.sha256(message.encode("utf-8")).digest()
        signature = hmac.new(
            base64.b64decode(self._exchange.secret),
            sha256_hash,
            hashlib.sha512
        ).digest()
        return base64.b64encode(signature).decode("utf-8")
