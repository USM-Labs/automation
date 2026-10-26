# Лабораторная работа 2: currency_exchange_rate.py

## Описание

`currency_exchange_rate.py` получает курс одной валюты к другой на указанную дату
через Web API сервиса lab02prep и сохраняет результат в JSON-файл.

Скрипт:

1. принимает исходную валюту, целевую валюту и дату как параметры командной строки;
2. проверяет параметры до обращения к сервису (код валюты, формат даты, диапазон дат);
3. отправляет запрос `POST /?from=XXX&to=YYY&date=YYYY-MM-DD` с телом `key=<API_KEY>`;
4. проверяет ответ (HTTP-статус, корректность JSON, поле `error`, наличие `data` и `rate`);
5. сохраняет результат в `data/{FROM}_{TO}_{ГГГГ-ММ-ДД}.json` (директория создаётся при необходимости);
6. при любой ошибке выводит понятное сообщение в stderr, дописывает строку в `error.log`
   и завершается с ненулевым кодом возврата.

Директория `data/` и файл `error.log` всегда находятся рядом со скриптом (в `lab02/`),
независимо от текущей директории, из которой скрипт запущен.

## Требования

- Python 3.10+
- requests 2.32.3
- запущенный сервис lab02prep (по умолчанию `http://localhost:8080`)

## Установка зависимостей

```
cd lab02
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Синтаксис

```
python3 currency_exchange_rate.py --from CODE --to CODE --date YYYY-MM-DD
                                  [--api-key KEY] [--base-url URL] [--timeout SEC]
python3 currency_exchange_rate.py -h
```

Пример:

```
$ python3 currency_exchange_rate.py --from USD --to MDL --date 2025-01-15
USD/MDL on 2025-01-15: 0.05316066748534094
saved: data/USD_MDL_2025-01-15.json
```

Запуск из корня репозитория тоже работает, файл сохраняется в `lab02/data/`:

```
$ python3 lab02/currency_exchange_rate.py --from USD --to MDL --date 2025-01-15
USD/MDL on 2025-01-15: 0.05316066748534094
saved: lab02/data/USD_MDL_2025-01-15.json
```

## Параметры

| Опция        | Обязательная | По умолчанию                                | Описание                                        |
|--------------|--------------|---------------------------------------------|-------------------------------------------------|
| `--from`     | да           | -                                           | исходная валюта, 3 латинские буквы (`USD`)      |
| `--to`       | да           | -                                           | целевая валюта, 3 латинские буквы (`MDL`)       |
| `--date`     | да           | -                                           | дата `ГГГГ-ММ-ДД` в диапазоне 2025-01-01..2025-09-15 |
| `--api-key`  | нет          | `$API_KEY`, иначе `EXAMPLE_API_KEY`         | ключ API, передаётся в теле запроса             |
| `--base-url` | нет          | `$API_BASE_URL`, иначе `http://localhost:8080` | адрес сервиса                                |
| `--timeout`  | нет          | `10`                                        | таймаут запроса в секундах (положительное число) |
| `-h`, `--help` | нет        | -                                           | показать справку и выйти                        |

Коды валют приводятся к верхнему регистру (`usd` -> `USD`), поэтому сервис всегда получает
корректный код.

## Переменные окружения

| Переменная     | Назначение                                                  |
|----------------|-------------------------------------------------------------|
| `API_KEY`      | ключ API, если не указан `--api-key`                        |
| `API_BASE_URL` | адрес сервиса, если не указан `--base-url`                  |

Приоритет: опция командной строки > переменная окружения > значение по умолчанию.
Значение `EXAMPLE_API_KEY` - документированный ключ локального сервиса lab02prep.

## Коды возврата

| Код | Значение                                                                                  |
|-----|-------------------------------------------------------------------------------------------|
| 0   | курс получен и сохранён (или показана справка)                                            |
| 2   | неверные аргументы: код валюты, формат даты, дата вне диапазона, таймаут, отсутствует опция |
| 3   | ошибка API: непустое поле `error`, HTTP-статус не 200, ответ не JSON, нет `data`/`rate`   |
| 4   | сетевая ошибка: соединение отклонено, таймаут, хост недоступен                            |
| 5   | не удалось записать файл результата                                                       |

## Формат выходного файла

Имя: `data/{FROM}_{TO}_{ГГГГ-ММ-ДД}.json`, например `data/USD_MDL_2025-01-15.json`.

Содержимое (`data/USD_MDL_2025-01-15.json`):

