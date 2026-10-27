<?php

declare(strict_types=1);

/**
 * Web entry point of isbn-tools: checks an ISBN from the query string.
 */

require __DIR__ . '/../vendor/autoload.php';

use Splavski\IsbnTools\InvalidIsbnException;
use Splavski\IsbnTools\Isbn;

/**
 * Escapes a string for HTML output.
 *
 * @param string $value raw value
 *
 * @return string value safe for HTML text and attributes
 */
function e(string $value): string
{
    return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

// Значение берётся только из GET-параметра isbn; пустая строка означает, что номер не введён.
$input = isset($_GET['isbn']) && is_string($_GET['isbn']) ? trim($_GET['isbn']) : '';
$isbn = null;
$error = null;

if ($input !== '') {
    try {
        $isbn = Isbn::fromString($input);
    } catch (InvalidIsbnException $exception) {
        // Неверный номер: код 422 и сообщение исключения.
        http_response_code(422);
        $error = $exception->getMessage();
    }
}

// Примеры для проверки: два номера с префиксом 978, один с префиксом 979 и один неверный.
$samples = ['0-306-40615-2', '978-3-16-148410-0', '979-10-90636-07-1', '0-306-40615-3'];
?>
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>isbn-tools: проверка ISBN</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
<main>
    <h1>Проверка ISBN</h1>
    <p>Введите номер ISBN-10 или ISBN-13; дефисы и пробелы допускаются.</p>

    <form method="get" action="">
        <label for="isbn">Номер ISBN</label>
        <input type="text" id="isbn" name="isbn" value="<?= e($input) ?>" maxlength="32" required>
        <button type="submit">Проверить</button>
    </form>

<?php if ($isbn !== null): ?>
    <table>
        <tr><th>Введено</th><td><?= e($input) ?></td></tr>
        <tr><th>ISBN-13</th><td><?= e($isbn->toIsbn13()) ?></td></tr>
        <tr><th>ISBN-10</th><td><?= e($isbn->toIsbn10() ?? 'нет: префикс 979') ?></td></tr>
        <tr><th>Статус</th><td class="ok">номер корректен</td></tr>
    </table>
<?php elseif ($error !== null): ?>
    <p class="error"><?= e($error) ?></p>
<?php endif; ?>

    <h2>Примеры</h2>
    <ul>
<?php foreach ($samples as $sample): ?>
        <li><a href="?isbn=<?= e(rawurlencode($sample)) ?>"><?= e($sample) ?></a></li>
<?php endforeach; ?>
    </ul>
</main>
</body>
</html>
