import sys
import os

sys.path.append(os.path.abspath("."))


from src.guardrails.pii_guardrail import PIIGuardrail


guardrail = PIIGuardrail()


safe_text = "Hello, how are you?"
email_text = "My email is test@example.com"
ssn_text = "My SSN is 123-45-6789"


print(guardrail.inspect(safe_text))
print(guardrail.inspect(email_text))
print(guardrail.inspect(ssn_text))