#!/usr/bin/env python3
"""Test script for KrakenFuturesNormalizationUtils ccxt_to_native method"""

import os
import sys

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from fundingbot_adapters.kraken_futures_client import KrakenFuturesSymbolConverter


def test_ccxt_to_native():
    """Test the ccxt_to_native conversion method"""
    converter = KrakenFuturesSymbolConverter()

    # Test cases based on the documentation and example
    test_cases = [
        # (input_ccxt_symbol, expected_kraken_symbol)
        ("XRP/USD:USD", "PF_XRPUSD"),
        ("BTC/USD:USD", "PF_XBTUSD"),  # BTC -> XBT conversion
        ("ETH/USD:USD", "PF_ETHUSD"),
        ("SOL/USD:USD", "PF_SOLUSD"),
    ]

    print("Testing ccxt_to_native conversion:")
    print("=" * 50)

    all_passed = True

    for ccxt_symbol, expected_kraken in test_cases:
        try:
            result = converter.from_standard_to_native(ccxt_symbol)
            if result == expected_kraken:
                print(f"✅ {ccxt_symbol} -> {result}")
            else:
                print(f"❌ {ccxt_symbol} -> {result} (expected: {expected_kraken})")
                all_passed = False
        except Exception as e:
            print(f"❌ {ccxt_symbol} -> ERROR: {e}")
            all_passed = False

    # Test error cases
    print("\nTesting error cases:")
    print("=" * 30)

    error_cases = [
        "XRP/USD",  # Missing :USD part
        "XRPUSD",  # Missing / separator
        "XRP:USD",  # Missing / separator in base/quote part
        "",  # Empty string
    ]

    for invalid_symbol in error_cases:
        try:
            result = converter.from_standard_to_native(invalid_symbol)
            print(f"❌ {invalid_symbol} -> {result} (should have raised error)")
            all_passed = False
        except ValueError as e:
            print(f"✅ {invalid_symbol} -> ValueError: {e}")
        except Exception as e:
            print(f"❌ {invalid_symbol} -> Unexpected error: {e}")
            all_passed = False

    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed!")
        return True
    print("💥 Some tests failed!")
    return False


if __name__ == "__main__":
    success = test_ccxt_to_native()
    sys.exit(0 if success else 1)
