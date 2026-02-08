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

### Error Response Format
```json
{
    "result": "error",
    "error": "Insufficient margin",
    "serverTime": "2024-01-01T12:00:00.000Z"
}
```

### Error Handling Implementation
```python
async def _handle_response(self, response: dict) -> dict:
    """Handle Kraken Futures API response"""
    if response.get('result') == 'error':
        error_msg = response.get('error', 'Unknown error')
        
        # Map Kraken errors to fundingbot-sdk errors
        if 'Insufficient margin' in error_msg:
            raise InsufficientFundsError(error_msg)
        elif 'Invalid symbol' in error_msg:
            raise InvalidSymbolError(error_msg)
        elif 'Rate limit' in error_msg:
            raise RateLimitError(error_msg)
        else:
            raise ExchangeError(error_msg)
    
    return response
```

### Rate Limiting Strategy
```python
class KrakenRateLimiter:
    def __init__(self):
        self.public_limiter = AsyncLimiter(100, 60)    # 100 per minute
        self.private_limiter = AsyncLimiter(60, 60)    # 60 per minute
        self.burst_limiter = AsyncLimiter(5, 1)        # 5 per second
    
    async def acquire(self, is_private: bool = False):
        """Acquire rate limit tokens"""
        await self.burst_limiter.acquire()
        
        if is_private:
            await self.private_limiter.acquire()
        else:
            await self.public_limiter.acquire()
```

## Key Implementation Recommendations

### 1. Dual API Architecture
- Use CCXT for basic exchange functionality where possible
- Implement direct Futures API calls for futures-specific operations
- Maintain symbol conversion between formats

### 2. Method Override Priority
**High Priority (Must Override):**
- `get_funding_usdt_rates()` - CCXT cannot access funding rates
- `load_markets()` - Need futures markets, not spot markets
- `create_order()` - Different order parameters for futures

**Medium Priority (Should Override):**
- `fetch_positions()` - Futures-specific position data
- `fetch_balance()` - Futures account balance
- `cancel_order()` - Futures-specific cancellation

**Low Priority (Optional Override):**
- `fetch_ticker()` - Can use CCXT if symbol conversion is handled
- `fetch_order_book()` - Can use CCXT with symbol conversion

### 3. Error Handling Strategy
```python
async def _safe_ccxt_call(self, method_name: str, *args, **kwargs):
    """Safely call CCXT method with fallback to direct API"""
    try:
        method = getattr(self.exchange, method_name)
        return await method(*args, **kwargs)
    except Exception as e:
        self.logger.warning(f"CCXT {method_name} failed: {e}, falling back to direct API")
        # Implement direct API fallback
        return await self._direct_api_fallback(method_name, *args, **kwargs)
```

### 4. Symbol Management
```python
class SymbolManager:
    def __init__(self):
        self.kraken_to_ccxt_map = {}
        self.ccxt_to_kraken_map = {}
    
    async def initialize(self):
        """Initialize symbol mappings from Futures API"""
        instruments = await self._fetch_instruments()
        for instrument in instruments:
            if instrument['symbol'].startswith('PF_'):
                kraken_symbol = instrument['symbol']
                ccxt_symbol = self._convert_to_ccxt_format(kraken_symbol)
                
                self.kraken_to_ccxt_map[kraken_symbol] = ccxt_symbol
                self.ccxt_to_kraken_map[ccxt_symbol] = kraken_symbol
```

### 5. Configuration Management
```python
class KrakenConfig:
    SPOT_BASE_URL = 'https://api.kraken.com/0'
    FUTURES_BASE_URL = 'https://futures.kraken.com/derivatives/api/v3'
    
    SANDBOX_SPOT_URL = 'https://api.kraken.com/0'  # No sandbox for spot
    SANDBOX_FUTURES_URL = 'https://demo-futures.kraken.com/derivatives/api/v3'
    
    RATE_LIMITS = {
        'public': {'requests': 100, 'window': 60},
        'private': {'requests': 60, 'window': 60},
        'burst': {'requests': 5, 'window': 1}
    }
```

## Potential Challenges & Solutions

### Challenge 1: CCXT Incompatibility
**Problem:** CCXT Kraken client doesn't support futures trading or funding rates.

**Solution:**
- Implement hybrid approach using CCXT for basic functionality
- Override critical methods with direct Futures API calls
- Maintain compatibility with fundingbot-sdk interface

### Challenge 2: Symbol Format Differences
**Problem:** Kraken uses `PF_XBTUSD` while CCXT expects `BTC/USD:USD`.

