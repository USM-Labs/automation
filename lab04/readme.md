# Лабораторная работа 4: настройка Jenkins для автоматизации задач DevOps

## Цель

Цель работы: научиться настраивать Jenkins для автоматизации задач DevOps.

## Требования

- Docker 24+ (проверено на Docker Engine 29.8.2)
- Docker Compose v2 (команда `docker compose`, проверено на версии 5.6.0)
- свободные порты хоста 8080 и 50000

На моей машине порт 8080 занят контейнером `php_apache` (сервис lab02prep). Без его
остановки контроллер не запускается:

```
Bind for 0.0.0.0:8080 failed: port is already allocated
```

Поэтому перед `docker compose up` контейнер останавливается, а после работы запускается снова:

```
docker stop php_apache
# ... работа с lab04 ...
docker start php_apache
```

Версии компонентов, с которыми выполнена проверка:

| Компонент | Версия |
|-----------|--------|
| Jenkins (образ `jenkins/jenkins:lts`) | 2.580.1 LTS, Java 21.0.12 |
| Образ агента | `jenkins/ssh-agent:bookworm-jdk21` (Debian 12.10, Java 21.0.6) |
| PHP | 8.2.35 |
| Composer | 2.10.3 (из образа `composer:2.10`) |
| PHPUnit | 11.5.57 |
| Плагин SSH Build Agents | 3.1097.v868116049892 |
| Плагин Git | 5.11.0 |
| Плагин Timestamper | 1.30 |
| Плагин JUnit | 1442.vb_b_a_467df2767 |

## Структура проекта

```
lab04/
├── .dockerignore
├── .env.example
├── Dockerfile
├── Jenkinsfile
├── docker-compose.yml
├── isbn-tools/
│   ├── composer.json
│   ├── composer.lock
│   ├── phpunit.xml.dist
│   ├── src/
│   │   ├── InvalidIsbnException.php
│   │   ├── Isbn.php
│   │   └── IsbnValidator.php
│   └── tests/
│       ├── IsbnTest.php
│       └── IsbnValidatorTest.php
├── readme.md
└── secrets/
    └── .gitkeep
```

| Файл | Назначение |
|------|------------|
| `docker-compose.yml` | сервисы `jenkins-controller` и `ssh-agent`, тома `jenkins_home` и `jenkins_agent_volume`, сеть `jenkins-network` |
| `Dockerfile` | образ SSH-агента: `jenkins/ssh-agent:bookworm-jdk21` + PHP CLI, расширения для PHPUnit, unzip, Composer |
| `.dockerignore` | исключает ключи, `.env`, исходники проекта и документацию из контекста сборки образа |
| `.env.example` | шаблон файла `.env` с переменной `JENKINS_AGENT_SSH_PUBKEY` |
| `Jenkinsfile` | описание конвейера: стадии `Install Dependencies` и `Test`, блок `post` |
| `isbn-tools/composer.json` | описание PHP-библиотеки, автозагрузка PSR-4, зависимость PHPUnit `^11.5` |
| `isbn-tools/composer.lock` | зафиксированные версии зависимостей (создан в образе агента, PHP 8.2) |
| `isbn-tools/phpunit.xml.dist` | конфигурация PHPUnit: набор тестов `isbn-tools`, строгие режимы |
| `isbn-tools/src/*.php` | классы библиотеки |
| `isbn-tools/tests/*.php` | модульные тесты |
| `readme.md` | данный отчёт |
| `secrets/.gitkeep` | сохраняет каталог `secrets/` в репозитории; ключи создаются локально и не коммитятся |

В корневом `.gitignore` репозитория игнорируются `lab04/secrets/*` (кроме `.gitkeep`),
`.env`, `vendor/`, `.phpunit.cache/` и `build/`. Закрытый ключ, файл `.env`, каталог
`vendor/` и отчёты сборки в репозиторий не попадают.

## 1. Описание проекта

### 1.1 Библиотека isbn-tools

`isbn-tools`: небольшая PHP-библиотека для проверки и преобразования номеров ISBN
(International Standard Book Number). Существуют два формата номера:

1. **ISBN-10**: 9 цифр и контрольный символ. Сумма произведений цифр на веса 10, 9, ..., 1
   должна делиться на 11. Контрольный символ принимает значения от 0 до 10, значение 10
   записывается буквой `X`.
