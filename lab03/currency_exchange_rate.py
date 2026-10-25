#!/usr/bin/env python3
"""
currency_exchange_rate.py - get a currency exchange rate for a date from the
lab02prep Web API and save it as JSON.

Usage:
    python3 currency_exchange_rate.py --from USD --to MDL --date 2025-01-15
        [--api-key KEY] [--base-url URL] [--timeout SEC]
        [--days N]

    --days N  количество дней подряд, начиная с --date (по умолчанию 1)

The API key is taken from --api-key, then from the API_KEY environment
variable, then from DEFAULT_API_KEY. The base URL is taken from --base-url,
then from API_BASE_URL, then from DEFAULT_BASE_URL.

Results are saved to <script dir>/data/{FROM}_{TO}_{YYYY-MM-DD}.json.
Errors are printed to stderr and appended to <script dir>/error.log.

Exit codes:
    0 - rate received and saved
    2 - invalid arguments (currency code, date format, date range, timeout)
    3 - API error (error field, HTTP status, non-JSON or malformed response)
    4 - network error (connection refused, timeout, other transport failure)
    5 - the result file cannot be written

При --days N > 1 каждый день обрабатывается отдельно, а итоговый код
возврата равен максимальному коду по всем дням (0 только при полном успехе).
"""

import argparse
import json
import logging
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import requests

SCRIPT_NAME = "currency_exchange_rate.py"

DEFAULT_BASE_URL = "http://localhost:8080"
DEFAULT_API_KEY = "EXAMPLE_API_KEY"
REQUEST_TIMEOUT_SECONDS = 10

ENV_API_KEY = "API_KEY"
ENV_BASE_URL = "API_BASE_URL"

MIN_DATE = date(2025, 1, 1)
MAX_DATE = date(2025, 9, 15)
DATE_FORMAT = "%Y-%m-%d"
CURRENCY_CODE_LENGTH = 3

# Допустимое количество дней для --days и значение по умолчанию.
MIN_DAYS = 1
MAX_DAYS = 31
DEFAULT_DAYS = 1

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
ERROR_LOG_PATH = SCRIPT_DIR / "error.log"

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"

EXIT_OK = 0
EXIT_INVALID_ARGS = 2
EXIT_API_ERROR = 3
EXIT_NETWORK_ERROR = 4
EXIT_IO_ERROR = 5


class ExchangeRateError(Exception):
    """Signals an expected failure; exit_code is the process status to return."""

    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


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
                        metavar="YYYY-MM-DD",
                        help=f"date between {MIN_DATE} and {MAX_DATE}")
    parser.add_argument("--api-key", dest="api_key", default=None,
                        metavar="KEY",
                        help=f"API key (default: ${ENV_API_KEY} or {DEFAULT_API_KEY})")
    parser.add_argument("--base-url", dest="base_url", default=None,
                        metavar="URL",
                        help=f"service URL (default: ${ENV_BASE_URL} or {DEFAULT_BASE_URL})")
    parser.add_argument("--timeout", dest="timeout", type=float,
                        default=REQUEST_TIMEOUT_SECONDS, metavar="SEC",
                        help=f"request timeout in seconds (default: {REQUEST_TIMEOUT_SECONDS})")
    # Новый параметр: количество дней подряд, начиная с --date.
    parser.add_argument("--days", dest="days", type=int, default=DEFAULT_DAYS,
                        metavar="N",
                        help=(f"количество дней подряд, начиная с --date, "
                              f"от {MIN_DAYS} до {MAX_DAYS} (по умолчанию: {DEFAULT_DAYS})"))
    return parser.parse_args()


def validate_currency_code(code: str) -> str:
    """Validates a currency code and normalizes it to upper case.

    Returns:
        The code in upper case, e.g. "usd" -> "USD".
    Raises:
        ExchangeRateError (EXIT_INVALID_ARGS): not exactly 3 ASCII letters.
    """
    normalized = code.strip().upper()
    if (len(normalized) != CURRENCY_CODE_LENGTH
            or not normalized.isascii()
            or not normalized.isalpha()):
        raise ExchangeRateError(
            f"invalid currency code '{code}': expected {CURRENCY_CODE_LENGTH} latin letters",
            EXIT_INVALID_ARGS,
        )
    return normalized