**Solution:**
```python
class SymbolConverter:
    @staticmethod
    def to_ccxt(kraken_symbol: str) -> str:
        """Convert PF_XBTUSD -> BTC/USD:USD"""
        if not kraken_symbol.startswith('PF_'):
            raise ValueError(f"Invalid Kraken futures symbol: {kraken_symbol}")
        
        base_symbol = kraken_symbol[3:]  # Remove PF_
        
        # Handle XBT -> BTC conversion
        if base_symbol.startswith('XBT'):
            base_symbol = base_symbol.replace('XBT', 'BTC', 1)
        
        # Extract base and quote (assuming 3-char quote)
        base = base_symbol[:-3]
        quote = base_symbol[-3:]
        
        return f"{base}/{quote}:{quote}"
    
    @staticmethod
    def to_kraken(ccxt_symbol: str) -> str:
        """Convert BTC/USD:USD -> PF_XBTUSD"""
        if ':' not in ccxt_symbol:
            raise ValueError(f"Invalid CCXT swap symbol: {ccxt_symbol}")
        
        base_quote = ccxt_symbol.split(':')[0]
        base, quote = base_quote.split('/')
        
        # Handle BTC -> XBT conversion
        if base == 'BTC':
            base = 'XBT'
        
        return f"PF_{base}{quote}"
```

### Challenge 3: Authentication Complexity
**Problem:** Different authentication methods for Spot vs Futures APIs.

**Solution:**
```python
class KrakenAuthenticator:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
    
    def create_spot_signature(self, path: str, nonce: str, postdata: str) -> str:
        """Create signature for Spot API"""
        encoded = (nonce + postdata).encode('utf-8')
        message = path.encode('utf-8') + hashlib.sha256(encoded).digest()
        signature = hmac.new(
            base64.b64decode(self.api_secret),
            message,
            hashlib.sha512
        ).digest()
        return base64.b64encode(signature).decode('utf-8')
    
    def create_futures_signature(self, endpoint: str, nonce: str, postdata: str) -> str:
        """Create signature for Futures API"""
        message = postdata + nonce + endpoint
        signature = hmac.new(
            base64.b64decode(self.api_secret),
            message.encode('utf-8'),
            hashlib.sha512
        ).digest()
        return base64.b64encode(signature).decode('utf-8')
```

### Challenge 4: Rate Limiting Coordination
**Problem:** Different rate limits for Spot and Futures APIs.

**Solution:**
```python
class DualRateLimiter:
    def __init__(self):
        self.spot_limiter = AsyncLimiter(100, 60)      # Spot API limits
        self.futures_limiter = AsyncLimiter(60, 60)    # Futures API limits
        self.global_burst = AsyncLimiter(10, 1)        # Global burst limit
    
    async def acquire_spot(self):
        await self.global_burst.acquire()
        await self.spot_limiter.acquire()
    
    async def acquire_futures(self):
        await self.global_burst.acquire()
        await self.futures_limiter.acquire()
```

### Challenge 5: Market Data Synchronization
**Problem:** Ensuring consistent market data between Spot and Futures APIs.

**Solution:**
```python
class MarketDataManager:
    def __init__(self, client):
        self.client = client
        self.futures_markets = {}
        self.last_update = None
    
    async def get_unified_markets(self) -> dict:
        """Get unified market data combining Spot and Futures"""
        # Load CCXT spot markets
        spot_markets = await self.client.exchange.load_markets()
        
        # Load Futures markets directly
        futures_markets = await self._load_futures_markets()
        
        # Combine and normalize
        unified_markets = {}
        
        # Add futures markets with proper CCXT format
        for kraken_symbol, market_data in futures_markets.items():
            ccxt_symbol = SymbolConverter.to_ccxt(kraken_symbol)
            unified_markets[ccxt_symbol] = {
                'id': kraken_symbol,
                'symbol': ccxt_symbol,
                'base': market_data['base'],
                'quote': market_data['quote'],
                'settle': market_data['quote'],
                'type': 'swap',
                'spot': False,
                'margin': True,
                'swap': True,
                'future': False,
                'active': market_data['active'],
                'contract': True,
                'linear': True,
                'inverse': False
            }
        
        return unified_markets
```

### Challenge 6: Testing Strategy
**Problem:** Testing with both Spot and Futures APIs in sandbox environment.

**Solution:**
```python
class KrakenTestClient(KrakenClient):
    def __init__(self, api_key: str, api_secret: str):
        super().__init__(api_key, api_secret, sandbox=True)
        
        # Override URLs for testing
        self.futures_base_url = 'https://demo-futures.kraken.com/derivatives/api/v3'
    
    async def _mock_funding_rates(self) -> List[FundingRate]:
        """Mock funding rates for testing"""
        return [
            FundingRate(
                symbol='BTC/USD:USD',
                funding_rate=0.0001,
                funding_time=datetime.utcnow()
            )
        ]
```

This comprehensive research document provides the foundation for successfully implementing the KrakenClient with proper Futures API integration while maintaining compatibility with the fundingbot-sdk interface.