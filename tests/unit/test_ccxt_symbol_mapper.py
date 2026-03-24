"""Unit tests for CcxtSymbolMapper class."""

import pytest

from fundingbot_adapters.utils.ccxt_symbol_mapper import CcxtSymbolMapper


class TestCcxtSymbolMapper:
    """Test cases for CcxtSymbolMapper class."""

    def test_quote_from_stable_to_fiat_usdt_to_usd(self):
        """Test conversion from USDT to USD in quote currency."""
        # Test basic USDT -> USD conversion
        result = CcxtSymbolMapper.quote_from_stable_to_fiat("XRP/USDT:USDT")
        assert result == "XRP/USD:USD"

    def test_quote_from_stable_to_fiat_only_quote_usdt(self):
        """Test conversion when only quote currency is USDT."""
        result = CcxtSymbolMapper.quote_from_stable_to_fiat("BTC/USDT:BTC")
        assert result == "BTC/USD:BTC"

    def test_quote_from_stable_to_fiat_no_usdt(self):
        """Test that symbols without USDT remain unchanged."""
        result = CcxtSymbolMapper.quote_from_stable_to_fiat("BTC/ETH:ETH")
        assert result == "BTC/ETH:ETH"

    def test_quote_from_stable_to_fiat_invalid_format_no_colon(self):
        """Test ValueError when symbol has no colon."""
        with pytest.raises(ValueError, match="Invalid CCXT swap symbol format"):
            CcxtSymbolMapper.quote_from_stable_to_fiat("BTC/USDT")

    def test_quote_from_stable_to_fiat_invalid_format_no_slash(self):
        """Test ValueError when symbol has no slash in base/quote part."""
        with pytest.raises(ValueError, match="Invalid CCXT symbol format"):
            CcxtSymbolMapper.quote_from_stable_to_fiat("BTCUSDT:USDT")

    def test_quote_from_stable_to_fiat_empty_string(self):
        """Test ValueError with empty string."""
        with pytest.raises(ValueError, match="Invalid CCXT swap symbol format"):
            CcxtSymbolMapper.quote_from_stable_to_fiat("")

    def test_quote_from_stable_to_fiat_multiple_colons(self):
        """Test that multiple colons cause ValueError due to unpacking error."""
        with pytest.raises(ValueError, match="too many values to unpack"):
            CcxtSymbolMapper.quote_from_stable_to_fiat("BTC/USDT:USDT:EXTRA")

    def test_quote_from_stable_to_fiat_multiple_slashes(self):
        """Test that multiple slashes cause ValueError due to unpacking error."""
        with pytest.raises(ValueError, match="too many values to unpack"):
            CcxtSymbolMapper.quote_from_stable_to_fiat("BTC/USD/EXTRA:USDT")

    def test_quote_from_fiat_to_stable_usd_to_usdt(self):
        """Test conversion from USD to USDT in quote currency."""
        result = CcxtSymbolMapper.quote_from_fiat_to_stable("XRP/USD:USD")
        assert result == "XRP/USDT:USDT"

    def test_quote_from_fiat_to_stable_only_quote_usd(self):
        """Test conversion when only quote currency is USD."""
        result = CcxtSymbolMapper.quote_from_fiat_to_stable("BTC/USD:BTC")
        assert result == "BTC/USDT:BTC"

    def test_quote_from_fiat_to_stable_no_usd(self):
        """Test that symbols without USD remain unchanged."""
        result = CcxtSymbolMapper.quote_from_fiat_to_stable("BTC/ETH:ETH")
        assert result == "BTC/ETH:ETH"

    def test_quote_from_fiat_to_stable_invalid_format_no_colon(self):
        """Test ValueError when symbol has no colon."""
        with pytest.raises(ValueError, match="Invalid CCXT swap symbol format"):
            CcxtSymbolMapper.quote_from_fiat_to_stable("BTC/USD")

    def test_quote_from_fiat_to_stable_invalid_format_no_slash(self):
        """Test ValueError when symbol has no slash in base/quote part."""
        with pytest.raises(ValueError, match="Invalid CCXT symbol format"):
            CcxtSymbolMapper.quote_from_fiat_to_stable("BTCUSD:USD")

    def test_quote_from_fiat_to_stable_empty_string(self):
        """Test ValueError with empty string."""
        with pytest.raises(ValueError, match="Invalid CCXT swap symbol format"):
            CcxtSymbolMapper.quote_from_fiat_to_stable("")

    def test_quote_from_fiat_to_stable_multiple_colons(self):
        """Test that multiple colons cause ValueError due to unpacking error."""
        with pytest.raises(ValueError, match="too many values to unpack"):
            CcxtSymbolMapper.quote_from_fiat_to_stable("BTC/USD:USD:EXTRA")

    def test_quote_from_fiat_to_stable_multiple_slashes(self):
        """Test that multiple slashes cause ValueError due to unpacking error."""
        with pytest.raises(ValueError, match="too many values to unpack"):
            CcxtSymbolMapper.quote_from_fiat_to_stable("BTC/USD/EXTRA:USD")

    def test_roundtrip_conversion(self):
        """Test that converting stable->fiat->stable returns original."""
        original = "XRP/USDT:USDT"
        fiat_version = CcxtSymbolMapper.quote_from_stable_to_fiat(original)
        back_to_stable = CcxtSymbolMapper.quote_from_fiat_to_stable(fiat_version)
        assert back_to_stable == original

    def test_roundtrip_conversion_reverse(self):
        """Test that converting fiat->stable->fiat returns original."""
        original = "XRP/USD:USD"
        stable_version = CcxtSymbolMapper.quote_from_fiat_to_stable(original)
        back_to_fiat = CcxtSymbolMapper.quote_from_stable_to_fiat(stable_version)
        assert back_to_fiat == original

    def test_numeric_base_currency(self):
        """Test handling of numeric characters in base currency."""
        result = CcxtSymbolMapper.quote_from_stable_to_fiat("1INCH/USDT:USDT")
        assert result == "1INCH/USD:USD"
