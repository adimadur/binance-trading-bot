from decimal import Decimal

from trading_bot.config import DEFAULT_BASE_URL, load_settings
from trading_bot.logging_config import REDACTED, redact_sensitive_fields, setup_logging
from trading_bot.models import OrderRequest, OrderSide, OrderType, SymbolRules


def test_load_settings_from_env_file(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "BINANCE_TESTNET_API_KEY=test-key",
                "BINANCE_TESTNET_API_SECRET=test-secret",
                "BINANCE_RECV_WINDOW=7000",
            ]
        ),
        encoding="utf-8",
    )

    settings = load_settings(env_file)

    assert settings.api_key == "test-key"
    assert settings.api_secret == "test-secret"
    assert settings.base_url == DEFAULT_BASE_URL
    assert settings.recv_window == 7000


def test_redact_sensitive_fields_recursively():
    payload = {
        "apiKey": "key",
        "signature": "signature",
        "nested": {"api_secret": "secret", "safe": "value"},
    }

    assert redact_sensitive_fields(payload) == {
        "apiKey": REDACTED,
        "signature": REDACTED,
        "nested": {"api_secret": REDACTED, "safe": "value"},
    }


def test_setup_logging_creates_log_file(tmp_path):
    log_file = tmp_path / "logs" / "trading_bot.log"

    logger = setup_logging(log_file)
    logger.info("foundation log test")

    assert log_file.exists()


def test_core_models_use_decimal_values():
    order = OrderRequest(
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("0.001"),
    )
    rules = SymbolRules(
        symbol="BTCUSDT",
        status="TRADING",
        order_types=frozenset({"MARKET", "LIMIT"}),
        time_in_force=frozenset({"GTC"}),
        min_qty=Decimal("0.001"),
        step_size=Decimal("0.001"),
    )

    assert order.quantity == Decimal("0.001")
    assert rules.min_qty == Decimal("0.001")
    assert rules.step_size == Decimal("0.001")

