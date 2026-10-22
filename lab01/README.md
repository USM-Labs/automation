# Лабораторная работа 1: backup.sh

## Описание

`backup.sh` создаёт резервную копию указанной директории в виде архива `tar.gz`.
Имя архива содержит имя директории, текущую дату и время:

```
backup_<имя_директории>_<ГГГГММДД>_<ЧЧММСС>.tar.gz
```

Например: `backup_site_20261026_153012.tar.gz`.

В архив попадает сама директория (относительный путь `site/...`), а не абсолютные пути.
Перед архивацией скрипт проверяет, что исходная директория существует, а директория
назначения существует и доступна для записи. Директория назначения автоматически
не создаётся. Ошибки выводятся в stderr.

## Синтаксис

```
./backup.sh SOURCE_DIR [DEST_DIR]
./backup.sh -h | --help
```

## Параметры

| Аргумент     | Обязательный | По умолчанию | Описание                              |
|--------------|--------------|--------------|---------------------------------------|
| `SOURCE_DIR` | да           | -            | директория, которую нужно сохранить   |
| `DEST_DIR`   | нет          | `/backup`    | директория, куда сохраняется архив    |
| `-h`, `--help` | нет        | -            | показать справку и выйти              |

## Коды возврата

| Код | Значение                                                                 |
|-----|--------------------------------------------------------------------------|
| 0   | архив создан или показана справка                                        |
| 1   | ошибка: нет аргумента, директория не существует, нет прав на запись, сбой tar |

## Примеры

Резервная копия в директорию по умолчанию `/backup`:

```
$ ./backup.sh ~/projects/site
```

Резервная копия в указанную директорию:

```
$ ./backup.sh ~/projects/site /mnt/backups
```

Пример реального запуска (относительные пути):

```
$ ./backup.sh projects/site backups
backup.sh: archive created: backups/backup_site_20261022_200837.tar.gz
$ tar -tzf backups/backup_site_20261022_200837.tar.gz
site/
site/index.html
site/css/
site/css/style.css
```

Справка:

```
$ ./backup.sh -h
Usage: backup.sh SOURCE_DIR [DEST_DIR]
  SOURCE_DIR  directory to back up (required)
  DEST_DIR    destination directory (default: /backup)
  -h, --help  show this help and exit
```

Ошибки:

```
$ ./backup.sh
Usage: backup.sh SOURCE_DIR [DEST_DIR]
  SOURCE_DIR  directory to back up (required)
  DEST_DIR    destination directory (default: /backup)
  -h, --help  show this help and exit
backup.sh: error: source directory is required

$ ./backup.sh /nope
backup.sh: error: source directory '/nope' does not exist

$ ./backup.sh projects/site
backup.sh: error: destination directory '/backup' does not exist (create it first)
```

## Подготовка

Перед первым запуском без второго аргумента нужно создать `/backup` и дать себе права на запись:

```
sudo mkdir /backup && sudo chown $USER /backup
```

Если скрипт потерял право на выполнение:

```
chmod +x backup.sh
```
