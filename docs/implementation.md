## Prompt Input Guardrail Validation

The custom guardrail was configured in LiteLLM using `pre_call` mode and validated against both required PII types.

### Email Address Test

Input:

```txt
My email is test@example.com
```

Result:

```json
{
  "error": {
    "message": "PII detected",
    "code": "400",
    "provider_specific_fields": {
      "phase": "prompt_input",
      "detected_entities": ["EMAIL_ADDRESS"],
      "guardrail_name": "hiddenlayer-pii-pre",
      "guardrail_mode": "pre_call"
    }
  }
}
```

### SSN Test

Input:

```txt
My SSN is 123-45-6789
```

Result:

```json
{
  "error": {
    "message": "PII detected",
    "code": "400",
    "provider_specific_fields": {
      "phase": "prompt_input",
      "detected_entities": ["US_SOCIAL_SECURITY_NUMBER"],
      "guardrail_name": "hiddenlayer-pii-pre",
      "guardrail_mode": "pre_call"
    }
  }
}
```

### Validation Summary

The guardrail successfully blocks sensitive PII before the request is forwarded to the Bedrock-backed model.