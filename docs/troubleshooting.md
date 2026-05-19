## Bedrock Anthropic access error

If LiteLLM returns:

"Model use case details have not been submitted for this account"

the LiteLLM proxy is working, but AWS Bedrock is blocking the Anthropic model until the account completes Anthropic model access setup.

Resolution:
1. Open Amazon Bedrock in the AWS Console.
2. Confirm the region matches the LiteLLM config.
3. Go to Model access / Model catalog.
4. Submit use case details for Anthropic models.
5. Wait several minutes and retry.

Temporary workaround:
Use an Amazon Bedrock model such as Nova Lite while Anthropic access is pending.

## Bedrock daily token quota

If LiteLLM returns a 429 error with:

"Too many tokens per day, please wait before trying again."

the LiteLLM proxy, authentication, and Bedrock model routing are working, but the AWS account has reached the daily token quota for that Bedrock model.

Resolution:
1. Wait for the quota window to reset.
2. Try a different Bedrock model.
3. Request a quota increase in AWS Service Quotas if needed.
4. Continue local guardrail development with mocked model responses while Bedrock quota is unavailable.

## Custom guardrail import resolution issues

During LiteLLM startup, the proxy failed to load the custom guardrail with errors similar to:

```txt
ImportError: Could not import HiddenLayerPIIGuardrail from custom_guardrail
```

and

```txt
ModuleNotFoundError: No module named 'config.custom_guardrail'
```

### Root Cause

LiteLLM dynamically imports custom guardrails relative to the config file path. Python package resolution required explicit package initialization and `PYTHONPATH` configuration.

The project structure uses:

```txt
config/custom_guardrail.py
src/guardrails/
```

Without package initialization, Python could not resolve imports correctly during LiteLLM startup.

### Resolution

Added package initialization files:

```bash
touch config/__init__.py
touch src/__init__.py
touch src/guardrails/__init__.py
```

Started LiteLLM with explicit project root pathing:

```bash
PYTHONPATH=. litellm --config config/litellm.config.yaml --port 4000
```

### Key Learning

When LiteLLM dynamically loads custom guardrails, Python module resolution must be configured correctly for local project imports.

Explicit package initialization and `PYTHONPATH` configuration ensured the custom guardrail could successfully import internal detector modules.