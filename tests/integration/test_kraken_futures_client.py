from collections.abc import AsyncIterator
from typing import override

import pytest
from tests.integration.base import CcxtClientContract, CexClientPort

from config import KRAKEN_API_KEY, KRAKEN_PASSWORD, KRAKEN_SECRET, TESTNET
from fundingbot_adapters.kraken_futures_client import KrakenFuturesClient
from fundingbot_sdk.contracts.ports.cex_client import CexClientConfig
from fundingbot_sdk.toolkit.client_base import CcxtClient


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

    @pytest.mark.skip("#15 funding_date отсутствует в элементе ответа")
    @override
    async def test_get_funding_usdt_rates(self, client: CcxtClient):
        return await super().test_get_funding_usdt_rates(client)

    @pytest.mark.skip("#15 Value error, Отсутствует значение даты финансирования")
    @override
    async def test_get_funding_rate(self, client: CcxtClient, symbol: str):
        return await super().test_get_funding_rate(client, symbol)


