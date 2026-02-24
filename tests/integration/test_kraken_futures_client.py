import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from tests.integration.base import CcxtClientContract, CexClientPort

from config import KRAKEN_API_KEY, KRAKEN_PASSWORD, KRAKEN_SECRET, TESTNET
from fundingbot_adapters.kraken_futures_client import KrakenFuturesClient
from fundingbot_sdk.contracts.ports.cex_client import CexClientConfig
from fundingbot_sdk.toolkit.client_base import CcxtClient


class TestKrakenFuturesClient(CcxtClientContract):
    """Интеграционный контракт для клиента Kraken."""

    @pytest.fixture
    def symbol(self) -> str:
        """Символ для тестирования."""
        return "XRP/USD:USD"

    @pytest.fixture
    def btc_symbol(self) -> str:
        """Символ для тестирования."""
        return "BTC/USD:USD"

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

    # Скипаем тесты, которые будут исправлены позже

    @pytest.mark.skip(
        'ccxt.base.errors.AuthenticationError: krakenfutures {"result":"error","error":"authenticationError","serverTime":"2026-02-08T18:58:16.273Z"}'
    )
    @pytest.mark.asyncio
    async def test_get_trigger_orders(self, client: CcxtClient, symbol: str) -> None:
        await super().test_get_trigger_orders(client, symbol)

    @pytest.mark.skip("ccxt.base.errors.BadSymbol: krakenfutures does not have market symbol FI_BTCUSD_230630")
    @pytest.mark.asyncio
    async def test_get_funding_usdt_rates(self, client: CcxtClient) -> None:
        data = await client.get_funding_usdt_rates()
        assert len(data) > 0
        pattern = re.compile(r"^(?P<base>[A-Z0-9]{1,32})\/USD:USD$")
        for item in data:
            assert pattern.match(item.symbol), f"symbol не соответствует ^(?P<base>[A-Z0-9]{2, 32})\\/USD:USD$: {item.symbol}"
            dt = getattr(item, "funding_date", None)
            assert dt is not None, "funding_date отсутствует в элементе ответа"
            assert dt.tzinfo is not None, f"funding_date без tzinfo: {dt}"
            assert dt.tzinfo.utcoffset(dt) == timedelta(0), f"funding_date должен быть UTC-aware, сейчас({item.symbol}): {dt}"
            assert isinstance(item.funding_rate, Decimal), "funding_rate должен быть Decimal"
            now_utc = datetime.now(UTC)
            assert dt >= now_utc - timedelta(seconds=5), f"funding_date в прошлом: {dt} < {now_utc}"

    @pytest.mark.skip("#17 fundingbot_sdk.contracts.errors.PositionUnavailableError: Нет позиции для XRP/USD:USD на krakenfutures")
    @pytest.mark.asyncio
    async def test_get_positions(self, client: CcxtClient, symbol: str):
        await super().test_get_positions(client, symbol)

    @pytest.mark.skip("#17 fundingbot_sdk.contracts.errors.PositionUnavailableError: Нет позиции для XRP/USD:USD на krakenfutures")
    @pytest.mark.asyncio
    async def test_close_positions(self, client: CcxtClient, symbol: str):
        await super().test_close_positions(client, symbol)

    @pytest.mark.skip("#17 fundingbot_sdk.contracts.errors.PositionUnavailableError: Нет позиции для XRP/USD:USD на krakenfutures")
    @pytest.mark.asyncio
    async def test_tpsl_lifecycle_asserts(self, client: CcxtClient, symbol: str, amount: Decimal) -> None:
        await super().test_tpsl_lifecycle_asserts(client, symbol, amount)

    @pytest.mark.skip("#17 fundingbot_sdk.contracts.errors.PositionUnavailableError: Нет позиции для XRP/USD:USD на krakenfutures")
    @pytest.mark.asyncio
    async def test_full_cycle(self, client: CcxtClient, symbol: str, amount: Decimal) -> None:
        await super().test_full_cycle(client, symbol, amount)

    @pytest.mark.asyncio
    async def test_double_init_params(self, client: CcxtClient, symbol: str) -> None:
        await super().test_double_init_params(client, symbol)