2. **ISBN-13**: 13 цифр с префиксом 978 или 979. Цифры умножаются поочерёдно на веса 1 и 3,
   сумма должна делиться на 10.

Номер ISBN-10 переводится в ISBN-13 так: к первым 9 цифрам добавляется префикс 978 и
заново вычисляется контрольная цифра. Обратное преобразование возможно только для
префикса 978; у номеров с префиксом 979 нет эквивалента ISBN-10.

Пространство имён: `Splavski\IsbnTools`. Во всех файлах указан `declare(strict_types=1);`,
все классы объявлены как `final`.

| Класс | Метод | Назначение |
|-------|-------|------------|
| `IsbnValidator` | `normalize(string $raw): string` | удаляет дефисы и пробелы, переводит `x` в `X` |
| | `isValidIsbn10(string $isbn): bool` | проверка формата и контрольного символа ISBN-10 |
| | `isValidIsbn13(string $isbn): bool` | проверка префикса, формата и контрольной цифры ISBN-13 |
| | `checkDigit10(string $first9): string` | контрольный символ ISBN-10 (`0`..`9` или `X`) |
| | `checkDigit13(string $first12): string` | контрольная цифра ISBN-13 |
| `Isbn` | `fromString(string $raw): self` | разбор ISBN-10 или ISBN-13, при ошибке исключение `InvalidIsbnException` |
| | `toIsbn13(): string` | номер в формате ISBN-13 |
| | `toIsbn10(): ?string` | номер в формате ISBN-10 или `null` для префикса 979 |
| | `equals(self $other): bool` | сравнение двух номеров |
| `InvalidIsbnException` | нет | наследник `\InvalidArgumentException` |

Объект `Isbn` неизменяемый: конструктор закрытый, номер хранится в свойстве `readonly`
в формате ISBN-13. Сообщения исключений:

- `Номер ISBN "%s" должен содержать 10 или 13 символов.`
- `Номер ISBN "%s" имеет неверную контрольную цифру.`

### 1.2 Тесты

13 тестовых методов в двух классах; с учётом наборов данных (`#[DataProvider]`)
PHPUnit выполняет 23 теста.

| № | Класс | Метод | Что проверяется |
|---|-------|-------|-----------------|
| 1 | `IsbnValidatorTest` | `testNormalizeRemovesHyphensAndSpaces` | `0-8044 2957-x` → `080442957X` |
| 2 | | `testAcceptsValidIsbn10` | 3 набора: `0306406152`, `080442957X`, `0262033844` |
| 3 | | `testRejectsInvalidIsbn10` | 4 набора: неверная контрольная цифра, 9 цифр, `X` не в конце, буквы |
| 4 | | `testAcceptsValidIsbn13` | 3 набора: `9780306406157`, `9780262033848`, `9791090636071` |
| 5 | | `testRejectsInvalidIsbn13` | 4 набора: неверная контрольная цифра, 12 цифр, префикс 977, буква `X` |
| 6 | | `testCheckDigit10CanBeX` | `080442957` → `X` |
| 7 | | `testCheckDigit13` | `978030640615` → `7` |
| 8 | `IsbnTest` | `testConvertsIsbn10ToIsbn13` | `0-306-40615-2` → `9780306406157` |
| 9 | | `testToIsbn10RoundTrip` | `080442957X` → ISBN-13 → `080442957X` |
| 10 | | `testToIsbn10IsNullFor979Prefix` | `979-10-90636-07-1` → `null` |
| 11 | | `testRejectsWrongLength` | исключение и сообщение для `12345` |
| 12 | | `testRejectsWrongCheckDigit` | исключение и сообщение для `978-0-306-40615-8` |
| 13 | | `testEqualsComparesNormalizedValues` | ISBN-10 и ISBN-13 одной книги равны, разные книги не равны |

Все контрольные цифры в тестах вычислены заранее и проверены вручную по правилам из 1.1.

### 1.3 Выбор версий

1. Тег образа агента зафиксирован (`bookworm-jdk21`), а не взят `latest`. Тег `latest`
   со временем начинает указывать на другой выпуск Debian и другую версию PHP, и сборка
   перестаёт быть воспроизводимой. По той же причине Composer копируется из образа с
   тегом `composer:2.10`, а `composer.lock` хранится в репозитории.
