#!/bin/sh
# Сценарий запуска тестового сервера: установка открытого ключа Ansible и запуск sshd.
set -eu

# Ключ передаётся из .env; без него контейнер не запускается.
if [ -z "${ANSIBLE_SSH_PUBKEY:-}" ]; then
    echo "Ошибка: переменная ANSIBLE_SSH_PUBKEY не задана." >&2
    exit 1
fi

printf '%s\n' "$ANSIBLE_SSH_PUBKEY" > /home/ansible/.ssh/authorized_keys
chown ansible:ansible /home/ansible/.ssh/authorized_keys
chmod 0600 /home/ansible/.ssh/authorized_keys

# Каталог разделения привилегий sshd отсутствует после запуска контейнера.
install -d -m 0755 /run/sshd

# Без systemd Apache не запускается сам после перезапуска контейнера.
# Если Apache уже установлен плейбуком, он запускается здесь.
if [ -x /etc/init.d/apache2 ]; then
    service apache2 start
fi

exec /usr/sbin/sshd -D -e
