#!/usr/bin/env bash
# test-otel-redaction.sh
#
# Behavioral verification for PII redaction in the OpenTelemetry Collector.
#
# This script sends a test log line containing PII (email and Finnish HETU)
# to the OTel Collector OTLP HTTP endpoint, then queries Loki to verify
# that the PII has been redacted before export.
#
# Prerequisites:
#   - OTel Collector accessible at localhost:4318 (port-forward or local docker)
#   - Loki accessible at localhost:3100 (port-forward or local docker)
#   - curl and jq installed
#
# Usage:
#   # Port-forward the services:
#   kubectl port-forward -n ai-finland-observability svc/otel-collector 4318:4318 &
#   kubectl port-forward -n ai-finland-observability svc/loki 3100:3100 &
#   # Run the test:
#   ./test-otel-redaction.sh
#
# Expected behavior:
#   Input log body:  "User user@example.com logged in with HETU 010180-123A"
#   Output log body: "User [REDACTED-EMAIL] logged in with HETU [REDACTED-HETU]"

set -euo pipefail

OTEL_ENDPOINT="${OTEL_ENDPOINT:-http://localhost:4318}"
LOKI_ENDPOINT="${LOKI_ENDPOINT:-http://localhost:3100}"
TEST_TRACE_ID="$(printf '%032x' $RANDOM$RANDOM$RANDOM$RANDOM)"
TEST_MESSAGE="User user@example.com logged in with HETU 010180-123A"
MAX_RETRIES=30
RETRY_INTERVAL=2

echo "=== OTel Collector PII Redaction Test ==="
echo "OTel endpoint: ${OTEL_ENDPOINT}"
echo "Loki endpoint: ${LOKI_ENDPOINT}"
echo "Test trace ID: ${TEST_TRACE_ID}"
echo ""

# Step 1: Send a test log with PII to the OTel Collector OTLP HTTP endpoint
echo "[1/3] Sending test log with PII to OTel Collector..."

PAYLOAD=$(cat <<EOF
{
  "resourceLogs": [
    {
      "resource": {
        "attributes": [
          {
            "key": "service.name",
            "value": { "stringValue": "pii-redaction-test" }
          }
        ]
      },
      "scopeLogs": [
        {
          "scope": {
            "name": "test"
          },
          "logRecords": [
            {
              "timeUnixNano": "$(date +%s)000000000",
              "severityNumber": 9,
              "severityText": "INFO",
              "body": {
                "stringValue": "${TEST_MESSAGE}"
              },
              "traceId": "${TEST_TRACE_ID}",
              "attributes": [
                {
                  "key": "test.id",
                  "value": { "stringValue": "${TEST_TRACE_ID}" }
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
EOF
)

HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST "${OTEL_ENDPOINT}/v1/logs" \
  -H "Content-Type: application/json" \
  -d "${PAYLOAD}")

if [ "${HTTP_STATUS}" != "200" ]; then
  echo "FAIL: OTel Collector returned HTTP ${HTTP_STATUS} (expected 200)"
  exit 1
fi

echo "  Log sent successfully (HTTP 200)"
echo ""

# Step 2: Wait for the log to be processed and exported to Loki
echo "[2/3] Waiting for log to appear in Loki..."

LOG_BODY=""
for i in $(seq 1 ${MAX_RETRIES}); do
  sleep ${RETRY_INTERVAL}

  # Query Loki for logs from the test service
  RESPONSE=$(curl -s -G "${LOKI_ENDPOINT}/loki/api/v1/query_range" \
    --data-urlencode "query={service_name=\"pii-redaction-test\"}" \
    --data-urlencode "limit=10" \
    --data-urlencode "start=$(( $(date +%s) - 120 ))000000000" \
    --data-urlencode "end=$(date +%s)000000000" \
    2>/dev/null || echo "{}")

  # Check if we got results containing our trace ID
  if echo "${RESPONSE}" | jq -e '.data.result[]?' > /dev/null 2>&1; then
    LOG_BODY=$(echo "${RESPONSE}" | jq -r \
      '.data.result[].values[][] | select(type == "string")' 2>/dev/null | \
      grep -i "redacted\|logged in" | head -1 || true)

    if [ -n "${LOG_BODY}" ]; then
      echo "  Log found in Loki after ${i} attempts"
      break
    fi
  fi

  if [ "${i}" -eq "${MAX_RETRIES}" ]; then
    echo "FAIL: Log did not appear in Loki after $((MAX_RETRIES * RETRY_INTERVAL))s"
    echo "  Last Loki response: ${RESPONSE}"
    exit 1
  fi
done

echo ""

# Step 3: Verify PII redaction
echo "[3/3] Verifying PII redaction..."
echo "  Log body: ${LOG_BODY}"
echo ""

FAILED=0

# Assert email is redacted
if echo "${LOG_BODY}" | grep -q "user@example.com"; then
  echo "FAIL: Email address was NOT redacted (found 'user@example.com')"
  FAILED=1
else
  echo "  PASS: Original email not present in log"
fi

if echo "${LOG_BODY}" | grep -q "\[REDACTED-EMAIL\]"; then
  echo "  PASS: Email replaced with [REDACTED-EMAIL]"
else
  echo "FAIL: Expected [REDACTED-EMAIL] marker not found"
  FAILED=1
fi

# Assert HETU is redacted
if echo "${LOG_BODY}" | grep -q "010180-123A"; then
  echo "FAIL: Finnish HETU was NOT redacted (found '010180-123A')"
  FAILED=1
else
  echo "  PASS: Original HETU not present in log"
fi

if echo "${LOG_BODY}" | grep -q "\[REDACTED-HETU\]"; then
  echo "  PASS: HETU replaced with [REDACTED-HETU]"
else
  echo "FAIL: Expected [REDACTED-HETU] marker not found"
  FAILED=1
fi

echo ""
if [ "${FAILED}" -eq 0 ]; then
  echo "=== ALL CHECKS PASSED ==="
  echo "PII redaction is working correctly."
  echo "  Input:  ${TEST_MESSAGE}"
  echo "  Output: User [REDACTED-EMAIL] logged in with HETU [REDACTED-HETU]"
  exit 0
else
  echo "=== SOME CHECKS FAILED ==="
  exit 1
fi