2. В Debian 12 (bookworm) пакет `php-cli` содержит PHP 8.2. PHPUnit 12 требует
   PHP >= 8.3, поэтому выбран PHPUnit 11.5 (требует PHP >= 8.2). Попытка установить
   PHPUnit 12 описана в разделе 7.3.
3. `composer.lock` создан командой `composer update` внутри собранного образа агента,
   чтобы зависимости были подобраны для той же версии PHP, на которой работает конвейер.

## 2. Настройка Jenkins Controller

Все команды выполняются из каталога `lab04/`.

1. Запуск контроллера:

   ```
   docker compose up -d jenkins-controller
   ```

2. Пароль для первого входа:

   ```
   docker exec jenkins-controller cat /var/jenkins_home/secrets/initialAdminPassword
   ```

3. В браузере открывается `http://localhost:8080/`, на странице «Unlock Jenkins»
   вводится пароль из шага 2.
4. На странице «Customize Jenkins» выбирается «Install suggested plugins». В набор
   рекомендуемых плагинов (19 плагинов, вместе с зависимостями установлено 94) входят
   Pipeline, Git, SSH Build Agents и Timestamper.
5. Создаётся учётная запись администратора (страница «Create First Admin User»).
6. На странице «Instance Configuration» оставляется Jenkins URL `http://localhost:8080/`,
   затем «Save and Finish» и «Start using Jenkins».
7. Проверка плагинов: Manage Jenkins → Plugins → Installed plugins. Должны быть
   установлены:

   | Плагин | Для чего нужен |
   |--------|----------------|
   | SSH Build Agents (`ssh-slaves`) | способ запуска агента «Launch agents via SSH» |
   | Git (`git`) | получение Jenkinsfile и исходников из репозитория |
   | Timestamper (`timestamper`) | шаг `timestamps()` в Jenkinsfile |
   | JUnit (`junit`) | шаг `junit` в Jenkinsfile; устанавливается как зависимость рекомендуемых плагинов |

   Все четыре плагина установлены после «Install suggested plugins»; отдельная установка
   не потребовалась.

## 3. Настройка SSH-агента

1. Создание пары ключей в каталоге `secrets/` (пароль ключа пустой, так как агент
   подключается без участия пользователя):

   ```
   cd secrets
   ssh-keygen -f jenkins_agent_ssh_key -C jenkins-agent
   cd ..
   ```

   OpenSSH по умолчанию создаёт ключ типа ed25519. Параметр `-C jenkins-agent` задаёт
   комментарий ключа вместо имени пользователя и хоста. Результат:
   `secrets/jenkins_agent_ssh_key` (закрытый ключ) и `secrets/jenkins_agent_ssh_key.pub`
   (открытый ключ).

2. Создание файла `.env` по шаблону `.env.example`. Открытый ключ записывается одной
   строкой:

   ```
   printf 'JENKINS_AGENT_SSH_PUBKEY=%s\n' "$(cat secrets/jenkins_agent_ssh_key.pub)" > .env
   ```

   Docker Compose читает `.env` из каталога проекта и подставляет значение в
   `JENKINS_AGENT_SSH_PUBKEY=${JENKINS_AGENT_SSH_PUBKEY}`. Скрипт образа `jenkins/ssh-agent`
   при старте записывает этот ключ в `/home/jenkins/.ssh/authorized_keys`.

3. Файл `.dockerignore` исключает из контекста сборки `secrets/`, `.env`, `isbn-tools/`,
   `readme.md` и `Jenkinsfile`. Образу агента эти файлы не нужны: ключ передаётся через
   переменную окружения, а исходники агент получает из Git во время сборки. Так закрытый
   ключ не попадает в контекст сборки и в слои образа.

4. Сборка образа агента и перезапуск проекта, чтобы применить `.env`:

   ```
   docker compose up -d --build
   ```

5. Проверка:

   ```
   $ docker compose exec ssh-agent php --version
   PHP 8.2.35 (cli) (built: Oct 21 2026 06:29:51) (NTS)
   Copyright (c) The PHP Group
   Zend Engine v4.2.35, Copyright (c) Zend Technologies
       with Zend OPcache v8.2.35, Copyright (c), by Zend Technologies
   ```

Состав `Dockerfile`:

