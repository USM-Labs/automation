# Базовый образ: официальный Python 3.12 на Debian bookworm с зафиксированным тегом.
FROM python:3.12-slim-bookworm

# Часовой пояс контейнера, чтобы задания выполнялись по местному времени.
ENV TZ=Europe/Chisinau
# Установка tzdata без интерактивных вопросов.
ARG DEBIAN_FRONTEND=noninteractive

# Установка cron и tzdata, настройка часового пояса и очистка кэша apt.
RUN apt-get update \
    && apt-get install -y --no-install-recommends cron tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo "$TZ" > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория со скриптом.
WORKDIR /opt/lab03

# Установка зависимостей Python из зафиксированного списка.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование скрипта получения курса валют.
COPY currency_exchange_rate.py .

# Копирование заданий cron в системный каталог с обязательными правами 0644.
COPY cronjob /etc/cron.d/lab03
RUN chmod 0644 /etc/cron.d/lab03

# Копирование точки входа и назначение прав на выполнение.
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh

# Точка входа: подготовка окружения и запуск cron.
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
