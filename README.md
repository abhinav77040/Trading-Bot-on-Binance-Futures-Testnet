# Binance Futures Testnet – Trading Bot

A clean, production-grade Python CLI for placing orders on the **Binance USDT-M Futures Testnet**.  
Supports Market, Limit, and Stop-Limit orders with full logging and structured error handling.

---

## Features

| Feature | Detail |
|---|---|
| Order types | `MARKET`, `LIMIT`, `STOP_LIMIT` (Stop-Limit) |
| Sides | `BUY`, `SELL` |
| Input validation | Symbol, side, type, quantity, price, stop-price cross-checks |
| Logging | Rotating file log (`logs/trading_bot.log`) + console |
| Error handling | API errors, network failures, bad input – all handled gracefully |
| Structure | Separate client / orders / validators / CLI layers |
| No heavy deps | Only `requests` + stdlib |

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # package exports
│   ├── client.py            # Binance REST client (signing, retries, logging)
│   ├── orders.py            # order placement + pretty-print layer
│   ├── validators.py        # input validation
│   └── logging_config.py   # rotating file + console logging setup
├── cli.py                   # argparse CLI entry point
├── logs/
│   └── trading_bot.log      # auto-created; sample included in repo
├── README.md
└── requirements.txt
```

---

## Setup

### 1 – Prerequisites

- Python 3.8+
- A Binance Futures Testnet account

### 2 – Get Testnet API Credentials

1. Visit **https://testnet.binancefuture.com**
2. Log in (GitHub OAuth) → click **API Key**
3. Copy your **API Key** and **Secret Key**

### 3 – Install Dependencies

```bash
git clone <your-repo-url>
cd trading_bot

python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 4 – Set Credentials

**Option A – Environment variables (recommended)**

```bash
export BINANCE_API_KEY="your_api_key_here"
export BINANCE_API_SECRET="your_api_secret_here"
```

**Option B – CLI flags** (see examples below)

---

## How to Run

### General syntax

```bash
python cli.py [CREDENTIALS] --symbol SYMBOL --side SIDE --type TYPE --quantity QTY [OPTIONS]
```

### Place a Market BUY

```bash
python cli.py \
  --symbol BTCUSDT \
  --side   BUY \
  --type   MARKET \
  --quantity 0.001
```

### Place a Limit SELL

```bash
python cli.py \
  --symbol   ETHUSDT \
  --side     SELL \
  --type     LIMIT \
  --quantity 0.05 \
  --price    3420
```

### Place a Stop-Limit BUY (bonus order type)

```bash
python cli.py \
  --symbol     BTCUSDT \
  --side       BUY \
  --type       STOP_LIMIT \
  --quantity   0.001 \
  --price      65000 \
  --stop-price 64500
```

### Pass credentials as CLI flags

```bash
python cli.py \
  --api-key    "YOUR_KEY" \
  --api-secret "YOUR_SECRET" \
  --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

### Quiet mode (no stdout, logs still written)

```bash
python cli.py --quiet --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

---

## CLI Reference

| Flag | Required | Description |
|---|---|---|
| `--symbol` / `-s` | ✅ | Futures symbol, e.g. `BTCUSDT` |
| `--side` | ✅ | `BUY` or `SELL` |
| `--type` / `-t` | ✅ | `MARKET`, `LIMIT`, or `STOP_LIMIT` |
| `--quantity` / `-q` | ✅ | Base asset quantity |
| `--price` / `-p` | LIMIT / STOP_LIMIT | Limit price |
| `--stop-price` | STOP_LIMIT | Stop trigger price |
| `--tif` | No | Time-in-force: `GTC` (default), `IOC`, `FOK` |
| `--api-key` | No* | Binance API key (or env var) |
| `--api-secret` | No* | Binance API secret (or env var) |
| `--base-url` | No | Override base URL (default: testnet) |
| `--quiet` | No | Suppress stdout output |

\* Required via env var or flag.

---

## Sample Output

```
╔══════════════════════════════════════════════════════════╗
║        Binance Futures Testnet  –  Trading Bot           ║
║        USDT-M Perpetuals   |   Python 3.x                ║
╚══════════════════════════════════════════════════════════╝

════════════════════════════════════════════════════════════
  ORDER REQUEST SUMMARY
════════════════════════════════════════════════════════════
  Symbol     : BTCUSDT
  Side       : BUY
  Type       : MARKET
  Quantity   : 0.001
────────────────────────────────────────────────────────────

════════════════════════════════════════════════════════════
  ORDER RESPONSE
════════════════════════════════════════════════════════════
  Order ID     : 4195820731
  Symbol       : BTCUSDT
  Side         : BUY
  Type         : MARKET
  Status       : FILLED
  Orig Qty     : 0.001
  Executed Qty : 0.001
  Avg Price    : 63482.50000
────────────────────────────────────────────────────────────

  ✓  Order placed successfully!
```

---

## Logs

All API requests, responses, and errors are written to **`logs/trading_bot.log`**.

```
2025-07-10T09:14:02 | INFO     | trading_bot.orders | Placing BUY MARKET order | symbol=BTCUSDT qty=0.001 ...
2025-07-10T09:14:02 | DEBUG    | trading_bot.client | → POST /fapi/v1/order  params={...}
2025-07-10T09:14:02 | DEBUG    | trading_bot.client | ← HTTP 200  body={...}
2025-07-10T09:14:02 | INFO     | trading_bot.client | Order placed successfully | orderId=4195820731 status=FILLED
```

The log file rotates at 5 MB (3 backups kept).

---

## Architecture Notes

| Layer | File | Responsibility |
|---|---|---|
| **Client** | `bot/client.py` | HTTP, signing, retries, raw API errors |
| **Orders** | `bot/orders.py` | Business logic, display formatting |
| **Validators** | `bot/validators.py` | Input parsing and cross-field validation |
| **Logging** | `bot/logging_config.py` | File + console handler setup |
| **CLI** | `cli.py` | argparse, credential resolution, exit codes |

---

## Assumptions

- Testnet only – the default `--base-url` points to `https://testnet.binancefuture.com`
- Quantity precision: passed as-is to the API. Binance will reject quantities that violate the symbol's `LOT_SIZE` filter (check testnet exchange info for the exact step size)
- `STOP_LIMIT` maps to Binance's `STOP` futures type (a stop-limit order)
- No position-size checks are performed client-side; the API enforces margin requirements

---

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | Order placed successfully |
| `1` | Validation or credentials error |
| `2` | Binance API or network error |
| `3` | Unexpected / unhandled error |
