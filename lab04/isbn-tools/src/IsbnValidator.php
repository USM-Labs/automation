<?php

declare(strict_types=1);

namespace Splavski\IsbnTools;

/**
 * Pure static helpers for ISBN-10 and ISBN-13 check digits.
 */
final class IsbnValidator
{
    /**
     * Removes hyphens and spaces and converts a lowercase "x" to "X".
     *
     * @param string $raw ISBN as entered by a user, e.g. "0-306-40615-2"
     *
     * @return string ISBN without separators
     */
    public static function normalize(string $raw): string
    {
        return strtoupper(str_replace(['-', ' '], '', $raw));
    }

    /**
     * Checks a normalized ISBN-10: nine digits, then a digit or "X",
     * weighted sum (weights 10..1) divisible by 11.
     *
     * @param string $isbn normalized ISBN-10
     *
     * @return bool true if the format and the check digit are correct
     */
    public static function isValidIsbn10(string $isbn): bool
    {
        if (preg_match('/^\d{9}[\dX]$/', $isbn) !== 1) {
            return false;
        }

        return self::checkDigit10(substr($isbn, 0, 9)) === $isbn[9];
    }

    /**
     * Checks a normalized ISBN-13: thirteen digits with prefix 978 or 979
     * and a correct mod 10 check digit (weights 1 and 3).
     *
     * @param string $isbn normalized ISBN-13
     *
     * @return bool true if the format, the prefix and the check digit are correct
     */
    public static function isValidIsbn13(string $isbn): bool
    {
        if (preg_match('/^97[89]\d{10}$/', $isbn) !== 1) {
            return false;
        }

        return self::checkDigit13(substr($isbn, 0, 12)) === $isbn[12];
    }

    /**
     * Computes the ISBN-10 check digit.
     *
     * @param string $first9 the first nine digits
     *
     * @return string "0".."9" or "X" (value 10)
     */
    public static function checkDigit10(string $first9): string
    {
        $sum = 0;
        for ($i = 0; $i < 9; $i++) {
            // Вес цифры убывает от 10 до 2.
            $sum += (10 - $i) * (int) $first9[$i];
        }
        $digit = (11 - $sum % 11) % 11;

        return $digit === 10 ? 'X' : (string) $digit;
    }

    /**
     * Computes the ISBN-13 check digit.
     *
     * @param string $first12 the first twelve digits
     *
     * @return string "0".."9"
     */
    public static function checkDigit13(string $first12): string
    {
        $sum = 0;
        for ($i = 0; $i < 12; $i++) {
            // Цифры на чётных позициях имеют вес 1, на нечётных вес 3.
            $sum += ($i % 2 === 0 ? 1 : 3) * (int) $first12[$i];
        }

        return (string) ((10 - $sum % 10) % 10);
    }
}
