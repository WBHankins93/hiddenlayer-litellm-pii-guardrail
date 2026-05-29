#!/usr/bin/env bash

set -e

BASE_URL="${BASE_URL:-http://localhost:4000}"
API_KEY="${LITELLM_MASTER_KEY:?LITELLM_MASTER_KEY must be set}"
MODEL="${MODEL:-bedrock-jamba}"
FALLBACK_MODEL="${FALLBACK_MODEL:-groq-llama}"

echo "Listing configured models..."
curl "$BASE_URL/v1/models" \
  -H "Authorization: Bearer $API_KEY"

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
        \"content\": \"My SSN is 424-45-6839\"
      }
    ]
  }"

echo
echo "Testing safe prompt (Bedrock)..."
curl "$BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"$MODEL\",
    \"messages\": [
      {
        \"role\": \"user\",
        \"content\": \"What is the capital of the United States?\"
      }
    ]
  }"

echo
echo "Testing realistic PII blocking (mixed content)..."
curl "$BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"$FALLBACK_MODEL\",
    \"messages\": [
      {
        \"role\": \"user\",
        \"content\": \"I need help writing a cover letter for a software engineering position. My name is John Smith, my email is john.smith@gmail.com, and my SSN is 433-77-9090. I have 5 years of experience in Python and AWS.\"
      }
    ],
    \"max_tokens\": 200
  }"

echo
echo "Testing safe prompt (Groq fallback)..."
curl "$BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"$FALLBACK_MODEL\",
    \"messages\": [
      {
        \"role\": \"user\",
        \"content\": \"What is the capital of the United States?\"
      }
    ]
  }"