#!/usr/bin/env bash

################################################################################
# run_compatibility_tests.sh
#
# Comprehensive test runner for schema compatibility testing with reporting
#
# Features:
# - Runs pytest test suite
# - Generates HTML, JSON, XML, and CSV reports
# - Tests against live Schema Registry
# - Produces compatibility transition matrix
# - Creates summary statistics
#
# Usage:
#   ./scripts/run_compatibility_tests.sh [OPTIONS]
#
# Options:
#   --html           Generate HTML report (default: enabled)
#   --json           Generate JSON report (default: enabled)
#   --csv            Generate CSV report (default: enabled)
#   --live           Test against live Schema Registry (requires SR_URL)
#   --report-dir     Output directory for reports (default: ./test-reports)
#   --verbose        Verbose output
#   --help           Show this help message
#
# Environment Variables:
#   SR_URL           Schema Registry URL (default: http://localhost:8081)
#   API_URL          Multi-backend API URL (default: http://localhost:8000)
#   REPORT_DIR       Report output directory
#
# Exit Codes:
#   0 - All tests passed
#   1 - Test failures or errors
#   2 - Setup/configuration error
################################################################################

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration
SCHEMA_REGISTRY_URL="${SR_URL:-http://localhost:8081}"
API_URL="${API_URL:-http://localhost:8000}"
REPORT_DIR="${REPORT_DIR:-${PROJECT_ROOT}/test-reports}"
RUN_HTML=true
RUN_JSON=true
RUN_CSV=true
RUN_LIVE=false
VERBOSE=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Functions
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

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

show_header() {
    echo ""
    echo "================================================================"
    echo -e "${CYAN}    Schema Compatibility Test Suite with Reporting${NC}"
    echo "================================================================"
    echo ""
}

show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Comprehensive test runner for schema compatibility testing.

Options:
  --html           Generate HTML report (default: enabled)
  --json           Generate JSON report (default: enabled)
  --csv            Generate CSV report (default: enabled)
  --live           Test against live Schema Registry
  --report-dir DIR Output directory for reports
  --verbose        Verbose output
  --help           Show this help message

Environment Variables:
  SR_URL           Schema Registry URL (default: http://localhost:8081)
  API_URL          Multi-backend API URL (default: http://localhost:8000)

Examples:
  # Run all tests with default reporting
  $0

  # Run with live Schema Registry testing
  SR_URL=http://prod-sr:8081 $0 --live

  # Generate only HTML report
  $0 --html --no-json --no-csv

  # Custom report directory
  $0 --report-dir /tmp/reports
EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --html)
            RUN_HTML=true
            shift
            ;;
        --no-html)
            RUN_HTML=false
            shift
            ;;
        --json)
            RUN_JSON=true
            shift
            ;;
        --no-json)
            RUN_JSON=false
            shift
            ;;
        --csv)
            RUN_CSV=true
            shift
            ;;
        --no-csv)
            RUN_CSV=false
            shift
            ;;
        --live)
            RUN_LIVE=true
            shift
            ;;
        --report-dir)
            REPORT_DIR="$2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 2
            ;;
    esac
done

# Show header
show_header

# Validate dependencies
log_step "Checking dependencies..."
MISSING_DEPS=()

if ! command -v python3 &> /dev/null; then
    MISSING_DEPS+=("python3")
fi

if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
    MISSING_DEPS+=("pip")
fi

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    log_error "Missing dependencies: ${MISSING_DEPS[*]}"
    log_error "Please install missing dependencies and try again"
    exit 2
fi

log_info "All dependencies found"

# Check if pytest is installed
if ! python3 -c "import pytest" 2>/dev/null; then
    log_warn "pytest not found, installing..."
    pip3 install pytest pytest-html pytest-json-report pytest-cov
fi

# Create report directory
log_step "Setting up report directory: $REPORT_DIR"
mkdir -p "$REPORT_DIR"
log_info "Report directory ready"

# Check if we're in the right directory
if [ ! -f "$PROJECT_ROOT/requirements.txt" ]; then
    log_error "Cannot find requirements.txt. Are you in the correct directory?"
    exit 2
fi

# Install dependencies if needed
log_step "Checking Python dependencies..."
if [ "$VERBOSE" = true ]; then
    pip3 install -q -r "$PROJECT_ROOT/requirements.txt"
else
    pip3 install -q -r "$PROJECT_ROOT/requirements.txt" > /dev/null 2>&1
fi
log_info "Python dependencies satisfied"

# Test configuration
echo ""
echo "Test Configuration:"
echo "  Project Root:      $PROJECT_ROOT"
echo "  Report Directory:  $REPORT_DIR"
echo "  Schema Registry:   $SCHEMA_REGISTRY_URL"
echo "  API URL:           $API_URL"
echo "  HTML Report:       $RUN_HTML"
echo "  JSON Report:       $RUN_JSON"
echo "  CSV Report:        $RUN_CSV"
echo "  Live Testing:      $RUN_LIVE"
echo ""

# Build pytest command
PYTEST_CMD="pytest"
PYTEST_ARGS=()

# Add test directory
PYTEST_ARGS+=("$PROJECT_ROOT/tests/")

# Verbose mode
if [ "$VERBOSE" = true ]; then
    PYTEST_ARGS+=("-vv")
