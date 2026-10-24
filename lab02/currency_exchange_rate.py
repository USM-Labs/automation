#!/usr/bin/env python3
"""
currency_exchange_rate.py - get a currency exchange rate for a date from the
lab02prep Web API and save it as JSON.

Usage:
    python3 currency_exchange_rate.py --from USD --to MDL --date 2025-01-15
        [--api-key KEY] [--base-url URL] [--timeout SEC]
"""

import argparse
import sys

SCRIPT_NAME = "currency_exchange_rate.py"

DEFAULT_BASE_URL = "http://localhost:8080"
DEFAULT_API_KEY = "EXAMPLE_API_KEY"
REQUEST_TIMEOUT_SECONDS = 10

EXIT_OK = 0


def parse_arguments() -> argparse.Namespace:
    """Reads the command-line options.

    Returns:
        Namespace with from_currency, to_currency, date, api_key,
        base_url and timeout. Only long options are accepted.
    """
    parser = argparse.ArgumentParser(
        prog=SCRIPT_NAME,
        description="Get a currency exchange rate for a date and save it as JSON.",
    )
    parser.add_argument("--from", dest="from_currency", required=True,
                        metavar="CODE", help="source currency, e.g. USD")
    parser.add_argument("--to", dest="to_currency", required=True,
                        metavar="CODE", help="target currency, e.g. MDL")
    parser.add_argument("--date", dest="date", required=True,
                        metavar="YYYY-MM-DD", help="date of the rate")
    parser.add_argument("--api-key", dest="api_key", default=DEFAULT_API_KEY,
                        metavar="KEY", help=f"API key (default: {DEFAULT_API_KEY})")
    parser.add_argument("--base-url", dest="base_url", default=DEFAULT_BASE_URL,
                        metavar="URL", help=f"service URL (default: {DEFAULT_BASE_URL})")
    parser.add_argument("--timeout", dest="timeout", type=float,
                        default=REQUEST_TIMEOUT_SECONDS, metavar="SEC",
                        help=f"request timeout in seconds (default: {REQUEST_TIMEOUT_SECONDS})")
    return parser.parse_args()


def main() -> int:
    """Entry point: parse the options and echo the request.

    Returns:
        One of the EXIT_* codes.
    """
    args = parse_arguments()
    print(f"request: {args.from_currency}->{args.to_currency} on {args.date} "
          f"from {args.base_url}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
