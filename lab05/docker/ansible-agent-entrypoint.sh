#!/bin/sh
# Сценарий запуска агента Ansible: установка открытого ключа Jenkins и запуск sshd.
set -eu

# Ключ передаётся из .env; без него контейнер не запускается.
if [ -z "${JENKINS_AGENT_SSH_PUBKEY:-}" ]; then
    echo "Ошибка: переменная JENKINS_AGENT_SSH_PUBKEY не задана." >&2
    exit 1
fi

# Каталог .ssh находится в томе jenkins_ansible_agent_home; права задаются явно.
install -d -m 0700 -o jenkins -g jenkins /home/jenkins/.ssh
printf '%s\n' "$JENKINS_AGENT_SSH_PUBKEY" > /home/jenkins/.ssh/authorized_keys
chown jenkins:jenkins /home/jenkins/.ssh/authorized_keys
chmod 0600 /home/jenkins/.ssh/authorized_keys

# Каталог разделения привилегий sshd отсутствует после запуска контейнера.
install -d -m 0755 /run/sshd

exec /usr/sbin/sshd -D -e
