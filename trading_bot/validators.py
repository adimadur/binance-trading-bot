"""Validation helpers for order input and Binance exchange rules."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from .exceptions import ExchangeRuleError, ValidationError
from .models import OrderRequest, OrderSide, OrderType, SymbolRules

SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]+$")
LIMIT_TIME_IN_FORCE = "GTC"


def validate_symbol(raw: object) -> str:
    """Normalize and validate a Binance symbol."""
    symbol = "" if raw is None else str(raw).strip().upper()
    if not symbol or not SYMBOL_PATTERN.fullmatch(symbol):
        raise ValidationError("Symbol must be an uppercase alphanumeric pair, e.g. BTCUSDT.")
    return symbol


def validate_side(raw: object) -> OrderSide:
    """Normalize and validate order side."""
    side = "" if raw is None else str(raw).strip().upper()
    try:
        return OrderSide(side)
    except ValueError as exc:
        valid = ", ".join(side.value for side in OrderSide)
        raise ValidationError(f"Side must be one of: {valid}.") from exc


def validate_order_type(raw: object) -> OrderType:
    """Normalize and validate order type."""
    order_type = "" if raw is None else str(raw).strip().upper()
    try:
        return OrderType(order_type)
    except ValueError as exc:
        valid = ", ".join(order_type.value for order_type in OrderType)
        raise ValidationError(f"Order type must be one of: {valid}.") from exc


def parse_positive_decimal(raw: object, field_name: str) -> Decimal:
    """Parse a positive decimal from raw user input."""
    if raw is None:
        raise ValidationError(f"{field_name} is required.")
    try:
        value = Decimal(str(raw).strip())
    except (InvalidOperation, AttributeError) as exc:
        raise ValidationError(f"{field_name} must be a number.") from exc
    if not value.is_finite():
        raise ValidationError(f"{field_name} must be a finite number.")
    if value <= 0:
        raise ValidationError(f"{field_name} must be positive.")
    return value


def validate_quantity(raw: object) -> Decimal:
    """Validate order quantity."""
    return parse_positive_decimal(raw, "Quantity")


def validate_price(order_type: OrderType, raw: object) -> Decimal | None:
    """Validate order price according to order type."""
    if order_type is OrderType.MARKET:
        if raw is None or str(raw).strip() == "":
            return None
        raise ValidationError("Price must not be provided for MARKET orders.")
    return parse_positive_decimal(raw, "Price")


def parse_symbol_rules(
    exchange_info: dict[str, Any],
    symbol: str,
    order_type: OrderType | None = None,
) -> SymbolRules:
    """Extract validation rules for one symbol from Binance exchangeInfo."""
    normalized_symbol = validate_symbol(symbol)
    symbol_info = _find_symbol_info(exchange_info, normalized_symbol)

    filters = {
        item.get("filterType"): item
        for item in symbol_info.get("filters", [])
        if isinstance(item, dict)
    }
    lot_filter = _select_lot_filter(filters, order_type)
    price_filter = filters.get("PRICE_FILTER", {})
    notional_filter = filters.get("MIN_NOTIONAL") or filters.get("NOTIONAL") or {}

    return SymbolRules(
        symbol=normalized_symbol,
        status=str(symbol_info.get("status", "")),
        order_types=frozenset(str(item) for item in symbol_info.get("orderTypes", [])),
        time_in_force=frozenset(str(item) for item in symbol_info.get("timeInForce", [])),
        min_qty=_positive_decimal_or_none(lot_filter.get("minQty")),
        max_qty=_positive_decimal_or_none(lot_filter.get("maxQty")),
        step_size=_positive_decimal_or_none(lot_filter.get("stepSize")),
        min_price=_positive_decimal_or_none(price_filter.get("minPrice")),
        max_price=_positive_decimal_or_none(price_filter.get("maxPrice")),
        tick_size=_positive_decimal_or_none(price_filter.get("tickSize")),
        min_notional=_positive_decimal_or_none(
            notional_filter.get("notional") or notional_filter.get("minNotional")
        ),
    )


def validate_against_symbol_rules(order: OrderRequest, rules: SymbolRules) -> None:
    """Validate a built order against exchange rules for its symbol."""
    if order.symbol != rules.symbol:
        raise ExchangeRuleError(
            f"Order symbol {order.symbol} does not match rules for {rules.symbol}."
        )
    if rules.status != "TRADING":
        raise ExchangeRuleError(
            f"Symbol {rules.symbol} is not trading; current status is {rules.status}."
        )
    if order.order_type.value not in rules.order_types:
        raise ExchangeRuleError(
            f"{order.order_type.value} orders are not supported for {rules.symbol}."
        )
    if order.order_type is OrderType.LIMIT and LIMIT_TIME_IN_FORCE not in rules.time_in_force:
        raise ExchangeRuleError(
            f"{LIMIT_TIME_IN_FORCE} time in force is not supported for {rules.symbol}."
        )

    _validate_decimal_bounds(order.quantity, "Quantity", rules.min_qty, rules.max_qty)
    _validate_increment(order.quantity, "Quantity", rules.step_size)

    if order.order_type is OrderType.LIMIT:
        if order.price is None:
            raise ExchangeRuleError("LIMIT orders require a price.")
        _validate_decimal_bounds(order.price, "Price", rules.min_price, rules.max_price)
        _validate_increment(order.price, "Price", rules.tick_size)
        _validate_min_notional(order.quantity, order.price, rules.min_notional)


def _find_symbol_info(exchange_info: dict[str, Any], symbol: str) -> dict[str, Any]:
    for item in exchange_info.get("symbols", []):
        if isinstance(item, dict) and item.get("symbol") == symbol:
            return item
    raise ExchangeRuleError(f"Symbol {symbol} was not found in Binance exchange info.")


def _select_lot_filter(
    filters: dict[str | None, dict[str, Any]],
    order_type: OrderType | None,
) -> dict[str, Any]:
    if order_type is OrderType.MARKET and filters.get("MARKET_LOT_SIZE"):
        return filters["MARKET_LOT_SIZE"]
    return filters.get("LOT_SIZE") or filters.get("MARKET_LOT_SIZE") or {}


def _positive_decimal_or_none(raw: object) -> Decimal | None:
    if raw is None:
        return None
    try:
        value = Decimal(str(raw))
    except InvalidOperation:
        return None
    if not value.is_finite() or value <= 0:
        return None
    return value


def _validate_decimal_bounds(
    value: Decimal,
    field_name: str,
    minimum: Decimal | None,
    maximum: Decimal | None,
) -> None:
    if minimum is not None and value < minimum:
        raise ExchangeRuleError(f"{field_name} must be at least {minimum}.")
    if maximum is not None and value > maximum:
        raise ExchangeRuleError(f"{field_name} must be at most {maximum}.")


def _validate_increment(value: Decimal, field_name: str, increment: Decimal | None) -> None:
    if increment is None:
        return
    if value % increment != 0:
        raise ExchangeRuleError(f"{field_name} must be a multiple of {increment}.")


def _validate_min_notional(
    quantity: Decimal,
    price: Decimal,
    min_notional: Decimal | None,
) -> None:
    if min_notional is None:
        return
    if quantity * price < min_notional:
        raise ExchangeRuleError(f"Order notional must be at least {min_notional}.")
