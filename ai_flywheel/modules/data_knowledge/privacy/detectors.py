"""Privacy & PII Engine — PII detection via regex patterns.

Pure Python regex-based detectors for common PII types including
email, phone, SSN, credit cards, IP addresses, and name patterns.
"""

from __future__ import annotations

import re

from .schemas import PIIDetectionItem

# ------------------------------------------------------------------
# Regex Patterns
# ------------------------------------------------------------------

_EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)

_PHONE_PATTERN = re.compile(
    r"(?<!\d)"
    r"(?:"
    r"\+?1[\s\-.]?\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}"  # US: +1 (xxx) xxx-xxxx
    r"|"
    r"\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}"  # US: (xxx) xxx-xxxx
    r"|"
    r"\+\d{1,3}[\s\-.]?\d{1,4}[\s\-.]?\d{1,4}[\s\-.]?\d{1,9}"  # International
    r")"
    r"(?!\d)"
)

_SSN_PATTERN = re.compile(
    r"\b\d{3}-\d{2}-\d{4}\b"
)

_CREDIT_CARD_PATTERN = re.compile(
    r"\b(?:\d{4}[\s\-]?){3}\d{4}\b"
)

_IPV4_PATTERN = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
)

_NAME_PREFIX_PATTERN = re.compile(
    r"\b(?:Mr|Mrs|Ms|Miss|Dr|Prof|Rev|Sir|Madam)\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b"
)


# ------------------------------------------------------------------
# Luhn Check for Credit Cards
# ------------------------------------------------------------------


def _luhn_check(number: str) -> bool:
    """Validate a credit card number using the Luhn algorithm."""
    digits = [int(d) for d in number if d.isdigit()]
    if len(digits) != 16:
        return False

    # Double every second digit from the right
    checksum = 0
    for i, digit in enumerate(reversed(digits)):
        if i % 2 == 1:
            doubled = digit * 2
            checksum += doubled - 9 if doubled > 9 else doubled
        else:
            checksum += digit

    return checksum % 10 == 0


# ------------------------------------------------------------------
# Individual Detectors
# ------------------------------------------------------------------


def detect_email(text: str) -> list[PIIDetectionItem]:
    """Detect email addresses in text."""
    detections: list[PIIDetectionItem] = []
    for match in _EMAIL_PATTERN.finditer(text):
        detections.append(
            PIIDetectionItem(
                pii_type="email",
                value=match.group(),
                start=match.start(),
                end=match.end(),
                confidence=0.95,
            )
        )
    return detections


def detect_phone(text: str) -> list[PIIDetectionItem]:
    """Detect phone numbers (US + international) in text."""
    detections: list[PIIDetectionItem] = []
    for match in _PHONE_PATTERN.finditer(text):
        value = match.group().strip()
        # Filter out short matches that are likely not phone numbers
        digits_only = re.sub(r"\D", "", value)
        if len(digits_only) < 7:
            continue
        detections.append(
            PIIDetectionItem(
                pii_type="phone",
                value=value,
                start=match.start(),
                end=match.end(),
                confidence=0.85,
            )
        )
    return detections


def detect_ssn(text: str) -> list[PIIDetectionItem]:
    """Detect SSN patterns (xxx-xx-xxxx) in text."""
    detections: list[PIIDetectionItem] = []
    for match in _SSN_PATTERN.finditer(text):
        value = match.group()
        # Exclude obviously invalid SSNs (000, 666, 900-999 area numbers)
        area = int(value[:3])
        if area == 0 or area == 666 or area >= 900:
            continue
        detections.append(
            PIIDetectionItem(
                pii_type="ssn",
                value=value,
                start=match.start(),
                end=match.end(),
                confidence=0.90,
            )
        )
    return detections


def detect_credit_card(text: str) -> list[PIIDetectionItem]:
    """Detect 16-digit card patterns with Luhn check in text."""
    detections: list[PIIDetectionItem] = []
    for match in _CREDIT_CARD_PATTERN.finditer(text):
        value = match.group()
        digits_only = re.sub(r"\D", "", value)
        if len(digits_only) == 16 and _luhn_check(digits_only):
            detections.append(
                PIIDetectionItem(
                    pii_type="credit_card",
                    value=value,
                    start=match.start(),
                    end=match.end(),
                    confidence=0.92,
                )
            )
    return detections


def detect_ip_address(text: str) -> list[PIIDetectionItem]:
    """Detect IPv4 addresses in text."""
    detections: list[PIIDetectionItem] = []
    for match in _IPV4_PATTERN.finditer(text):
        detections.append(
            PIIDetectionItem(
                pii_type="ip_address",
                value=match.group(),
                start=match.start(),
                end=match.end(),
                confidence=0.80,
            )
        )
    return detections


def detect_name_patterns(text: str) -> list[PIIDetectionItem]:
    """Detect name patterns: capitalized word pairs near title keywords (Mr., Ms., Dr., etc.)."""
    detections: list[PIIDetectionItem] = []
    for match in _NAME_PREFIX_PATTERN.finditer(text):
        # The full match includes the prefix + name
        full_value = match.group()
        detections.append(
            PIIDetectionItem(
                pii_type="person_name",
                value=full_value,
                start=match.start(),
                end=match.end(),
                confidence=0.70,
            )
        )
    return detections


# ------------------------------------------------------------------
# Combined Detector
# ------------------------------------------------------------------


def detect_pii(text: str) -> list[PIIDetectionItem]:
    """Run all PII detectors against the given text.

    Returns a combined list of all detections, sorted by position.
    """
    detections: list[PIIDetectionItem] = []
    detections.extend(detect_email(text))
    detections.extend(detect_phone(text))
    detections.extend(detect_ssn(text))
    detections.extend(detect_credit_card(text))
    detections.extend(detect_ip_address(text))
    detections.extend(detect_name_patterns(text))

    # Sort by start position
    detections.sort(key=lambda d: d.start)
    return detections