| Инструкция | Назначение |
|------------|------------|
| `FROM jenkins/ssh-agent:bookworm-jdk21` | базовый образ с sshd, Java 21 и git |
| `php-cli` | интерпретатор PHP 8.2 |
| `php-xml` | расширения dom, xml, xmlwriter, необходимые PHPUnit |
| `php-mbstring` | расширение mbstring, необходимое PHPUnit |
| `unzip` | распаковка архивов пакетов Composer |
| `COPY --from=composer:2.10` | Composer 2.10 из официального образа |

## 4. Подключение агента к Jenkins

### 4.1 Учётные данные

1. Manage Jenkins → Credentials → System → Global credentials (unrestricted) → Add Credentials.
2. Поля:

   | Поле | Значение |
   |------|----------|
   | Kind | SSH Username with private key |
   | Scope | Global |
   | ID | `ssh-agent-key` |
   | Description | Ключ SSH-агента ssh-agent1 |
   | Username | `jenkins` |
   | Private Key | Enter directly → содержимое файла `secrets/jenkins_agent_ssh_key` |
   | Passphrase | пусто |

3. Create.

### 4.2 Проверка ключа хоста (Known hosts file)

Для узла выбрана стратегия «Known hosts file Verification Strategy». Контроллер подключается
только к хосту, чей ключ уже записан в `/var/jenkins_home/.ssh/known_hosts`; подмена хоста
`ssh-agent` в сети будет обнаружена. Стратегия «Non verifying» такой проверки не выполняет.

Ключ хоста агента заносится в `known_hosts` контроллера до запуска узла:

```
docker exec jenkins-controller sh -c 'mkdir -p ~/.ssh && ssh-keyscan -H ssh-agent >> ~/.ssh/known_hosts'
```

Команда выполняется внутри контроллера, поэтому имя `ssh-agent` разрешается через сеть
`jenkins-network`. Ключ `-H` хеширует имена хостов в файле.

Образ `jenkins/ssh-agent` создаёт ключи хоста заново при каждом создании контейнера.
После пересоздания `ssh-agent` (например, `docker compose up -d` после изменения `.env`)
запись в `known_hosts` устаревает, и её нужно обновить (см. раздел 7.3, проблема 3).

### 4.3 Узел ssh-agent1

1. Manage Jenkins → Nodes → New Node.
2. Node name: `ssh-agent1`, тип Permanent Agent, Create.
3. Поля:

   | Поле | Значение |
   |------|----------|
   | Number of executors | 1 |
   | Remote root directory | `/home/jenkins/agent` |
   | Labels | `php-agent` |
   | Usage | Only build jobs with label expressions matching this node |
   | Launch method | Launch agents via SSH |
   | Host | `ssh-agent` |
   | Credentials | `jenkins (Ключ SSH-агента ssh-agent1)` |
   | Host Key Verification Strategy | Known hosts file Verification Strategy |
   | Port (Advanced) | 22 |
   | Availability | Keep this agent online as much as possible |

4. Save.

Режим Usage «Only build jobs with label expressions matching this node» означает, что на
агенте выполняются только задания с меткой `php-agent`.

Журнал узла (Nodes → ssh-agent1 → Log) после успешного подключения (сокращено):

```
[10/26/26 07:43:45] [SSH] SSH host key matches key in Known Hosts file. Connection will be allowed.
[10/26/26 07:43:45] [SSH] Authentication successful.
...
[10/26/26 07:43:45] [SSH] Starting sftp client.
[10/26/26 07:43:45] [SSH] Copying latest remoting.jar...
[10/26/26 07:43:45] [SSH] Copied 1,418,560 bytes.
Expanded the channel window size to 4MB
[10/26/26 07:43:45] [SSH] Starting agent process: cd "/home/jenkins/agent" && java  -jar remoting.jar -workDir /home/jenkins/agent -jar-cache /home/jenkins/agent/remoting/jarCache
...
<===[JENKINS REMOTING CAPACITY]===>   channel started
Remoting version: 3386.v353e57a_1b_ea_0
Launcher: SSHLauncher
Communication Protocol: Standard in/out
This is a Unix agent
Agent successfully connected and online
```

Время в журналах Jenkins указано в UTC (часовой пояс контейнера контроллера).

## 5. Создание pipeline

### 5.1 Задание

New Item → имя `isbn-tools-pipeline` → тип Pipeline → OK. Раздел Pipeline:

| Поле | Значение |
|------|----------|
| Definition | Pipeline script from SCM |
| SCM | Git |
| Repository URL | `https://github.com/USM-Labs/automation.git` |
| Credentials | none (репозиторий публичный) |
| Branch Specifier | `*/lab04` |
| Script Path | `lab04/Jenkinsfile` |
| Lightweight checkout | включено |

