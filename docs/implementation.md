## Prompt Input Guardrail Validation

The custom LiteLLM guardrail was configured in `pre_call` mode and validated against:

- email addresses
- US Social Security Numbers


### Email Address Blocking Test

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