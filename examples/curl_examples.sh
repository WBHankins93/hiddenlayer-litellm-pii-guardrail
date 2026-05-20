#!/usr/bin/env bash

set -e

BASE_URL="${BASE_URL:-http://localhost:4000}"
API_KEY="${LITELLM_MASTER_KEY:-bh-hiddenlayer-demo}"
MODEL="${MODEL:-bedrock-amazon-nova-lite}"

echo "Listing configured models..."
curl "$BASE_URL/v1/models" \
  -H "Authorization: Bearer $API_KEY"

echo
echo "Testing safe prompt..."
curl "$BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"$MODEL\",
    \"messages\": [
      {
        \"role\": \"user\",
        \"content\": \"Say hello in one sentence.\"
      }
    ]
  }"

echo
echo "Testing email PII blocking..."
curl "$BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"$MODEL\",
    \"messages\": [
      {
        \"role\": \"user\",
        \"content\": \"My email is test@example.com\"
      }
    ]
  }"

echo
echo "Testing SSN PII blocking..."
curl "$BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"$MODEL\",
    \"messages\": [
      {
        \"role\": \"user\",
        \"content\": \"My SSN is 123-45-6789\"
      }
    ]
  }"