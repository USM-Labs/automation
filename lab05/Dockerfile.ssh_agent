# Образ SSH-агента Jenkins с PHP и Composer.
# Тег зафиксирован: Debian 12 (bookworm), PHP 8.2, Java 21.
FROM jenkins/ssh-agent:bookworm-jdk21

# Установка PHP CLI, расширений, необходимых PHPUnit (dom, xml, xmlwriter, mbstring),
# и unzip для распаковки пакетов Composer; очистка кэша apt.
RUN apt-get update \
    && apt-get install -y --no-install-recommends php-cli php-xml php-mbstring unzip \
    && rm -rf /var/lib/apt/lists/*

# Composer копируется из официального образа с зафиксированной версией.
COPY --from=composer:2.10 /usr/bin/composer /usr/local/bin/composer
