#!/usr/bin/env python3
"""
Kraken Futures Funding Dates Analysis Script

This script analyzes the historical funding rate data availability across different
trading symbols on Kraken Futures by:
1. Fetching all available tickers
2. For each symbol, retrieving historical funding rates
3. Calculating and displaying the time span of available data
"""

import logging
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('funding_dates.log')
    ]
)
logger = logging.getLogger(__name__)

# API endpoints
TICKERS_URL = "https://futures.kraken.com/derivatives/api/v3/tickers"
FUNDING_RATES_URL = "https://futures.kraken.com/derivatives/api/v3/historical-funding-rates"

# Request configuration
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
BACKOFF_FACTOR = 1.0


class KrakenFundingAnalyzer:
    """Analyzer for Kraken Futures funding rate data availability."""
    
    def __init__(self):
        """Initialize the analyzer with configured HTTP session."""
        self.session = self._create_session()
        self.results: List[Dict] = []
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy."""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=MAX_RETRIES,
            backoff_factor=BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def fetch_tickers(self) -> Optional[List[str]]:
        """
        Fetch all available tickers from Kraken Futures API.
        
        Returns:
            List of symbol names or None if request fails
        """
        try:
            logger.info("Fetching tickers from Kraken Futures API...")
            response = self.session.get(TICKERS_URL, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("result") != "success":
                logger.error(f"API returned error: {data.get('error', 'Unknown error')}")
                return None
            
            tickers = data.get("tickers", [])
            symbols = [ticker.get("symbol") for ticker in tickers if ticker.get("symbol")]
            
            logger.info(f"Successfully fetched {len(symbols)} symbols")
            return symbols
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch tickers: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error while fetching tickers: {e}")
            return None
    
    def fetch_funding_rates(self, symbol: str) -> Optional[List[Dict]]:
        """
        Fetch historical funding rates for a specific symbol.
        
        Args:
            symbol: The trading symbol to fetch data for
            
        Returns:
            List of funding rate records or None if request fails
        """
        try:
            params = {"symbol": symbol}
            response = self.session.get(
                FUNDING_RATES_URL, 
                params=params, 
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("result") != "success":
                logger.warning(f"No funding data for {symbol}: {data.get('error', 'Unknown error')}")
                return None
            
            funding_rates = data.get("rates", [])
            return funding_rates
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to fetch funding rates for {symbol}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error for {symbol}: {e}")
            return None
    
    def calculate_time_span(self, funding_rates: List[Dict]) -> Optional[Tuple[datetime, datetime, timedelta]]:
        """
        Calculate the time span of funding rate data.

        Args:
            funding_rates: List of funding rate records

        Returns:
            Tuple of (second_max_date, max_date, time_span) or None if calculation fails
        """
        if not funding_rates:
            return None
        
        try:
            timestamps = []
            has_timestamp_not_on_full_hour = False
            for rate in funding_rates:
                timestamp_str = rate.get("timestamp")
                if timestamp_str:
                    # Parse ISO format timestamp
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    timestamps.append(timestamp)

                    if timestamp.minute != 0 or timestamp.second != 0 or timestamp.microsecond != 0:
                        has_timestamp_not_on_full_hour = True
            
            if not timestamps or len(timestamps) < 2:
                return None

            timestamps.sort(reverse=True)

            max_date = timestamps[0]
            second_max_date = timestamps[1]
            time_span = max_date - second_max_date
            
            return second_max_date, max_date, time_span, has_timestamp_not_on_full_hour
            
        except Exception as e:
            logger.warning(f"Failed to calculate time span: {e}")
            return None
    
    def format_time_span(self, time_span: timedelta) -> str:
        """
        Format a timedelta into a readable string.
        
        Args:
            time_span: The time span to format
            
        Returns:
            Formatted string representation
        """
        total_seconds = int(time_span.total_seconds())
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        
        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0 and days == 0:  # Only show minutes if less than a day
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        
        if not parts:
            return "Less than 1 minute"
        
        return ", ".join(parts)
    
    def analyze_symbol(self, symbol: str) -> Dict:
        """
        Analyze funding rate data for a single symbol.
        
        Args:
            symbol: The trading symbol to analyze
            
        Returns:
            Dictionary containing analysis results
        """
        logger.info(f"Analyzing symbol: {symbol}")
        
        funding_rates = self.fetch_funding_rates(symbol)
        
        result = {
            "symbol": symbol,
            "has_data": False,
            "record_count": 0,
            "time_span": None,
            "time_span_formatted": "No data available",
            "min_date": None,
            "max_date": None,
            "error": None
        }
        
        if funding_rates is None:
            result["error"] = "Failed to fetch data"
            return result
        
        if not funding_rates:
            result["error"] = "No funding rate records found"
            return result
        
        result["has_data"] = True
        result["record_count"] = len(funding_rates)
        result["has_timestamp_not_on_full_hour"] = False

        time_span_data = self.calculate_time_span(funding_rates)
        if time_span_data:
            second_max_date, max_date, time_span, has_timestamp_not_on_full_hour = time_span_data
            result["time_span"] = time_span
            result["time_span_formatted"] = self.format_time_span(time_span)
            result["second_max_date"] = second_max_date.isoformat()
            result["max_date"] = max_date.isoformat()
            result["has_timestamp_not_on_full_hour"] = has_timestamp_not_on_full_hour
        else:
            result["error"] = "Failed to calculate time span"
        
        return result
    
    def run_analysis(self) -> None:
        """Run the complete funding rate analysis."""
        logger.info("Starting Kraken Futures funding rate analysis...")
        
        # Fetch all symbols
        symbols = self.fetch_tickers()
        if not symbols:
            logger.error("Failed to fetch symbols. Exiting.")
            return
        
        logger.info(f"Analyzing {len(symbols)} symbols...")
        
        # Analyze each symbol
        for i, symbol in enumerate(symbols, 1):
            try:
                result = self.analyze_symbol(symbol)
                self.results.append(result)
                
                # Print progress and result
                progress = f"[{i}/{len(symbols)}]"
                if result["has_data"]:
                    print(f"{progress} {symbol}: {result['time_span_formatted']} (last timestamp: {result['max_date']})")
                else:
                    print(f"{progress} {symbol}: {result['time_span_formatted']}")
                
                # Add small delay to be respectful to the API
                if i < len(symbols):
                    import time
                    time.sleep(0.1)
                    
            except KeyboardInterrupt:
                logger.info("Analysis interrupted by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error analyzing {symbol}: {e}")
                continue
        
        self.print_summary()
    
    def print_summary(self) -> None:
        """Print a summary of the analysis results."""
        if not self.results:
            logger.info("No results to summarize")
            return
        
        total_symbols = len(self.results)
        symbols_with_data = sum(1 for r in self.results if r["has_data"])
        symbols_without_data = total_symbols - symbols_with_data
        
        print("\n" + "="*60)
        print("ANALYSIS SUMMARY")
        print("="*60)
        print(f"Total symbols analyzed: {total_symbols}")
        print(f"Symbols with funding data: {symbols_with_data}")
        print(f"Symbols without funding data: {symbols_without_data}")
        
        if symbols_with_data > 0:
            # Find symbols with longest and shortest data spans
            symbols_with_spans = [r for r in self.results if r["has_data"] and r["time_span"]]
            
            if symbols_with_spans:
                longest_span = max(symbols_with_spans, key=lambda x: x["time_span"])
                shortest_span = min(symbols_with_spans, key=lambda x: x["time_span"])
                
                print(f"\nLongest data span: {longest_span['symbol']} - {longest_span['time_span_formatted']}")
                print(f"Shortest data span: {shortest_span['symbol']} - {shortest_span['time_span_formatted']}")
                
                # Calculate average span
                total_seconds = sum(r["time_span"].total_seconds() for r in symbols_with_spans)
                avg_seconds = total_seconds / len(symbols_with_spans)
                avg_span = timedelta(seconds=avg_seconds)
                print(f"Average data span: {self.format_time_span(avg_span)}")

                print(f"\nSymbols with timestamps not on 0 minutes 0 seconds: {sum(1 if r["has_timestamp_not_on_full_hour"] == True else 0 for r in self.results)}")
        
        print("="*60)
        logger.info("Analysis completed successfully")


def main():
    """Main entry point for the script."""
    try:
        analyzer = KrakenFundingAnalyzer()
        analyzer.run_analysis()
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Script failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()