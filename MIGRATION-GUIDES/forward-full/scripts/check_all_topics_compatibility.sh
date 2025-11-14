#!/usr/bin/env bash

################################################################################
# check_all_topics_compatibility.sh
#
# Prüft alle Subjects in der Schema Registry auf FORWARD_FULL Kompatibilität
# und erstellt einen detaillierten CSV-Report
#
# Verwendung:
#   SCHEMA_REGISTRY_URL=http://localhost:8081 \
#   REPORT_FILE=report.csv \
#   ./check_all_topics_compatibility.sh
#
# Exit Codes:
#   0 - Alle Subjects sind kompatibel für FORWARD_FULL
#   1 - Fehler bei der Ausführung
#   2 - Mindestens ein Subject ist NICHT kompatibel
################################################################################

set -euo pipefail

# Konfiguration
SCHEMA_REGISTRY_URL="${SCHEMA_REGISTRY_URL:-http://localhost:8081}"
REPORT_FILE="${REPORT_FILE:-schema_full_compatibility_report.csv}"

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Hilfsfunktionen
log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $*"
}

# Prüfe Abhängigkeiten
if ! command -v curl &> /dev/null; then
    log_error "curl is not installed"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    log_error "jq is not installed. Please install jq to use this script."
    exit 1
fi

# Header
echo "================================================================"
log_info "Schema Registry Full Compatibility Check"
log_info "Schema Registry URL: $SCHEMA_REGISTRY_URL"
log_info "Writing report: $REPORT_FILE"
echo "================================================================"
echo ""

# Prüfe Schema Registry Verbindung
log_step "Testing Schema Registry connection..."
if ! curl -s -f "${SCHEMA_REGISTRY_URL}/subjects" > /dev/null; then
    log_error "Cannot connect to Schema Registry at $SCHEMA_REGISTRY_URL"
    exit 1
fi
log_info "Connection successful"
echo ""

# CSV Header erstellen
echo "subject,version,latest_version,is_compatible,compatibility_details" > "$REPORT_FILE"

# Hole alle Subjects
log_step "Fetching all subjects..."
SUBJECTS=$(curl -s "${SCHEMA_REGISTRY_URL}/subjects" | jq -r '.[]')

if [ -z "$SUBJECTS" ]; then
    log_warn "No subjects found in the Schema Registry"
    exit 0
fi

subject_count=$(echo "$SUBJECTS" | wc -l)
log_info "Found $subject_count subjects"
echo ""

# Tracking
declare -A subject_results
OVERALL_OK=true
current=0

