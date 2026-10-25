# Лабораторная работа 3: запуск currency_exchange_rate.py по расписанию (cron)

## Описание

Цель работы: настроить планировщик задач cron для автоматического запуска скрипта
`currency_exchange_rate.py` из лабораторной работы 2.

Скрипт и cron работают в Docker-контейнере `lab03-currency-cron`. Контейнер подключён
к сети уже запущенного сервиса lab02prep и обращается к нему по адресу `http://web`.

По расписанию выполняются две задачи:

1. ежедневно в 06:00 запрашивается курс MDL -> EUR за предыдущий день;
2. еженедельно в пятницу в 17:00 запрашивается курс MDL -> USD за предыдущую неделю:
   7 дневных курсов, по одному за каждый из 7 предыдущих дней (с пятницы по четверг).

Вывод каждой задачи (stdout и stderr) дописывается в файл `/var/log/cron.log`
внутри контейнера.

## Требования

- Docker 24+ (проверено на Docker Engine 29.8.2)
- Docker Compose v2 (команда `docker compose`)
- запущенный сервис lab02prep: контейнер `php_apache` в сети `lab02prep_default`
  (сеть должна существовать до запуска контейнера lab03, так как она объявлена внешней)

Проверка сервиса lab02prep:

```
$ docker ps --filter name=php_apache --format '{{.Names}} {{.Networks}}'
php_apache lab02prep_default
```

## Расписание

| Задача      | Выражение cron | Направление | Период                                   |
|-------------|----------------|-------------|------------------------------------------|
| Ежедневная  | `0 6 * * *`    | MDL -> EUR  | предыдущий день                          |
| Еженедельная| `0 17 * * 5`   | MDL -> USD  | 7 предыдущих дней (с пятницы по четверг) |

Время местное: в образе задан часовой пояс `Europe/Chisinau` (EET/EEST).

Задачи записаны в файле `cronjob` в системном формате `/etc/cron.d` (с полем пользователя):

```
SHELL=/bin/sh
PATH=/usr/local/bin:/usr/bin:/bin

0 6 * * * root python3 /opt/lab03/currency_exchange_rate.py --from MDL --to EUR --date "$(date --date='yesterday' '+\%Y-\%m-\%d')" >> /var/log/cron.log 2>&1

0 17 * * 5 root python3 /opt/lab03/currency_exchange_rate.py --from MDL --to USD --date "$(date --date='7 days ago' '+\%Y-\%m-\%d')" --days 7 >> /var/log/cron.log 2>&1
```

Пояснения:

1. Дата вычисляется командой GNU `date`: `yesterday` для ежедневной задачи,
   `7 days ago` (начало диапазона) для еженедельной.
2. Символ `%` в строке crontab означает перевод строки, поэтому в файле он экранирован как `\%`.
3. cron запускает задачи с минимальным окружением, поэтому `PATH` задан явно
   (интерпретатор `python3` официального образа находится в `/usr/local/bin`).
4. Переменные `API_BASE_URL` и `API_KEY` задаются в `docker-compose.yml`; точка входа
   сохраняет их в `/etc/environment` (`env > /etc/environment`), откуда cron передаёт
   их заданиям (модуль pam_env).

## Изменения в скрипте по сравнению с lab02

Скрипт скопирован из `lab02/` и изменён в одном месте: добавлен параметр `--days N`.

| Параметр   | Значение по умолчанию | Допустимые значения | Назначение                                  |
|------------|-----------------------|---------------------|---------------------------------------------|
| `--days N` | `1`                   | от 1 до 31          | количество дней подряд, начиная с `--date`  |

Правила:

1. `--date` остаётся обязательным и задаёт первый день диапазона; без `--days`
   скрипт работает так же, как в lab02.
2. Сначала один раз проверяются общие параметры: коды валют, формат начальной даты,
   `--timeout` и `--days`. Ошибка в них завершает скрипт с кодом 2 без запросов к сервису.
3. Затем каждый день `--date + i` (i = 0 .. N-1) обрабатывается отдельно: проверка диапазона
   2025-01-01..2025-09-15, запрос, сохранение в `data/{FROM}_{TO}_{ГГГГ-ММ-ДД}.json`.
   Для каждого дня выводится своя строка результата или строка
   `currency_exchange_rate.py: error: ...`, ошибка также дописывается в `error.log`.
4. Код возврата равен максимальному коду по всем дням: 0 только если все дни обработаны
   успешно. Коды те же, что в lab02 (2, 3, 4, 5).
5. Вывод сбрасывается после каждой строки (`flush=True`), поэтому в `/var/log/cron.log`
   строки stdout и stderr идут в порядке дней.

Пример: `--date 2025-09-08 --days 7` обрабатывает даты с 2025-09-08 по 2025-09-14
(результат приведён в разделе «Запуск с датой из диапазона данных»).

Значение вне диапазона:

```
$ docker compose exec currency-cron python3 /opt/lab03/currency_exchange_rate.py --from MDL --to EUR --date 2025-09-12 --days 0
currency_exchange_rate.py: error: invalid number of days 0: expected 1..31
$ echo $?
2
```