else
    PYTEST_ARGS+=("-v")
fi

# Coverage
PYTEST_ARGS+=("--cov=$PROJECT_ROOT/src")
PYTEST_ARGS+=("--cov-report=term-missing")
PYTEST_ARGS+=("--cov-report=html:$REPORT_DIR/coverage")

# HTML report
if [ "$RUN_HTML" = true ]; then
    PYTEST_ARGS+=("--html=$REPORT_DIR/test-report.html")
    PYTEST_ARGS+=("--self-contained-html")
fi

# JSON report
if [ "$RUN_JSON" = true ]; then
    PYTEST_ARGS+=("--json-report")
    PYTEST_ARGS+=("--json-report-file=$REPORT_DIR/test-report.json")
fi

# JUnit XML (for CI/CD)
PYTEST_ARGS+=("--junit-xml=$REPORT_DIR/junit.xml")

# Color output
PYTEST_ARGS+=("--color=yes")

# Run pytest
log_step "Running pytest test suite..."
echo ""

set +e  # Don't exit on test failures
$PYTEST_CMD "${PYTEST_ARGS[@]}"
PYTEST_EXIT_CODE=$?
set -e

echo ""

# Generate additional reports
if [ "$RUN_CSV" = true ]; then
    log_step "Generating CSV compatibility matrix..."

    CSV_FILE="$REPORT_DIR/compatibility-matrix.csv"

    # Run Python script to generate matrix
    python3 << 'PYEOF' > "$CSV_FILE"
import sys
sys.path.insert(0, '$PROJECT_ROOT')

from tests.test_compatibility_transitions import COMPATIBILITY_TRANSITIONS

# CSV header
print("from_mode,to_mode,risk_level,requires_validation,description")

# Data rows
for from_mode, to_mode, risk_level, requires_validation, description in COMPATIBILITY_TRANSITIONS:
    # Escape commas in description
    desc_clean = description.replace(',', ';')
    print(f"{from_mode},{to_mode},{risk_level},{requires_validation},{desc_clean}")
PYEOF

    log_info "CSV matrix created: $CSV_FILE"
fi

# Live Schema Registry testing
if [ "$RUN_LIVE" = true ]; then
    log_step "Running live Schema Registry tests..."

    # Check if SR is accessible
    if curl -s -f "$SCHEMA_REGISTRY_URL/subjects" > /dev/null 2>&1; then
        log_info "Schema Registry is accessible at $SCHEMA_REGISTRY_URL"

        # Generate live compatibility report
        LIVE_REPORT="$REPORT_DIR/live-compatibility-check.json"

        log_info "Fetching subjects from Schema Registry..."
        curl -s "$SCHEMA_REGISTRY_URL/subjects" | python3 -m json.tool > "$LIVE_REPORT" || true

        log_info "Live report created: $LIVE_REPORT"
    else
        log_warn "Schema Registry not accessible at $SCHEMA_REGISTRY_URL"
        log_warn "Skipping live tests"
    fi
fi

# Generate summary report
log_step "Generating summary report..."

SUMMARY_FILE="$REPORT_DIR/test-summary.txt"

cat > "$SUMMARY_FILE" << EOF
================================================================
Schema Compatibility Test Suite - Summary Report
================================================================

Test Run: $(date)

Configuration:
  Project Root:      $PROJECT_ROOT
  Schema Registry:   $SCHEMA_REGISTRY_URL
  API URL:           $API_URL

Reports Generated:
$([ "$RUN_HTML" = true ] && echo "  ✓ HTML Report:     test-report.html" || echo "  ✗ HTML Report:     disabled")
$([ "$RUN_JSON" = true ] && echo "  ✓ JSON Report:     test-report.json" || echo "  ✗ JSON Report:     disabled")
$([ "$RUN_CSV" = true ] && echo "  ✓ CSV Matrix:      compatibility-matrix.csv" || echo "  ✗ CSV Matrix:      disabled")
  ✓ Coverage:        coverage/index.html
  ✓ JUnit XML:       junit.xml

Test Result: $([ $PYTEST_EXIT_CODE -eq 0 ] && echo "✓ PASSED" || echo "✗ FAILED")
Exit Code: $PYTEST_EXIT_CODE

================================================================
All reports available in: $REPORT_DIR
================================================================
EOF

cat "$SUMMARY_FILE"

# Final status
echo ""
if [ $PYTEST_EXIT_CODE -eq 0 ]; then
    log_success "All tests passed! ✓"
    echo ""
    echo "View reports:"
    [ "$RUN_HTML" = true ] && echo "  HTML:     open $REPORT_DIR/test-report.html"
    echo "  Coverage: open $REPORT_DIR/coverage/index.html"
    [ "$RUN_JSON" = true ] && echo "  JSON:     cat $REPORT_DIR/test-report.json"
    [ "$RUN_CSV" = true ] && echo "  CSV:      cat $REPORT_DIR/compatibility-matrix.csv"
else
    log_error "Tests failed with exit code $PYTEST_EXIT_CODE"
    echo ""
    echo "Check reports for details:"
    [ "$RUN_HTML" = true ] && echo "  HTML:     open $REPORT_DIR/test-report.html"
    echo "  Summary:  cat $REPORT_DIR/test-summary.txt"
fi

echo ""

exit $PYTEST_EXIT_CODE