```json
{
    "from": "USD",
    "to": "MDL",
    "date": "2025-01-15",
    "rate": 0.05316066748534094,
    "source": "http://localhost:8080/?from=USD&to=MDL&date=2025-01-15",
    "retrieved_at": "2026-10-24T19:37:12+03:00"
}
```

- `rate` - значение, которое вернул сервис, без изменений;
- `source` - URL запроса; ключ API передаётся только в теле POST-запроса, поэтому в URL и в сохранённом файле он отсутствует;
- `retrieved_at` - локальное время получения ответа.

## Журнал ошибок

Файл `error.log` (рядом со скриптом), каждая ошибка занимает одну строку, файл дополняется:

```
ГГГГ-ММ-ДД ЧЧ:ММ:СС,мс | ERROR    | {FROM}->{TO} on {ДАТА}: {сообщение}
```

Пример:

```
2026-10-24 19:50:14,503 | ERROR    | GBP->MDL on 2025-01-15: API returned an error: The currency GBP is unknown
```

Ошибки проверки параметров тоже записываются в журнал. Не записываются только ошибки
синтаксиса командной строки, которые выводит сам `argparse` (например, отсутствует `--date`).

## Структура скрипта

Константы в начале модуля: `DEFAULT_BASE_URL`, `DEFAULT_API_KEY`, `REQUEST_TIMEOUT_SECONDS`,
`MIN_DATE`, `MAX_DATE`, `DATE_FORMAT`, `SCRIPT_DIR`, `DATA_DIR`, `ERROR_LOG_PATH`,
коды возврата `EXIT_OK`, `EXIT_INVALID_ARGS`, `EXIT_API_ERROR`, `EXIT_NETWORK_ERROR`, `EXIT_IO_ERROR`.

| Элемент                    | Назначение                                                                 |
|----------------------------|----------------------------------------------------------------------------|
| `ExchangeRateError`        | исключение для обрабатываемых ошибок, хранит код возврата `exit_code`      |
| `parse_arguments()`        | разбор опций `--from`, `--to`, `--date`, `--api-key`, `--base-url`, `--timeout` |
| `validate_currency_code()` | проверка кода валюты (3 латинские буквы) и приведение к верхнему регистру  |
| `validate_date()`          | разбор даты `ГГГГ-ММ-ДД` и проверка диапазона 2025-01-01..2025-09-15       |
| `validate_timeout()`       | проверка, что таймаут положительный                                        |
| `resolve_api_key()`        | выбор ключа: `--api-key` > `$API_KEY` > `EXAMPLE_API_KEY`                  |
| `resolve_base_url()`       | выбор адреса: `--base-url` > `$API_BASE_URL` > `http://localhost:8080`     |
| `build_source_url()`       | формирование URL запроса                                                   |
| `fetch_exchange_rate()`    | POST-запрос к API, обработка сетевых ошибок и проверка ответа             |
| `build_output_path()`      | путь `data/{FROM}_{TO}_{ДАТА}.json` рядом со скриптом                      |
| `save_result()`            | создание `data/` и запись JSON                                             |
| `configure_logging()`      | логгер с `FileHandler` на `error.log`, уровень ERROR                       |
| `main()`                   | последовательность: аргументы -> проверка -> запрос -> сохранение; перехват `ExchangeRateError`, вывод в stderr, запись в журнал, код возврата |

Логика `main()`:

1. разобрать аргументы и настроить журнал;
2. проверить валюты, дату и таймаут (до любого сетевого запроса);
3. определить ключ API и адрес сервиса;
4. выполнить запрос и проверить ответ;
5. сохранить JSON и вывести курс и путь к файлу;
6. при `ExchangeRateError` - сообщение в stderr, строка в `error.log`, код возврата из исключения.

## Тестирование

### Серия запросов: USD -> MDL, 9 дат с интервалом 30 дней

Даты: начиная с 2025-01-15 каждые 30 дней, последняя 2025-09-12 (все в диапазоне данных).

```
python3 currency_exchange_rate.py --from USD --to MDL --date 2025-01-15
python3 currency_exchange_rate.py --from USD --to MDL --date 2025-02-14
python3 currency_exchange_rate.py --from USD --to MDL --date 2025-03-16
python3 currency_exchange_rate.py --from USD --to MDL --date 2025-04-15
python3 currency_exchange_rate.py --from USD --to MDL --date 2025-05-15
python3 currency_exchange_rate.py --from USD --to MDL --date 2025-06-14
python3 currency_exchange_rate.py --from USD --to MDL --date 2025-07-14
python3 currency_exchange_rate.py --from USD --to MDL --date 2025-08-13
python3 currency_exchange_rate.py --from USD --to MDL --date 2025-09-12
```

