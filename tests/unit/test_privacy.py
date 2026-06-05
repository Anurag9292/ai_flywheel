"""Unit tests for the Privacy & PII Engine — testing detectors directly."""

import pytest

from ai_flywheel.modules.data_knowledge.privacy.detectors import (
    detect_credit_card,
    detect_email,
    detect_phone,
    detect_pii,
    detect_ssn,
)
from ai_flywheel.modules.data_knowledge.privacy.service import PrivacyEngine


def test_detect_email():
    """Test email detection via regex."""
    text = "Contact us at hello@example.com or support@test.io for help."

    results = detect_email(text)

    assert len(results) == 2
    assert results[0].pii_type == "email"
    assert results[0].value == "hello@example.com"
    assert results[1].value == "support@test.io"
    # Confidence should be high
    assert all(r.confidence >= 0.9 for r in results)


def test_detect_phone():
    """Test phone number detection for US formats."""
    text = "Call me at (555) 123-4567 or +1 800-555-0199."

    results = detect_phone(text)

    assert len(results) >= 1
    assert all(r.pii_type == "phone" for r in results)
    # Should detect at least the first number
    values = [r.value for r in results]
    # Check that at least one detected number contains 555-123-4567 digits
    assert any("555" in v and "4567" in v for v in values)


def test_detect_ssn():
    """Test SSN detection (xxx-xx-xxxx format)."""
    text = "My SSN is 123-45-6789 and not 000-12-3456."

    results = detect_ssn(text)

    # Should detect 123-45-6789 but not 000-12-3456 (invalid area code 000)
    assert len(results) == 1
    assert results[0].pii_type == "ssn"
    assert results[0].value == "123-45-6789"


def test_detect_credit_card():
    """Test credit card detection with Luhn validation."""
    # 4532015112830366 passes Luhn check
    text = "Card number: 4532 0151 1283 0366 ending in 0366."

    results = detect_credit_card(text)

    assert len(results) == 1
    assert results[0].pii_type == "credit_card"
    assert "4532" in results[0].value

    # Invalid card number (fails Luhn) — should NOT be detected
    invalid_text = "Not a card: 1234 5678 9012 3456."
    invalid_results = detect_credit_card(invalid_text)
    assert len(invalid_results) == 0


def test_redact_replaces_pii():
    """Test that redaction replaces all detected PII with [REDACTED]."""
    engine = PrivacyEngine()

    text = "Email me at test@example.com, SSN is 123-45-6789."
    detections = detect_pii(text)
    result = engine._redact_content(text, detections)

    assert "test@example.com" not in result.redacted_content
    assert "123-45-6789" not in result.redacted_content
    assert "[REDACTED]" in result.redacted_content
    assert result.redactions_made >= 2


@pytest.mark.asyncio
async def test_sanitize_for_llm():
    """Test that sanitize_for_llm removes PII from text."""
    engine = PrivacyEngine()

    text = "User john@company.com said their SSN is 456-78-9012."
    sanitized = await engine.sanitize_for_llm(text)

    assert "john@company.com" not in sanitized
    assert "456-78-9012" not in sanitized
    assert "[REDACTED]" in sanitized

    # Clean text should pass through unchanged
    clean = "This is a normal sentence without PII."
    result = await engine.sanitize_for_llm(clean)
    assert result == clean
