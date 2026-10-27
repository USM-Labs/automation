# Лабораторная работа 5: настройка тестового сервера с помощью Ansible

## Цель

Цель работы: научиться создавать плейбуки Ansible для автоматизации настройки серверов.

## Требования и версии

- Docker 24+ (проверено на Docker Engine 29.8.2)
- Docker Compose v2 (команда `docker compose`, проверено на версии 5.6.0)
- свободные порты хоста 8080 и 50000 (Jenkins) и 8081 (сайт на тестовом сервере)

Если порт на хосте занят, его нужно освободить или изменить левую часть записи в `ports` файла `compose.yaml`.

Версии компонентов, с которыми выполнена проверка:

| Компонент | Где | Версия |
|-----------|-----|--------|
| Jenkins (`jenkins/jenkins:lts`) | jenkins-controller | 2.580.1 LTS, Java 21.0.12 |
| Базовый образ | ssh-agent | `jenkins/ssh-agent:bookworm-jdk21` (Debian 12.10, Java 21.0.6) |
| PHP / Composer / PHPUnit | ssh-agent | 8.2.35 / 2.10.3 / 11.5.57 |
| Базовый образ | ansible-agent, test-server | `ubuntu:24.04` (Ubuntu 24.04.5 LTS) |
| Java (`openjdk-21-jre-headless`) | ansible-agent | 21.0.12.1 |
| Ansible (пакет `ansible` из Ubuntu) | ansible-agent | 9.2.0, ansible-core 2.16.3, Python 3.12.3 |
| Коллекции `ansible.posix` / `community.general` | ansible-agent | 1.5.4 / 8.3.0 (входят в пакет `ansible`) |
| git / rsync | ansible-agent | 2.43.0 / 3.2.7 |
| OpenSSH / Python | test-server | 9.6p1 / 3.12.3 |
| Apache / PHP / Composer | test-server (ставит Ansible) | 2.4.58 / 8.3.6 / 2.7.1 |
| Плагин Docker (`docker-plugin`) | Jenkins | 1336.v3711dec712de |
| Плагин Docker Pipeline (`docker-workflow`) | Jenkins | 653.v2f2c08eff0ec |
| Плагин GitHub Integration (`github-pullrequest`) | Jenkins | 0.7.5 |
| Плагин SSH Agent (`ssh-agent`) | Jenkins | 433.v9e73d67c3f74 |
| Плагин SSH Build Agents (`ssh-slaves`) | Jenkins | 3.1097.v868116049892 |
| Плагины Git / Pipeline / JUnit | Jenkins | 5.11.0 / 608.v67378e9d3db_1 / 1442.vb_b_a_467df2767 |
| Плагины Timestamper / Credentials Binding | Jenkins | 1.30 / 728.v902a_273b_8947 |

## Структура

```
lab05/
├── .dockerignore
├── .env.example
├── compose.yaml
├── Dockerfile.ssh_agent
├── Dockerfile.ansible_agent
├── Dockerfile.test_server
├── docker/
│   ├── ansible-agent-entrypoint.sh
│   └── test-server-entrypoint.sh
├── ansible/
│   ├── ansible.cfg
│   ├── hosts.ini
│   ├── setup_test_server.yml
│   ├── deploy_isbn_tools.yml
│   └── templates/
│       └── isbn-tools.conf.j2
├── pipelines/
│   ├── php_build_and_test_pipeline.groovy
│   ├── ansible_setup_pipeline.groovy
│   └── php_deploy_pipeline.groovy
├── isbn-tools/
│   ├── composer.json
│   ├── composer.lock
│   ├── phpunit.xml.dist
│   ├── public/
│   │   ├── index.php
│   │   └── style.css
│   ├── src/
│   └── tests/
├── readme.md
└── secrets/
    └── .gitkeep
```

| Файл | Назначение |
|------|------------|
| `compose.yaml` | сервисы `jenkins-controller`, `ssh-agent`, `ansible-agent`, `test-server`; тома и сеть `jenkins-network` |
| `Dockerfile.ssh_agent` | образ SSH-агента для сборки PHP-проекта (без изменений по сравнению с lab04) |
| `Dockerfile.ansible_agent` | образ агента Ansible: Ubuntu 24.04, sshd, Java 21, Ansible, git, rsync |
| `Dockerfile.test_server` | образ тестового сервера: Ubuntu 24.04, sshd, sudo, python3, пользователь `ansible` |
| `docker/*.sh` | сценарии запуска контейнеров: установка открытого ключа из переменной окружения и запуск sshd |
| `.env.example` | шаблон `.env` с тремя открытыми ключами |
| `.dockerignore` | исключает из контекста сборки ключи, `.env`, проект, плейбуки, конвейеры и отчёт |
| `ansible/ansible.cfg` | настройки Ansible: инвентарь, строгая проверка ключа хоста, повышение привилегий |
| `ansible/hosts.ini` | инвентарь: хост `test-server`, пользователь `ansible` |
| `ansible/setup_test_server.yml` | плейбук настройки сервера: Apache2, PHP, виртуальный хост |
| `ansible/deploy_isbn_tools.yml` | плейбук развёртывания isbn-tools |
| `ansible/templates/isbn-tools.conf.j2` | шаблон виртуального хоста Apache |
| `pipelines/*.groovy` | три конвейера Jenkins |
| `isbn-tools/` | PHP-библиотека из lab04 и веб-страница `public/index.php` |
| `secrets/.gitkeep` | сохраняет каталог `secrets/`; ключи создаются локально и не коммитятся |

В корневом `.gitignore` игнорируются `lab05/secrets/*` (кроме `.gitkeep`), `.env`, `vendor/`,
`.phpunit.cache/` и `build/`. Закрытые ключи и файл `.env` в репозиторий не попадают.

## 1. Описание проекта

### 1.1 Стенд

Стенд состоит из четырёх контейнеров в одной сети `jenkins-network`:

