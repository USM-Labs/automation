<?php

declare(strict_types=1);

namespace Splavski\IsbnTools;

/**
 * Thrown when a string cannot be parsed as a valid ISBN-10 or ISBN-13.
 */
final class InvalidIsbnException extends \InvalidArgumentException
{
}
