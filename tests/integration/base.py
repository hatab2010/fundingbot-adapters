from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import re
import pytest

from fundingbot_sdk.contracts.ports.cex_client import CexClientPort
from fundingbot_sdk.contracts.protocols import PositionProtocol
from fundingbot_sdk.toolkit.client_base import CcxtClient


class CcxtClientContract:
    """Тестовый контракт для проверки работы CcxtClient."""

    @pytest.fixture
    def symbol(self) -> str:
        """Символ для тестирования."""
        return "XRP/USDT:USDT"

    @pytest.fixture
    def amount(self) -> Decimal:
        """Количество контрактов для тестирования."""
        return Decimal(5)

    @pytest.fixture
    def client(self) -> CexClientPort:
        """Должен быть реализован в наследнике для конкретной биржи."""
        raise NotImplementedError

    @pytest.mark.asyncio
    async def test_close_positions(self, client: CcxtClient, symbol: str):
        positions = await client.get_positions([symbol])
        if len(positions) == 0:
            return

        for position in positions:
            await client.create_order(
                symbol=symbol,
                side="sell" if position.side == "long" else "buy",
                order_type="market",
                amount=position.contracts,
                params={"reduceOnly": True, "offset": "close"},
            )

    @pytest.mark.asyncio
    async def test_get_balance(self, client: CcxtClient):
        """Тестирование получения баланса."""
        balance = await client.get_balance("USDT")
        assert balance.free > 0

    @pytest.mark.asyncio
    async def test_get_trigger_orders(self, client: CcxtClient, symbol: str) -> None:
        tpsl_orders = await client.get_trigger_orders(symbol=symbol)
        assert len(tpsl_orders) == 0

    @pytest.mark.asyncio
    async def test_get_positions(self, client: CcxtClient, symbol: str):
        positions = await client.get_positions([symbol])
        assert len(positions) == 0

    @pytest.mark.asyncio
    async def test_tpsl_lifecycle_asserts(self, client: CcxtClient, symbol: str, amount: Decimal) -> None:
        """Проверяет TPSL-цикл: плечо, TP/SL-ордера, маржу и режим позиции.

        Шаги:
        1) Установить one-way режим (hedged=False), isolated маржу и плечо.
        2) Открыть позицию с TP/SL через create_tpsl_position.
        3) Проверить: в позиции нужное плечо и hedged=False; открыты 2 триггер-ордера (TP+SL).
        4) Закрыть позицию и убедиться, что позиции нет и ордера исчезли.
        """
        await client.load_markets()
        expected_leverage = 3

        # 1) Инициализация режимов и плеча
        await client.set_position_mode(hedged=False, symbol=symbol)
        await client.set_margin_mode(margin_mode="isolated", symbol=symbol)
        await client.set_leverage(leverage=expected_leverage, symbol=symbol)

        # Подготовка размеров
        instrument = await client.get_instrument_info(symbol)
        contracts = amount / instrument.contract_size

        ticker = await client.get_ticker(symbol)
        take_profit = ticker.last_price * Decimal("1.2")
        stop_loss = ticker.last_price * Decimal("0.9")

        # 2) Открываем позицию с TP/SL
        await client.create_tpsl_position(
            symbol=symbol,
            order_type="market",
            side="buy",
            amount=contracts,
            take_profit=take_profit,
            stop_loss=stop_loss,
        )

        # 3) Проверки позиции
        positions = await client.get_positions([symbol])
        assert len(positions) == 1
        position = positions[0]

        # Проверка плеча и режима позиции (one-way)
        assert int(position.leverage) == expected_leverage
        assert position.hedged is False
        assert position.margin_mode == "isolated"

        # TP/SL как план-ордера: ожидаем два ордера (profit_plan + loss_plan)
        tpsl_orders = await client.get_trigger_orders(symbol=symbol)
        expected_tpsl_orders = 2  # Ожидается 2 ордера (TP и SL)
        assert len(tpsl_orders) == expected_tpsl_orders

        # 4) Закрываем позицию рыночным reduceOnly и проверяем, что ордера исчезли
        await client.create_order(
            symbol=symbol,
            order_type="market",
            side="sell",
            amount=position.contracts,
            params={"reduceOnly": True, "offset": "close"},
        )

        positions_after = await client.get_positions([symbol])
        assert len(positions_after) == 0

        tpsl_orders_after = await client.get_trigger_orders(symbol=symbol)
        assert len(tpsl_orders_after) == 0

    @pytest.mark.asyncio
    async def test_get_funding_usdt_rates(self, client: CcxtClient):
        data = await client.get_funding_usdt_rates()
        assert len(data) > 0
        pattern = re.compile(r"^(?P<base>[A-Z0-9]{1,32})\/USDT:USDT$")
        for item in data:
            assert pattern.match(item.symbol), (
                f"symbol не соответствует ^(?P<base>[A-Z0-9]{2,32})\\/USDT:USDT$: {item.symbol}"
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
    async def test_get_ticker(self, client: CcxtClient):
        await client.load_markets()
        data = await client.get_ticker("BTC/USDT:USDT")
        assert data.last_price != 0

    @pytest.mark.asyncio
    async def test_get_instrument_info(self, client: CcxtClient, symbol: str):
        data = await client.get_instrument_info(symbol=symbol)
        assert data.amount_precision != 0
        assert data.price_precision != 0
        assert data.contract_size != 0

        assert data.symbol == symbol

    @pytest.mark.asyncio
    async def test_full_cycle(self, client: CcxtClient, symbol: str, amount: Decimal) -> None:
        """Проверяет цикл buy/sell с разными плечами и закрытием позиции.

        Шаги:
        1) Установить one-way режим (hedged=False) и isolated маржу.
        2) Для buy и sell установить разные плечи и открыть позицию market.
        3) Проверить свойства позиции: плечо, режимы, наличие контрактов и метаданные.
        4) Закрыть позицию рыночным reduceOnly и убедиться в отсутствии позиции.
        """
        await client.load_markets()

        instrument_info = await client.get_instrument_info(symbol)
        amount /= instrument_info.contract_size

        await client.set_position_mode(hedged=False, symbol=symbol)
        await client.set_margin_mode(margin_mode="isolated", symbol=symbol)

        leverage_by_side = {"buy": 2, "sell": 4}

        for side in ["buy", "sell"]:
            expected_leverage = leverage_by_side[side]
            await client.set_leverage(leverage=expected_leverage, symbol=symbol)

            positions_before = await client.get_positions([symbol])
            assert len(positions_before) == 0

            await client.create_order(symbol=symbol, side=side, order_type="market", amount=amount)

            data_with_position: Sequence[PositionProtocol] = await client.get_positions([symbol])
            assert len(data_with_position) == 1
            position = data_with_position[0]

            # Проверки параметров позиции
            assert int(position.leverage) == expected_leverage
            assert position.hedged is False
            assert position.margin_mode == "isolated"
            assert position.contracts > 0
            assert position.entry_price > 0
            assert position.notional > 0
            assert position.symbol == symbol

            # Закрытие позиции
            await client.create_order(
                symbol=symbol,
                side="sell" if side == "buy" else "buy",
                order_type="market",
                amount=position.contracts,
                params={"reduceOnly": True, "offset": "close"},
            )

            data_without_position = await client.get_positions([symbol])
            assert len(data_without_position) == 0


    @pytest.mark.asyncio
    async def test_double_init_params(self, client: CcxtClient, symbol: str):
        await client.set_position_mode(hedged=False, symbol=symbol)
        await client.set_position_mode(hedged=False, symbol=symbol)
        await client.set_leverage(leverage=1, symbol=symbol)
        await client.set_leverage(leverage=1, symbol=symbol)
        await client.set_margin_mode(margin_mode="isolated", symbol=symbol, params={"leverage": 1})
        await client.set_margin_mode(margin_mode="isolated", symbol=symbol, params={"leverage": 1})

    @pytest.mark.asyncio
    async def test_set_leverage(self, client: CcxtClient, symbol: str):
        await client.set_leverage(leverage=1, symbol=symbol)

    @pytest.mark.asyncio
    async def test_set_position_mode(self, client: CcxtClient):
        await client.set_position_mode(hedged=False, symbol=None)

    @pytest.mark.asyncio
    async def test_set_margin_mode(self, client: CcxtClient, symbol: str):
        await client.set_margin_mode(margin_mode="isolated", symbol=symbol, params={"leverage": 1})
