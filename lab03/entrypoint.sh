#!/bin/sh
# Точка входа контейнера: подготавливает окружение и журнал, затем запускает cron.

# Завершать работу при любой ошибке и при обращении к неопределённой переменной.
set -eu

# Файл журнала, в который задания cron записывают свой вывод.
LOG_FILE="/var/log/cron.log"
# Файл с заданиями cron в системном формате.
CRON_FILE="/etc/cron.d/lab03"

# Сохраняет переменные окружения контейнера, так как cron не передаёт их заданиям.
save_environment() {
    env > /etc/environment
    echo "Переменные окружения сохранены в /etc/environment"
}

# Создаёт файл журнала, доступный для записи всем пользователям.
create_log_file() {
    echo "Создание файла журнала..."
    touch "$LOG_FILE"
    chmod 666 "$LOG_FILE"
    echo "Файл журнала создан: $LOG_FILE"
}

# Проверяет наличие файла заданий и выводит его активные строки.
check_cron_file() {
    if [ ! -f "$CRON_FILE" ]; then
        echo "Ошибка: файл $CRON_FILE не найден" >&2
        exit 1
    fi
    echo "Активные строки $CRON_FILE:"
    sed '/^#/d;/^$/d' "$CRON_FILE"
}

# Непрерывно выводит новые строки журнала в стандартный вывод контейнера.
monitor_logs() {
    echo "=== Просмотр журнала cron ==="
    tail -f "$LOG_FILE"
}

# Запускает демон cron на переднем плане, заменяя текущий процесс.
run_cron() {
    echo "=== Запуск демона cron ==="
    exec cron -f
}

save_environment
create_log_file
check_cron_file
monitor_logs &
run_cron