| Сервис | Образ | Роль | Порты хоста |
|--------|-------|------|-------------|
| `jenkins-controller` | `jenkins/jenkins:lts` | управляет всеми конвейерами | 8080, 50000 |
| `ssh-agent` | `Dockerfile.ssh_agent` | агент `php-agent`: Composer и PHPUnit | нет |
| `ansible-agent` | `Dockerfile.ansible_agent` | агент `ansible-agent`: выполняет плейбуки | нет |
| `test-server` | `Dockerfile.test_server` | тестовый сервер, который настраивает Ansible | 8081 → 80 |

Подключения и ключи:

| Откуда | Куда | Пользователь | Ключевая пара | Где закрытый ключ |
|--------|------|--------------|---------------|-------------------|
| Jenkins | ssh-agent | `jenkins` | `jenkins_agent_ssh_key` | учётные данные `ssh-agent-key` |
| Jenkins | ansible-agent | `jenkins` | `jenkins_ansible_agent_key` | учётные данные `ansible-agent-key` |
| ansible-agent | test-server | `ansible` | `ansible_test_server_key` | учётные данные `ansible-test-server-key` |

Открытые ключи попадают в контейнеры через переменные окружения из `.env`. Закрытые ключи
хранятся только в Jenkins; в образы и в репозиторий ключи не входят.

### 1.2 Проект isbn-tools

`isbn-tools` перенесён из lab04 без изменений в `src/`, `tests/`, `composer.json` и
`composer.lock`: библиотека проверяет номера ISBN-10 и ISBN-13 и переводит их из одного
формата в другой (класс `Splavski\IsbnTools\Isbn`). Тесты прежние: 23 теста PHPUnit.

### 1.3 Веб-страница

Для развёртывания добавлен каталог `public/`:

- `index.php` принимает номер из GET-параметра `isbn`, вызывает `Isbn::fromString()` и выводит
  таблицу: введённое значение, ISBN-13, ISBN-10 (для префикса 979 выводится `нет: префикс 979`)
  и статус;
- при неверном номере страница возвращает код `422` и сообщение исключения `InvalidIsbnException`;
- под формой приведены четыре примера: три корректных номера и один с неверной контрольной цифрой;
- весь вывод проходит через `htmlspecialchars`; JavaScript не используется;
- `style.css`: системный шрифт, ширина до 40rem, один акцентный цвет.

## 2. Настройка Jenkins Controller

1. Запуск стенда:

   ```
   cp .env.example .env    # затем подставить открытые ключи, см. разделы 3, 4 и 5
   docker compose up -d --build
   ```

2. Пароль для разблокировки:

   ```
   docker compose exec jenkins-controller cat /var/jenkins_home/secrets/initialAdminPassword
   ```

3. На `http://localhost:8080` ввести пароль, выбрать **Install suggested plugins**.
4. Создать первого администратора, оставить Jenkins URL `http://localhost:8080/`.
5. **Manage Jenkins → Plugins → Available plugins**: установить плагины из задания:

   | Плагин | Идентификатор | Версия |
   |--------|---------------|--------|
   | Docker | `docker-plugin` | 1336.v3711dec712de |
   | Docker Pipeline | `docker-workflow` | 653.v2f2c08eff0ec |
   | GitHub Integration | `github-pullrequest` | 0.7.5 |
   | SSH Agent | `ssh-agent` | 433.v9e73d67c3f74 |

   Плагины SSH Build Agents, Git, Pipeline, Timestamper и Credentials Binding входят в набор
   рекомендуемых. JUnit устанавливается как зависимость. После установки Jenkins перезапускается.

## 3. Настройка SSH-агента

`Dockerfile.ssh_agent` совпадает с `Dockerfile` из lab04: `jenkins/ssh-agent:bookworm-jdk21`,
пакеты `php-cli php-xml php-mbstring unzip`, Composer из образа `composer:2.10`.

1. Ключевая пара Jenkins → ssh-agent:

   ```
   ssh-keygen -t ed25519 -N "" -C jenkins-ssh-agent -f secrets/jenkins_agent_ssh_key
   ```

   Открытый ключ записывается в `.env` как `JENKINS_AGENT_SSH_PUBKEY`.

2. Учётные данные: **Manage Jenkins → Credentials → System → Global credentials → Add Credentials**:
   Kind **SSH Username with private key**, ID `ssh-agent-key`, Username `jenkins`,
   Private Key **Enter directly** (содержимое `secrets/jenkins_agent_ssh_key`).

3. Ключи хостов обоих агентов заносятся в `known_hosts` контроллера одной командой:

   ```
   docker compose exec -u jenkins jenkins-controller sh -c \
     'mkdir -p -m 700 ~/.ssh && ssh-keyscan -t ed25519 ssh-agent ansible-agent >> ~/.ssh/known_hosts'
   ```

   Отпечатки в `known_hosts` сравниваются с ключами самих агентов:

   ```
   $ docker compose exec -u jenkins jenkins-controller ssh-keygen -lf /var/jenkins_home/.ssh/known_hosts
   256 SHA256:l8y4rQCyO2czLl1oD1vilpfeB1DBaCQwVNvIj7Q+epk ansible-agent (ED25519)
   256 SHA256:YTIafRsXoiQB3Kj3U3mDJWd2WHodjPFDeu4VtUN4QA8 ssh-agent (ED25519)
   $ docker compose exec ssh-agent ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
   256 SHA256:YTIafRsXoiQB3Kj3U3mDJWd2WHodjPFDeu4VtUN4QA8 root@2413f49d0927 (ED25519)
   $ docker compose exec ansible-agent ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
   256 SHA256:l8y4rQCyO2czLl1oD1vilpfeB1DBaCQwVNvIj7Q+epk root@buildkitsandbox (ED25519)
   ```

   Отпечатки совпадают. Комментарий ключа показывает разницу образов: `jenkins/ssh-agent`
   создаёт ключи хоста при запуске контейнера (`root@<id контейнера>`), а в образе
   `ansible-agent` они созданы при сборке (`root@buildkitsandbox`). Поэтому после
   пересоздания контейнера `ssh-agent` сканирование нужно повторить, как в lab04.

