<?php

declare(strict_types=1);

namespace Splavski\IsbnTools\Tests;

use PHPUnit\Framework\Attributes\CoversClass;
use PHPUnit\Framework\Attributes\DataProvider;
use PHPUnit\Framework\TestCase;
use Splavski\IsbnTools\IsbnValidator;

/**
 * Unit tests for check digit calculation and ISBN format validation.
 */
#[CoversClass(IsbnValidator::class)]
final class IsbnValidatorTest extends TestCase
{
    public function testNormalizeRemovesHyphensAndSpaces(): void
    {
        self::assertSame('080442957X', IsbnValidator::normalize('0-8044 2957-x'));
    }

    /**
     * @return array<string, array{string}>
     */
    public static function validIsbn10Provider(): array
    {
        return [
            'обычная контрольная цифра' => ['0306406152'],
            'контрольная цифра X' => ['080442957X'],
            'контрольная цифра 4' => ['0262033844'],
        ];
    }

    #[DataProvider('validIsbn10Provider')]
    public function testAcceptsValidIsbn10(string $isbn): void
    {
        self::assertTrue(IsbnValidator::isValidIsbn10($isbn));
    }

    /**
     * @return array<string, array{string}>
     */
    public static function invalidIsbn10Provider(): array
    {
        return [
            'неверная контрольная цифра' => ['0306406153'],
            'девять цифр' => ['030640615'],
            'X не на последней позиции' => ['03064X6152'],
            'буквы' => ['ABCDEFGHIJ'],
        ];
    }

    #[DataProvider('invalidIsbn10Provider')]
    public function testRejectsInvalidIsbn10(string $isbn): void
    {
        self::assertFalse(IsbnValidator::isValidIsbn10($isbn));
    }

    /**
     * @return array<string, array{string}>
     */
    public static function validIsbn13Provider(): array
    {
        return [
            'префикс 978' => ['9780306406157'],
            'префикс 978, контрольная цифра 8' => ['9780262033848'],
            'префикс 979' => ['9791090636071'],
        ];
    }

    #[DataProvider('validIsbn13Provider')]
    public function testAcceptsValidIsbn13(string $isbn): void
    {
        self::assertTrue(IsbnValidator::isValidIsbn13($isbn));
    }

    /**
     * @return array<string, array{string}>
     */
    public static function invalidIsbn13Provider(): array
    {
        return [
            'неверная контрольная цифра' => ['9780306406158'],
            'двенадцать цифр' => ['978030640615'],
            'неизвестный префикс' => ['9770306406157'],
            'буква X' => ['978030640615X'],
        ];
    }

    #[DataProvider('invalidIsbn13Provider')]
    public function testRejectsInvalidIsbn13(string $isbn): void
    {
        self::assertFalse(IsbnValidator::isValidIsbn13($isbn));
    }

    public function testCheckDigit10CanBeX(): void
    {
        self::assertSame('X', IsbnValidator::checkDigit10('080442957'));
    }

    public function testCheckDigit13(): void
    {
        self::assertSame('7', IsbnValidator::checkDigit13('978030640615'));
    }
}
