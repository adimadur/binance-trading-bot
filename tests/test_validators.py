from decimal import Decimal

import pytest

from trading_bot.exceptions import ExchangeRuleError, ValidationError
from trading_bot.models import OrderRequest, OrderSide, OrderType
from trading_bot.validators import (
    parse_symbol_rules,
    validate_against_symbol_rules,
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_symbol,
)


def exchange_info(**overrides):
    symbol_info = {
        "symbol": "BTCUSDT",
        "status": "TRADING",
        "orderTypes": ["LIMIT", "MARKET"],
        "timeInForce": ["GTC", "IOC", "FOK"],
        "filters": [
            {
                "filterType": "LOT_SIZE",
                "minQty": "0.001",
                "maxQty": "100",
                "stepSize": "0.001",
            },
            {
                "filterType": "MARKET_LOT_SIZE",
                "minQty": "0.001",
                "maxQty": "200",
                "stepSize": "0.001",
            },
            {
                "filterType": "PRICE_FILTER",
                "minPrice": "100",
                "maxPrice": "1000000",
                "tickSize": "0.10",
            },
            {"filterType": "MIN_NOTIONAL", "notional": "5"},
        ],
    }
    symbol_info.update(overrides)
    return {"symbols": [symbol_info]}


def market_order(quantity="0.010"):
    return OrderRequest(
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal(quantity),
    )


def limit_order(quantity="0.010", price="50000.10"):
    return OrderRequest(
        symbol="BTCUSDT",
        side=OrderSide.SELL,
        order_type=OrderType.LIMIT,
        quantity=Decimal(quantity),
        price=Decimal(price),
        time_in_force="GTC",
    )


def test_static_validators_normalize_valid_values():
    assert validate_symbol("btcusdt") == "BTCUSDT"
    assert validate_side("buy") is OrderSide.BUY
    assert validate_order_type("limit") is OrderType.LIMIT
    assert validate_quantity("0.001") == Decimal("0.001")
    assert validate_price(OrderType.LIMIT, "50000.10") == Decimal("50000.10")
    assert validate_price(OrderType.MARKET, None) is None


@pytest.mark.parametrize("raw", ["", "BTC-USDT", "BTC/USDT", None])
def test_validate_symbol_rejects_invalid_symbols(raw):
    with pytest.raises(ValidationError):
        validate_symbol(raw)


@pytest.mark.parametrize("raw", ["HOLD", "", None])
def test_validate_side_rejects_invalid_sides(raw):
    with pytest.raises(ValidationError):
        validate_side(raw)


@pytest.mark.parametrize("raw", ["STOP", "", None])
def test_validate_order_type_rejects_invalid_types(raw):
    with pytest.raises(ValidationError):
        validate_order_type(raw)


@pytest.mark.parametrize("raw", ["0", "-1", "abc", None])
def test_validate_quantity_rejects_invalid_values(raw):
    with pytest.raises(ValidationError):
        validate_quantity(raw)


def test_validate_price_rejects_market_price():
    with pytest.raises(ValidationError):
        validate_price(OrderType.MARKET, "100")


@pytest.mark.parametrize("raw", ["0", "-1", "abc", None])
def test_validate_price_rejects_invalid_limit_prices(raw):
    with pytest.raises(ValidationError):
        validate_price(OrderType.LIMIT, raw)


def test_parse_symbol_rules_extracts_filters():
    rules = parse_symbol_rules(exchange_info(), "btcusdt", OrderType.LIMIT)

    assert rules.symbol == "BTCUSDT"
    assert rules.status == "TRADING"
    assert rules.order_types == frozenset({"LIMIT", "MARKET"})
    assert rules.time_in_force == frozenset({"GTC", "IOC", "FOK"})
    assert rules.min_qty == Decimal("0.001")
    assert rules.max_qty == Decimal("100")
    assert rules.step_size == Decimal("0.001")
    assert rules.min_price == Decimal("100")
    assert rules.max_price == Decimal("1000000")
    assert rules.tick_size == Decimal("0.10")
    assert rules.min_notional == Decimal("5")


def test_parse_symbol_rules_uses_market_lot_size_for_market_orders():
    info = exchange_info(
        filters=[
            {
                "filterType": "LOT_SIZE",
                "minQty": "0.001",
                "maxQty": "100",
                "stepSize": "0.001",
            },
            {
                "filterType": "MARKET_LOT_SIZE",
                "minQty": "0.010",
                "maxQty": "10",
                "stepSize": "0.010",
            },
        ]
    )

    rules = parse_symbol_rules(info, "BTCUSDT", OrderType.MARKET)

    assert rules.min_qty == Decimal("0.010")
    assert rules.max_qty == Decimal("10")
    assert rules.step_size == Decimal("0.010")


def test_parse_symbol_rules_rejects_unknown_symbol():
    with pytest.raises(ExchangeRuleError):
        parse_symbol_rules(exchange_info(), "ETHUSDT", OrderType.LIMIT)


def test_validate_against_symbol_rules_accepts_valid_market_and_limit_orders():
    market_rules = parse_symbol_rules(exchange_info(), "BTCUSDT", OrderType.MARKET)
    limit_rules = parse_symbol_rules(exchange_info(), "BTCUSDT", OrderType.LIMIT)

    validate_against_symbol_rules(market_order(), market_rules)
    validate_against_symbol_rules(limit_order(), limit_rules)


def test_validate_against_symbol_rules_rejects_non_trading_symbol():
    rules = parse_symbol_rules(exchange_info(status="BREAK"), "BTCUSDT", OrderType.MARKET)

    with pytest.raises(ExchangeRuleError):
        validate_against_symbol_rules(market_order(), rules)


def test_validate_against_symbol_rules_rejects_unsupported_order_type():
    rules = parse_symbol_rules(exchange_info(orderTypes=["LIMIT"]), "BTCUSDT", OrderType.MARKET)

    with pytest.raises(ExchangeRuleError):
        validate_against_symbol_rules(market_order(), rules)


def test_validate_against_symbol_rules_rejects_missing_gtc_for_limit_order():
    rules = parse_symbol_rules(exchange_info(timeInForce=["IOC"]), "BTCUSDT", OrderType.LIMIT)

    with pytest.raises(ExchangeRuleError):
        validate_against_symbol_rules(limit_order(), rules)


@pytest.mark.parametrize("quantity", ["0.0009", "200.001", "0.0015"])
def test_validate_against_symbol_rules_rejects_invalid_quantities(quantity):
    rules = parse_symbol_rules(exchange_info(), "BTCUSDT", OrderType.MARKET)

    with pytest.raises(ExchangeRuleError):
        validate_against_symbol_rules(market_order(quantity), rules)


@pytest.mark.parametrize("price", ["99.90", "1000000.10", "50000.15"])
def test_validate_against_symbol_rules_rejects_invalid_limit_prices(price):
    rules = parse_symbol_rules(exchange_info(), "BTCUSDT", OrderType.LIMIT)

    with pytest.raises(ExchangeRuleError):
        validate_against_symbol_rules(limit_order(price=price), rules)


def test_validate_against_symbol_rules_rejects_min_notional_failure():
    rules = parse_symbol_rules(exchange_info(), "BTCUSDT", OrderType.LIMIT)

    with pytest.raises(ExchangeRuleError):
        validate_against_symbol_rules(limit_order(quantity="0.001", price="100"), rules)
