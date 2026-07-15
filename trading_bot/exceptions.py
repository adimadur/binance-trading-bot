"""Custom exception hierarchy for the trading bot."""

from __future__ import annotations


class TradingBotError(Exception):
    """Base exception for expected trading bot failures."""


class ConfigError(TradingBotError):
    """Raised when required runtime configuration is invalid or missing."""


class ValidationError(TradingBotError):
    """Raised when user-supplied order input is invalid."""


class ExchangeRuleError(ValidationError):
    """Raised when an order violates Binance exchange rules."""


class BinanceAPIError(TradingBotError):
    """Raised when Binance returns a structured API error."""


class BinanceHTTPError(TradingBotError):
    """Raised when Binance returns an unexpected HTTP error."""


class NetworkError(TradingBotError):
    """Raised when Binance cannot be reached."""


class BinanceResponseError(TradingBotError):
    """Raised when Binance returns an unexpected response shape."""

