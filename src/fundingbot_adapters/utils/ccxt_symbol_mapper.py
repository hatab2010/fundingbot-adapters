class CcxtSymbolMapper:
    @staticmethod
    def quote_from_usdt_to_usd(symbol: str) -> str:
        """Для символа с фиатной котируемой валютой возвращает валютой возвращает символ с соответствующей с криптовалютой в качестве котируемой.

        Examples:
        'XRP/USDT:USD' -> 'XRP/USD:USDT'

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
    def quote_from_usd_to_usdt(symbol: str) -> str:
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
