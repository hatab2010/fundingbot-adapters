from collections.abc import AsyncIterator

import pytest
from tests.integration.base import CcxtClientContract

from config import BITGET_API_KEY, BITGET_PASSWORD, BITGET_SECRET, TESTNET
from fundingbot_adapters.bitget_client import BitgetClient
from fundingbot_sdk.contracts.ports.cex_client import CexClientConfig


class TestBitgetClient(CcxtClientContract):
    """Интеграционный контракт для клиента Bitget."""

    @pytest.fixture
    async def client(self) -> AsyncIterator[BitgetClient]:
        """Выдавать Bitget‑клиент и закрывать соединение после теста.

        Yields:
            Клиент для интеграционных тестов Bitget.

        """
        config = CexClientConfig(
            api_key=BITGET_API_KEY,
            api_secret=BITGET_SECRET,
            password=BITGET_PASSWORD,
            testnet=TESTNET,
            default_type="swap",
        )
        client = BitgetClient(config, verbose=True)
        try:
            yield client
        finally:
            await client.close()