Серия запускалась из корня репозитория (`python3 lab02/currency_exchange_rate.py ...`),
файлы появились в `lab02/data/`.

| Дата       | Курс USD/MDL         | Файл                              |
|------------|----------------------|-----------------------------------|
| 2025-01-15 | 0.05316066748534094  | `data/USD_MDL_2025-01-15.json`    |
| 2025-02-14 | 0.05346106964908153  | `data/USD_MDL_2025-02-14.json`    |
| 2025-03-16 | 0.05600546613349463  | `data/USD_MDL_2025-03-16.json`    |
| 2025-04-15 | 0.058039315832544965 | `data/USD_MDL_2025-04-15.json`    |
| 2025-05-15 | 0.05778342771293193  | `data/USD_MDL_2025-05-15.json`    |
| 2025-06-14 | 0.05900087911309879  | `data/USD_MDL_2025-06-14.json`    |
| 2025-07-14 | 0.05897165232672654  | `data/USD_MDL_2025-07-14.json`    |
| 2025-08-13 | 0.05938912347592662  | `data/USD_MDL_2025-08-13.json`    |
| 2025-09-12 | 0.059952757227304886 | `data/USD_MDL_2025-09-12.json`    |

### Дополнительная пара: EUR -> RON

```
$ python3 currency_exchange_rate.py --from EUR --to RON --date 2025-06-14
EUR/RON on 2025-06-14: 0.19885082625490486
saved: data/EUR_RON_2025-06-14.json
```

### Ошибочные параметры

Каждая команда выводит сообщение в stderr, дописывает строку в `error.log`
и завершается с указанным кодом.

| № | Команда | Код | Вывод в stderr |
|---|---------|-----|----------------|
| 1 | `--from GBP --to MDL --date 2025-01-15` | 3 | `currency_exchange_rate.py: error: API returned an error: The currency GBP is unknown` |
| 2 | `--from RUS --to MDL --date 2025-01-15` | 3 | `currency_exchange_rate.py: error: API returned an error: Unknown currency rus` |
| 3 | `--from USD --to MDL --date 2025-01-15 --api-key WRONG` | 3 | `currency_exchange_rate.py: error: API returned an error: Invalid API key` |
| 4 | `--from USD --to MDL --date 2025-01-15 --base-url http://localhost:9999` | 4 | `currency_exchange_rate.py: error: cannot connect to http://localhost:9999 (connection refused)` |
| 5 | `--from USD --to MDL --date 2025-02-30` | 2 | `currency_exchange_rate.py: error: invalid date '2025-02-30': expected an existing date in YYYY-MM-DD format` |
| 6 | `--from USD --to MDL --date 2024-12-31` | 2 | `currency_exchange_rate.py: error: date 2024-12-31 is outside the supported range 2025-01-01..2025-09-15` |

Полные команды:

```
python3 currency_exchange_rate.py --from GBP --to MDL --date 2025-01-15
python3 currency_exchange_rate.py --from RUS --to MDL --date 2025-01-15
python3 currency_exchange_rate.py --from USD --to MDL --date 2025-01-15 --api-key WRONG
python3 currency_exchange_rate.py --from USD --to MDL --date 2025-01-15 --base-url http://localhost:9999
python3 currency_exchange_rate.py --from USD --to MDL --date 2025-02-30
python3 currency_exchange_rate.py --from USD --to MDL --date 2024-12-31
```

Результат: файл `error.log` (6 строк), он сохранён в репозитории.

## Ограничения

- Сервис содержит данные только за период 2025-01-01..2025-09-15. Для дат вне диапазона
  сервис не возвращает ошибку, а молча подставляет последний известный курс, поэтому
  скрипт отклоняет такие даты сам (код 2).
- Сервис при неверном формате даты отвечает HTML-страницей с ошибкой PHP (HTTP 200).
  Скрипт проверяет формат даты заранее, а на случай не-JSON ответа выводит
  `response is not valid JSON` (код 3).
- Валюта `RUS` присутствует в списке валют сервиса, но запрос с ней завершается ошибкой
  `Unknown currency rus` - это ошибка данных на стороне сервиса.
- Значение `rate` сохраняется в том виде, в котором его вернул сервис.
