from collections.abc import AsyncIterator
from datetime import timedelta, datetime, UTC
from decimal import Decimal

import pytest
import re

from fundingbot_sdk.toolkit.client_base import CcxtClient
from tests.integration.base import CcxtClientContract, CexClientPort

from config import KRAKEN_API_KEY, KRAKEN_PASSWORD, KRAKEN_SECRET, TESTNET
from fundingbot_adapters.futures_kraken_client import FuturesKrakenClient
from fundingbot_sdk.contracts.ports.cex_client import CexClientConfig


class TestFututresKrakenClient(CcxtClientContract):
    """Интеграционный контракт для клиента Kraken."""

    @pytest.fixture
    async def client(self) -> AsyncIterator[CexClientPort]:
        """Выдавать Kraken‑клиент и закрывать соединение после теста.

        Yields:
            Клиент для интеграционных тестов Kraken.

        """
        config = CexClientConfig(
            api_key=KRAKEN_API_KEY,
            api_secret=KRAKEN_SECRET,
            password=KRAKEN_PASSWORD,
            testnet=TESTNET,
            default_type="swap",
        )
        client = FuturesKrakenClient(config, verbose=True)
        try:
            yield client
        finally:
            await client.close()

    # Скипаем тесты, которые будут исправлены позже

    @pytest.mark.asyncio
    async def test_get_balance(self, client: CcxtClient):
        """Тестирование получения баланса."""
        balance = await client.get_balance("USD")
        assert balance.free > 0

    #    @pytest.mark.skip
    @pytest.mark.asyncio
    async def test_get_ticker(self, client: CcxtClient) -> None:
        await client.load_markets()
        data = await client.get_ticker("BTC/USD:USD")
        assert data.last_price != 0

    @pytest.mark.asyncio
    async def test_close_positions(self, client: CcxtClient, symbol: str) -> None:
        await super().test_close_positions(client, 'XRP/USD:USD')

    @pytest.mark.skip
    @pytest.mark.asyncio
    async def test_get_trigger_orders(self, client: CcxtClient, symbol: str) -> None:
        await super().test_get_trigger_orders(client, 'XRP/USD:USD')

    @pytest.mark.skip
    @pytest.mark.asyncio
    async def test_tpsl_lifecycle_asserts(self, client: CcxtClient, symbol: str, amount: Decimal) -> None:
        await super().test_tpsl_lifecycle_asserts(client, symbol, amount)

    @pytest.mark.skip
    @pytest.mark.asyncio
    async def test_get_funding_usdt_rates(self, client: CcxtClient) -> None:
        data = await client.get_funding_usdt_rates()
        assert len(data) > 0
        pattern = re.compile(r"^(?P<base>[A-Z0-9]{1,32})\/USD:USD$")
        for item in data:
            assert pattern.match(item.symbol), (
                f"symbol не соответствует ^(?P<base>[A-Z0-9]{2, 32})\\/USD:USD$: {item.symbol}"
            )
            dt = getattr(item, "funding_date", None)
            assert dt is not None, "funding_date отсутствует в элементе ответа"
            assert dt.tzinfo is not None, f"funding_date без tzinfo: {dt}"
            assert dt.tzinfo.utcoffset(dt) == timedelta(0), (
                f"funding_date должен быть UTC-aware, сейчас({item.symbol}): {dt}"
            )
            assert isinstance(item.funding_rate, Decimal), "funding_rate должен быть Decimal"
            now_utc = datetime.now(UTC)
            assert dt >= now_utc - timedelta(seconds=5), f"funding_date в прошлом: {dt} < {now_utc}"

    @pytest.mark.asyncio
    async def test_get_instrument_info(self, client: CcxtClient, symbol: str) -> None:
        await super().test_get_instrument_info(client, 'XRP/USD:USD')

    @pytest.mark.skip
    @pytest.mark.asyncio
    async def test_full_cycle(self, client: CcxtClient, symbol: str) -> None:
        await super().test_get_instrument_info(client, symbol)

    @pytest.mark.skip
    @pytest.mark.asyncio
    async def test_double_init_params(self, client: CcxtClient, symbol: str) -> None:
        await super().test_double_init_params(client, symbol)

    @pytest.mark.skip
    @pytest.mark.asyncio
    async def test_set_leverage(self, client: CcxtClient, symbol: str) -> None:
        await super().test_set_leverage(client, symbol)

    @pytest.mark.skip
    @pytest.mark.asyncio
    async def test_set_position_mode(self, client: CcxtClient) -> None:
        await super().test_set_position_mode(client)

    @pytest.mark.skip
    @pytest.mark.asyncio
    async def test_set_margin_mode(self, client: CcxtClient, symbol: str) -> None:
        await super().test_get_instrument_info(client, symbol)