4. Узел: **Manage Jenkins → Nodes → New Node**, имя `ssh-agent1`, **Permanent Agent**:

   | Параметр | Значение |
   |----------|----------|
   | Number of executors | 1 |
   | Remote root directory | `/home/jenkins/agent` |
   | Labels | `php-agent` |
   | Usage | Only build jobs with label expressions matching this node |
   | Launch method | Launch agents via SSH |
   | Host | `ssh-agent` |
   | Credentials | `ssh-agent-key` |
   | Host Key Verification Strategy | Known hosts file Verification Strategy |

## 4. Агент Ansible

### 4.1 Dockerfile.ansible_agent

| Инструкция | Назначение |
|------------|------------|
| `FROM ubuntu:24.04` | задание требует Ubuntu; тег зафиксирован |
| `apt-get install ... openssh-server openssh-client git rsync ansible openjdk-21-jre-headless ca-certificates` | sshd для подключения Jenkins; Java 21 той же основной версии, что у контроллера (Jenkins 2.580.1 требует Java 21 на агенте); git для получения репозитория; rsync и ssh-клиент для модуля `synchronize`; пакет `ansible` 9.2.0 |
| `userdel --remove ubuntu && useradd --uid 1000 ... jenkins` | пользователь `jenkins` с UID 1000, как в образе SSH-агента; в `ubuntu:24.04` UID 1000 занят пользователем `ubuntu` |
| `install -d ... /home/jenkins/agent`, `/home/jenkins/.ssh` | каталоги создаются с владельцем `jenkins`; том `jenkins_ansible_agent_home` при первом создании наследует эти права |
| `printf ... > /etc/ssh/sshd_config.d/10-key-only.conf` и `sshd -t` | вход только по ключу, без root, только пользователь `jenkins`; синтаксис проверяется при сборке |
| `COPY docker/ansible-agent-entrypoint.sh`, `ENTRYPOINT` | сценарий запуска (ниже) |

Пакет `ansible` выбран вместо `ansible-core`: только в нём есть коллекции `ansible.posix`
(модуль `synchronize`) и `community.general` (модули `composer` и `ini_file`).

Сценарий `docker/ansible-agent-entrypoint.sh`:

1. проверяет переменную `JENKINS_AGENT_SSH_PUBKEY`; если она пуста, выводит ошибку и завершает
   контейнер с кодом 1;
2. записывает ключ в `/home/jenkins/.ssh/authorized_keys` с правами `0600` и владельцем `jenkins`;
3. создаёт `/run/sshd` (без этого каталога sshd не запускается);
4. запускает `sshd -D -e`.

В `compose.yaml` переменная `JENKINS_ANSIBLE_AGENT_SSH_PUBKEY` из `.env` передаётся в контейнер
под именем `JENKINS_AGENT_SSH_PUBKEY`. Домашний каталог `/home/jenkins` хранится в томе
`jenkins_ansible_agent_home`, поэтому `~/.ssh/known_hosts` агента сохраняется при пересоздании
контейнера.

### 4.2 Ключи и узел

1. Ключевая пара Jenkins → ansible-agent:

   ```
   ssh-keygen -t ed25519 -N "" -C jenkins-ansible-agent -f secrets/jenkins_ansible_agent_key
   ```

   Открытый ключ записывается в `.env` как `JENKINS_ANSIBLE_AGENT_SSH_PUBKEY`.

2. Учётные данные `ansible-agent-key`: SSH Username with private key, Username `jenkins`,
   закрытый ключ `secrets/jenkins_ansible_agent_key`.
3. Ключ хоста `ansible-agent` уже занесён в `known_hosts` контроллера (раздел 3, шаг 3).
4. Узел `ansible-agent1`: параметры как у `ssh-agent1`, кроме: Labels `ansible-agent`,
   Host `ansible-agent`, Credentials `ansible-agent-key`.

Журнал подключения узла (сокращён):

```
[10/27/26 09:31:01] [SSH] Opening SSH connection to ansible-agent:22.
Searching for ansible-agent in /var/jenkins_home/.ssh/known_hosts
[10/27/26 09:31:01] [SSH] SSH host key matches key in Known Hosts file. Connection will be allowed.
[10/27/26 09:31:01] [SSH] Authentication successful.
[10/27/26 09:31:02] [SSH] Copying latest remoting.jar...
[10/27/26 09:31:02] [SSH] Starting agent process: cd "/home/jenkins/agent" && java  -jar remoting.jar -workDir /home/jenkins/agent -jar-cache /home/jenkins/agent/remoting/jarCache
Remoting version: 3386.v353e57a_1b_ea_0
Agent successfully connected and online
```

Время в журналах Jenkins указано в UTC (часовой пояс контейнеров).

Вывод `ansible --version` на агенте (из конвейера `test-server-setup`):

```
ansible [core 2.16.3]
  config file = /home/jenkins/agent/workspace/test-server-setup/lab05/ansible/ansible.cfg
  configured module search path = ['/home/jenkins/.ansible/plugins/modules', '/usr/share/ansible/plugins/modules']
  ansible python module location = /usr/lib/python3/dist-packages/ansible
  ansible collection location = /home/jenkins/.ansible/collections:/usr/share/ansible/collections
  executable location = /usr/bin/ansible
  python version = 3.12.3 (main, Aug 31 2026, 10:18:26) [GCC 13.3.0] (/usr/bin/python3)
  jinja version = 3.1.2
  libyaml = True
```

Строка `config file` подтверждает, что используется `lab05/ansible/ansible.cfg`.

### 4.3 Настройка Ansible (ansible.cfg)

| Параметр | Значение | Зачем |
|----------|----------|-------|
| `inventory` | `hosts.ini` | инвентарь не нужно указывать в командной строке |
| `host_key_checking` | `True` | ключ хоста `test-server` проверяется по `~/.ssh/known_hosts`; значение по умолчанию записано явно |
| `interpreter_python` | `/usr/bin/python3` | без автоматического поиска интерпретатора и предупреждения о нём |
| `retry_files_enabled` | `False` | файлы `*.retry` не создаются в рабочем каталоге |
| `deprecation_warnings` | `True` | предупреждения об устаревших возможностях не скрываются |
| `become_method`, `become_user` | `sudo`, `root` | повышение привилегий для `become: true` |

