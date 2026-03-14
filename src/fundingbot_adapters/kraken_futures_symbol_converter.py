class KrakenFuturesSymbolConverter:
    """клиент Kraken Futures на базе ccxt для USDT‑свопов."""

    @staticmethod
    def from_ccxt_to_kraken(symbol: str) -> str:  # noqa: PLR6301
        """Convert CCXT symbol format to Kraken symbol format.

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

    @staticmethod
    def quote_from_usdt_to_usd(symbol: str) -> str:  # noqa: PLR6301
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

    @staticmethod
    def quote_from_usd_to_usdt(symbol: str) -> str:  # noqa: PLR6301
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
