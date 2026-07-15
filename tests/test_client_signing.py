import hashlib
import hmac
from urllib.parse import urlencode

import httpx

from trading_bot.client import API_KEY_HEADER, BinanceFuturesClient
from trading_bot.orders import build_order_request


def test_signed_order_request_has_deterministic_signature_and_api_key_header(httpx_mock):
    order = build_order_request("BTCUSDT", "BUY", "MARKET", "0.001")
    timestamp = 1700000000000
    api_secret = "test-secret"
    expected_params = {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "type": "MARKET",
        "quantity": "0.001",
        "newOrderRespType": "RESULT",
        "timestamp": str(timestamp),
        "recvWindow": "5000",
    }
    expected_signature = hmac.new(
        api_secret.encode("utf-8"),
        urlencode(expected_params).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    def handler(request: httpx.Request) -> httpx.Response:
        params = dict(request.url.params)
        assert request.headers[API_KEY_HEADER] == "test-key"
        assert "test-key" not in str(request.url)
        assert params == {**expected_params, "signature": expected_signature}
        return httpx.Response(200, json={"orderId": 123, "status": "NEW"})

    httpx_mock.add_callback(
        handler,
        method="POST",
    )
    client = BinanceFuturesClient(
        api_key="test-key",
        api_secret=api_secret,
        timestamp_provider=lambda: timestamp,
    )

    assert client.place_order(order) == {"orderId": 123, "status": "NEW"}


def test_test_order_uses_test_endpoint_and_allows_empty_response(httpx_mock):
    order = build_order_request("BTCUSDT", "SELL", "LIMIT", "0.01", "2500")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/fapi/v1/order/test"
        assert request.headers[API_KEY_HEADER] == "test-key"
        params = dict(request.url.params)
        assert params["symbol"] == "BTCUSDT"
        assert params["side"] == "SELL"
        assert params["type"] == "LIMIT"
        assert params["price"] == "2500"
        assert params["timeInForce"] == "GTC"
        assert "signature" in params
        return httpx.Response(200)

    httpx_mock.add_callback(
        handler,
        method="POST",
    )
    client = BinanceFuturesClient(
        api_key="test-key",
        api_secret="test-secret",
        timestamp_provider=lambda: 1700000000000,
    )

    assert client.test_order(order) == {}
