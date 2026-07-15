"""Typed domain models for order placement."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any


class OrderSide(StrEnum):
    """Supported Binance order sides."""

    BUY = "BUY"
    SELL = "SELL"


class OrderType(StrEnum):
    """Supported Binance order types for this assignment."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"


@dataclass(frozen=True, slots=True)
class OrderRequest:
    """A validated order request before serialization to Binance."""

    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Decimal | None = None
    time_in_force: str | None = None
    new_order_resp_type: str = "RESULT"


@dataclass(frozen=True, slots=True)
class OrderResponse:
    """Important fields returned by Binance after order placement."""

    order_id: int | None
    status: str | None
    executed_qty: Decimal | None
    avg_price: Decimal | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SymbolRules:
    """Exchange rules used to validate price and quantity precision."""

    symbol: str
    status: str
    order_types: frozenset[str]
    time_in_force: frozenset[str]
    min_qty: Decimal | None = None
    max_qty: Decimal | None = None
    step_size: Decimal | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    tick_size: Decimal | None = None
    min_notional: Decimal | None = None

