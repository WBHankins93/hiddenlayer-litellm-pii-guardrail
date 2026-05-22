import pytest
from src.guardrails.detectors import (
    PresidioPIIDetector,
    RegexPIIDetector,
    CompositePIIDetector,
)
from src.guardrails.pii_guardrail import PIIGuardrail


class TestPresidioPIIDetector:
    """Tests for Presidio-based PII detection."""

    def setup_method(self):
        self.detector = PresidioPIIDetector()

    def test_detects_email(self):
        findings = self.detector.detect("Contact me at test@example.com")
        entity_types = [f["entity_type"] for f in findings]
        assert "EMAIL_ADDRESS" in entity_types

    def test_detects_ssn(self):
        findings = self.detector.detect("My SSN is 123-45-6789")
        entity_types = [f["entity_type"] for f in findings]
        assert "US_SOCIAL_SECURITY_NUMBER" in entity_types

    def test_clean_text_returns_empty(self):
        findings = self.detector.detect("Hello, how are you?")
        assert findings == []


class TestRegexPIIDetector:
    """Tests for regex-based PII detection."""

    def setup_method(self):
        self.detector = RegexPIIDetector()

    def test_detects_ssn_format(self):
        findings = self.detector.detect("My SSN is 123-45-6789")
        assert len(findings) == 1
        assert findings[0]["entity_type"] == "US_SOCIAL_SECURITY_NUMBER"
        assert findings[0]["score"] == 1.0

    def test_ignores_partial_ssn(self):
        findings = self.detector.detect("Call 123-45 for info")
        assert findings == []

    def test_ignores_ssn_without_boundaries(self):
        findings = self.detector.detect("ID0123-45-67890")
        assert findings == []

    def test_clean_text_returns_empty(self):
        findings = self.detector.detect("Nothing sensitive here")
        assert findings == []


class TestCompositePIIDetector:
    """Tests for composite detection with deduplication."""

    def setup_method(self):
        self.detector = CompositePIIDetector()

    def test_detects_email_and_ssn_together(self):
        text = "Email: test@example.com SSN: 123-45-6789"
        findings = self.detector.detect(text)
        entity_types = {f["entity_type"] for f in findings}
        assert "EMAIL_ADDRESS" in entity_types
        assert "US_SOCIAL_SECURITY_NUMBER" in entity_types

    def test_deduplicates_ssn_findings(self):
        findings = self.detector.detect("My SSN is 123-45-6789")
        ssn_findings = [f for f in findings if f["entity_type"] == "US_SOCIAL_SECURITY_NUMBER"]
        assert len(ssn_findings) == 1


class TestPIIGuardrail:
    """Tests for guardrail allow/block decisions."""

    def setup_method(self):
        self.guardrail = PIIGuardrail()

    def test_allows_clean_text(self):
        result = self.guardrail.inspect("Hello, how are you?")
        assert result["allowed"] is True
        assert result["findings"] == []

    def test_blocks_email(self):
        result = self.guardrail.inspect("My email is test@example.com")
        assert result["allowed"] is False
        entity_types = [f["entity_type"] for f in result["findings"]]
        assert "EMAIL_ADDRESS" in entity_types

    def test_blocks_ssn(self):
        result = self.guardrail.inspect("My SSN is 123-45-6789")
        assert result["allowed"] is False
        entity_types = [f["entity_type"] for f in result["findings"]]
        assert "US_SOCIAL_SECURITY_NUMBER" in entity_types

    def test_blocks_mixed_pii(self):
        text = "Email me at test@example.com, SSN 123-45-6789"
        result = self.guardrail.inspect(text)
        assert result["allowed"] is False
        entity_types = {f["entity_type"] for f in result["findings"]}
        assert "EMAIL_ADDRESS" in entity_types
        assert "US_SOCIAL_SECURITY_NUMBER" in entity_types

    def test_allows_non_blocked_entity(self):
        result = self.guardrail.inspect("Call me at 555-867-5309")
        assert result["allowed"] is True