## Сборка и запуск

Все команды выполняются из директории `lab03/`.

1. Сборка образа `lab03-currency-cron:1.0`:

   ```
   docker compose build
   ```

2. Запуск контейнера в фоновом режиме:

   ```
   docker compose up -d
   ```

3. Проверка состояния:

   ```
   $ docker compose ps
   NAME                  IMAGE                     COMMAND                  SERVICE         CREATED         STATUS         PORTS
   lab03-currency-cron   lab03-currency-cron:1.0   "/usr/local/bin/entr…"   currency-cron   2 seconds ago   Up 2 seconds
   ```

Сообщения точки входа при старте (`docker compose logs currency-cron`):

```
Переменные окружения сохранены в /etc/environment
Создание файла журнала...
Файл журнала создан: /var/log/cron.log
Активные строки /etc/cron.d/lab03:
SHELL=/bin/sh
PATH=/usr/local/bin:/usr/bin:/bin
0 6 * * * root python3 /opt/lab03/currency_exchange_rate.py --from MDL --to EUR --date "$(date --date='yesterday' '+\%Y-\%m-\%d')" >> /var/log/cron.log 2>&1
0 17 * * 5 root python3 /opt/lab03/currency_exchange_rate.py --from MDL --to USD --date "$(date --date='7 days ago' '+\%Y-\%m-\%d')" --days 7 >> /var/log/cron.log 2>&1
=== Запуск демона cron ===
=== Просмотр журнала cron ===
```

Так как точка входа выполняет `tail -f /var/log/cron.log`, новые строки журнала
также видны в `docker compose logs -f currency-cron`.

## Проверка работы

### Процесс cron

```
$ docker compose top
SERVICE        #   UID   PID   PPID  C   STIME  TTY  TIME      CMD
currency-cron  1   root  7857  7833  0   15:22  ?    00:00:00  cron -f
currency-cron  1   root  7885  7857  0   15:22  ?    00:00:00  /bin/sh /usr/local/bin/entrypoint.sh
currency-cron  1   root  7886  7885  0   15:22  ?    00:00:00  tail -f /var/log/cron.log
```

`cron -f` является основным процессом контейнера (запущен через `exec`),
`tail -f` выводит журнал.

### Установленные задания

```
$ docker compose exec currency-cron ls -l /etc/cron.d/lab03
-rw-r--r-- 1 root root 1174 Oct 25 17:22 /etc/cron.d/lab03
$ docker compose exec currency-cron cat /etc/cron.d/lab03
```

Ожидается: владелец `root:root`, права `-rw-r--r--` (0644), 2 строки переменных
(`SHELL`, `PATH`) и 2 активные строки заданий, совпадающие с разделом «Расписание».

### Часовой пояс

```
$ docker compose exec currency-cron date
Sun Oct 25 17:23:09 EET 2026
```

### Ручной запуск задания

Команда ежедневной задачи, выполненная в контейнере вручную:

```
docker compose exec currency-cron sh -c 'python3 /opt/lab03/currency_exchange_rate.py --from MDL --to EUR --date "$(date --date=yesterday +%Y-%m-%d)" >> /var/log/cron.log 2>&1'
```

Экранирование \% нужно только внутри файла cronjob: при ручном запуске в shell символ % пишется без обратной косой черты.

Результат в журнале:

```
$ docker compose exec currency-cron tail -n 5 /var/log/cron.log
currency_exchange_rate.py: error: date 2026-10-24 is outside the supported range 2025-01-01..2025-09-15
```

Строка ошибки ожидаема (см. раздел «Ожидаемая ошибка при реальном запуске») и подтверждает,
что вывод задачи попадает в `/var/log/cron.log`.

### Запуск с датой из диапазона данных

Еженедельная задача с начальной датой 2025-09-08 (7 дней, с 2025-09-08 по 2025-09-14):

```
$ docker compose exec currency-cron python3 /opt/lab03/currency_exchange_rate.py --from MDL --to USD --date 2025-09-08 --days 7
MDL/USD on 2025-09-08: 16.6978
saved: data/MDL_USD_2025-09-08.json
MDL/USD on 2025-09-09: 16.6883
saved: data/MDL_USD_2025-09-09.json
MDL/USD on 2025-09-10: 16.6409
saved: data/MDL_USD_2025-09-10.json
MDL/USD on 2025-09-11: 16.6846
saved: data/MDL_USD_2025-09-11.json
MDL/USD on 2025-09-12: 16.6798
saved: data/MDL_USD_2025-09-12.json
MDL/USD on 2025-09-13: 16.6798
saved: data/MDL_USD_2025-09-13.json
MDL/USD on 2025-09-14: 16.6798
saved: data/MDL_USD_2025-09-14.json
$ echo $?
0
```

Диапазон, выходящий за последнюю дату данных (2025-09-15), обрабатывается по дням,
код возврата 2:

