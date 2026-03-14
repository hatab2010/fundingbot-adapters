# Kraken Futures API Research

## Executive Summary

This research document provides comprehensive analysis for implementing a Kraken Futures API client for perpetual futures trading within the fundingbot ecosystem. The critical finding is that **CCXT's Kraken implementation only supports spot trading** (`'swap': False, 'future': False`) and cannot access perpetual futures or funding rates.

**Key Findings:**
- Kraken operates separate APIs: Spot API for traditional trading and Futures API for derivatives
- Standard CCXT Kraken client cannot retrieve funding rates or trade perpetual futures
- Direct API integration with Kraken Futures API is required
- Symbol format conversion between Kraken native (`PF_XBTUSD`) and CCXT normalized (`BTC/USD:USD`) is essential
- Authentication uses HMAC-SHA512 with different signature construction than Bitget

**Implementation Approach:**
The KrakenClient must override key methods to directly call Kraken Futures API endpoints while maintaining compatibility with the fundingbot-sdk interface.

## API Structure Comparison (Kraken vs Bitget)

### Kraken API Architecture
```
Spot API:     https://api.kraken.com/0/
Futures API:  https://futures.kraken.com/derivatives/api/v3/
```

**Kraken Spot API:**
- Endpoint: `https://api.kraken.com/0/`
- Supports: Spot trading only
- No funding rates available
- No perpetual futures
- CCXT compatible

**Kraken Futures API:**
- Endpoint: `https://futures.kraken.com/derivatives/api/v3/`
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

### Bitget Authentication (Reference)
```python
# Bitget uses different signature construction
def create_signature(self, timestamp: str, method: str, path: str, body: str) -> str:
    """
    Bitget signature: timestamp + method + path + body
    """
    message = timestamp + method + path + body
    signature = hmac.new(
        self.api_secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()
    return base64.b64encode(signature).decode('utf-8')
```

### Key Authentication Differences

| Aspect | Kraken Futures | Bitget |
|--------|----------------|--------|
| Hash Algorithm | HMAC-SHA512 | HMAC-SHA256 |
| Message Format | `postdata + nonce + endpoint` | `timestamp + method + path + body` |
| Secret Encoding | Base64 decoded | UTF-8 encoded |
| Header Names | `APIKey`, `Nonce`, `Authent` | `ACCESS-KEY`, `ACCESS-TIMESTAMP`, `ACCESS-SIGN` |

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

### Symbol Conversion Implementation
```python
def kraken_to_ccxt_symbol(self, kraken_symbol: str) -> str:
    """Convert Kraken Futures symbol to CCXT format"""
    if not kraken_symbol.startswith('PF_'):
        raise ValueError(f"Invalid Kraken futures symbol: {kraken_symbol}")
    
    # Remove PF_ prefix
    base_symbol = kraken_symbol[3:]
    
    # Handle special cases
    symbol_map = {
        'XBTUSD': 'BTC/USD:USD',
        'ETHUSD': 'ETH/USD:USD',
        'SOLUSD': 'SOL/USD:USD',
        # Add more mappings as needed
    }
    
    return symbol_map.get(base_symbol, f"{base_symbol[:-3]}/{base_symbol[-3:]}:{base_symbol[-3:]}")

def ccxt_to_kraken_symbol(self, ccxt_symbol: str) -> str:
    """Convert CCXT symbol to Kraken Futures format"""
    if ':' not in ccxt_symbol:
        raise ValueError(f"Invalid CCXT swap symbol: {ccxt_symbol}")
    
    base_quote = ccxt_symbol.split(':')[0]  # BTC/USD from BTC/USD:USD
    base, quote = base_quote.split('/')
    
    # Handle special cases
    if base == 'BTC':
        base = 'XBT'
    
    return f"PF_{base}{quote}"
```

### Market Type Detection
```python
def is_perpetual_future(self, symbol: str) -> bool:
    """Check if symbol represents a perpetual future"""
    # CCXT format check
    if ':' in symbol and symbol.endswith(':USD'):
        return True
    
    # Kraken format check
    if symbol.startswith('PF_'):
        return True
    
    return False
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

**Bitget Order Placement (Reference):**
```python
# Uses CCXT standardized parameters
order = await exchange.create_order(
    symbol='BTC/USD:USD',
    type='limit',
    side='buy',
    amount=1,
    price=50000.0
)
```

### Order Status Mapping

| Kraken Status | CCXT Status | Description |
|---------------|-------------|-------------|
| `untouched` | `open` | Order placed, not filled |
| `partiallyFilled` | `open` | Partially executed |
| `filled` | `closed` | Fully executed |
| `cancelled` | `canceled` | Order cancelled |
| `rejected` | `rejected` | Order rejected |

### Order Management Implementation
```python
async def create_order(self, symbol: str, type: str, side: str, amount: float, price: float = None) -> dict:
    """Create order using Kraken Futures API"""
    kraken_symbol = self.ccxt_to_kraken_symbol(symbol)
    
    params = {
        'orderType': 'lmt' if type == 'limit' else 'mkt',
        'symbol': kraken_symbol,
        'side': side,
        'size': int(amount),  # Kraken uses integer sizes
    }
    
    if type == 'limit' and price:
        params['limitPrice'] = price
    
    response = await self._request('POST', '/sendorder', params)
    return self._parse_order(response)
```

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

### Balance Information

**Kraken Futures Balance Endpoint:**
```
GET /derivatives/api/v3/accounts
```

**Response Format:**
```json
{
    "result": "success",
    "accounts": {
        "cash": {
            "balances": {
                "USD": 10000.50
            }
        }
    }
}
```

### Implementation Example
```python
async def fetch_positions(self) -> List[dict]:
    """Fetch open positions from Kraken Futures"""
    response = await self._request('GET', '/openpositions')
    positions = []
    
    for pos in response.get('openPositions', []):
        positions.append({
            'symbol': self.kraken_to_ccxt_symbol(pos['symbol']),
            'side': pos['side'],
            'size': pos['size'],
            'unrealizedPnl': pos['unrealizedPnl'],
            'entryPrice': pos['entryPrice'],
            'markPrice': pos['markPrice']
        })
    
    return positions
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
