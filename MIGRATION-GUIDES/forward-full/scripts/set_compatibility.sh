#!/usr/bin/env bash

################################################################################
# set_compatibility.sh
#
# Setzt den Kompatibilitätsmodus für Subjects in der Schema Registry
#
# Verwendung:
#   # Global setzen
#   ./set_compatibility.sh --global FORWARD_FULL
#
#   # Für spezifisches Subject setzen
#   ./set_compatibility.sh --subject my-topic-value FORWARD_FULL
#
#   # Mit Custom Schema Registry URL
#   SCHEMA_REGISTRY_URL=http://registry:8081 ./set_compatibility.sh --global FORWARD_FULL
################################################################################

set -euo pipefail

# Konfiguration
SCHEMA_REGISTRY_URL="${SCHEMA_REGISTRY_URL:-http://localhost:8081}"

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Hilfsfunktionen
log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

show_usage() {
    cat << EOF
Usage:
  $0 [OPTIONS] <COMPATIBILITY_MODE>

Options:
  --global              Set compatibility globally (default)
  --subject <name>      Set compatibility for specific subject
  -h, --help           Show this help message

Compatibility Modes:
  BACKWARD              (default) New schema can read data written with previous schema
  BACKWARD_TRANSITIVE   New schema can read data from all previous schemas
  FORWARD               Previous schema can read data written with new schema
  FORWARD_TRANSITIVE    All previous schemas can read data from new schema
  FORWARD_FULL          Most strict: FORWARD + BACKWARD for all versions
  FULL                  BACKWARD + FORWARD (bidirectional)
  FULL_TRANSITIVE       BACKWARD_TRANSITIVE + FORWARD_TRANSITIVE
  NONE                  No compatibility checks

Environment Variables:
  SCHEMA_REGISTRY_URL   Schema Registry URL (default: http://localhost:8081)

Examples:
  # Set global compatibility to FORWARD_FULL
  $0 --global FORWARD_FULL

  # Set compatibility for specific subject
  $0 --subject my-topic-value FORWARD_FULL

  # With custom registry URL
  SCHEMA_REGISTRY_URL=http://registry:8081 $0 --global FORWARD_FULL

EOF
}

# Parameter parsen
MODE="global"
SUBJECT=""
COMPATIBILITY=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --global)
            MODE="global"
            shift
            ;;
        --subject)
            MODE="subject"
            SUBJECT="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            COMPATIBILITY="$1"
            shift
            ;;
    esac
done

# Validierung
if [ -z "$COMPATIBILITY" ]; then
    log_error "Compatibility mode is required"
    echo ""
    show_usage
    exit 1
fi

# Validiere Kompatibilitätsmodus
VALID_MODES=(
    "BACKWARD"
    "BACKWARD_TRANSITIVE"
    "FORWARD"
    "FORWARD_TRANSITIVE"
    "FORWARD_FULL"
    "FULL"
    "FULL_TRANSITIVE"
    "NONE"
)

valid=false
for mode in "${VALID_MODES[@]}"; do
    if [ "$COMPATIBILITY" = "$mode" ]; then
        valid=true
        break
    fi
done

if [ "$valid" = false ]; then
    log_error "Invalid compatibility mode: $COMPATIBILITY"
    echo "Valid modes: ${VALID_MODES[*]}"
    exit 1
fi

# Prüfe Subject-Parameter
if [ "$MODE" = "subject" ] && [ -z "$SUBJECT" ]; then
    log_error "Subject name is required when using --subject"
    exit 1
fi

# Header
echo "================================================================"
log_info "Setting Schema Registry Compatibility"
log_info "Schema Registry: $SCHEMA_REGISTRY_URL"
if [ "$MODE" = "global" ]; then
    log_info "Mode: Global"
else
    log_info "Mode: Subject-specific"
    log_info "Subject: $SUBJECT"
fi
log_info "Compatibility: $COMPATIBILITY"
echo "================================================================"
echo ""

# Bereite URL und Request vor
if [ "$MODE" = "global" ]; then
    URL="${SCHEMA_REGISTRY_URL}/config"
else
    URL="${SCHEMA_REGISTRY_URL}/config/${SUBJECT}"
fi

# Hole aktuellen Status
log_info "Fetching current compatibility setting..."
current=$(curl -s "$URL" 2>/dev/null || echo '{"compatibilityLevel":"UNKNOWN"}')
current_level=$(echo "$current" | jq -r '.compatibilityLevel // "UNKNOWN"')

if [ "$current_level" != "UNKNOWN" ]; then
    log_info "Current compatibility: $current_level"
else
    log_warn "Could not fetch current compatibility (might be first time setting)"
fi
echo ""

# Bestätigung bei kritischen Änderungen
if [ "$COMPATIBILITY" = "FORWARD_FULL" ]; then
    log_warn "FORWARD_FULL is the most strict compatibility mode!"
    log_warn "This will require ALL future schemas to be forward AND backward compatible."
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        log_info "Operation cancelled"
        exit 0
    fi
    echo ""
fi

# Setze Kompatibilität
log_info "Setting compatibility to $COMPATIBILITY..."

response=$(curl -s -w "\n%{http_code}" \
    -X PUT \
    -H "Content-Type: application/vnd.schemaregistry.v1+json" \
    --data "{\"compatibility\": \"${COMPATIBILITY}\"}" \
    "$URL")

# Parse Response
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    log_info "✓ Compatibility successfully set to $COMPATIBILITY"
    echo ""
    echo "Response: $body"
    echo ""

    # Zeige nächste Schritte
    if [ "$COMPATIBILITY" = "FORWARD_FULL" ]; then
        echo "================================================================"
        log_info "Next Steps:"
        echo "================================================================"
        echo ""
        echo "1. Test with a new schema version to verify compatibility:"
        echo ""
        if [ "$MODE" = "subject" ]; then
            echo "   curl -X POST -H 'Content-Type: application/vnd.schemaregistry.v1+json' \\"
            echo "     --data @new-schema.json \\"
            echo "     ${SCHEMA_REGISTRY_URL}/subjects/${SUBJECT}/versions"
        else
            echo "   curl -X POST -H 'Content-Type: application/vnd.schemaregistry.v1+json' \\"
            echo "     --data @new-schema.json \\"
            echo "     ${SCHEMA_REGISTRY_URL}/subjects/<your-subject>/versions"
        fi
        echo ""
        echo "2. Monitor your Schema Registry logs for any compatibility errors"
        echo ""
        echo "3. Have a rollback plan ready:"
        echo ""
        echo "   ./set_compatibility.sh $([ "$MODE" = "subject" ] && echo "--subject $SUBJECT" || echo "--global") FORWARD_TRANSITIVE"
        echo ""
    fi

    exit 0
else
    log_error "Failed to set compatibility (HTTP $http_code)"
    echo ""
    echo "Response: $body"
    echo ""

    # Hilfreiche Fehlermeldungen
    if [ "$http_code" = "422" ]; then
        log_error "Unprocessable Entity - The compatibility mode might not be supported"
    elif [ "$http_code" = "404" ]; then
        log_error "Not Found - Subject does not exist: $SUBJECT"
    fi

    exit 1
fi
