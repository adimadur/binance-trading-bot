"""Console and JSON formatting helpers for the CLI."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from rich.console import Console
from rich.table import Table

from .logging_config import LOG_FILE
from .models import OrderRequest
from .orders import format_decimal


def order_request_to_dict(order: OrderRequest) -> dict[str, str | None]:
    """Convert an order request into display/JSON-friendly values."""
    return {
        "symbol": order.symbol,
        "side": order.side.value,
        "order_type": order.order_type.value,
        "quantity": format_decimal(order.quantity),
        "price": format_decimal(order.price) if order.price is not None else None,
    }


def response_summary(response: dict[str, Any]) -> dict[str, Any]:
    """Extract assignment-required response fields from Binance response data."""
    return {
        "orderId": response.get("orderId", "N/A"),
        "status": response.get("status", "ACCEPTED" if response == {} else "N/A"),
        "executedQty": response.get("executedQty", "N/A"),
        "avgPrice": response.get("avgPrice") or "N/A",
    }


def json_success_payload(
    order: OrderRequest,
    response: dict[str, Any],
    dry_run: bool,
) -> dict[str, Any]:
    """Build the successful machine-readable CLI response."""
    return {
        "ok": True,
        "dry_run": dry_run,
        "request": order_request_to_dict(order),
        "response": response_summary(response),
    }


def json_error_payload(error: str) -> dict[str, Any]:
    """Build the failed machine-readable CLI response."""
    return {"ok": False, "error": error, "log_file": str(LOG_FILE)}


def print_order_summary(console: Console, order: OrderRequest) -> None:
    """Print an order summary table."""
    table = Table(title="Order Summary", show_header=True, header_style="bold cyan")
    table.add_column("Field")
    table.add_column("Value")

    for key, value in order_request_to_dict(order).items():
        if value is not None:
            table.add_row(key, value)

    console.print(table)


def print_order_response(console: Console, response: dict[str, Any]) -> None:
    """Print the required Binance response summary fields."""
    table = Table(title="Order Response", show_header=True, header_style="bold cyan")
    table.add_column("Field")
    table.add_column("Value")

    for key, value in response_summary(response).items():
        table.add_row(key, _stringify(value))

    console.print(table)


def print_success(console: Console, message: str) -> None:
    """Print a success message."""
    console.print(f"[bold green]SUCCESS:[/bold green] {message}")


def print_error(console: Console, message: str) -> None:
    """Print an error message."""
    console.print(f"[bold red]FAILED:[/bold red] {message}")
    console.print(f"See log file for details: {LOG_FILE}")


def _stringify(value: Any) -> str:
    if isinstance(value, Decimal):
        return format_decimal(value)
    return str(value)

