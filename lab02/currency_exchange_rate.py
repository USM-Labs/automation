#!/usr/bin/env python3
"""
currency_exchange_rate.py - get a currency exchange rate for a date from the
lab02prep Web API and save it as JSON.

Usage:
    python3 currency_exchange_rate.py --from USD --to MDL --date 2025-01-15
        [--api-key KEY] [--base-url URL] [--timeout SEC]

The API key is taken from --api-key, then from the API_KEY environment
variable, then from DEFAULT_API_KEY. The base URL is taken from --base-url,
then from API_BASE_URL, then from DEFAULT_BASE_URL.

Results are saved to <script dir>/data/{FROM}_{TO}_{YYYY-MM-DD}.json.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import requests

SCRIPT_NAME = "currency_exchange_rate.py"

DEFAULT_BASE_URL = "http://localhost:8080"
DEFAULT_API_KEY = "EXAMPLE_API_KEY"
REQUEST_TIMEOUT_SECONDS = 10

ENV_API_KEY = "API_KEY"
ENV_BASE_URL = "API_BASE_URL"

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"

EXIT_OK = 0
EXIT_API_ERROR = 3


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
    parser.add_argument("--api-key", dest="api_key", default=None,
                        metavar="KEY",
                        help=f"API key (default: ${ENV_API_KEY} or {DEFAULT_API_KEY})")
    parser.add_argument("--base-url", dest="base_url", default=None,
                        metavar="URL",
                        help=f"service URL (default: ${ENV_BASE_URL} or {DEFAULT_BASE_URL})")
    parser.add_argument("--timeout", dest="timeout", type=float,
                        default=REQUEST_TIMEOUT_SECONDS, metavar="SEC",
                        help=f"request timeout in seconds (default: {REQUEST_TIMEOUT_SECONDS})")
    return parser.parse_args()


def resolve_api_key(cli_value: Optional[str]) -> str:
    """Resolves the API key.

    Order of precedence: --api-key, the API_KEY variable, DEFAULT_API_KEY.
    """
    if cli_value:
        return cli_value
    return os.environ.get(ENV_API_KEY) or DEFAULT_API_KEY


def resolve_base_url(cli_value: Optional[str]) -> str:
    """Resolves the service base URL (without a trailing slash).

    Order of precedence: --base-url, the API_BASE_URL variable, DEFAULT_BASE_URL.
    """
    value = cli_value or os.environ.get(ENV_BASE_URL) or DEFAULT_BASE_URL
    return value.rstrip("/")


def build_source_url(base_url: str, from_currency: str, to_currency: str,
                     on_date: str) -> str:
    """Returns the request URL with from/to/date in the query string.

    The API key is deliberately absent: it is sent in the POST body.
    """
    return f"{base_url}/?from={from_currency}&to={to_currency}&date={on_date}"


def fetch_exchange_rate(base_url: str, api_key: str, from_currency: str,
                        to_currency: str, on_date: str,
                        timeout: float = REQUEST_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Sends the POST request.

    Returns:
        The "data" object of the response (from, to, rate, date).
    """
    url = build_source_url(base_url, from_currency, to_currency, on_date)
    response = requests.post(url, data={"key": api_key}, timeout=timeout)
    body = response.json()
    if body.get("error"):
        print(f"{SCRIPT_NAME}: error: API returned an error: {body['error']}",
              file=sys.stderr)
        sys.exit(EXIT_API_ERROR)
    return body["data"]


def build_output_path(from_currency: str, to_currency: str, on_date: str) -> Path:
    """Returns the output file path: DATA_DIR/{FROM}_{TO}_{YYYY-MM-DD}.json."""
    return DATA_DIR / f"{from_currency}_{to_currency}_{on_date}.json"


def save_result(payload: dict[str, Any], path: Path) -> None:
    """Stores the payload in a JSON file (indent 4, UTF-8).

    The parent directory is created when it does not exist yet.
    Raises:
        OSError: the file cannot be written (handled by the caller).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output_file:
        json.dump(payload, output_file, ensure_ascii=False, indent=4)
        output_file.write("\n")


def main() -> int:
    """Entry point: request the rate and save it.

    Returns:
        One of the EXIT_* codes.
    """
    args = parse_arguments()
    from_currency = args.from_currency.upper()
    to_currency = args.to_currency.upper()
    on_date = args.date

    api_key = resolve_api_key(args.api_key)
    base_url = resolve_base_url(args.base_url)
    data = fetch_exchange_rate(base_url, api_key, from_currency,
                               to_currency, on_date, args.timeout)

    payload: dict[str, Any] = {
        "from": from_currency,
        "to": to_currency,
        "date": on_date,
        "rate": data["rate"],
        "source": build_source_url(base_url, from_currency, to_currency, on_date),
        "retrieved_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    output_path = build_output_path(from_currency, to_currency, on_date)
    save_result(payload, output_path)

    print(f"{from_currency}/{to_currency} on {on_date}: {payload['rate']}")
    print(f"saved: {os.path.relpath(output_path)}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
