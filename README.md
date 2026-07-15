# Binance Futures Testnet Trading Bot

A small production-style Python CLI for placing `MARKET` and `LIMIT` orders on
Binance USDT-M Futures Testnet.

The implementation uses direct REST calls with `httpx`, HMAC SHA256 request
signing, exchange-rule validation, `Decimal`-based numeric handling, structured
logging, and a Typer/Rich command-line interface.

## Safety

This project is configured for Binance Futures Testnet only:

```text
https://testnet.binancefuture.com
```

Do not use live Binance API keys with this project.

## Setup

1. Create Binance Futures Testnet API keys.
   - Open https://testnet.binancefuture.com
   - Sign in.
   - Create an HMAC API key and secret.

2. Create and activate a virtual environment.

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install the project.

   ```bash
   python -m pip install -e ".[dev]"
   ```

   Alternatively, install runtime dependencies only:

   ```bash
   python -m pip install -r requirements.txt
   ```

4. Configure credentials.

   ```bash
   cp .env.example .env
   ```

   Edit `.env`:

   ```text
   BINANCE_TESTNET_API_KEY=your_api_key_here
   BINANCE_TESTNET_API_SECRET=your_api_secret_here
   BINANCE_BASE_URL=https://testnet.binancefuture.com
   BINANCE_RECV_WINDOW=5000
   ```

## Usage

Show help:

```bash
python -m trading_bot --help
python -m trading_bot place --help
```

Dry-run a market order without placing it:

```bash
python -m trading_bot place BTCUSDT BUY MARKET 0.001 --dry-run --yes
```

Dry-run a limit order:

```bash
python -m trading_bot place ETHUSDT SELL LIMIT 0.01 --price 2500 --dry-run --yes
```

Place a real testnet market order:

```bash
python -m trading_bot place BTCUSDT BUY MARKET 0.001 --yes
```

Place a real testnet limit order:

```bash
python -m trading_bot place ETHUSDT SELL LIMIT 0.01 --price 2500 --yes
```

Use interactive mode:

```bash
python -m trading_bot interactive
```

Emit JSON output:

```bash
python -m trading_bot place BTCUSDT BUY MARKET 0.001 --dry-run --json
```

## Output

Human output includes:

- Order summary: symbol, side, order type, quantity, and price when applicable.
- Order response: `orderId`, `status`, `executedQty`, and `avgPrice` when available.
- Final success or failure message.

JSON output returns:

```json
{
  "ok": true,
  "dry_run": true,
  "request": {
    "symbol": "BTCUSDT",
    "side": "BUY",
    "order_type": "MARKET",
    "quantity": "0.001",
    "price": null
  },
  "response": {
    "orderId": "N/A",
    "status": "ACCEPTED",
    "executedQty": "N/A",
    "avgPrice": "N/A"
  }
}
```

## Logging

Logs are written to:

```text
logs/trading_bot.log
```

The log records Binance request, response, and error events. API keys and
signatures are redacted. The committed log file demonstrates successful testnet
MARKET and LIMIT order placement.

## Validation

The CLI validates:

- Symbol format.
- Side: `BUY` or `SELL`.
- Order type: `MARKET` or `LIMIT`.
- Positive `Decimal` quantity and price values.
- Binance exchange rules from `/fapi/v1/exchangeInfo`, including trading status,
  supported order types, quantity step size, price tick size, and notional limits
  when provided.

## Assumptions

- USDT-M Futures only.
- Binance Futures Testnet only.
- `MARKET` and `LIMIT` orders only.
- `LIMIT` orders use `GTC`.
- The app uses direct REST calls instead of `python-binance`.
- Credentials are loaded from environment variables or `.env`.

## Troubleshooting

- Missing credentials: verify `.env` contains `BINANCE_TESTNET_API_KEY` and
  `BINANCE_TESTNET_API_SECRET`.
- Invalid symbol: use a USDT-M Futures symbol such as `BTCUSDT` or `ETHUSDT`.
- Precision failures: choose quantities and prices that match Binance step size
  and tick size.
- Insufficient testnet balance: add testnet funds or reduce quantity.
- Timestamp or `recvWindow` errors: ensure system time is correct, or increase
  `BINANCE_RECV_WINDOW`.
- Binance 5xx errors: Futures Testnet can be unstable; retry after a short wait.

## Development Checks

```bash
python -m pytest
python -m ruff check .
python -m compileall trading_bot
```

