import base64
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import requests
from setuptools.msvc import environ

API_KEY = environ.get("KRAKEN_API_KEY")
API_SECRET = environ.get("KRAKEN_SECRET")

BASE_URL = "https://futures.kraken.com/derivatives/api/v3"


def create_spot_signature(path: str, nonce: str, postdata: str) -> str:
    """Create signature for Spot API"""
    encoded = (nonce + postdata).encode("utf-8")
    message = path.encode("utf-8") + hashlib.sha256(encoded).digest()
    signature = hmac.new(base64.b64decode(API_SECRET), message, hashlib.sha512).digest()
    return base64.b64encode(signature).decode("utf-8")


def sign_kraken_futures(path, body):
    """См. https://docs.kraken.com/api/docs/guides/spot-rest-auth#setting-the-api-sign-parameter"""
    # nonce в миллисекундах
    nonce = str(int(time.time() * 1000))

    headers = {
        "APIKey": API_KEY,
        "Nonce": nonce,
        "Authent": create_futures_signature(path, nonce, body),
        "Content-Type": "application/json",
    }

    return headers


def set_margin_mode(symbol: str, mode: str, max_leverage: float | None = None):
    """Устанавливает margin mode для контракта:
    mode: "cross" или "isolated"
    Если передан max_leverage -> режим будет isolated.[web:1]
    """
    path = "/leveragepreferences"
    url = BASE_URL + path

    # Согласно docs: можно задать symbol, marginMode и/или maxLeverage.[web:1]
    payload = {"symbol": symbol}

    # Если явно указать режим
    if mode.lower() == "cross":
        payload["marginMode"] = "cross"
    elif mode.lower() == "isolated":
        payload["marginMode"] = "isolated"
    else:
        raise ValueError("mode must be 'cross' or 'isolated'")

    # Если хотим задать максимальное плечо (переводит в isolated)
    if max_leverage is not None:
        payload["maxLeverage"] = max_leverage

    body = json.dumps(payload)

    headers = sign_kraken_futures(path=path, body=body)

    resp = requests.put(url, headers=headers, data=body, timeout=10)
    resp.raise_for_status()
    return resp.json()


def create_futures_signature(endpoint: str, nonce: str, postdata: str) -> str:
    message = postdata + nonce + endpoint
    sha256_hash = hashlib.sha256(message.encode("utf-8")).digest()
    signature = hmac.new(base64.b64decode(API_SECRET), sha256_hash, hashlib.sha512).digest()
    return base64.b64encode(signature).decode("utf-8")


if __name__ == "__main__":
    nonce = str(int(time.time() * 1000))
    body_dict = {"symbol": "PF_XBTUSD", "maxLeverage": 3}
    body = json.dumps(body_dict, separators=(",", ":"))

    headers = {
        "APIKey": API_KEY,
        "Nonce": nonce,
        "Authent": create_futures_signature("/api/v3/leveragepreferences", nonce, urlencode(body_dict)),
        "Content-Type": "application/json",
    }

    response = requests.put("https://demo-futures.kraken.com/derivatives/api/v3/leveragepreferences", headers=headers, params=body_dict)
    print(response)
    print(response.json())
