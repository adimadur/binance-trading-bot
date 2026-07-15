"""Order construction and Binance payload serialization."""

from __future__ import annotations

from decimal import Decimal

from .models import OrderRequest, SymbolRules
from .validators import (
    LIMIT_TIME_IN_FORCE,
    validate_against_symbol_rules,
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_symbol,
)


def build_order_request(
    symbol: object,
    side: object,
    order_type: object,
    quantity: object,
    price: object = None,
    rules: SymbolRules | None = None,
) -> OrderRequest:
    """Build and optionally exchange-rule-validate an order request."""
    normalized_order_type = validate_order_type(order_type)
    request = OrderRequest(
        symbol=validate_symbol(symbol),
        side=validate_side(side),
        order_type=normalized_order_type,
        quantity=validate_quantity(quantity),
        price=validate_price(normalized_order_type, price),
        time_in_force=LIMIT_TIME_IN_FORCE if normalized_order_type.value == "LIMIT" else None,
        new_order_resp_type="RESULT",
    )

    if rules is not None:
        validate_against_symbol_rules(request, rules)

    return request


def serialize_order_payload(order: OrderRequest) -> dict[str, str]:
    """Serialize an order request to Binance REST parameter names."""
    payload = {
        "symbol": order.symbol,
        "side": order.side.value,
        "type": order.order_type.value,
        "quantity": format_decimal(order.quantity),
        "newOrderRespType": order.new_order_resp_type,
    }
    if order.price is not None:
        payload["price"] = format_decimal(order.price)
    if order.time_in_force is not None:
        payload["timeInForce"] = order.time_in_force
    return payload


def format_decimal(value: Decimal) -> str:
    """Format a decimal without scientific notation."""
    return format(value, "f")