Закрытый ключ в `ansible.cfg` и `hosts.ini` намеренно не указан. Он хранится в учётных данных
Jenkins и передаётся параметром `--private-key` (раздел 7.2).

## 5. Тестовый сервер

### 5.1 Dockerfile.test_server

| Инструкция | Назначение |
|------------|------------|
| `FROM ubuntu:24.04` | в Ubuntu 22.04 есть только PHP 8.1, а `isbn-tools` требует `php >=8.2`; в 24.04 PHP 8.3 |
| `apt-get install ... openssh-server sudo python3` | sshd для Ansible, sudo для `become`, python3 для модулей Ansible |
| `useradd --create-home --shell /bin/bash ansible` | пользователь `ansible` без пароля; вход только по ключу |
| `/etc/sudoers.d/ansible` + `visudo -cf` | `ansible ALL=(ALL) NOPASSWD:ALL`, права `0440`; файл проверяется при сборке |
| `10-key-only.conf` + `sshd -t` | `PasswordAuthentication no`, `KbdInteractiveAuthentication no`, `PermitRootLogin no`, `AllowUsers ansible` |
| `EXPOSE 22 80`, `ENTRYPOINT` | SSH для Ansible, HTTP для сайта |

Apache и PHP в образ не входят: их устанавливает плейбук.

Сценарий `docker/test-server-entrypoint.sh` устроен так же, как у агента (переменная
`ANSIBLE_SSH_PUBKEY`, владелец ключа `ansible`), и дополнительно запускает Apache, если он уже
установлен:

```
if [ -x /etc/init.d/apache2 ]; then
    service apache2 start
fi
```

В контейнере нет systemd, поэтому `enabled: true` в задаче `service` не запускает Apache после
перезапуска контейнера; эту роль выполняет сценарий запуска. Проверка:

```
$ docker compose restart test-server
$ docker logs --tail 4 test-server
 * Starting Apache httpd web server apache2
Server listening on 0.0.0.0 port 22.
$ curl -s 'http://localhost:8081/?isbn=978-3-16-148410-0' | grep -E 'ISBN-1[03]<'
        <tr><th>ISBN-13</th><td>9783161484100</td></tr>
        <tr><th>ISBN-10</th><td>316148410X</td></tr>
```

Без ключа контейнер не запускается:

```
$ docker run --rm lab05-test-server
Ошибка: переменная ANSIBLE_SSH_PUBKEY не задана.
```

### 5.2 Ключи

1. Ключевая пара ansible-agent → test-server:

   ```
   ssh-keygen -t ed25519 -N "" -C ansible-test-server -f secrets/ansible_test_server_key
   ```

   Открытый ключ записывается в `.env` как `ANSIBLE_TEST_SERVER_SSH_PUBKEY`; в контейнер он
   передаётся как `ANSIBLE_SSH_PUBKEY`.

2. Учётные данные `ansible-test-server-key`: SSH Username with private key, Username `ansible`,
   закрытый ключ `secrets/ansible_test_server_key`.

3. Ключ хоста `test-server` один раз заносится в `known_hosts` агента и сверяется с ключом сервера:

   ```
   $ docker compose exec -u jenkins ansible-agent sh -c 'ssh-keyscan -t ed25519 test-server >> ~/.ssh/known_hosts'
   $ docker compose exec -u jenkins ansible-agent ssh-keygen -lf /home/jenkins/.ssh/known_hosts
   256 SHA256:IZPqCeo7D1Oqo2UwtQLiYYz/RFfUt2hEA5mGzCs5z54 test-server (ED25519)
   $ docker compose exec test-server ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
   256 SHA256:IZPqCeo7D1Oqo2UwtQLiYYz/RFfUt2hEA5mGzCs5z54 root@buildkitsandbox (ED25519)
   ```

   При первом подключении OpenSSH (параметр `UpdateHostKeys`) сам добавляет в `known_hosts`
   ключи RSA и ECDSA того же сервера в хешированном виде; это штатное поведение клиента.

   Ключи хоста `test-server` созданы при сборке образа, поэтому они не меняются при пересоздании
   контейнера (это проверено в разделе 8.1, пункт 4) и меняются только после пересборки образа.
   После пересборки шаг повторяется.

### 5.3 Инвентарь hosts.ini

```ini
[test_servers]
test-server ansible_host=test-server ansible_port=22 ansible_user=ansible
```

Имя хоста совпадает с именем сервиса в `compose.yaml`; его разрешает DNS сети `jenkins-network`.

## 6. Плейбук setup_test_server.yml

Один play для группы `test_servers` с `become: true`. Переменные: `app_name: isbn-tools`,
`app_root: /var/www/isbn-tools`, `server_name: test-server`, `php_version: "8.3"`.

| № | Задача | Модуль | Зачем |
|---|--------|--------|-------|
| 1 | Установить пакеты Apache, PHP и Composer | `ansible.builtin.apt` | `apache2`, `libapache2-mod-php`, `php-cli`, `php-mbstring`, `composer`, `unzip`, `rsync`; `update_cache` не чаще раза в час (`cache_valid_time: 3600`) |
| 2 | Задать ServerName для всего сервера | `ansible.builtin.copy` | файл `conf-available/servername.conf` со строкой `ServerName test-server` |
| 3 | Включить конфигурацию servername | `ansible.builtin.command` | `a2enconf servername`, `creates:` делает задачу идемпотентной |
| 4 | Создать каталог public проекта | `ansible.builtin.file` | `/var/www/isbn-tools/public`, владелец `root`, группа `www-data`, `0755` |
| 5 | Создать виртуальный хост isbn-tools | `ansible.builtin.template` | `sites-available/isbn-tools.conf` из шаблона |
| 6 | Включить сайт isbn-tools | `ansible.builtin.command` | `a2ensite isbn-tools`, `creates:` |
| 7 | Отключить сайт по умолчанию | `ansible.builtin.command` | `a2dissite 000-default`, `removes:` |
| 8 | Отключить expose_php в php.ini модуля Apache | `community.general.ini_file` | версия PHP не передаётся в заголовке `X-Powered-By` |
| 9 | Запустить Apache | `ansible.builtin.service` | `state: started`; после установки пакета Apache не запущен |

