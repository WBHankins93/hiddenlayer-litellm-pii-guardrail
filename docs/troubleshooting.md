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