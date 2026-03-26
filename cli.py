#!/usr/bin/env python3
"""
Binance Futures Testnet – Trading Bot CLI
==========================================

Usage examples
--------------
# Market BUY
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

# Limit SELL
python cli.py --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.01 --price 3500

# Stop-Limit BUY (bonus order type)
python cli.py --symbol BTCUSDT --side BUY --type STOP_LIMIT \
              --quantity 0.001 --price 65000 --stop-price 64500

# Use env vars instead of CLI flags for credentials:
#   export BINANCE_API_KEY=...
#   export BINANCE_API_SECRET=...
"""

from __future__ import annotations

import argparse
import os
import sys
import textwrap
from decimal import Decimal

# Ensure the project root is importable
sys.path.insert(0, os.path.dirname(__file__))

from bot.logging_config import setup_logging, get_logger
from bot.client import BinanceFuturesClient, BinanceAPIError, BinanceNetworkError
from bot.validators import validate_order_params
from bot.orders import place_order

# Initialise logging early so all sub-modules inherit the configuration
setup_logging()
logger = get_logger("cli")


# ── CLI Banner ────────────────────────────────────────────────────────────────

BANNER = r"""
╔══════════════════════════════════════════════════════════╗
║        Binance Futures Testnet  –  Trading Bot           ║
║        USDT-M Perpetuals   |   Python 3.x                ║
╚══════════════════════════════════════════════════════════╝
"""


def print_banner() -> None:
    print(BANNER)


# ── Argument parser ───────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent("""\
            Place Market, Limit, or Stop-Limit orders on Binance Futures Testnet.

            Credentials can be supplied via:
              1. --api-key / --api-secret  CLI flags
              2. BINANCE_API_KEY / BINANCE_API_SECRET  environment variables
        """),
        epilog=textwrap.dedent("""\
            Examples:
              # Market BUY
              python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

              # Limit SELL
              python cli.py --symbol ETHUSDT --side SELL --type LIMIT \\
                            --quantity 0.01 --price 3500

              # Stop-Limit BUY
              python cli.py --symbol BTCUSDT --side BUY --type STOP_LIMIT \\
                            --quantity 0.001 --price 65000 --stop-price 64500
        """),
    )

    # ── Credentials ──
    creds = parser.add_argument_group("credentials (or use env vars)")
    creds.add_argument(
        "--api-key",
        default=os.environ.get("BINANCE_API_KEY"),
        help="Binance API key  [env: BINANCE_API_KEY]",
    )
    creds.add_argument(
        "--api-secret",
        default=os.environ.get("BINANCE_API_SECRET"),
        help="Binance API secret  [env: BINANCE_API_SECRET]",
    )

    # ── Order params ──
    order = parser.add_argument_group("order parameters")
    order.add_argument(
        "--symbol", "-s",
        required=True,
        metavar="SYMBOL",
        help="Futures symbol, e.g. BTCUSDT",
    )
    order.add_argument(
        "--side",
        required=True,
        choices=["BUY", "SELL"],
        type=str.upper,
        help="Order side: BUY or SELL",
    )
    order.add_argument(
        "--type", "-t",
        dest="order_type",
        required=True,
        choices=["MARKET", "LIMIT", "STOP_LIMIT"],
        type=str.upper,
        help="Order type",
    )
    order.add_argument(
        "--quantity", "-q",
        required=True,
        metavar="QTY",
        help="Base asset quantity to trade",
    )
    order.add_argument(
        "--price", "-p",
        default=None,
        metavar="PRICE",
        help="Limit price (required for LIMIT / STOP_LIMIT)",
    )
    order.add_argument(
        "--stop-price",
        dest="stop_price",
        default=None,
        metavar="STOP_PRICE",
        help="Stop trigger price (required for STOP_LIMIT)",
    )
    order.add_argument(
        "--tif",
        dest="time_in_force",
        default="GTC",
        choices=["GTC", "IOC", "FOK"],
        help="Time-in-force for LIMIT orders (default: GTC)",
    )

    # ── Misc ──
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress detailed stdout output (logs still written to file)",
    )
    parser.add_argument(
        "--base-url",
        default="https://testnet.binancefuture.com",
        help="Binance Futures base URL (default: testnet)",
    )

    return parser


# ── Main ─────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    """
    CLI entry point.

    Returns exit code:
      0 – success
      1 – user / validation error
      2 – API or network error
      3 – unexpected error
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.quiet:
        print_banner()

    logger.info(
        "CLI invoked | symbol=%s side=%s type=%s qty=%s price=%s stopPrice=%s",
        args.symbol, args.side, args.order_type,
        args.quantity, args.price, args.stop_price,
    )

    # ── Validate credentials ──────────────────────────────────────────────────
    if not args.api_key or not args.api_secret:
        print(
            "\n  ERROR: API credentials are required.\n"
            "  Set --api-key / --api-secret  or  "
            "BINANCE_API_KEY / BINANCE_API_SECRET env vars.\n"
        )
        logger.error("No API credentials provided.")
        return 1

    # ── Validate order parameters ─────────────────────────────────────────────
    try:
        params = validate_order_params(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
        )
    except ValueError as exc:
        print(f"\n  VALIDATION ERROR: {exc}\n")
        logger.error("Validation error: %s", exc)
        return 1

    # ── Build client ──────────────────────────────────────────────────────────
    try:
        client = BinanceFuturesClient(
            api_key=args.api_key,
            api_secret=args.api_secret,
            base_url=args.base_url,
        )
    except ValueError as exc:
        print(f"\n  CLIENT ERROR: {exc}\n")
        logger.error("Client init error: %s", exc)
        return 1

    # ── Place order ───────────────────────────────────────────────────────────
    try:
        place_order(
            client=client,
            symbol=params["symbol"],
            side=params["side"],
            order_type=params["order_type"],
            quantity=params["quantity"],
            price=params["price"],
            stop_price=params["stop_price"],
            time_in_force=args.time_in_force,
            verbose=not args.quiet,
        )
    except BinanceAPIError as exc:
        logger.error("Order failed (API): %s", exc)
        return 2
    except BinanceNetworkError as exc:
        logger.error("Order failed (network): %s", exc)
        return 2
    except Exception as exc:
        logger.exception("Order failed (unexpected): %s", exc)
        return 3

    return 0


if __name__ == "__main__":
    sys.exit(main())