Пакеты: `libapache2-mod-php` подключает PHP к Apache; `php-mbstring` нужен для нормализации
ввода и Composer; `composer` и `unzip` нужны при развёртывании; `rsync` нужен модулю
`synchronize` на стороне сервера.

Задача 8 в обоих запусках показала `ok`: в `/etc/php/8.3/apache2/php.ini` Ubuntu значение уже
`expose_php = Off` (в `cli/php.ini` оно `On`). Задача оставлена: она фиксирует требуемое значение
явно и вернёт его, если файл будет изменён.

Обработчики (handlers), оба подписаны на событие `apache config changed`:

1. `Проверить конфигурацию Apache`: `apache2ctl configtest`, `changed_when: false`;
2. `Перезагрузить Apache`: `service: state=reloaded`.

Обработчики выполняются в порядке объявления, поэтому перезагрузка происходит только после
успешной проверки синтаксиса. Если `configtest` завершится ошибкой, play остановится и Apache
продолжит работать со старой конфигурацией.

Шаблон `templates/isbn-tools.conf.j2`:

```apache
# {{ ansible_managed }}
# Виртуальный хост проекта {{ app_name }}.
<VirtualHost *:80>
    ServerName {{ server_name }}
    DocumentRoot {{ app_root }}/public

    <Directory {{ app_root }}/public>
        Require all granted
        AllowOverride None
        DirectoryIndex index.php
    </Directory>

    ErrorLog ${APACHE_LOG_DIR}/{{ app_name }}_error.log
    CustomLog ${APACHE_LOG_DIR}/{{ app_name }}_access.log combined
</VirtualHost>
```