def validate_date(value: str) -> date:
    """Validates a YYYY-MM-DD string against the calendar and the data range.

    Returns:
        The parsed date.
    Raises:
        ExchangeRateError (EXIT_INVALID_ARGS): unparseable date or a date
        outside MIN_DATE..MAX_DATE.
    """
    try:
        parsed = datetime.strptime(value.strip(), DATE_FORMAT).date()
    except ValueError:
        raise ExchangeRateError(
            f"invalid date '{value}': expected an existing date in YYYY-MM-DD format",
            EXIT_INVALID_ARGS,
        ) from None
    # The service silently returns the last known rate for dates out of range.
    if not MIN_DATE <= parsed <= MAX_DATE:
        raise ExchangeRateError(
            f"date {parsed} is outside the supported range {MIN_DATE}..{MAX_DATE}",
            EXIT_INVALID_ARGS,
        )
    return parsed


def parse_start_date(value: str) -> date:
    """Проверяет только формат начальной даты YYYY-MM-DD (без проверки диапазона).

    Returns:
        Разобранная дата.
    Raises:
        ExchangeRateError (EXIT_INVALID_ARGS): строка не является датой
        в формате YYYY-MM-DD.
    """
    try:
        return datetime.strptime(value.strip(), DATE_FORMAT).date()
    except ValueError:
        raise ExchangeRateError(
            f"invalid date '{value}': expected an existing date in YYYY-MM-DD format",
            EXIT_INVALID_ARGS,
        ) from None


def validate_days(value: int) -> int:
    """Проверяет количество дней для --days.

    Returns:
        Значение без изменений.
    Raises:
        ExchangeRateError (EXIT_INVALID_ARGS): значение вне MIN_DAYS..MAX_DAYS.
    """
    if not MIN_DAYS <= value <= MAX_DAYS:
        raise ExchangeRateError(
            f"invalid number of days {value}: expected {MIN_DAYS}..{MAX_DAYS}",
            EXIT_INVALID_ARGS,
        )
    return value


def validate_timeout(seconds: float) -> float:
    """Validates the request timeout.

    Returns:
        The timeout unchanged.
    Raises:
        ExchangeRateError (EXIT_INVALID_ARGS): zero or negative value.
    """
    if not seconds > 0:
        raise ExchangeRateError(
            f"invalid timeout {seconds}: expected a positive number of seconds",
            EXIT_INVALID_ARGS,
        )
    return seconds


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
                     on_date: date) -> str:
    """Returns the request URL with from/to/date in the query string.

    The API key is deliberately absent: it is sent in the POST body.
    """
    return (f"{base_url}/?from={from_currency}&to={to_currency}"
            f"&date={on_date.strftime(DATE_FORMAT)}")