```
$ docker compose exec currency-cron sh -c 'python3 /opt/lab03/currency_exchange_rate.py --from MDL --to EUR --date 2025-09-14 --days 3 >> /var/log/cron.log 2>&1; echo "exit=$?"; tail -n 5 /var/log/cron.log'
exit=2
MDL/EUR on 2025-09-14: 19.487
saved: data/MDL_EUR_2025-09-14.json
MDL/EUR on 2025-09-15: 19.4642
saved: data/MDL_EUR_2025-09-15.json
currency_exchange_rate.py: error: date 2025-09-16 is outside the supported range 2025-01-01..2025-09-15
```

### Проверка через временное расписание

Временный файл с заданием, которое выполняется каждую минуту:

```
docker compose exec currency-cron sh -c "printf '%s\n' 'PATH=/usr/local/bin:/usr/bin:/bin' '* * * * * root python3 /opt/lab03/currency_exchange_rate.py --from MDL --to EUR --date 2025-09-12 >> /var/log/cron.log 2>&1' > /etc/cron.d/lab03-check && chmod 0644 /etc/cron.d/lab03-check"
```

Строка `PATH=` обязательна: переменные файла `/etc/cron.d/lab03` действуют только в нём,
а без неё cron использует `PATH=/usr/bin:/bin`, где нет `python3`.

Через 1–2 минуты в журнале появляются строки, записанные самим cron:

```
$ docker compose exec currency-cron tail -n 4 /var/log/cron.log
MDL/EUR on 2025-09-12: 19.487
saved: ../opt/lab03/data/MDL_EUR_2025-09-12.json
MDL/EUR on 2025-09-12: 19.487
saved: ../opt/lab03/data/MDL_EUR_2025-09-12.json
```

Путь `../opt/lab03/data/...` указан относительно домашней директории `/root`, из которой
cron запускает задания; файл сохраняется в `/opt/lab03/data/`. Успешный запрос подтверждает,
что задание cron получило `API_BASE_URL=http://web` и `API_KEY` из `/etc/environment`
(адрес по умолчанию `http://localhost:8080` внутри контейнера недоступен).

Удаление временного задания:

```
docker compose exec currency-cron rm /etc/cron.d/lab03-check
```

## Ожидаемая ошибка при реальном запуске

cron использует реальную системную дату (2026 год), а данные сервиса есть только
за 2025-01-01..2025-09-15. Скрипт проверяет диапазон до обращения к сервису, поэтому
при запуске по расписанию в `/var/log/cron.log` записывается ошибка, а скрипт
завершается с кодом 2:

```
currency_exchange_rate.py: error: date 2026-10-24 is outside the supported range 2025-01-01..2025-09-15
```

Еженедельная задача записывает 7 таких строк, по одной на каждый день диапазона.
Это ожидаемое поведение: расписание и запись вывода работают, а успешный запрос
показан в разделах «Запуск с датой из диапазона данных» и «Проверка через временное расписание».

## Структура проекта

```
lab03/
├── .dockerignore
├── Dockerfile
├── cronjob
├── currency_exchange_rate.py
├── docker-compose.yml
├── entrypoint.sh
├── readme.md
└── requirements.txt
```

| Файл                        | Назначение |
|-----------------------------|------------|
| `.dockerignore`             | исключает из контекста сборки файлы, не нужные в образе (`__pycache__/`, `data/`, `error.log`, документацию, compose-файл) |
| `Dockerfile`                | образ на основе `python:3.12-slim-bookworm`: установка cron и tzdata, часовой пояс `Europe/Chisinau`, установка `requests`, копирование скрипта, `cronjob` в `/etc/cron.d/lab03` (права 0644) и точки входа |
| `cronjob`                   | задания cron в формате `/etc/cron.d`: ежедневная (MDL -> EUR) и еженедельная (MDL -> USD) с выводом в `/var/log/cron.log` |
| `currency_exchange_rate.py` | скрипт из lab02 с добавленным параметром `--days N` |
| `docker-compose.yml`        | сборка образа `lab03-currency-cron:1.0`, контейнер `lab03-currency-cron`, переменные `API_BASE_URL` и `API_KEY`, подключение к внешней сети `lab02prep_default` |
| `entrypoint.sh`             | точка входа: сохраняет окружение в `/etc/environment`, создаёт `/var/log/cron.log`, проверяет `/etc/cron.d/lab03`, выводит журнал через `tail -f` и запускает `cron -f` |
| `readme.md`                 | описание работы (этот файл) |
| `requirements.txt`          | зависимость Python: `requests==2.32.3` |

Директория `data/` и файл `error.log` создаются скриптом внутри контейнера
(`/opt/lab03/data/`, `/opt/lab03/error.log`); тома не используются, поэтому при удалении
контейнера они удаляются.

Базовый образ `python:3.12-slim-bookworm`: в нём уже есть Python 3.12 и pip, поэтому из apt ставятся только `cron` и `tzdata`.

## Остановка и очистка

```
docker compose down --rmi local
```

Команда останавливает и удаляет контейнер и собранный образ `lab03-currency-cron:1.0`.
Внешняя сеть `lab02prep_default` и сервис lab02prep не затрагиваются.