Первый успешный запуск (сборка #2 задания `test-server-setup`):

```
09:34:13  PLAY [Настроить тестовый сервер для isbn-tools] ********************************
09:34:13  TASK [Gathering Facts] *********************************************************
09:34:16  ok: [test-server]
09:34:16  TASK [Установить пакеты Apache, PHP и Composer] ********************************
09:35:24  changed: [test-server]
...
09:35:34  RUNNING HANDLER [Проверить конфигурацию Apache] ********************************
09:35:34  ok: [test-server]
09:35:34  RUNNING HANDLER [Перезагрузить Apache] *****************************************
09:35:35  changed: [test-server]
09:35:35  PLAY RECAP *********************************************************************
09:35:35  test-server                : ok=12   changed=9    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

Повторный запуск без изменений (сборка #3):

```
09:36:36  PLAY RECAP *********************************************************************
09:36:36  test-server                : ok=10   changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

Во втором запуске ни одна задача не изменила сервер, поэтому обработчики не вызывались
(`ok=10` вместо `ok=12`).

## 7. Конвейеры

Все три задания создаются одинаково: **New Item → Pipeline**, раздел **Pipeline**:

| Параметр | Значение |
|----------|----------|
| Definition | Pipeline script from SCM |
| SCM | Git |
| Repository URL | `https://github.com/USM-Labs/automation.git` |
| Branch Specifier | `*/main` (пока ветка lab05 не была слита: `*/lab05`) |
| Script Path | `lab05/pipelines/<файл>.groovy` |

| Задание | Script Path | Агент |
|---------|-------------|-------|
| `isbn-tools-build` | `lab05/pipelines/php_build_and_test_pipeline.groovy` | `php-agent` |
| `test-server-setup` | `lab05/pipelines/ansible_setup_pipeline.groovy` | `ansible-agent` |
| `isbn-tools-deploy` | `lab05/pipelines/php_deploy_pipeline.groovy` | `ansible-agent` |

Общие опции всех конвейеров: `skipDefaultCheckout()` (репозиторий клонируется явной стадией
`Checkout` с шагом `checkout scm`), `timestamps()`, `timeout(time: 15, unit: 'MINUTES')`.

Порядок запуска: `isbn-tools-build` → `test-server-setup` → `isbn-tools-deploy`.
Из выводов ниже убраны строки `[Pipeline]` и служебные строки git.

### 7.1 Сборка и тестирование (php_build_and_test_pipeline.groovy)

Файл получен из `Jenkinsfile` lab04: добавлены стадии `Checkout` и `Report`, путь проекта
изменён на `lab05/isbn-tools`.

| Стадия | Действия |
|--------|----------|
| `Checkout` | `checkout scm` |
| `Install Dependencies` | `php --version`, `composer --version`, `composer validate --strict`, `composer install --no-interaction --no-progress --prefer-dist` |
| `Test` | `vendor/bin/phpunit --log-junit build/junit.xml` |
| `Report` | `junit testResults: "${PROJECT_DIR}/build/junit.xml"` |

Отчёт публикуется без `allowEmptyResults`: если файл отчёта не создан, стадия `Report`
завершается ошибкой.

Сборка #1 (сокращено):

```
Running on ssh-agent1 in /home/jenkins/agent/workspace/isbn-tools-build
09:32:13  Timeout set to expire in 15 min
09:32:21  Preparing project...
09:32:22  + php --version
09:32:23  PHP 8.2.35 (cli) (built: Oct 21 2026 06:29:51) (NTS)
09:32:24  + composer validate --strict
09:32:25  ./composer.json is valid
09:32:26  + composer install --no-interaction --no-progress --prefer-dist
09:32:26  Verifying lock file contents can be installed on current platform.
09:32:27  Package operations: 27 installs, 0 updates, 0 removals
09:32:50    - Installing phpunit/phpunit (11.5.57): Extracting archive
09:32:50  Generating autoload files
09:32:51  Running tests...
09:32:52  + vendor/bin/phpunit --log-junit build/junit.xml
09:32:52  PHPUnit 11.5.57 by Sebastian Bergmann and contributors.
09:32:52  Runtime:       PHP 8.2.35
09:32:52  .......................                                           23 / 23 (100%)
09:32:52  OK (23 tests, 26 assertions)
09:32:53  Recording test results
09:32:56  Pipeline completed.
09:32:57  All stages completed successfully!
Finished: SUCCESS
```

На странице сборки ссылка **Tests (no failures)**: 23 пройдено, 0 ошибок, 0 пропущено.

### 7.2 Настройка тестового сервера (ansible_setup_pipeline.groovy)

| Стадия | Действия |
|--------|----------|
| `Checkout` | `checkout scm` |
| `Run Playbook` | в каталоге `lab05/ansible`: `ansible --version`; внутри `withCredentials`: `ansible-playbook setup_test_server.yml --syntax-check`, затем `ansible-playbook setup_test_server.yml --private-key "$ANSIBLE_KEY"` |

```groovy
withCredentials([sshUserPrivateKey(credentialsId: 'ansible-test-server-key', keyFileVariable: 'ANSIBLE_KEY')]) {
    sh 'ansible-playbook setup_test_server.yml --syntax-check'
    sh 'ansible-playbook setup_test_server.yml --private-key "$ANSIBLE_KEY"'
}
```

`withCredentials` создаёт временный файл с закрытым ключом и удаляет его после выполнения блока.
Команды записаны в одинарных кавычках: переменную `$ANSIBLE_KEY` раскрывает оболочка, а не Groovy,
поэтому путь к ключу не попадает в текст скрипта. В журнале путь заменён на `****`.

Сборка #2 (сокращено, полный список задач в разделе 6):

```
09:34:10  + ansible --version
09:34:10  ansible [core 2.16.3]
09:34:11  + ansible-playbook setup_test_server.yml --syntax-check
09:34:12  playbook: setup_test_server.yml
09:34:12  + ansible-playbook setup_test_server.yml --private-key ****
09:34:13  PLAY [Настроить тестовый сервер для isbn-tools] ********************************
...
09:35:35  test-server                : ok=12   changed=9    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
09:35:35  Test server configured successfully.
Finished: SUCCESS
```

Сборка #1 этого задания завершилась ошибкой до того, как ключ `test-server` был занесён в
`known_hosts` агента (раздел 8.3, проблема 1).

### 7.3 Развёртывание (php_deploy_pipeline.groovy)

| Стадия | Действия |
|--------|----------|
| `Checkout` | `checkout scm` |
| `Copy Files` | `ansible-playbook deploy_isbn_tools.yml --syntax-check`, затем `--tags copy` |
| `Configure` | `ansible-playbook deploy_isbn_tools.yml --tags configure` |

Обе стадии работают в `lab05/ansible` внутри `withCredentials` с тем же ключом
`ansible-test-server-key`. Теги плейбука соответствуют стадиям один к одному; без тегов плейбук
выполняет развёртывание полностью.

Задачи `deploy_isbn_tools.yml`:

| Тег | Задача | Модуль | Параметры |
|-----|--------|--------|-----------|
| `copy` | Скопировать файлы проекта на сервер | `ansible.posix.synchronize` | `delete: true`; `verify_host: true`; `owner: false`, `group: false`; `--chmod=D755,F644`; исключены `tests/`, `vendor/`, `build/`, `.phpunit.cache/`, `phpunit.xml.dist` |
| `configure` | Установить зависимости Composer без dev-пакетов | `community.general.composer` | `command: install`, `no_dev: true`, `optimize_autoloader: true` (из `composer.lock`) |
| `configure` | Назначить владельца, группу и права файлов проекта | `ansible.builtin.file` | `recurse: true`, `root:www-data`, `u=rwX,g=rX,o=rX` |
| `configure` | Запросить страницу с проверочным номером | `ansible.builtin.uri` | `http://localhost/?isbn=0306406152` |
| `configure` | Убедиться, что страница вернула ISBN-13 | `ansible.builtin.assert` | в ответе есть `9780306406157` |

Каталог `vendor/` на сервере исключён из синхронизации, поэтому `delete: true` его не удаляет:
rsync не удаляет на приёмнике исключённые пути без `--delete-excluded`. Это видно по повторным
запускам: `vendor/` остаётся на месте, задача Composer показывает `ok`.

Задача Composer показывает `ok` и на чистом сервере. У `isbn-tools` нет зависимостей времени
выполнения (только `php >=8.2`), поэтому `composer install --no-dev` не устанавливает пакеты,
а только создаёт `vendor/autoload.php`; модуль считает изменением только установку пакетов.
Что автозагрузка работает, подтверждают две последние задачи: страница вызывает класс `Isbn`.

Сборка #5 (после пересоздания контейнера сервера, раздел 8.1, пункт 4; сокращено):

```
Running on ansible-agent1 in /home/jenkins/agent/workspace/isbn-tools-deploy
09:43:44  + ansible-playbook deploy_isbn_tools.yml --syntax-check
09:43:46  playbook: deploy_isbn_tools.yml
09:43:46  + ansible-playbook deploy_isbn_tools.yml --tags copy --private-key ****
09:43:51  TASK [Скопировать файлы проекта на сервер] *************************************
09:43:51  [DEPRECATION WARNING]: The connection's stdin object is deprecated. Call
09:43:51  display.prompt_until(msg) instead. This feature will be removed in version
09:43:51  2.19. Deprecation warnings can be disabled by setting
09:43:51  deprecation_warnings=False in ansible.cfg.
09:43:52  changed: [test-server]
09:43:52  test-server                : ok=2    changed=1    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
09:43:53  + ansible-playbook deploy_isbn_tools.yml --tags configure --private-key ****
09:43:56  TASK [Установить зависимости Composer без dev-пакетов] *************************
09:43:57  ok: [test-server]
09:43:57  TASK [Назначить владельца, группу и права файлов проекта] **********************
09:43:59  changed: [test-server]
09:44:00  TASK [Убедиться, что страница вернула ISBN-13] *********************************
09:44:00  ok: [test-server] => {
09:44:00      "changed": false,
09:44:00      "msg": "Страница вернула 9780306406157."
09:44:00  }
09:44:00  test-server                : ok=5    changed=1    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
09:44:01  isbn-tools deployed successfully.
Finished: SUCCESS
```

Повторное развёртывание без изменений в проекте (сборка #4): в обеих стадиях `changed=0`.

```
09:40:01  test-server                : ok=2    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
09:40:15  test-server                : ok=5    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

Права на сервере после развёртывания:

```
$ docker compose exec test-server ls -la /var/www/isbn-tools
drwxr-xr-x 5 root www-data  4096 Oct 27 09:43 .
-rw-r--r-- 1 root www-data   641 Oct 27 09:36 composer.json
-rw-r--r-- 1 root www-data 65513 Oct 27 09:36 composer.lock
drwxr-xr-x 2 root www-data  4096 Oct 27 09:36 public
drwxr-xr-x 2 root www-data  4096 Oct 27 09:36 src
drwxr-xr-x 3 root www-data  4096 Oct 27 09:43 vendor
```

Тестов, `phpunit.xml.dist` и dev-пакетов на сервере нет.

### 7.4 Проверка развёрнутого проекта

Страница открывается в браузере по адресу `http://localhost:8081/`. Проверка из командной строки:

```
$ curl -s 'http://localhost:8081/?isbn=0-306-40615-2' | grep -E '<title>|<tr>'
    <title>isbn-tools: проверка ISBN</title>
        <tr><th>Введено</th><td>0-306-40615-2</td></tr>
        <tr><th>ISBN-13</th><td>9780306406157</td></tr>
        <tr><th>ISBN-10</th><td>0306406152</td></tr>
        <tr><th>Статус</th><td class="ok">номер корректен</td></tr>

$ curl -s 'http://localhost:8081/?isbn=979-10-90636-07-1' | grep -E '<tr>'
        <tr><th>Введено</th><td>979-10-90636-07-1</td></tr>
        <tr><th>ISBN-13</th><td>9791090636071</td></tr>
        <tr><th>ISBN-10</th><td>нет: префикс 979</td></tr>
        <tr><th>Статус</th><td class="ok">номер корректен</td></tr>

$ curl -si 'http://localhost:8081/?isbn=0-306-40615-3' | grep -E 'HTTP/|X-Powered|Server:|class="error"'
HTTP/1.1 422 Unprocessable Entity
Server: Apache/2.4.58 (Ubuntu)
    <p class="error">Номер ISBN &quot;0-306-40615-3&quot; имеет неверную контрольную цифру.</p>

$ curl -s 'http://localhost:8081/?isbn=12345' | grep error
    <p class="error">Номер ISBN &quot;12345&quot; должен содержать 10 или 13 символов.</p>
```

Заголовка `X-Powered-By` в ответе нет (задача 8 плейбука). Неверный номер возвращает код `422`,
кавычки в сообщении экранированы.

## 8. Ответы на вопросы

### 8.1 Преимущества Ansible для настройки серверов

1. **Идемпотентность.** Модули описывают требуемое состояние, а не последовательность команд.
   Повторный запуск `setup_test_server.yml` на настроенном сервере дал `changed=0` (раздел 6),
   повторное развёртывание тоже `changed=0` (раздел 7.3). Для `command` то же поведение
   обеспечивают `creates:` и `removes:`.

2. **Без агента на сервере.** На управляемом сервере нужны только sshd, python3 и sudo: образ
   `test-server` содержит ровно это и занимает 215 МБ. Для сравнения, агенту Jenkins нужны
   Java 21 и процесс `remoting.jar`; образ `ansible-agent` с Java и Ansible занимает 1,31 ГБ.
   Ansible подключается по SSH, отдельной службы и дополнительных портов на сервере нет.

3. **Пробный запуск.** `--check --diff` показывает изменения, ничего не меняя. Пробный запуск с
   изменённым в шаблоне `AllowOverride None` на `AllowOverride FileInfo`:

   ```
   TASK [Создать виртуальный хост isbn-tools] *************************************
   --- before: /etc/apache2/sites-available/isbn-tools.conf
   -        AllowOverride None
   +        AllowOverride FileInfo
   changed: [test-server]
   ```

   После пробного запуска в файле на сервере осталось `AllowOverride None`.

4. **Восстановление сервера тем же плейбуком.** Контейнер сервера пересоздан с нуля:

   ```
   $ docker compose up -d --force-recreate --no-deps test-server
   $ curl -sS http://localhost:8081/
   curl: (56) Recv failure: Connection reset by peer
   ```

   Apache и сайта в новом контейнере нет. После запуска `test-server-setup` (сборка #4) и
   `isbn-tools-deploy` (сборка #5):

   ```
   test-server                : ok=12   changed=9    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
   test-server                : ok=2    changed=1    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
   test-server                : ok=5    changed=1    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
   $ curl -s 'http://localhost:8081/?isbn=0-306-40615-2' | grep 'ISBN-13<'
           <tr><th>ISBN-13</th><td>9780306406157</td></tr>
   ```

   Сервер восстановлен за две сборки без ручных действий. Повторно сканировать ключ хоста не
   пришлось: образ не пересобирался, ключи хоста те же.

### 8.2 Другие модули Ansible для управления конфигурацией

Столбец «Коллекция» показывает, что входит в `ansible-core`, а что требует полного пакета
`ansible` (или установки коллекции через `ansible-galaxy`). Отметка «да» означает, что модуль
использован в этой работе.

| Область | Модуль (FQCN) | Коллекция | Назначение | Здесь |
|---------|---------------|-----------|------------|-------|
| Пакеты | `ansible.builtin.apt` | ansible-core | пакеты Debian и Ubuntu | да |
| | `ansible.builtin.package` | ansible-core | пакеты через менеджер ОС, без привязки к дистрибутиву | |
| | `ansible.builtin.dnf` | ansible-core | пакеты RHEL, Fedora | |
| Файлы | `ansible.builtin.copy` | ansible-core | копирование файла или содержимого | да |
| | `ansible.builtin.template` | ansible-core | файл из шаблона Jinja2 | да |
| | `ansible.builtin.lineinfile` | ansible-core | одна строка в файле | |
| | `ansible.builtin.blockinfile` | ansible-core | блок строк с маркерами | |
| | `ansible.builtin.file` | ansible-core | каталоги, права, владельцы, ссылки | да |
| | `community.general.ini_file` | community.general | параметр в INI-файле | да |
| Службы | `ansible.builtin.service` | ansible-core | запуск, остановка, перезагрузка служб | да |
| | `ansible.builtin.systemd_service` | ansible-core | службы systemd, `daemon_reload` | |
| Пользователи | `ansible.builtin.user` | ansible-core | учётные записи | |
| | `ansible.builtin.group` | ansible-core | группы | |
| | `ansible.posix.authorized_key` | ansible.posix | ключи в `authorized_keys` | |
| Развёртывание | `ansible.posix.synchronize` | ansible.posix | rsync между хостами | да |
| | `ansible.builtin.git` | ansible-core | клонирование репозитория на сервер | |
| | `ansible.builtin.unarchive` | ansible-core | распаковка архива | |
| | `ansible.builtin.get_url` | ansible-core | загрузка файла по URL | |
| Веб и PHP | `community.general.apache2_module` | community.general | включение модулей Apache | |
| | `community.general.composer` | community.general | команды Composer | да |
| Проверки | `ansible.builtin.uri` | ansible-core | HTTP-запросы | да |
| | `ansible.builtin.assert` | ansible-core | проверка условий | да |
| Сеть | `community.general.ufw` | community.general | правила межсетевого экрана UFW | |

### 8.3 Проблемы при создании плейбука и их решение

Проблемы перечислены в порядке появления.

**1. Первое подключение к серверу.**

- Симптом: сборка #1 задания `test-server-setup`:

  ```
  09:33:39  fatal: [test-server]: UNREACHABLE! => {"changed": false, "msg": "Failed to connect to the host via ssh: Host key verification failed.", "unreachable": true}
  09:33:39  test-server                : ok=0    changed=0    unreachable=1    failed=0    skipped=0    rescued=0    ignored=0
  ```

- Причина: `host_key_checking = True`, а в `~/.ssh/known_hosts` агента ещё не было ключа
  `test-server`.
- Решение: ключ занесён через `ssh-keyscan` и сверен с отпечатком на сервере (раздел 5.2, шаг 3).
  Отключать проверку (`host_key_checking = False`) не стал: тогда подмена сервера в сети
  осталась бы незамеченной. Сборка #2 прошла успешно.

**2. Файлы проекта на сервере доступны группе на запись.**

- Симптом: после первого развёртывания (сборка #1 `isbn-tools-deploy`) на сервере:

  ```
  drwxrwxr-x 5 root www-data  4096 Oct 27 09:37 .
  -rw-rw-r-- 1 root www-data   641 Oct 27 09:36 composer.json
  drwxrwxr-x 2 root www-data  4096 Oct 27 09:36 public
  drwxrwxr-x 2 root www-data  4096 Oct 27 09:36 src
  ```

  Группа `www-data`, от имени которой работает Apache, могла бы изменять файлы сайта.

- Причина: агент Jenkins на `ansible-agent` запускается через SSH-сессию. В Ubuntu
  `/etc/login.defs` содержит `USERGROUPS_ENAB yes`, и pam_umask для пользователя с собственной
  группой задаёт umask `0002`. Процесс агента наследует его:

  ```
  $ docker compose exec ansible-agent sh -c 'grep Umask /proc/$(pgrep java)/status'
  Umask:	0002
  $ docker compose exec ssh-agent sh -c 'grep Umask /proc/$(pgrep java)/status'
  Umask:	0022
  ```

  git создаёт рабочую копию с правами `664/775`, а `synchronize` (rsync в режиме archive)
  переносит их на сервер.

- Решение, шаг 1: в задачу `file` добавлен `mode: "u=rwX,g=rX,o=rX"`. Права исправились, но
  сборка #2 показала `changed=1` в обеих стадиях без изменений в проекте: rsync возвращал
  владельца и права с агента, задача `file` возвращала их обратно, и так при каждом запуске.
- Решение, шаг 2: в `synchronize` добавлены `owner: false`, `group: false` и
  `--chmod=D755,F644`. Права задаются уже при копировании, задача `file` только подтверждает их.
  Сборки #3 и #4: `changed=0`.

**3. Предупреждение при копировании.**

- Симптом: при каждом запуске задачи `synchronize` выводится
  `[DEPRECATION WARNING]: The connection's stdin object is deprecated` (раздел 7.3).
- Причина: модуль `ansible.posix.synchronize` 1.5.4 обращается к устаревшему атрибуту
  соединения в ansible-core 2.16.3. Это предупреждение о будущей версии 2.19, на результат
  копирования оно не влияет.
- Решение: предупреждение оставлено видимым (`deprecation_warnings = True`). При переходе на
  ansible-core 2.19 потребуется более новая версия коллекции `ansible.posix`.

**4. Модуль synchronize не проверял ключ хоста.**

- Симптом: при ручном запуске плейбука на агенте с ключом `-v` в команде rsync видны параметры,
  отключающие проверку (сокращено):

  ```
  "cmd": "/usr/bin/rsync --delay-updates -F --compress --delete-after --archive --no-owner --no-group --rsh='/usr/bin/ssh -S none -i ... -o Port=22 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null' ...
  ```

  `host_key_checking = True` в `ansible.cfg` действовал только на подключения самого Ansible,
  а копирование файлов шло без проверки сервера.

- Причина: у `ansible.posix.synchronize` параметр `verify_host` по умолчанию `false`, и модуль
  сам добавляет эти параметры ssh.
- Решение: в задачу добавлен `verify_host: true`. После этого в команде остаётся
  `--rsh='/usr/bin/ssh -S none -i ... -o Port=22'`, и rsync использует `~/.ssh/known_hosts` агента.
  Проверка с намеренно заменённым ключом `test-server` в `known_hosts`: копирование
  завершается ошибкой, затем исходный файл восстановлен.

  ```
  @    WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!     @
  Host key for test-server has changed and you have requested strict checking.
  Host key verification failed.
  ```

  Развёртывание после исправления (сборка #7): `changed=0` в обеих стадиях.

## Остановка и очистка

```
# Остановка стенда; с ключом -v удаляются и тома (настройки Jenkins, known_hosts агента).
docker compose down
docker compose down -v
```

Состояние тестового сервера (Apache, PHP, сайт) хранится только в контейнере и исчезает вместе с
ним. После `docker compose up -d` сервер восстанавливается конвейерами `test-server-setup` и
`isbn-tools-deploy`.
