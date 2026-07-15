"""Direct REST client for Binance USDT-M Futures Testnet."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import urlencode

import httpx

from .config import DEFAULT_BASE_URL, DEFAULT_RECV_WINDOW, Settings
from .exceptions import BinanceAPIError, BinanceHTTPError, BinanceResponseError, NetworkError
from .logging_config import LOGGER_NAME, redact_sensitive_fields, setup_logging
from .models import OrderRequest
from .orders import serialize_order_payload

API_KEY_HEADER = "X-MBX-APIKEY"
DEFAULT_TIMEOUT = 10.0


class BinanceFuturesClient:
    """Small httpx-based client for Binance USDT-M Futures REST endpoints."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = DEFAULT_BASE_URL,
        recv_window: int = DEFAULT_RECV_WINDOW,
        timeout: float = DEFAULT_TIMEOUT,
        timestamp_provider: Callable[[], int] | None = None,
        http_client: httpx.Client | None = None,
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.recv_window = recv_window
        self._timestamp_provider = timestamp_provider or _current_timestamp_ms
        self._owns_http_client = http_client is None
        self._http = http_client or httpx.Client(base_url=self.base_url, timeout=timeout)
        self._logger = logging.getLogger(LOGGER_NAME)
        if not self._logger.handlers:
            setup_logging()

    @classmethod
    def from_settings(cls, settings: Settings) -> BinanceFuturesClient:
        """Build a client from loaded application settings."""
        return cls(
            api_key=settings.api_key,
            api_secret=settings.api_secret,
            base_url=settings.base_url,
            recv_window=settings.recv_window,
        )

    def get_server_time(self) -> int:
        """Return Binance server time in milliseconds."""
        response = self._request("GET", "/fapi/v1/time", signed=False)
        server_time = response.get("serverTime")
        if not isinstance(server_time, int):
            raise BinanceResponseError("Binance time response did not include integer serverTime.")
        return server_time

    def get_exchange_info(self) -> dict[str, Any]:
        """Return raw Binance exchangeInfo data."""
        return self._request("GET", "/fapi/v1/exchangeInfo", signed=False)

    def test_order(self, order: OrderRequest) -> dict[str, Any]:
        """Validate an order through Binance without placing it."""
        return self._request(
            "POST",
            "/fapi/v1/order/test",
            params=serialize_order_payload(order),
            signed=True,
            allow_empty_response=True,
        )

    def place_order(self, order: OrderRequest) -> dict[str, Any]:
        """Place an order and return Binance's raw response."""
        return self._request(
            "POST",
            "/fapi/v1/order",
            params=serialize_order_payload(order),
            signed=True,
        )

    def close(self) -> None:
        """Close the underlying HTTP client if this instance owns it."""
        if self._owns_http_client:
            self._http.close()

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        signed: bool = False,
        allow_empty_response: bool = False,
    ) -> dict[str, Any]:
        request_params = dict(params or {})
        headers = {}

        if signed:
            request_params = self._sign_params(request_params)
            headers[API_KEY_HEADER] = self.api_key

        self._log_event(
            "binance.request",
            method=method,
            endpoint=endpoint,
            params=request_params,
            headers=headers,
        )

        try:
            response = self._http.request(
                method,
                endpoint,
                params=request_params,
                headers=headers,
            )
        except httpx.RequestError as exc:
            self._log_event(
                "binance.error",
                method=method,
                endpoint=endpoint,
                params=request_params,
                error=_sanitize_error_message(str(exc), request_params),
                error_type=exc.__class__.__name__,
            )
            raise NetworkError(f"Network error while contacting Binance: {exc}") from exc

        self._log_event(
            "binance.response",
            method=method,
            endpoint=endpoint,
            status_code=response.status_code,
            response=_response_log_body(response, endpoint),
        )

        if response.status_code >= 400:
            self._raise_http_error(response)

        if allow_empty_response and not response.content:
            return {}

        try:
            data = response.json()
        except ValueError as exc:
            raise BinanceResponseError("Binance returned a non-JSON response.") from exc

        if not isinstance(data, dict):
            raise BinanceResponseError("Binance returned an unexpected JSON response.")
        return data

    def _sign_params(self, params: dict[str, Any]) -> dict[str, Any]:
        signed_params = {
            **params,
            "timestamp": str(self._timestamp_provider()),
            "recvWindow": str(self.recv_window),
        }
        query_string = urlencode(signed_params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        signed_params["signature"] = signature
        return signed_params

    def _raise_http_error(self, response: httpx.Response) -> None:
        try:
            data = response.json()
        except ValueError as exc:
            raise BinanceHTTPError(
                f"Binance returned HTTP {response.status_code}: {response.text}"
            ) from exc

        if isinstance(data, dict) and "code" in data and "msg" in data:
            code = data.get("code")
            raise BinanceAPIError(str(data.get("msg")), code if isinstance(code, int) else None)

        raise BinanceHTTPError(f"Binance returned HTTP {response.status_code}: {data}")

    def _log_event(self, event: str, **fields: Any) -> None:
        payload = {"event": event, **fields}
        self._logger.info(json.dumps(redact_sensitive_fields(payload), sort_keys=True))


def _current_timestamp_ms() -> int:
    return int(time.time() * 1000)


def _response_log_body(response: httpx.Response, endpoint: str) -> Any:
    if not response.content:
        return {}
    try:
        data = response.json()
    except ValueError:
        return response.text
    if endpoint == "/fapi/v1/exchangeInfo" and isinstance(data, dict) and "symbols" in data:
        return {
            "serverTime": data.get("serverTime"),
            "assets_count": len(data.get("assets", [])),
            "symbols_count": len(data.get("symbols", [])),
        }
    return data


def _sanitize_error_message(message: str, params: dict[str, Any]) -> str:
    sanitized = message
    for key, value in params.items():
        if key == "signature":
            sanitized = sanitized.replace(str(value), "<redacted>")
    return sanitized
