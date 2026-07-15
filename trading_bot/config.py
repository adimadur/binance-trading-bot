"""Application configuration loading."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .exceptions import ConfigError

DEFAULT_BASE_URL = "https://testnet.binancefuture.com"
DEFAULT_RECV_WINDOW = 5000


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings needed to access Binance Futures Testnet."""

    api_key: str
    api_secret: str
    base_url: str = DEFAULT_BASE_URL
    recv_window: int = DEFAULT_RECV_WINDOW


def load_settings(env_file: str | Path | None = None) -> Settings:
    """Load settings from environment variables and an optional .env file."""
    if env_file is None:
        env_file = Path.cwd() / ".env"

    logging.getLogger("dotenv.main").setLevel(logging.ERROR)
    load_dotenv(env_file)

    api_key = os.getenv("BINANCE_TESTNET_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_TESTNET_API_SECRET", "").strip()
    base_url = os.getenv("BINANCE_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/")
    recv_window_raw = os.getenv("BINANCE_RECV_WINDOW", str(DEFAULT_RECV_WINDOW)).strip()

    if not api_key:
        raise ConfigError("Missing BINANCE_TESTNET_API_KEY.")
    if not api_secret:
        raise ConfigError("Missing BINANCE_TESTNET_API_SECRET.")

    try:
        recv_window = int(recv_window_raw)
    except ValueError as exc:
        raise ConfigError("BINANCE_RECV_WINDOW must be an integer.") from exc

    if recv_window <= 0:
        raise ConfigError("BINANCE_RECV_WINDOW must be positive.")
    if not base_url:
        raise ConfigError("BINANCE_BASE_URL cannot be empty.")

    return Settings(
        api_key=api_key,
        api_secret=api_secret,
        base_url=base_url,
        recv_window=recv_window,
    )
