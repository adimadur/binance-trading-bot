from decimal import Decimal

import pytest

from trading_bot.exceptions import ExchangeRuleError, ValidationError
from trading_bot.models import OrderSide, OrderType, SymbolRules
from trading_bot.orders import build_order_request, format_decimal, serialize_order_payload


def symbol_rules():
    return SymbolRules(
        symbol="BTCUSDT",
        status="TRADING",
        order_types=frozenset({"MARKET", "LIMIT"}),
        time_in_force=frozenset({"GTC"}),
        min_qty=Decimal("0.001"),
        max_qty=Decimal("100"),
        step_size=Decimal("0.001"),
        min_price=Decimal("100"),
        max_price=Decimal("1000000"),
        tick_size=Decimal("0.10"),
        min_notional=Decimal("5"),
    )


def test_build_order_request_creates_market_order():
    order = build_order_request("btcusdt", "buy", "market", "0.001", rules=symbol_rules())

    assert order.symbol == "BTCUSDT"
    assert order.side is OrderSide.BUY
    assert order.order_type is OrderType.MARKET
    assert order.quantity == Decimal("0.001")
    assert order.price is None
    assert order.time_in_force is None
    assert order.new_order_resp_type == "RESULT"


def test_build_order_request_creates_limit_order_with_gtc():
    order = build_order_request("ETHUSDT", "SELL", "LIMIT", "0.02", "2500")

    assert order.symbol == "ETHUSDT"
    assert order.side is OrderSide.SELL
    assert order.order_type is OrderType.LIMIT
    assert order.quantity == Decimal("0.02")
    assert order.price == Decimal("2500")
    assert order.time_in_force == "GTC"
    assert order.new_order_resp_type == "RESULT"


def test_build_order_request_rejects_invalid_input_before_rules():
    with pytest.raises(ValidationError):
        build_order_request("BTCUSDT", "BUY", "LIMIT", "0.01")


def test_build_order_request_applies_exchange_rules():
    with pytest.raises(ExchangeRuleError):
        build_order_request("BTCUSDT", "BUY", "MARKET", "0.0015", rules=symbol_rules())


def test_serialize_market_order_payload():
    order = build_order_request("BTCUSDT", "BUY", "MARKET", "0.001")

    assert serialize_order_payload(order) == {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "type": "MARKET",
        "quantity": "0.001",
        "newOrderRespType": "RESULT",
    }


def test_serialize_limit_order_payload():
    order = build_order_request("BTCUSDT", "SELL", "LIMIT", "0.0200", "2500.10")

    assert serialize_order_payload(order) == {
        "symbol": "BTCUSDT",
        "side": "SELL",
        "type": "LIMIT",
        "quantity": "0.0200",
        "price": "2500.10",
        "timeInForce": "GTC",
        "newOrderRespType": "RESULT",
    }


def test_format_decimal_avoids_scientific_notation():
    assert format_decimal(Decimal("1E-8")) == "0.00000001"

