# Kraken Futures API Research

## API Structure Comparison (Kraken vs Bitget)

### Kraken API Architecture

**Kraken Futures API:**
- Endpoint: `https://futures.kraken.com/derivatives/api/v3/`
- REST API Guides: https://docs.kraken.com/api/docs/guides/global-intro
- REST API Reference Documentation: https://docs.kraken.com/api/docs/futures-api/trading/get-tickers
- Kraken API Center landing page: https://docs.kraken.com/api/
- Supports: Perpetual futures, options, funding rates
- Separate authentication system
- Not directly supported by CCXT
- Required for fundingbot implementation

### Bitget API Architecture (Reference)
```
Unified API:  https://api.bitget.com/api/
```

**Bitget Unified API:**
- Single endpoint for spot and futures
- CCXT fully compatible
- Funding rates accessible via CCXT
- Consistent authentication across all products

### Key Architectural Differences

| Feature | Kraken | Bitget |
|---------|--------|--------|
| API Structure | Separate Spot/Futures APIs | Unified API |
| CCXT Support | Spot only | Full support |
| Funding Rates | Futures API only | Available via CCXT |
| Authentication | Different per API | Unified |
| Symbol Format | Different per API | Consistent |

## Authentication Differences

### Kraken Futures Authentication
```python
# Signature construction for Kraken Futures
def create_signature(self, endpoint: str, nonce: str, postdata: str) -> str:
    """
    Kraken Futures uses HMAC-SHA512 with specific message format:
    message = postdata + nonce + endpoint
    """
    message = postdata + nonce + endpoint
    signature = hmac.new(
        base64.b64decode(self.api_secret),
        message.encode('utf-8'),
        hashlib.sha512
    ).digest()
    return base64.b64encode(signature).decode('utf-8')
```

**Headers Required:**
```python
headers = {
    'APIKey': self.api_key,
    'Nonce': nonce,
    'Authent': signature,
    'Content-Type': 'application/x-www-form-urlencoded'
}
```

## Market Data & Symbol Handling

### Symbol Format Conversion

**Kraken Futures Native Format:**
```
PF_XBTUSD    # Bitcoin perpetual future
PF_ETHUSD    # Ethereum perpetual future
PF_SOLUSD    # Solana perpetual future
```

**CCXT Normalized Format:**
```
BTC/USD:USD  # Bitcoin perpetual future
ETH/USD:USD  # Ethereum perpetual future
SOL/USD:USD  # Solana perpetual future
```

## Order Management Differences

### Order Placement

**Kraken Futures Order Endpoint:**
```
POST /derivatives/api/v3/sendorder
```

**Required Parameters:**
```python
{
    'orderType': 'lmt',  # limit order
    'symbol': 'PF_XBTUSD',
    'side': 'buy',
    'size': 1,
    'limitPrice': 50000.0,
    'reduceOnly': False
}
```

### Order Status Mapping

| Kraken Status | CCXT Status | Description |
|---------------|-------------|-------------|
| `untouched` | `open` | Order placed, not filled |
| `partiallyFilled` | `open` | Partially executed |
| `filled` | `closed` | Fully executed |
| `cancelled` | `canceled` | Order cancelled |
| `rejected` | `rejected` | Order rejected |

## Position & Balance Management

### Position Information

**Kraken Futures Position Endpoint:**
```
GET /derivatives/api/v3/openpositions
```

**Response Format:**
```json
{
    "result": "success",
    "openPositions": [
        {
            "symbol": "PF_XBTUSD",
            "side": "long",
            "size": 100,
            "unrealizedPnl": 150.25,
            "entryPrice": 49500.0,
            "markPrice": 50000.0
        }
    ]
}
```

## Funding Rate Implementation

### Critical Implementation Detail

**The `get_funding_usdt_rates()` method must be completely overridden** because CCXT cannot access Kraken Futures funding rates.

### Kraken Futures Funding Rate Endpoint
```
GET /derivatives/api/v3/historicalfundingrates
```

**Parameters:**
```python
{
    'symbol': 'PF_XBTUSD'  # Required: specific symbol
}
```

**Response Format:**
```json
{
    "result": "success",
    "rates": [
        {
            "timestamp": "2024-01-01T08:00:00.000Z",
            "fundingRate": 0.0001,
            "symbol": "PF_XBTUSD"
        }
    ]
}
```

### Override Implementation
```python
async def get_funding_usdt_rates(self) -> List[FundingRate]:
    """
    Override to fetch funding rates directly from Kraken Futures API
    CCXT cannot access these rates from the spot API
    """
    funding_rates = []
    
    # Get all perpetual future symbols
    markets = await self.load_markets()
    swap_symbols = [symbol for symbol, market in markets.items() if market.get('swap', False)]
    
    for symbol in swap_symbols:
        try:
            kraken_symbol = self.ccxt_to_kraken_symbol(symbol)
            
            # Fetch funding rate from Kraken Futures API
            response = await self._request('GET', '/historicalfundingrates', {
                'symbol': kraken_symbol
            })
            
            if response.get('result') == 'success' and response.get('rates'):
                latest_rate = response['rates'][-1]  # Get most recent rate
                
                funding_rates.append(FundingRate(
                    symbol=symbol,
                    funding_rate=latest_rate['fundingRate'],
                    funding_time=self._parse_timestamp(latest_rate['timestamp'])
                ))
                
        except Exception as e:
            self.logger.warning(f"Failed to fetch funding rate for {symbol}: {e}")
            continue
    
    return funding_rates
```

### Funding Rate Schedule
- **Kraken Futures:** Every 8 hours (00:00, 08:00, 16:00 UTC)
- **Bitget:** Every 8 hours (similar schedule)

## Rate Limiting & Error Handling

### Kraken Futures Rate Limits

**Public Endpoints:**
- Rate Limit: 100 requests per minute
- Burst Limit: 10 requests per second

**Private Endpoints:**
- Rate Limit: 60 requests per minute
- Burst Limit: 5 requests per second

**Headers in Response:**
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1640995200
```

### 5. Configuration Management
```python
class KrakenPathsAndConfigs:
    FUTURES_BASE_URL = 'https://futures.kraken.com/derivatives/api/v3'
    SANDBOX_FUTURES_URL = 'https://demo-futures.kraken.com/derivatives/api/v3'
    
    RATE_LIMITS = {
        'public': {'requests': 100, 'window': 60},
        'private': {'requests': 60, 'window': 60},
        'burst': {'requests': 5, 'window': 1}
    }
```