После слияния ветки `lab04` в `main` Branch Specifier меняется на `*/main`.

Jenkinsfile читается контроллером из репозитория, а исходники проекта получает агент:
стадия `Declarative: Checkout SCM` выполняется на узле `ssh-agent1`.

### 5.2 Jenkinsfile

Каркас из задания сохранён: агент с меткой `php-agent`, две стадии, блок `post` с
сообщениями `always`, `success` и `failure`. Добавлено:

| Элемент | Назначение |
|---------|------------|
| `options { timestamps() }` | время у каждой строки журнала (плагин Timestamper) |
| `options { timeout(time: 10, unit: 'MINUTES') }` | прерывание зависшей сборки через 10 минут |
| `environment { PROJECT_DIR = 'lab04/isbn-tools' }` | каталог проекта задаётся в одном месте |
| `dir("${PROJECT_DIR}")` | команды выполняются в каталоге проекта |

Стадия **Install Dependencies**:

1. `php --version` и `composer --version` записывают в журнал версии окружения агента.
2. `composer validate --strict` проверяет `composer.json` и соответствие ему
   `composer.lock`; любое предупреждение считается ошибкой.
3. `composer install --no-interaction --no-progress --prefer-dist` устанавливает
   зависимости строго по `composer.lock`, без вопросов и без индикатора прогресса.

Стадия **Test**: `vendor/bin/phpunit --log-junit build/junit.xml` запускает тесты из
`phpunit.xml.dist` и сохраняет отчёт в формате JUnit. Каталог `build/` PHPUnit создаёт сам.

Блок **post**: в `always` шаг `junit` публикует `build/junit.xml` (страница Tests
сборки), `allowEmptyResults: true` не даёт шагу завершиться ошибкой, если стадия Test не
дошла до запуска тестов; затем выводится `Pipeline completed.`. В `success` и `failure`
выводятся сообщения из задания.

## 6. Результат выполнения

Сборка запускается кнопкой Build Now. Журнал сборки №1 (Console Output, сокращено:
строки получения исходников из Git и часть строк загрузки пакетов заменены на `...`):

