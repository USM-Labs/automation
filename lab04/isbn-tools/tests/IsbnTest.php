<?php

declare(strict_types=1);

namespace Splavski\IsbnTools\Tests;

use PHPUnit\Framework\Attributes\CoversClass;
use PHPUnit\Framework\TestCase;
use Splavski\IsbnTools\InvalidIsbnException;
use Splavski\IsbnTools\Isbn;
use Splavski\IsbnTools\IsbnValidator;

/**
 * Unit tests for parsing, conversion and comparison of ISBN value objects.
 */
#[CoversClass(Isbn::class)]
#[CoversClass(IsbnValidator::class)]
#[CoversClass(InvalidIsbnException::class)]
final class IsbnTest extends TestCase
{
    public function testConvertsIsbn10ToIsbn13(): void
    {
        self::assertSame('9780306406157', Isbn::fromString('0-306-40615-2')->toIsbn13());
    }

    public function testToIsbn10RoundTrip(): void
    {
        // Преобразование ISBN-10 -> ISBN-13 -> ISBN-10 возвращает исходный номер.
        self::assertSame('080442957X', Isbn::fromString('080442957X')->toIsbn10());
    }

    public function testToIsbn10IsNullFor979Prefix(): void
    {
        self::assertNull(Isbn::fromString('979-10-90636-07-1')->toIsbn10());
    }

    public function testRejectsWrongLength(): void
    {
        $this->expectException(InvalidIsbnException::class);
        $this->expectExceptionMessage('Номер ISBN "12345" должен содержать 10 или 13 символов.');

        Isbn::fromString('12345');
    }

    public function testRejectsWrongCheckDigit(): void
    {
        $this->expectException(InvalidIsbnException::class);
        $this->expectExceptionMessage('Номер ISBN "978-0-306-40615-8" имеет неверную контрольную цифру.');

        Isbn::fromString('978-0-306-40615-8');
    }

    public function testEqualsComparesNormalizedValues(): void
    {
        $fromIsbn10 = Isbn::fromString('0 306 40615 2');
        $fromIsbn13 = Isbn::fromString('978-0-306-40615-7');

        self::assertTrue($fromIsbn10->equals($fromIsbn13));
        self::assertFalse($fromIsbn10->equals(Isbn::fromString('9780262033848')));
    }
}
