import re
from presidio_analyzer import AnalyzerEngine


class PIIDetector:
    def detect(self, text: str):
        raise NotImplementedError


class PresidioPIIDetector(PIIDetector):
    def __init__(self):
        self.analyzer = AnalyzerEngine()

    def detect(self, text: str):
        results = self.analyzer.analyze(
            text=text,
            language="en"
        )

        findings = []

        for result in results:

            findings.append({
                "entity_type": result.entity_type,
                "start": result.start,
                "end": result.end,
                "score": result.score
            })

        return findings


class RegexPIIDetector(PIIDetector):
    SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

    def detect(self, text: str):
        findings = []

        for match in self.SSN_PATTERN.finditer(text):
            findings.append({
                "entity_type": "US_SOCIAL_SECURITY_NUMBER",
                "start": match.start(),
                "end": match.end(),
                "score": 1.0
            })

        return findings


class CompositePIIDetector(PIIDetector):
    def __init__(self):
        self.detectors = [
            PresidioPIIDetector(),
            RegexPIIDetector()
        ]

    def detect(self, text: str):
        findings = []

        for detector in self.detectors:
            findings.extend(detector.detect(text))

        return findings