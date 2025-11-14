#!/usr/bin/env bash

################################################################################
# check_topic_compatibility.sh
#
# Prüft, ob ein Topic bereit ist für FORWARD_FULL Kompatibilität
#
# Verwendung:
#   SCHEMA_REGISTRY_URL=http://localhost:8081 ./check_topic_compatibility.sh my-topic
#
# Exit Codes:
#   0 - Topic ist kompatibel für FORWARD_FULL
#   1 - Fehler bei der Ausführung
#   2 - Topic ist NICHT kompatibel für FORWARD_FULL
################################################################################

set -euo pipefail

# Konfiguration
SCHEMA_REGISTRY_URL="${SCHEMA_REGISTRY_URL:-http://localhost:8081}"
TOPIC="${1:-}"

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Hilfsfunktion für formatierte Ausgabe
log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Prüfe Parameter
if [ -z "$TOPIC" ]; then
    echo "Usage: $0 <topic-name>"
    echo ""
    echo "Environment Variables:"
    echo "  SCHEMA_REGISTRY_URL - Schema Registry URL (default: http://localhost:8081)"
    echo ""
    echo "Example:"
    echo "  SCHEMA_REGISTRY_URL=http://schema-registry:8081 $0 my-topic"
    exit 1
fi

# Prüfe ob curl verfügbar ist
if ! command -v curl &> /dev/null; then
    log_error "curl is not installed"
    exit 1
fi

# Prüfe ob jq verfügbar ist
if ! command -v jq &> /dev/null; then
    log_error "jq is not installed. Please install jq to use this script."
    exit 1
fi

# Header
echo "================================================================"
log_info "Checking FORWARD_FULL compatibility for topic: $TOPIC"
log_info "Schema Registry: $SCHEMA_REGISTRY_URL"
echo "================================================================"
echo ""

# Subjects für Key und Value
SUBJECTS=(
  "${TOPIC}-key"
  "${TOPIC}-value"
)

overall_ok=true

# Iteriere über alle Subjects
for SUBJECT in "${SUBJECTS[@]}"; do
    echo "---- Subject: ${SUBJECT} ----"

    # Prüfe ob Subject existiert
    http_code=$(curl -s -o /dev/null -w "%{http_code}" "${SCHEMA_REGISTRY_URL}/subjects/${SUBJECT}/versions")

    if [ "$http_code" != "200" ]; then
        log_warn "No subject found → skipping"
        echo ""
        continue
    fi

    # Hole alle Versionen
    versions=$(curl -s "${SCHEMA_REGISTRY_URL}/subjects/${SUBJECT}/versions" | jq -r '.[]')

    if [ -z "$versions" ]; then
        log_warn "No versions found → skipping"
        echo ""
        continue
    fi

    echo "  Versions: $(echo $versions | tr '\n' ' ')"

    # Hole die neueste Version
    latest=$(echo "$versions" | tail -n1)
    echo "  Latest version: $latest"

    # Hole das neueste Schema
    latest_schema=$(curl -s "${SCHEMA_REGISTRY_URL}/subjects/${SUBJECT}/versions/${latest}")
    latest_schema_def=$(echo "$latest_schema" | jq -r '.schema')

    echo "  Testing backward compatibility for ALL versions → FULL readiness"
    subject_ok=true

    # Teste jede Version gegen die neueste
    for v in $versions; do
        # Überspringe die neueste Version (immer kompatibel mit sich selbst)
        if [ "$v" = "$latest" ]; then
            continue
        fi

        echo -n "    Version $v → latest ... "

        # Hole das Schema der älteren Version
        old_schema=$(curl -s "${SCHEMA_REGISTRY_URL}/subjects/${SUBJECT}/versions/${v}")
        old_schema_def=$(echo "$old_schema" | jq -r '.schema')

        # Teste Backward-Kompatibilität: Kann die neueste Version Daten lesen,
        # die mit der alten Version geschrieben wurden?
        # Für FORWARD_FULL müssen alle alten Versionen backward-kompatibel zur neuesten sein
        test_payload=$(jq -n \
            --arg schema "$latest_schema_def" \
            '{schema: $schema}')

        result=$(curl -s \
            -X POST \
            -H "Content-Type: application/vnd.schemaregistry.v1+json" \
            -d "$test_payload" \
            "${SCHEMA_REGISTRY_URL}/compatibility/subjects/${SUBJECT}/versions/${v}")

        compatible=$(echo "$result" | jq -r '.is_compatible // false')

        if [ "$compatible" = "true" ]; then
            echo -e "${GREEN}OK${NC}"
        else
            echo -e "${RED}FAILED${NC}"
            echo "      → Not backward compatible. FORWARD_FULL mode would reject future updates."

            # Zeige Details falls verfügbar
            messages=$(echo "$result" | jq -r '.messages[]? // empty' 2>/dev/null || echo "")
            if [ -n "$messages" ]; then
                echo "      → Details: $messages"
            fi

            subject_ok=false
            overall_ok=false
        fi
    done

    # Subject-Ergebnis
    if [ "$subject_ok" = true ]; then
        echo -e "  Result: ${GREEN}✔${NC} Subject ${SUBJECT} is FULL-compatible across all versions"
    else
        echo -e "  Result: ${RED}✘${NC} Subject ${SUBJECT} is NOT FULL-compatible"
    fi

    echo ""
done

# Finale Zusammenfassung
echo "==== SUMMARY ===="
if [ "$overall_ok" = true ]; then
    echo -e "${GREEN}✔ Topic '${TOPIC}' is safe for FORWARD_FULL compatibility${NC}"
    echo ""
    echo "You can now enable FORWARD_FULL with:"
    echo "  curl -X PUT -H 'Content-Type: application/vnd.schemaregistry.v1+json' \\"
    echo "    --data '{\"compatibility\": \"FORWARD_FULL\"}' \\"
    echo "    ${SCHEMA_REGISTRY_URL}/config/${TOPIC}-value"
    exit 0
else
    echo -e "${RED}✘ Topic '${TOPIC}' has at least one incompatible schema version${NC}"
    echo "  → DO NOT enable FORWARD_FULL without:"
    echo "     1. Reviewing incompatible schemas"
    echo "     2. Fixing compatibility issues"
    echo "     3. Or accepting that future schema updates may be rejected"
    exit 2
fi
