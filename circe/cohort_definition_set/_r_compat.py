"""Small compatibility helpers mirroring the R CohortGenerator/SqlRender string rules.

The legacy cohort-definition layout is defined by R code: CSV headers use
``SqlRender::snakeCaseToCamelCase``, file stems use ``stringi::stri_sprintf``
plus ``stringi::stri_trans_general(..., "latin-ascii")``.  These helpers keep
the Python loader byte-for-byte compatible for the cases that matter when
looking up files on disk.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from collections.abc import Sequence
from typing import Any

logger = logging.getLogger(__name__)

_SNAKE_CASE_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")

# stringi's Latin-ASCII transliteration decomposes most accented Latin letters
# through NFKD.  These do not decompose and need explicit mappings.  Non-Latin
# scripts are deliberately left untouched, matching R:
#   stri_trans_general(c("café", "Straße", "Ærø", "Москва"), "latin-ascii")
#   -> "cafe", "Strasse", "AEro", "Москва"
_LATIN_FALLBACK = {
    "ß": "ss",
    "ẞ": "SS",
    "Æ": "AE",
    "æ": "ae",
    "Œ": "OE",
    "œ": "oe",
    "Ø": "O",
    "ø": "o",
    "Đ": "D",
    "đ": "d",
    "Ð": "D",
    "ð": "d",
    "Þ": "TH",
    "þ": "th",
    "Ł": "L",
    "ł": "l",
    "Ħ": "H",
    "ħ": "h",
    "Ŋ": "N",
    "ŋ": "n",
    "Ŧ": "T",
    "ŧ": "t",
    "Ə": "E",
    "ə": "e",
}


def is_snake_case(value: str) -> bool:
    """Return whether *value* matches SqlRender's snake_case header pattern."""
    return bool(_SNAKE_CASE_RE.fullmatch(value))


def snake_case_to_camel_case(value: str) -> str:
    """Mirror ``SqlRender::snakeCaseToCamelCase`` exactly.

    The R implementation lower-cases the input, replaces ``_<letter>`` with the
    upper-case letter, then removes underscores before digits.  In particular
    mixed-case headers such as ``cohort_ID`` become ``cohortId``.
    """
    result = value.lower()
    for letter in "abcdefghijklmnopqrstuvwxyz":
        result = result.replace("_" + letter, letter.upper())
    result = re.sub(r"_([0-9])", r"\1", result)
    return result


def normalize_header(value: str) -> str:
    """Apply R's snake_case -> camelCase conversion only to snake_case headers."""
    header = value.strip()
    if is_snake_case(header):
        return snake_case_to_camel_case(header)
    return header


def transliterate_latin_ascii(value: str) -> str:
    """Mirror ``stringi::stri_trans_general(value, "latin-ascii")``.

    Uses PyICU when available for exact ICU parity.  The pure-Python fallback
    handles accented Latin letters and the common non-decomposing Latin
    characters while leaving non-Latin scripts unchanged, as R does.
    """
    if not value:
        return value

    try:
        from icu import Transliterator  # type: ignore[import-not-found]
    except ImportError:
        return _fallback_transliterate_latin_ascii(value)

    try:
        return str(Transliterator.createInstance("Latin-ASCII").transliterate(value))
    except Exception:  # pragma: no cover - ICU runtime edge case
        logger.debug("ICU Latin-ASCII transliteration failed for %r", value, exc_info=True)
        return _fallback_transliterate_latin_ascii(value)


def _fallback_transliterate_latin_ascii(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    characters: list[str] = []
    for character in decomposed:
        if unicodedata.combining(character):
            continue
        replacement = _LATIN_FALLBACK.get(character)
        if replacement is not None:
            characters.append(replacement)
        else:
            characters.append(character)

    result = "".join(characters)
    if result != value:
        logger.debug("Transliterated %r to %r using the fallback Latin-ASCII map", value, result)
    return result


def format_file_stem(format_string: str, values: Sequence[Any]) -> str:
    """Format a legacy JSON/SQL file stem with R ``stri_sprintf`` semantics."""
    if not isinstance(format_string, str) or not format_string:
        raise ValueError("cohort_file_name_format must be a non-empty string")
    try:
        formatted = format_string % tuple(values)
    except TypeError:
        # R's stringi::stri_sprintf coerces character values for numeric
        # conversions (e.g. stri_sprintf("%d", "1") -> "1").
        coerced: list[Any] = []
        for value in values:
            text = str(value).strip()
            try:
                coerced.append(int(text))
                continue
            except ValueError:
                pass
            try:
                coerced.append(float(text))
                continue
            except ValueError:
                coerced.append(value)
        try:
            formatted = format_string % tuple(coerced)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Could not format cohort file stem with format {format_string!r} "
                f"and values {tuple(values)!r}: {exc}"
            ) from exc
    except ValueError as exc:
        raise ValueError(
            f"Could not format cohort file stem with format {format_string!r} "
            f"and values {tuple(values)!r}: {exc}"
        ) from exc

    stem = transliterate_latin_ascii(str(formatted))
    if not stem:
        raise ValueError(
            f"Cohort file stem is empty after formatting (format={format_string!r}, values={tuple(values)!r})"
        )
    return stem


__all__ = [
    "format_file_stem",
    "is_snake_case",
    "normalize_header",
    "snake_case_to_camel_case",
    "transliterate_latin_ascii",
]
