"""Typer command-line interface for the trading bot."""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Annotated, Any

import typer
from rich.console import Console

from .client import BinanceFuturesClient
from .config import Settings, load_settings
from .exceptions import TradingBotError
from .formatting import (
    json_error_payload,
    json_success_payload,
    print_error,
    print_order_response,
    print_order_summary,
    print_success,
)
from .models import OrderRequest, OrderType
from .orders import build_order_request
from .validators import parse_symbol_rules, validate_against_symbol_rules, validate_order_type

EPILOG = """
Examples:

  python -m trading_bot place BTCUSDT BUY MARKET 0.001 --dry-run
  python -m trading_bot place ETHUSDT SELL LIMIT 0.02 --price 2500 --yes
  python -m trading_bot interactive
"""

app = typer.Typer(
    help="Place MARKET and LIMIT orders on Binance USDT-M Futures Testnet.",
    epilog=EPILOG,
    no_args_is_help=True,
)
console = Console()


@app.command()
def place(
    symbol: Annotated[str, typer.Argument(help="Trading pair, e.g. BTCUSDT.")],
    side: Annotated[str, typer.Argument(help="BUY or SELL.")],
    order_type: Annotated[str, typer.Argument(help="MARKET or LIMIT.")],
    quantity: Annotated[str, typer.Argument(help="Order quantity.")],
    price: Annotated[
        str | None,
        typer.Option("--price", "-p", help="Required for LIMIT orders."),
    ] = None,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation for real order placement."),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Validate with Binance without placing an order."),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON only."),
    ] = False,
    base_url: Annotated[
        str | None,
        typer.Option("--base-url", help="Override Binance base URL."),
    ] = None,
) -> None:
    """Validate and submit one MARKET or LIMIT order."""
    try:
        result = run_place(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            yes=yes,
            dry_run=dry_run,
            json_output=json_output,
            base_url=base_url,
        )
    except TradingBotError as exc:
        _handle_error(exc, json_output)
        raise typer.Exit(1) from exc

    if json_output:
        console.print(json.dumps(result, sort_keys=True))


@app.command()
def interactive(
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation for real order placement."),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Validate with Binance without placing an order."),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON only."),
    ] = False,
    base_url: Annotated[
        str | None,
        typer.Option("--base-url", help="Override Binance base URL."),
    ] = None,
) -> None:
    """Collect order fields interactively, then use the same validation path."""
    try:
        symbol = typer.prompt("Symbol")
        side = typer.prompt("Side [BUY/SELL]")
        raw_order_type = typer.prompt("Order type [MARKET/LIMIT]")
        quantity = typer.prompt("Quantity")
        normalized_order_type = validate_order_type(raw_order_type)
        price = None
        if normalized_order_type is OrderType.LIMIT:
            price = typer.prompt("Price")

        result = run_place(
            symbol=symbol,
            side=side,
            order_type=raw_order_type,
            quantity=quantity,
            price=price,
            yes=yes,
            dry_run=dry_run,
            json_output=json_output,
            base_url=base_url,
        )
    except TradingBotError as exc:
        _handle_error(exc, json_output)
        raise typer.Exit(1) from exc

    if json_output:
        console.print(json.dumps(result, sort_keys=True))


def run_place(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: str | None,
    yes: bool,
    dry_run: bool,
    json_output: bool,
    base_url: str | None = None,
) -> dict[str, Any]:
    """Shared execution path for flag and interactive modes."""
    settings = _load_cli_settings(base_url)
    client = BinanceFuturesClient.from_settings(settings)

    try:
        order = build_order_request(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
        )
        exchange_info = client.get_exchange_info()
        rules = parse_symbol_rules(exchange_info, order.symbol, order.order_type)
        validate_against_symbol_rules(order, rules)

        if not json_output:
            print_order_summary(console, order)

        if not dry_run and not yes and not _confirm_real_order(order):
            raise typer.Abort()

        response = client.test_order(order) if dry_run else client.place_order(order)

        if not json_output:
            print_order_response(console, response)
            message = "Test order accepted by Binance." if dry_run else "Order placed on Binance."
            print_success(console, message)

        return json_success_payload(order, response, dry_run)
    finally:
        client.close()


def _load_cli_settings(base_url: str | None) -> Settings:
    settings = load_settings()
    if base_url is None:
        return settings
    return replace(settings, base_url=base_url.rstrip("/"))


def _confirm_real_order(order: OrderRequest) -> bool:
    return typer.confirm(
        f"Submit {order.side.value} {order.order_type.value} order for {order.symbol}?"
    )


def _handle_error(exc: TradingBotError, json_output: bool) -> None:
    if json_output:
        console.print(json.dumps(json_error_payload(str(exc)), sort_keys=True))
    else:
        print_error(console, str(exc))
