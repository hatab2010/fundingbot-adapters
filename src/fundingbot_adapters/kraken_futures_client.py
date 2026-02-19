from typing import Any

from fundingbot_sdk.contracts.errors import UnsupportedFeatureError
from fundingbot_sdk.contracts.ports.cex_client import CexClientConfig
from fundingbot_sdk.toolkit.client_base import CcxtClient

class KrakenFuturesClient(CcxtClient):
    """клиент Kraken на базе ccxt для USD‑свопов."""

    EXCHANGE_ID = "krakenfutures"

    def __init__(self, config: CexClientConfig, *, verbose: bool = False) -> None:
        self._leverage = None
        super().__init__(exchange_name=KrakenFuturesClient.EXCHANGE_ID, config=config, verbose=verbose)
        
        # Kraken Futures API configuration
        self.futures_base_url = 'https://futures.kraken.com/derivatives/api/v3'
        if config.testnet:
            self.futures_base_url = 'https://demo-futures.kraken.com/derivatives/api/v3'

    async def set_position_mode(self, *, hedged: bool, symbol: str | None = None,
                                params: dict[str, Any] | None = None) -> None:
        raise UnsupportedFeatureError(self.EXCHANGE_ID, "setPositionMode", params={})
