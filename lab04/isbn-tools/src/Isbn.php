<?php

declare(strict_types=1);

namespace Splavski\IsbnTools;

/**
 * Immutable ISBN value object; stores the number in ISBN-13 form.
 */
final class Isbn
{
    /**
     * @param string $isbn13 normalized and validated ISBN-13
     */
    private function __construct(private readonly string $isbn13)
    {
    }

    /**
     * Parses an ISBN-10 or ISBN-13 with optional hyphens and spaces.
     *
     * @param string $raw ISBN as entered by a user
     *
     * @return self value object in ISBN-13 form
     *
     * @throws InvalidIsbnException if the length or the check digit is wrong
     */
    public static function fromString(string $raw): self
    {
        $isbn = IsbnValidator::normalize($raw);

        if (strlen($isbn) === 10) {
            if (!IsbnValidator::isValidIsbn10($isbn)) {
                throw new InvalidIsbnException(sprintf('Номер ISBN "%s" имеет неверную контрольную цифру.', $raw));
            }
            // ISBN-10 переводится в ISBN-13 с префиксом 978 и новой контрольной цифрой.
            $first12 = '978' . substr($isbn, 0, 9);

            return new self($first12 . IsbnValidator::checkDigit13($first12));
        }

        if (strlen($isbn) === 13) {
            if (!IsbnValidator::isValidIsbn13($isbn)) {
                throw new InvalidIsbnException(sprintf('Номер ISBN "%s" имеет неверную контрольную цифру.', $raw));
            }

            return new self($isbn);
        }

        throw new InvalidIsbnException(sprintf('Номер ISBN "%s" должен содержать 10 или 13 символов.', $raw));
    }

    /**
     * @return string ISBN-13 without separators
     */
    public function toIsbn13(): string
    {
        return $this->isbn13;
    }

    /**
     * Converts back to ISBN-10.
     *
     * @return string|null ISBN-10, or null for the 979 prefix (no ISBN-10 equivalent)
     */
    public function toIsbn10(): ?string
    {
        if (!str_starts_with($this->isbn13, '978')) {
            return null;
        }
        $first9 = substr($this->isbn13, 3, 9);

        return $first9 . IsbnValidator::checkDigit10($first9);
    }

    /**
     * @param self $other another ISBN
     *
     * @return bool true if both denote the same ISBN-13
     */
    public function equals(self $other): bool
    {
        return $this->isbn13 === $other->isbn13;
    }
}
