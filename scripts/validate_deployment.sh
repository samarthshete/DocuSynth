#!/usr/bin/env bash
set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://localhost:8080}"
RAG_URL="${RAG_URL:-http://localhost:8001}"
DOCUSYNTH_USER="${DOCUSYNTH_USER:-demo}"
DOCUSYNTH_PASSWORD="${DOCUSYNTH_PASSWORD:-demo123}"
SAMPLE_PDF="${SAMPLE_PDF:-}"
QUERY_TEXT="${QUERY_TEXT:-Summarize the key ideas in this document.}"

generate_sample_pdf() {
  local out_path="$1"
  python3 - "$out_path" <<'PY'
from pathlib import Path
import sys

out = Path(sys.argv[1])
pdf = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 95 >>
stream
BT
/F1 18 Tf
72 720 Td
(DocuSynth deployment validation sample PDF.) Tj
0 -28 Td
(This file is used for ingest and query checks.) Tj
ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000241 00000 n 
0000000388 00000 n 
trailer
<< /Root 1 0 R /Size 6 >>
startxref
458
%%EOF
"""
out.write_bytes(pdf)
PY
}

if [[ -z "${SAMPLE_PDF}" ]]; then
  SAMPLE_PDF="/tmp/docusynth_validate_sample.pdf"
  generate_sample_pdf "${SAMPLE_PDF}"
fi

if [[ ! -f "${SAMPLE_PDF}" ]]; then
  echo "[validate] sample PDF not found: ${SAMPLE_PDF}" >&2
  exit 1
fi

check_status_200() {
  local name="$1"
  local url="$2"
  local status
  status="$(curl -sS -o /tmp/docusynth_validate_body.json -w "%{http_code}" "${url}")"
  if [[ "${status}" != "200" ]]; then
    echo "[validate] ${name} failed: status=${status} url=${url}" >&2
    cat /tmp/docusynth_validate_body.json >&2 || true
    exit 1
  fi
  echo "[validate] ${name} OK (${url})"
}

parse_json_field() {
  local file="$1"
  local expr="$2"
  python3 -c "import json; d=json.load(open('${file}')); v=${expr}; print(v if v is not None else '')"
}

echo "[validate] checking backend /health"
check_status_200 "backend health" "${BACKEND_URL}/health"

echo "[validate] checking rag /health"
check_status_200 "rag health" "${RAG_URL}/health"

echo "[validate] login"
login_status="$(curl -sS -o /tmp/docusynth_login.json -w "%{http_code}" \
  -X POST "${BACKEND_URL}/api/v1/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"${DOCUSYNTH_USER}\",\"password\":\"${DOCUSYNTH_PASSWORD}\"}")"
if [[ "${login_status}" != "200" ]]; then
  echo "[validate] login failed: status=${login_status}" >&2
  cat /tmp/docusynth_login.json >&2 || true
  exit 1
fi
TOKEN="$(parse_json_field /tmp/docusynth_login.json "d.get('token')")"
if [[ -z "${TOKEN}" ]]; then
  echo "[validate] login response missing token" >&2
  cat /tmp/docusynth_login.json >&2 || true
  exit 1
fi
echo "[validate] login OK"

echo "[validate] ingest sample PDF"
ingest_status="$(curl -sS -o /tmp/docusynth_ingest.json -w "%{http_code}" \
  -X POST "${BACKEND_URL}/api/v1/ingest" \
  -H "Authorization: Bearer ${TOKEN}" \
  -F "file=@${SAMPLE_PDF}")"
if [[ "${ingest_status}" != "200" ]]; then
  echo "[validate] ingest failed: status=${ingest_status}" >&2
  cat /tmp/docusynth_ingest.json >&2 || true
  exit 1
fi
DOC_ID="$(parse_json_field /tmp/docusynth_ingest.json "d.get('doc_id')")"
if [[ -z "${DOC_ID}" ]]; then
  echo "[validate] ingest response missing doc_id" >&2
  cat /tmp/docusynth_ingest.json >&2 || true
  exit 1
fi
echo "[validate] ingest OK doc_id=${DOC_ID}"

echo "[validate] query sample PDF"
query_status="$(curl -sS -o /tmp/docusynth_query.json -w "%{http_code}" \
  -X POST "${BACKEND_URL}/api/v1/query" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"doc_id\":\"${DOC_ID}\",\"question\":\"${QUERY_TEXT}\",\"top_k\":5}")"
if [[ "${query_status}" != "200" ]]; then
  echo "[validate] query failed: status=${query_status}" >&2
  cat /tmp/docusynth_query.json >&2 || true
  exit 1
fi
ANSWER="$(parse_json_field /tmp/docusynth_query.json "d.get('answer')")"
if [[ -z "${ANSWER}" ]]; then
  echo "[validate] query response missing answer" >&2
  cat /tmp/docusynth_query.json >&2 || true
  exit 1
fi
echo "[validate] query OK"
echo "[validate] deployment checks passed"