```
Started by user Splavski Maxim
...
[Pipeline] Start of Pipeline
[Pipeline] node
Running on ssh-agent1 in /home/jenkins/agent/workspace/isbn-tools-pipeline
[Pipeline] {
[Pipeline] stage
[Pipeline] { (Declarative: Checkout SCM)
[Pipeline] checkout
...
Commit message: "ci(lab04): add Jenkinsfile for php-agent pipeline"
First time build. Skipping changelog.
[Pipeline] }
[Pipeline] // stage
[Pipeline] withEnv
[Pipeline] {
[Pipeline] withEnv
[Pipeline] {
[Pipeline] timestamps
[Pipeline] {
[Pipeline] timeout
[2026-10-26T07:44:19.722Z] Timeout set to expire in 10 min
[Pipeline] {
[Pipeline] stage
[Pipeline] { (Install Dependencies)
[Pipeline] echo
[2026-10-26T07:44:19.765Z] Preparing project...
[Pipeline] dir
[2026-10-26T07:44:19.776Z] Running in /home/jenkins/agent/workspace/isbn-tools-pipeline/lab04/isbn-tools
[Pipeline] {
[Pipeline] sh
...
[2026-10-26T07:44:20.118Z] + php --version
[2026-10-26T07:44:20.118Z] PHP 8.2.35 (cli) (built: Oct 21 2026 06:29:51) (NTS)
[2026-10-26T07:44:20.118Z] Copyright (c) The PHP Group
[2026-10-26T07:44:20.118Z] Zend Engine v4.2.35, Copyright (c) Zend Technologies
[2026-10-26T07:44:20.118Z]     with Zend OPcache v8.2.35, Copyright (c), by Zend Technologies
[Pipeline] sh
[2026-10-26T07:44:20.404Z] + composer --version
[2026-10-26T07:44:20.404Z] Composer version 2.10.3 2026-08-27 13:34:23
[2026-10-26T07:44:20.404Z] PHP version 8.2.35 (/usr/bin/php8.2)
[2026-10-26T07:44:20.404Z] Run the "diagnose" command to get more detailed diagnostics output.
[Pipeline] sh
[2026-10-26T07:44:20.698Z] + composer validate --strict
[2026-10-26T07:44:20.698Z] ./composer.json is valid
[Pipeline] sh
[2026-10-26T07:44:20.971Z] + composer install --no-interaction --no-progress --prefer-dist
[2026-10-26T07:44:20.971Z] Installing dependencies from lock file (including require-dev)
[2026-10-26T07:44:20.971Z] Verifying lock file contents can be installed on current platform.
[2026-10-26T07:44:21.224Z] Package operations: 27 installs, 0 updates, 0 removals
[2026-10-26T07:44:21.225Z]   - Downloading staabm/side-effects-detector (1.0.5)
...
[2026-10-26T07:44:39.141Z]   - Installing phpunit/phpunit (11.5.57): Extracting archive
[2026-10-26T07:44:39.394Z] Generating autoload files
[2026-10-26T07:44:39.394Z] 25 packages you are using are looking for funding.
[2026-10-26T07:44:39.394Z] Use the `composer fund` command to find out more!
[Pipeline] }
[Pipeline] // dir
[Pipeline] }
[Pipeline] // stage
[Pipeline] stage
[Pipeline] { (Test)
[Pipeline] echo
[2026-10-26T07:44:39.465Z] Running tests...
[Pipeline] dir
[2026-10-26T07:44:39.470Z] Running in /home/jenkins/agent/workspace/isbn-tools-pipeline/lab04/isbn-tools
[Pipeline] {
[Pipeline] sh
[2026-10-26T07:44:39.751Z] + vendor/bin/phpunit --log-junit build/junit.xml
[2026-10-26T07:44:39.751Z] PHPUnit 11.5.57 by Sebastian Bergmann and contributors.
[2026-10-26T07:44:39.751Z] 
[2026-10-26T07:44:39.751Z] Runtime:       PHP 8.2.35
[2026-10-26T07:44:39.751Z] Configuration: /home/jenkins/agent/workspace/isbn-tools-pipeline/lab04/isbn-tools/phpunit.xml.dist
[2026-10-26T07:44:39.751Z] 
[2026-10-26T07:44:39.751Z] .......................                                           23 / 23 (100%)
[2026-10-26T07:44:39.751Z] 
[2026-10-26T07:44:39.751Z] Time: 00:00.002, Memory: 8.00 MB
[2026-10-26T07:44:39.751Z] 
[2026-10-26T07:44:39.752Z] OK (23 tests, 26 assertions)
[Pipeline] }
[Pipeline] // dir
[Pipeline] }
[Pipeline] // stage
[Pipeline] stage
[Pipeline] { (Declarative: Post Actions)
[Pipeline] junit
[2026-10-26T07:44:39.850Z] Recording test results
[2026-10-26T07:44:40.356Z] [Checks API] No suitable checks publisher found.
[Pipeline] echo
[2026-10-26T07:44:40.388Z] Pipeline completed.
[Pipeline] echo
[2026-10-26T07:44:40.404Z] All stages completed successfully!
[Pipeline] }
[Pipeline] // stage
[Pipeline] }
[Pipeline] // timeout
[Pipeline] }
[Pipeline] // timestamps
[Pipeline] }
[Pipeline] // withEnv
[Pipeline] }
[Pipeline] // withEnv
[Pipeline] }
[Pipeline] // node
[Pipeline] End of Pipeline
Finished: SUCCESS
```

На странице сборки №1 отображается ссылка `Tests (no failures)`. Страница Tests,
сформированная шагом `junit`, сообщает `All 23 tests are passing!`: 23 теста пройдено,
0 ошибок, 0 пропущено.

## 7. Ответы на вопросы

### 7.1 Преимущества Jenkins для автоматизации задач DevOps

1. **Конвейер как код.** Jenkinsfile хранится в репозитории вместе с проектом, поэтому
   изменения конвейера проходят ту же историю версий и ревью, что и код.
2. **Распределённое выполнение.** Контроллер только планирует задания и хранит
   результаты, а сборки выполняются на агентах в отдельных окружениях с нужными
   инструментами (здесь: PHP 8.2 и Composer только в образе агента).
3. **Экосистема плагинов.** Более тысячи плагинов подключают системы контроля версий,
   способы запуска агентов, отчёты тестов и уведомления без собственной разработки.
