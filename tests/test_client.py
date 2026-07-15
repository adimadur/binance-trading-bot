import json
import logging

import httpx
import pytest

from trading_bot.client import BinanceFuturesClient
from trading_bot.exceptions import (
    BinanceAPIError,
    BinanceHTTPError,
    BinanceResponseError,
    NetworkError,
)
from trading_bot.logging_config import LOGGER_NAME, REDACTED
from trading_bot.orders import build_order_request


def test_get_server_time_returns_integer_server_time(httpx_mock):
    httpx_mock.add_response(
        method="GET",
        url="https://testnet.binancefuture.com/fapi/v1/time",
        json={"serverTime": 1700000000000},
    )
    client = BinanceFuturesClient("key", "secret")

    assert client.get_server_time() == 1700000000000


def test_get_exchange_info_returns_raw_payload(httpx_mock):
    payload = {"symbols": [{"symbol": "BTCUSDT"}]}
    httpx_mock.add_response(
        method="GET",
        url="https://testnet.binancefuture.com/fapi/v1/exchangeInfo",
        json=payload,
    )
    client = BinanceFuturesClient("key", "secret")

    assert client.get_exchange_info() == payload


def test_place_order_uses_real_order_endpoint(httpx_mock):
    order = build_order_request("BTCUSDT", "BUY", "MARKET", "0.001")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/fapi/v1/order"
        return httpx.Response(200, json={"orderId": 1, "status": "NEW"})

    httpx_mock.add_callback(
        handler,
        method="POST",
    )
    client = BinanceFuturesClient("key", "secret", timestamp_provider=lambda: 1700000000000)

    assert client.place_order(order) == {"orderId": 1, "status": "NEW"}


def test_binance_json_error_maps_to_binance_api_error(httpx_mock):
    httpx_mock.add_response(
        method="GET",
        url="https://testnet.binancefuture.com/fapi/v1/exchangeInfo",
        status_code=400,
        json={"code": -2019, "msg": "Margin is insufficient."},
    )
    client = BinanceFuturesClient("key", "secret")

    with pytest.raises(BinanceAPIError) as exc_info:
        client.get_exchange_info()

    assert exc_info.value.code == -2019
    assert exc_info.value.message == "Margin is insufficient."
    assert "Binance API error -2019" in str(exc_info.value)


def test_non_json_http_error_maps_to_binance_http_error(httpx_mock):
    httpx_mock.add_response(
        method="GET",
        url="https://testnet.binancefuture.com/fapi/v1/exchangeInfo",
        status_code=502,
        text="Bad Gateway",
    )
    client = BinanceFuturesClient("key", "secret")

    with pytest.raises(BinanceHTTPError):
        client.get_exchange_info()


def test_network_error_maps_to_network_error(httpx_mock):
    httpx_mock.add_exception(httpx.ConnectError("connection failed"))
    client = BinanceFuturesClient("key", "secret")

    with pytest.raises(NetworkError):
        client.get_exchange_info()


def test_successful_non_json_response_maps_to_response_error(httpx_mock):
    httpx_mock.add_response(
        method="GET",
        url="https://testnet.binancefuture.com/fapi/v1/exchangeInfo",
        content=b"not json",
    )
    client = BinanceFuturesClient("key", "secret")

    with pytest.raises(BinanceResponseError):
        client.get_exchange_info()


def test_time_response_without_integer_server_time_maps_to_response_error(httpx_mock):
    httpx_mock.add_response(
        method="GET",
        url="https://testnet.binancefuture.com/fapi/v1/time",
        json={"serverTime": "1700000000000"},
    )
    client = BinanceFuturesClient("key", "secret")

    with pytest.raises(BinanceResponseError):
        client.get_server_time()


def test_client_logs_redacted_request_fields(httpx_mock):
    records: list[str] = []

    class ListHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record.getMessage())

    logger = logging.getLogger(LOGGER_NAME)
    handler = ListHandler()
    logger.addHandler(handler)
    try:
        httpx_mock.add_response(method="POST", status_code=200)
        client = BinanceFuturesClient(
            "test-key",
            "test-secret",
            timestamp_provider=lambda: 1700000000000,
        )

        client.test_order(build_order_request("BTCUSDT", "BUY", "MARKET", "0.001"))
    finally:
        logger.removeHandler(handler)

    request_logs = [json.loads(record) for record in records if "binance.request" in record]
    assert request_logs
    request_log = request_logs[0]
    assert request_log["headers"]["X-MBX-APIKEY"] == REDACTED
    assert request_log["params"]["signature"] == REDACTED
    assert "test-secret" not in records[0]
    assert "test-key" not in records[0]
