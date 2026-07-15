import json

from typer.testing import CliRunner

from trading_bot import cli
from trading_bot.config import Settings

runner = CliRunner()


def exchange_info():
    return {
        "symbols": [
            {
                "symbol": "BTCUSDT",
                "status": "TRADING",
                "orderTypes": ["MARKET", "LIMIT"],
                "timeInForce": ["GTC"],
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
                        "maxQty": "100",
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
        ]
    }


class FakeClient:
    instances = []
    exchange_info_payload = exchange_info()
    test_response = {}
    place_response = {
        "orderId": 123,
        "status": "NEW",
        "executedQty": "0.000",
        "avgPrice": "0.00",
    }

    def __init__(self, settings):
        self.settings = settings
        self.calls = []
        self.closed = False
        self.orders = []

    @classmethod
    def from_settings(cls, settings):
        instance = cls(settings)
        cls.instances.append(instance)
        return instance

    def get_exchange_info(self):
        self.calls.append("get_exchange_info")
        return self.exchange_info_payload

    def test_order(self, order):
        self.calls.append("test_order")
        self.orders.append(order)
        return self.test_response

    def place_order(self, order):
        self.calls.append("place_order")
        self.orders.append(order)
        return self.place_response

    def close(self):
        self.closed = True


def patch_cli(monkeypatch):
    FakeClient.instances = []
    FakeClient.exchange_info_payload = exchange_info()
    FakeClient.test_response = {}
    FakeClient.place_response = {
        "orderId": 123,
        "status": "NEW",
        "executedQty": "0.000",
        "avgPrice": "0.00",
    }
    monkeypatch.setattr(
        cli,
        "load_settings",
        lambda: Settings(api_key="key", api_secret="secret"),
    )
    monkeypatch.setattr(cli, "BinanceFuturesClient", FakeClient)


def test_root_help_shows_commands():
    result = runner.invoke(cli.app, ["--help"])

    assert result.exit_code == 0
    assert "place" in result.output
    assert "interactive" in result.output


def test_place_help_shows_options():
    result = runner.invoke(cli.app, ["place", "--help"])

    assert result.exit_code == 0
    assert "--dry-run" in result.output
    assert "--json" in result.output
    assert "--price" in result.output


def test_valid_dry_run_command_uses_test_order(monkeypatch):
    patch_cli(monkeypatch)

    result = runner.invoke(cli.app, ["place", "BTCUSDT", "BUY", "MARKET", "0.001", "--dry-run"])

    assert result.exit_code == 0
    assert "SUCCESS" in result.output
    assert FakeClient.instances[0].calls == ["get_exchange_info", "test_order"]
    assert FakeClient.instances[0].closed is True


def test_missing_limit_price_exits_nonzero(monkeypatch):
    patch_cli(monkeypatch)

    result = runner.invoke(cli.app, ["place", "BTCUSDT", "BUY", "LIMIT", "0.001"])

    assert result.exit_code == 1
    assert "Price is required" in result.output
    assert FakeClient.instances[0].calls == []


def test_invalid_side_exits_nonzero(monkeypatch):
    patch_cli(monkeypatch)

    result = runner.invoke(cli.app, ["place", "BTCUSDT", "HOLD", "MARKET", "0.001"])

    assert result.exit_code == 1
    assert "Side must be one of" in result.output
    assert FakeClient.instances[0].calls == []


def test_invalid_order_type_exits_nonzero(monkeypatch):
    patch_cli(monkeypatch)

    result = runner.invoke(cli.app, ["place", "BTCUSDT", "BUY", "STOP", "0.001"])

    assert result.exit_code == 1
    assert "Order type must be one of" in result.output
    assert FakeClient.instances[0].calls == []


def test_json_dry_run_outputs_valid_json(monkeypatch):
    patch_cli(monkeypatch)

    result = runner.invoke(
        cli.app,
        ["place", "BTCUSDT", "BUY", "MARKET", "0.001", "--dry-run", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["dry_run"] is True
    assert payload["request"]["symbol"] == "BTCUSDT"
    assert payload["response"]["status"] == "ACCEPTED"


def test_real_order_confirmation_decline_does_not_place_order(monkeypatch):
    patch_cli(monkeypatch)

    result = runner.invoke(cli.app, ["place", "BTCUSDT", "BUY", "MARKET", "0.001"], input="n\n")

    assert result.exit_code == 1
    assert FakeClient.instances[0].calls == ["get_exchange_info"]


def test_real_order_with_yes_places_order(monkeypatch):
    patch_cli(monkeypatch)

    result = runner.invoke(cli.app, ["place", "BTCUSDT", "BUY", "MARKET", "0.001", "--yes"])

    assert result.exit_code == 0
    assert "SUCCESS" in result.output
    assert FakeClient.instances[0].calls == ["get_exchange_info", "place_order"]


def test_interactive_uses_same_execution_path(monkeypatch):
    patch_cli(monkeypatch)

    result = runner.invoke(
        cli.app,
        ["interactive", "--dry-run"],
        input="BTCUSDT\nBUY\nMARKET\n0.001\n",
    )

    assert result.exit_code == 0
    assert "SUCCESS" in result.output
    assert FakeClient.instances[0].calls == ["get_exchange_info", "test_order"]