def fetch_exchange_rate(base_url: str, api_key: str, from_currency: str,
                        to_currency: str, on_date: date,
                        timeout: float = REQUEST_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Sends the POST request and checks the response.

    Returns:
        The "data" object of the response (from, to, rate, date).
    Raises:
        ExchangeRateError (EXIT_NETWORK_ERROR): connection or timeout failure.
        ExchangeRateError (EXIT_API_ERROR): bad HTTP status, non-JSON body,
        non-empty "error" field, missing "data" or "rate".
    """
    url = build_source_url(base_url, from_currency, to_currency, on_date)
    try:
        response = requests.post(url, data={"key": api_key}, timeout=timeout)
    except requests.exceptions.Timeout:
        raise ExchangeRateError(
            f"request to {base_url} timed out after {timeout:g} s",
            EXIT_NETWORK_ERROR,
        ) from None
    except requests.exceptions.ConnectionError as exc:
        reason = "connection refused" if "refused" in str(exc).lower() else "connection failed"
        raise ExchangeRateError(
            f"cannot connect to {base_url} ({reason})", EXIT_NETWORK_ERROR,
        ) from None
    except requests.exceptions.RequestException as exc:
        raise ExchangeRateError(
            f"request to {base_url} failed: {exc.__class__.__name__}",
            EXIT_NETWORK_ERROR,
        ) from None

    if response.status_code != 200:
        raise ExchangeRateError(
            f"unexpected HTTP status {response.status_code} from {base_url}",
            EXIT_API_ERROR,
        )

    try:
        body = response.json()
    except ValueError:
        # e.g. the PHP fatal error page returned with HTTP 200
        raise ExchangeRateError("response is not valid JSON", EXIT_API_ERROR) from None

    if not isinstance(body, dict):
        raise ExchangeRateError("response is not a JSON object", EXIT_API_ERROR)

    api_error = body.get("error")
    if api_error:
        raise ExchangeRateError(f"API returned an error: {api_error}", EXIT_API_ERROR)

    data = body.get("data")
    if not isinstance(data, dict):
        raise ExchangeRateError("response has no 'data' object", EXIT_API_ERROR)

    if not isinstance(data.get("rate"), (int, float)):
        raise ExchangeRateError("response 'data' has no numeric 'rate'", EXIT_API_ERROR)
    return data


def build_output_path(from_currency: str, to_currency: str, on_date: date) -> Path:
    """Returns the output file path: DATA_DIR/{FROM}_{TO}_{YYYY-MM-DD}.json."""
    file_name = f"{from_currency}_{to_currency}_{on_date.strftime(DATE_FORMAT)}.json"
    return DATA_DIR / file_name


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


def configure_logging() -> logging.Logger:
    """Configures the module logger.

    Returns:
        A logger whose only handler appends ERROR records to ERROR_LOG_PATH.
    """
    logger = logging.getLogger(SCRIPT_NAME)
    logger.setLevel(logging.ERROR)
    logger.propagate = False
    if not logger.handlers:
        # delay=True: error.log is created only when the first error happens
        handler = logging.FileHandler(ERROR_LOG_PATH, mode="a", encoding="utf-8", delay=True)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(handler)
    return logger


def process_date(from_currency: str, to_currency: str, day: date,
                 api_key: str, base_url: str, timeout: float,
                 logger: logging.Logger) -> int:
    """Обрабатывает один день: проверка диапазона, запрос, сохранение, вывод.

    Returns:
        Один из кодов EXIT_*; ошибка выводится в stderr и в error.log.
    """
    request_label = f"{from_currency}->{to_currency} on {day}"
    try:
        on_date = validate_date(day.strftime(DATE_FORMAT))
        data = fetch_exchange_rate(base_url, api_key, from_currency,
                                   to_currency, on_date, timeout)

        payload: dict[str, Any] = {
            "from": from_currency,
            "to": to_currency,
            "date": on_date.strftime(DATE_FORMAT),
            "rate": data["rate"],
            "source": build_source_url(base_url, from_currency, to_currency, on_date),
            "retrieved_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
        output_path = build_output_path(from_currency, to_currency, on_date)
        try:
            save_result(payload, output_path)
        except OSError as exc:
            raise ExchangeRateError(
                f"cannot write {output_path}: {exc.strerror}", EXIT_IO_ERROR,
            ) from None
    except ExchangeRateError as exc:
        # flush=True сохраняет порядок строк stdout и stderr при выводе в файл журнала.
        print(f"{SCRIPT_NAME}: error: {exc}", file=sys.stderr, flush=True)
        logger.error("%s: %s", request_label, exc)
        return exc.exit_code

    print(f"{from_currency}/{to_currency} on {on_date}: {payload['rate']}")
    print(f"saved: {os.path.relpath(output_path)}", flush=True)
    return EXIT_OK


def main() -> int:
    """Entry point: validate, request, save, report.

    Returns:
        One of the EXIT_* codes.
    """
    args = parse_arguments()
    logger = configure_logging()
    request_label = f"{args.from_currency}->{args.to_currency} on {args.date}"

    # Общие параметры проверяются один раз, до обработки отдельных дней.
    try:
        from_currency = validate_currency_code(args.from_currency)
        to_currency = validate_currency_code(args.to_currency)
        start_date = parse_start_date(args.date)
        timeout = validate_timeout(args.timeout)
        days = validate_days(args.days)
    except ExchangeRateError as exc:
        print(f"{SCRIPT_NAME}: error: {exc}", file=sys.stderr)
        logger.error("%s: %s", request_label, exc)
        return exc.exit_code

    api_key = resolve_api_key(args.api_key)
    base_url = resolve_base_url(args.base_url)

    # Каждый день диапазона обрабатывается отдельно; итоговый код возврата — максимальный.
    exit_code = EXIT_OK
    for offset in range(days):
        day = start_date + timedelta(days=offset)
        day_code = process_date(from_currency, to_currency, day,
                                api_key, base_url, timeout, logger)
        exit_code = max(exit_code, day_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