# Iteriere über alle Subjects
while IFS= read -r SUBJECT; do
    ((current++))
    echo "==== [$current/$subject_count] Checking subject: ${SUBJECT} ===="

    # Hole alle Versionen
    versions_response=$(curl -s "${SCHEMA_REGISTRY_URL}/subjects/${SUBJECT}/versions")

    if ! echo "$versions_response" | jq -e . >/dev/null 2>&1; then
        log_warn "Could not read versions for subject $SUBJECT → skipping"
        echo ""
        continue
    fi

    versions=$(echo "$versions_response" | jq -r '.[]')

    if [ -z "$versions" ]; then
        log_warn "No versions found → skipping"
        echo ""
        continue
    fi

    latest=$(echo "$versions" | tail -n1)
    version_count=$(echo "$versions" | wc -l)

    echo "  Versions: $(echo $versions | tr '\n' ' ')"
    echo "  Latest: $latest (total: $version_count versions)"

    # Hole das neueste Schema
    latest_schema=$(curl -s "${SCHEMA_REGISTRY_URL}/subjects/${SUBJECT}/versions/${latest}")
    latest_schema_def=$(echo "$latest_schema" | jq -r '.schema')

    subject_ok=true
    checked=0

    # Teste jede Version
    for v in $versions; do
        # Die neueste Version ist immer kompatibel mit sich selbst
        if [ "$v" = "$latest" ]; then
            echo "${SUBJECT},${v},${latest},true,Latest version (self-compatible)" >> "$REPORT_FILE"
            continue
        fi

        ((checked++))
        echo -n "    [$checked/$((version_count-1))] Version $v → latest ... "

        # Teste Backward-Kompatibilität
        test_payload=$(jq -n \
            --arg schema "$latest_schema_def" \
            '{schema: $schema}')

        result=$(curl -s \
            -X POST \
            -H "Content-Type: application/vnd.schemaregistry.v1+json" \
            -d "$test_payload" \
            "${SCHEMA_REGISTRY_URL}/compatibility/subjects/${SUBJECT}/versions/${v}")

        compatible=$(echo "$result" | jq -r '.is_compatible // false')

        # Details extrahieren
        details=$(echo "$result" | jq -r '.messages[]? // "No details"' 2>/dev/null | head -1)
        details=$(echo "$details" | tr ',' ';' | tr '\n' ' ')  # CSV-safe

        # In Report schreiben
        echo "${SUBJECT},${v},${latest},${compatible},${details}" >> "$REPORT_FILE"

        # Ausgabe
        if [ "$compatible" = "true" ]; then
            echo -e "${GREEN}OK${NC}"
        else
            echo -e "${RED}FAILED${NC}"
            echo "      → $details"
            subject_ok=false
            OVERALL_OK=false
        fi
    done

    # Subject-Ergebnis speichern
    subject_results["$SUBJECT"]=$subject_ok

    # Subject-Zusammenfassung
    if [ "$subject_ok" = true ]; then
        echo -e "  Result: ${GREEN}✔${NC} Subject is FULL-compatible"
    else
        echo -e "  Result: ${RED}✘${NC} Subject is NOT FULL-compatible"
    fi

    echo ""
done <<< "$SUBJECTS"

# Statistiken berechnen
compatible_subjects=0
incompatible_subjects=0

for subject in "${!subject_results[@]}"; do
    if [ "${subject_results[$subject]}" = true ]; then
        ((compatible_subjects++))
    else
        ((incompatible_subjects++))
    fi
done

# Finale Zusammenfassung
echo "================================================================"
echo "==== GLOBAL SUMMARY ===="
echo "================================================================"
echo ""
echo "Total subjects checked: $subject_count"
echo -e "Compatible subjects:    ${GREEN}$compatible_subjects${NC}"
echo -e "Incompatible subjects:  ${RED}$incompatible_subjects${NC}"
echo ""

if [ "$OVERALL_OK" = true ]; then
    echo -e "${GREEN}✔ All subjects are safe for FORWARD_FULL${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Review the detailed report: $REPORT_FILE"
    echo "  2. Enable FORWARD_FULL globally:"
    echo ""
    echo "     curl -X PUT -H 'Content-Type: application/vnd.schemaregistry.v1+json' \\"
    echo "       --data '{\"compatibility\": \"FORWARD_FULL\"}' \\"
    echo "       ${SCHEMA_REGISTRY_URL}/config"
    echo ""
else
    echo -e "${RED}✘ Some subjects have incompatible schema histories${NC}"
    echo ""
    echo "Incompatible subjects:"
    for subject in "${!subject_results[@]}"; do
        if [ "${subject_results[$subject]}" = false ]; then
            echo "  - $subject"
        fi
    done
    echo ""
    echo "Next steps:"
    echo "  1. Review the detailed report: $REPORT_FILE"
    echo "  2. For each incompatible subject, decide:"
    echo "     a) Fix the schema compatibility issues"
    echo "     b) Keep subject on FORWARD_TRANSITIVE"
    echo "     c) Accept that future updates may be rejected"
    echo ""
    echo "  3. Enable FORWARD_FULL only for compatible subjects:"
    echo ""
    echo "     curl -X PUT -H 'Content-Type: application/vnd.schemaregistry.v1+json' \\"
    echo "       --data '{\"compatibility\": \"FORWARD_FULL\"}' \\"
    echo "       ${SCHEMA_REGISTRY_URL}/config/<subject-name>"
    echo ""
fi

echo "================================================================"
log_info "Report created: $REPORT_FILE"
echo "================================================================"

# Exit mit entsprechendem Code
if [ "$OVERALL_OK" = true ]; then
    exit 0
else
    exit 2
fi