4. **Собственный сервер и открытый код.** Jenkins распространяется по лицензии MIT и
   разворачивается на своей инфраструктуре, без ограничений поставщика на минуты сборки.
5. **Воспроизводимость и аудит.** Для каждой сборки сохраняются журнал, ревизия
   исходников, результаты тестов и время выполнения, поэтому любую сборку можно разобрать
   и повторить.

### 7.2 Типы агентов Jenkins

Агенты различаются по двум признакам: по времени жизни и по способу подключения
к контроллеру.

**(а) По времени жизни**

| Тип | Описание |
|-----|----------|
| Постоянный агент (Permanent Agent) | узел создаётся вручную и существует постоянно; так настроен `ssh-agent1` |
| Облачный (временный) агент | создаётся под конкретную сборку и удаляется после неё; плагины Docker, Kubernetes, Amazon EC2 |
| Встроенный узел (Built-In Node) | исполнители на самом контроллере; для сборок не рекомендуется, так как сборка получает доступ к файлам контроллера |

**(б) По способу подключения**

| Способ | Описание |
|--------|----------|
| SSH (Launch agents via SSH) | соединение открывает контроллер: он входит на машину агента по ключу, копирует туда `remoting.jar` и стартует процесс агента; этот способ выбран для `ssh-agent1` |
| Входящий агент (inbound) | направление обратное: процесс на машине агента устанавливает связь с контроллером, либо через отдельный TCP-порт (по умолчанию 50000, он опубликован в `docker-compose.yml`), либо по WebSocket через основной HTTP-порт |
| Служба Windows | входящий агент, установленный как служба Windows |
| Запуск командой (command launcher) | контроллер запускает агент произвольной командой на своей стороне |

### 7.3 Проблемы и решения

| № | Проблема | Причина | Решение |
|---|----------|---------|---------|
| 1 | `composer install` в образе из задания (только `apt-get install -y php-cli`, Composer добавлен отдельно) завершается ошибкой: `phpunit/phpunit 11.5.57 requires ext-dom * -> it is missing from your system. Install or enable PHP's dom extension.`, для `sebastian/exporter 6.3.2`: `requires ext-mbstring *` | пакет `php-cli` в Debian не содержит расширений dom, xml, xmlwriter и mbstring, которые требует PHPUnit; в образе также нет `unzip` | в `Dockerfile` добавлены пакеты `php-xml`, `php-mbstring` и `unzip` |
| 2 | узел `ssh-agent1` не подключается, в журнале: `[SSH] No Known Hosts file was found at /var/jenkins_home/.ssh/known_hosts. Please ensure one is created at this path and that Jenkins can read it.` и `Key exchange was not finished, connection is closed.` | узел создан со стратегией Known hosts file до того, как в контроллере появился файл `known_hosts` | выполнена команда `ssh-keyscan` из раздела 4.2; при следующей попытке: `SSH host key matches key in Known Hosts file. Connection will be allowed.` |
| 3 | после пересоздания контейнера `ssh-agent` узел отключился (`Connection was broken`), повторный запуск: `[SSH] The SSH key presented by the remote host does not match the key saved in the Known Hosts file against this host. Connections to this host will be denied until the two keys match.` | образ `jenkins/ssh-agent` генерирует новые ключи хоста при создании контейнера, старая запись в `known_hosts` больше не совпадает | удалена старая запись и добавлена новая: `docker exec jenkins-controller sh -c 'ssh-keygen -R ssh-agent -f ~/.ssh/known_hosts && ssh-keyscan -H ssh-agent >> ~/.ssh/known_hosts'`, после чего узел подключился (`Agent successfully connected and online`) |
| 4 | `composer require --dev phpunit/phpunit:^12` в образе агента: `phpunit/phpunit[12.5.8, ..., 12.5.40] require php >=8.3 -> your php version (8.2.35) does not satisfy that requirement.` | в Debian 12 (bookworm) PHP 8.2, а PHPUnit 12 требует PHP 8.3 | в `composer.json` указан PHPUnit `^11.5` |

Кроме того, порт 8080 на моей машине занят контейнером `php_apache`; это учтено в разделе
«Требования».

## Остановка и очистка

```
docker compose down       # остановка и удаление контейнеров, данные в томах сохраняются
docker compose down -v    # то же, с удалением томов jenkins_home и jenkins_agent_volume
docker start php_apache   # возврат сервиса lab02prep на порт 8080
```
