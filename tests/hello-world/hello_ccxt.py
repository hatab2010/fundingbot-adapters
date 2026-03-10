import base64
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import ccxt
from setuptools.msvc import environ

API_KEY = environ.get("KRAKEN_API_KEY")
API_SECRET = environ.get("KRAKEN_SECRET")

BASE_URL = "https://futures.kraken.com/derivatives/api/v3"


def create_futures_signature(endpoint: str, nonce: str, postdata: str) -> str:
    message = postdata + nonce + endpoint
    sha256_hash = hashlib.sha256(message.encode("utf-8")).digest()
    signature = hmac.new(base64.b64decode(API_SECRET), sha256_hash, hashlib.sha512).digest()
    return base64.b64encode(signature).decode("utf-8")


if __name__ == "__main__":
    nonce = str(int(time.time() * 1000))
    params_dict = {"symbol": "PF_XBTUSD", "maxLeverage": 3}
    body = json.dumps(params_dict, separators=(",", ":"))

    headers = {
        "APIKey": API_KEY,
        "Nonce": nonce,
        "Authent": create_futures_signature("/api/v3/leveragepreferences", nonce, urlencode(params_dict)),
        "Content-Type": "application/json",
    }

    exchange = ccxt.krakenfutures({
        "apiKey": API_KEY,
        "secret": API_SECRET,
        "sandbox": True,  # для demo
        "enableRateLimit": True,
        # "uid": config.uid,
        "options": {"defaultType": "swap"},
    })

    symbol = "PF_XRPUSD"  # пример, подставь свой

    ticker = exchange.fetch_ticker(symbol)
    take_profit = ticker["last"] * 1.2
    stop_loss = ticker["last"] * 0.9

    data = exchange.create_order(
        symbol=symbol,
        side="buy",
        type="market",
        amount=5,
        params={"stopPrice": take_profit, "limitPrice": stop_loss},
    )

    unfiltered_orders = exchange.fetch_open_orders(symbol=symbol)
    print(unfiltered_orders)
