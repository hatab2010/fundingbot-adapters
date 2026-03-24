class CcxtSymbolMapper:
    """Утилитарный класс для преобразования символов торговых пар между различными форматами.

    Этот класс предоставляет статические методы для конвертации символов криптовалютных
    торговых пар между стейблкоинами (USDT) и фиатными валютами (USD). Основное назначение -
    обеспечить сопоставление символов разных бирж, у которых разные котируемые валюты:
    стейблкоин USDT и фиатная валюта USD.

    Символы имеют формат CCXT: "BASE/QUOTE:SETTLE", где:
    - BASE: базовая валюта (например, BTC, ETH, XRP)
    - QUOTE: котируемая валюта (например, USD, USDT)
    - SETTLE: валюта расчета, совпадающая с одной из двух предыдущих: либо с базовой, либо с котируемой

    Основная функциональность:
    - Конвертация USDT ↔ USD в котируемой валюте и валюте расчета
    - Валидация формата символов
    - Поддержка двунаправленных преобразований

    Examples:
        Конвертация из стейблкоина в фиат:

        >>> CcxtSymbolMapper.quote_from_stable_to_fiat("XRP/USDT:USDT")
        'XRP/USD:USD'
        >>> CcxtSymbolMapper.quote_from_stable_to_fiat("BTC/USDT:BTC")
        'BTC/USD:BTC'

        Конвертация из фиата в стейблкоин:

        >>> CcxtSymbolMapper.quote_from_fiat_to_stable("XRP/USD:USD")
        'XRP/USDT:USDT'
        >>> CcxtSymbolMapper.quote_from_fiat_to_stable("BTC/USD:BTC")
        'BTC/USDT:BTC'

        Символы без USD/USDT остаются неизменными:

        >>> CcxtSymbolMapper.quote_from_stable_to_fiat("BTC/ETH:ETH")
        'BTC/ETH:ETH'

        Двунаправленная конвертация:

        >>> original = "XRP/USDT:USDT"
        >>> fiat = CcxtSymbolMapper.quote_from_stable_to_fiat(original)
        >>> back = CcxtSymbolMapper.quote_from_fiat_to_stable(fiat)
        >>> back == original
        True

    Note:
        Все методы класса являются статическими и не требуют создания экземпляра класса.
        Класс работает только с символами в формате CCXT и выбрасывает ValueError
        при некорректном формате входных данных.

    """

    @staticmethod
    def quote_from_stable_to_fiat(symbol: str) -> str:
        """Конвертирует символ торговой пары из стейблкоина (USDT) в фиатную валюту (USD).

        Преобразует USDT в USD как в котируемой валюте, так и в валюте расчета.
        Символы, не содержащие USDT, остаются неизменными.

        Args:
            symbol: Символ торговой пары в формате CCXT "BASE/QUOTE:SETTLE".
                   Например: "XRP/USDT:USDT", "BTC/USDT:BTC".

        Returns:
            Преобразованный символ с USD вместо USDT. Например:
            "XRP/USDT:USDT" -> "XRP/USD:USD"
            "BTC/USDT:BTC" -> "BTC/USD:BTC"
            "BTC/ETH:ETH" -> "BTC/ETH:ETH" (без изменений)

        Raises:
            ValueError: Если символ имеет некорректный формат CCXT:
                - Отсутствует двоеточие (:)
                - Отсутствует слеш (/) в части BASE/QUOTE
                - Слишком много разделителей (множественные : или /)
                - Пустая строка

        Examples:
            >>> CcxtSymbolMapper.quote_from_stable_to_fiat("XRP/USDT:USDT")
            'XRP/USD:USD'
            >>> CcxtSymbolMapper.quote_from_stable_to_fiat("BTC/USDT:BTC")
            'BTC/USD:BTC'
            >>> CcxtSymbolMapper.quote_from_stable_to_fiat("BTC/ETH:ETH")
            'BTC/ETH:ETH'

        """
        base, quote, settle = CcxtSymbolMapper._parse_symbol(symbol)

        if quote == "USDT":
            quote = "USD"

        if settle == "USDT":
            settle = "USD"

        return f"{base}/{quote}:{settle}"

    @staticmethod
    def quote_from_fiat_to_stable(symbol: str) -> str:
        """Конвертирует из пары с фиатной котированной валютой в пару со стейблкоином.

        Examples:
        'XRP/USD:USD' -> 'XRP/USDT:USDT'

        Raises:
        ------
        ValueError
            If invalid CCXT symbol format.

        """
        base, quote, settle = CcxtSymbolMapper._parse_symbol(symbol)

        if quote == "USD":
            quote = "USDT"

        if settle == "USD":
            settle = "USDT"

        return f"{base}/{quote}:{settle}"

    @staticmethod
    def _parse_symbol(symbol: str) -> tuple[str, str, str]:
        """Парсит базовую, котируемую валюты и валюту расчёта из символа в формате BASE/QUOTE:SETTLE.

        Raises
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
        return base, quote, settle
