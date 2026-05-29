from src.guardrails.detectors import CompositePIIDetector


class PIIGuardrail:

    """Extend this set to block additional Presidio entity types without modifying detection logic. Can be extended to a policy map (block, warn, redact)"""
    BLOCKED_ENTITIES = {
        "EMAIL_ADDRESS",
        "US_SOCIAL_SECURITY_NUMBER",
        "US_SSN"
    }

    def __init__(self):
        self.detector = CompositePIIDetector()

    def inspect(self, text: str) -> dict:
        findings = self.detector.detect(text)

        blocked_findings = [
            finding for finding in findings
            if finding["entity_type"] in self.BLOCKED_ENTITIES
        ]

        return {
            "allowed": len(blocked_findings) == 0,
            "findings": blocked_findings
        }