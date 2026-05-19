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
            print(result.entity_type)

            findings.append({
                "entity_type": result.entity_type,
                "start": result.start,
                "end": result.end,
                "score": result.score
            })

        return findings