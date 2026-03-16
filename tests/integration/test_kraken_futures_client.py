from collections.abc import AsyncIterator

import pytest

from config import KRAKEN_API_KEY, KRAKEN_PASSWORD, KRAKEN_SECRET, TESTNET
from fundingbot_adapters.kraken_futures_client import KrakenFuturesClient
from fundingbot_sdk.contracts.ports.cex_client import CexClientConfig
from tests.integration.base import CcxtClientContract, CexClientPort


class TestKrakenFuturesClient(CcxtClientContract):
    """Интеграционный контракт для клиента Kraken."""

    @pytest.fixture
    async def client(self) -> AsyncIterator[CexClientPort]:
        """Выдавать Kraken‑клиент и закрывать соединение после теста.

        Yields:
            Клиент для интеграционных тестов Kraken.

        """
        config = CexClientConfig(
            api_key=KRAKEN_API_KEY, api_secret=KRAKEN_SECRET, password=KRAKEN_PASSWORD, testnet=TESTNET, default_type="swap"
        )
        client = KrakenFuturesClient(config, verbose=True)
        try:
            yield client
        finally:
            await client.close()
