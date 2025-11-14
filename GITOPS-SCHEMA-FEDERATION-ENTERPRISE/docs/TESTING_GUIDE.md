# Comprehensive Testing Guide

**Version:** 1.0.0
**Last Updated:** 2025-11-14

This guide covers all testing capabilities for the Multi-Backend Schema Registry system, including compatibility testing, live schema registry validation, and automated reporting.

---

## 📋 Table of Contents

- [Test Scripts Overview](#test-scripts-overview)
- [Quick Start](#quick-start)
- [Test Suite Components](#test-suite-components)
- [Running Tests](#running-tests)
- [Report Formats](#report-formats)
- [Live Schema Registry Testing](#live-schema-registry-testing)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)

---

## 📊 Test Scripts Overview

### 1. **run_compatibility_tests.sh** - Comprehensive Test Runner

**Location:** `scripts/run_compatibility_tests.sh`

**Features:**
- ✅ Runs complete pytest test suite
- ✅ Generates HTML, JSON, XML, and CSV reports
- ✅ Code coverage analysis
- ✅ Live Schema Registry testing
- ✅ Summary statistics

**Usage:**
```bash
# Run all tests with default settings
./scripts/run_compatibility_tests.sh

# Run with custom report directory
./scripts/run_compatibility_tests.sh --report-dir /tmp/reports

# Run with live Schema Registry testing
SR_URL=http://prod-sr:8081 ./scripts/run_compatibility_tests.sh --live

# Verbose output
./scripts/run_compatibility_tests.sh --verbose
```

---

### 2. **generate_test_report.py** - Beautiful HTML Reports

**Location:** `scripts/generate_test_report.py`

**Features:**
- ✅ Interactive HTML reports with visualizations
- ✅ Complete compatibility transition matrix
- ✅ Color-coded risk levels
- ✅ JSON export
- ✅ Statistics and summaries

**Usage:**
```bash
# Generate HTML and JSON reports
python3 scripts/generate_test_report.py

# Generate only HTML
python3 scripts/generate_test_report.py --format html

# Custom output directory
python3 scripts/generate_test_report.py --output-dir ./reports
```

**Output Example:**
```
Generating compatibility test reports...
Output directory: test-reports

✓ HTML report:  test-reports/compatibility-report.html
✓ JSON report:  test-reports/compatibility-report.json

✅ Generated 2 report(s)

View reports:
  open test-reports/compatibility-report.html
  cat test-reports/compatibility-report.json
```

---

### 3. **check_all_topics_compatibility.sh** - Live Schema Registry Validator

**Location:** `MIGRATION-GUIDES/forward-full/scripts/check_all_topics_compatibility.sh`

**Features:**
- ✅ Checks all subjects in a live Schema Registry
- ✅ Tests compatibility for target mode (FULL_TRANSITIVE, etc.)
- ✅ Generates CSV reports
- ✅ Color-coded console output
- ✅ Detailed error messages

**Usage:**
```bash
# Check all topics for FULL_TRANSITIVE compatibility
SCHEMA_REGISTRY_URL=http://localhost:8081 \
TARGET_MODE=FULL_TRANSITIVE \
./MIGRATION-GUIDES/forward-full/scripts/check_all_topics_compatibility.sh

# Check for BACKWARD_TRANSITIVE
SCHEMA_REGISTRY_URL=http://localhost:8081 \
TARGET_MODE=BACKWARD_TRANSITIVE \
REPORT_FILE=backward_check.csv \
./MIGRATION-GUIDES/forward-full/scripts/check_all_topics_compatibility.sh
```

**Output:**
```
================================================================
[INFO] Schema Registry Compatibility Check
[INFO] Schema Registry URL: http://localhost:8081
[INFO] Target Mode: FULL_TRANSITIVE
[INFO] Writing report: schema_FULL_TRANSITIVE_compatibility_report.csv
================================================================

[STEP] Testing Schema Registry connection...
[INFO] Connection successful

[STEP] Fetching all subjects...
[INFO] Found 12 subjects

==== [1/12] Checking subject: user-events-value ====
  Versions: 1 2 3
  Latest: 3 (total: 3 versions)
    [1/2] Version 1 → latest ... ✓ OK
    [2/2] Version 2 → latest ... ✓ OK
  Result: ✔ Subject is FULL-compatible

...

================================================================
==== GLOBAL SUMMARY ====
================================================================

Total subjects checked: 12
Compatible subjects:    10
Incompatible subjects:  2

✔ All subjects are safe for FULL_TRANSITIVE
```

---

## 🚀 Quick Start

### Run All Tests (Recommended)

```bash
cd GITOPS-SCHEMA-FEDERATION-ENTERPRISE

# Install dependencies
pip install -r requirements.txt

# Run complete test suite with all reports
./scripts/run_compatibility_tests.sh

# View HTML report
open test-reports/test-report.html

# View coverage
open test-reports/coverage/index.html
```

### Generate Standalone Report

```bash
# Generate beautiful HTML compatibility matrix
python3 scripts/generate_test_report.py

# Open in browser
open test-reports/compatibility-report.html
```

### Check Live Schema Registry

```bash
# Validate your production SR before migrating to FULL_TRANSITIVE
SCHEMA_REGISTRY_URL=https://your-sr.example.com \
TARGET_MODE=FULL_TRANSITIVE \
./MIGRATION-GUIDES/forward-full/scripts/check_all_topics_compatibility.sh

# Review CSV report
cat schema_FULL_TRANSITIVE_compatibility_report.csv
```

---

## 🧪 Test Suite Components

### Python Test Files

| File | Purpose | Tests |
|------|---------|-------|
| `tests/test_compatibility_transitions.py` | All 42 compatibility mode transitions | ✓ 42 transition scenarios<br>✓ Schema evolution patterns<br>✓ Validation requirements |
| `tests/test_confluent_plugin.py` | Confluent SR plugin tests | ✓ Connection<br>✓ Health checks<br>✓ Subject listing |
| `tests/test_unity_catalog_import.py` | Unity Catalog integration | ✓ Table import<br>✓ Schema conversion |

### Test Schemas

**Location:** `tests/test_compatibility_transitions.py` - `TestSchemas` class

Available test schemas:
1. **BASE_SCHEMA** - Starting point for tests
2. **BACKWARD_COMPATIBLE** - Add optional field with default
3. **FORWARD_COMPATIBLE** - Remove optional field
4. **FULL_COMPATIBLE** - Add nullable field (null default)
5. **BREAKING_TYPE_CHANGE** - Change field type (NONE only)
6. **BREAKING_REQUIRED_FIELD** - Add required field (NONE only)
7. **TYPE_WIDENING** - Union types (BACKWARD only)
8. **FIELD_RENAME_WITH_ALIAS** - Rename with alias (FULL compatible)
9. **NESTED_SCHEMA_V1/V2** - Complex nested evolution

---

## 📊 Report Formats

### 1. HTML Report (Interactive)

**Generated by:** `run_compatibility_tests.sh` or `generate_test_report.py`

**Location:** `test-reports/compatibility-report.html` or `test-reports/test-report.html`

**Features:**
- 📊 Complete 7x7 compatibility matrix
- 🎨 Color-coded risk levels
- 📈 Statistics dashboard
- 📝 Detailed transition descriptions
- 🖨️ Print-friendly
- 📱 Responsive design

**Example:**
```html
✅ SAFE Transitions: 21
⚠️ RISKY Transitions: 12
🔴 DANGEROUS Transitions: 9

Complete matrix showing all NONE → BACKWARD, BACKWARD → FORWARD, etc.
```

### 2. JSON Report (API-Friendly)

**Generated by:** `run_compatibility_tests.sh` or `generate_test_report.py`

**Location:** `test-reports/compatibility-report.json` or `test-reports/test-report.json`

**Structure:**
```json
{
  "generated_at": "2025-11-14T10:30:00",
  "total_transitions": 42,
  "transitions": [
    {
      "from_mode": "NONE",
      "to_mode": "BACKWARD",
      "risk_level": "RISKY",
      "requires_validation": true,
      "description": "NONE allowed breaking changes, BACKWARD requires validation"
    }
  ],
  "statistics": {
    "total": 42,
    "by_risk_level": {
      "SAFE": 21,
      "RISKY": 12,
      "DANGEROUS": 9
    },
    "requiring_validation": 28
  }
}
```

### 3. CSV Report (Excel/Spreadsheet)

**Generated by:** `run_compatibility_tests.sh` or `check_all_topics_compatibility.sh`

**Location:** `test-reports/compatibility-matrix.csv` or `schema_FULL_TRANSITIVE_compatibility_report.csv`

**Format:**
```csv
from_mode,to_mode,risk_level,requires_validation,description
NONE,BACKWARD,RISKY,True,NONE allowed breaking changes; BACKWARD requires validation
BACKWARD,BACKWARD_TRANSITIVE,SAFE,False,Adding transitive check is safe
...
```

### 4. Coverage Report (Code Coverage)

**Generated by:** `run_compatibility_tests.sh`

**Location:** `test-reports/coverage/index.html`

**Metrics:**
- Line coverage
- Branch coverage
- File-by-file breakdown
- Missing lines highlighted

### 5. JUnit XML (CI/CD)

**Generated by:** `run_compatibility_tests.sh`

**Location:** `test-reports/junit.xml`

**Usage:** Jenkins, GitLab CI, GitHub Actions, etc.

---

## 🔴 Live Schema Registry Testing

### Test Against Your Production SR

**Scenario:** You want to migrate from FORWARD_TRANSITIVE to FULL_TRANSITIVE on production.

**Steps:**

1. **Check current compatibility of all subjects:**
```bash
SCHEMA_REGISTRY_URL=https://prod-sr.example.com \
TARGET_MODE=FULL_TRANSITIVE \
./MIGRATION-GUIDES/forward-full/scripts/check_all_topics_compatibility.sh
```

2. **Review the report:**
```bash
cat schema_FULL_TRANSITIVE_compatibility_report.csv
```

3. **Interpret results:**
- ✅ **All compatible:** Safe to migrate globally
- ⚠️ **Some incompatible:** Migrate only compatible subjects
- 🔴 **Many incompatible:** Fix schemas before migration

4. **Use the API for live testing:**
```bash
# Using the multi-backend API
curl -X POST http://localhost:8000/api/v1/bulk/check-compatibility \
  -H "Content-Type: application/json" \
  -d '{
    "registry_ids": ["prod-confluent"],
    "target_mode": "FULL_TRANSITIVE",
    "subject_filter": "user-"
  }'
```

---

## 🔧 CI/CD Integration

### GitHub Actions

```yaml
name: Schema Compatibility Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd GITOPS-SCHEMA-FEDERATION-ENTERPRISE
          pip install -r requirements.txt

      - name: Run compatibility tests
        run: |
          cd GITOPS-SCHEMA-FEDERATION-ENTERPRISE
          ./scripts/run_compatibility_tests.sh

      - name: Upload test reports
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-reports
          path: GITOPS-SCHEMA-FEDERATION-ENTERPRISE/test-reports/

      - name: Publish test results
        uses: EnricoMi/publish-unit-test-result-action@v2
        if: always()
        with:
          files: GITOPS-SCHEMA-FEDERATION-ENTERPRISE/test-reports/junit.xml
```

### GitLab CI

```yaml
test:
  stage: test
  image: python:3.11
  script:
    - cd GITOPS-SCHEMA-FEDERATION-ENTERPRISE
    - pip install -r requirements.txt
    - ./scripts/run_compatibility_tests.sh
  artifacts:
    when: always
    paths:
      - GITOPS-SCHEMA-FEDERATION-ENTERPRISE/test-reports/
    reports:
      junit: GITOPS-SCHEMA-FEDERATION-ENTERPRISE/test-reports/junit.xml
      coverage_report:
        coverage_format: cobertura
        path: GITOPS-SCHEMA-FEDERATION-ENTERPRISE/test-reports/coverage.xml
```

### Jenkins

```groovy
pipeline {
    agent any

    stages {
        stage('Test') {
            steps {
                dir('GITOPS-SCHEMA-FEDERATION-ENTERPRISE') {
                    sh 'pip install -r requirements.txt'
                    sh './scripts/run_compatibility_tests.sh'
                }
            }
        }
    }

    post {
        always {
            junit 'GITOPS-SCHEMA-FEDERATION-ENTERPRISE/test-reports/junit.xml'
            publishHTML([
                reportDir: 'GITOPS-SCHEMA-FEDERATION-ENTERPRISE/test-reports',
                reportFiles: 'test-report.html',
                reportName: 'Test Report'
            ])
        }
    }
}
```

---

## 🐛 Troubleshooting

### Issue: pytest not found

**Error:**
```
bash: pytest: command not found
```

**Solution:**
```bash
pip install pytest pytest-html pytest-json-report pytest-cov
```

---

### Issue: Module import errors

**Error:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Solution:**
```bash
cd GITOPS-SCHEMA-FEDERATION-ENTERPRISE
pip install -r requirements.txt
```

---

### Issue: Permission denied for scripts

**Error:**
```
bash: ./scripts/run_compatibility_tests.sh: Permission denied
```

**Solution:**
```bash
chmod +x scripts/run_compatibility_tests.sh
chmod +x scripts/generate_test_report.py
```

---

### Issue: Schema Registry connection fails

**Error:**
```
[ERROR] Cannot connect to Schema Registry at http://localhost:8081
```

**Solution:**
```bash
# Check if SR is running
curl http://localhost:8081/subjects

# If not, start it
docker run -d -p 8081:8081 confluentinc/cp-schema-registry:7.5.0

# Or update the URL
export SR_URL=http://your-actual-sr:8081
```

---

### Issue: Reports not generated

**Error:**
```
Report directory not found
```

**Solution:**
```bash
# Create report directory manually
mkdir -p test-reports

# Or specify custom directory
./scripts/run_compatibility_tests.sh --report-dir ./custom-reports
```

---

## 📚 Additional Resources

- **[COMPATIBILITY_MODES_GUIDE.md](./COMPATIBILITY_MODES_GUIDE.md)** - Complete compatibility mode reference
- **[GETTING_STARTED.md](../GETTING_STARTED.md)** - Quick start guide
- **[IMPLEMENTATION_README.md](../IMPLEMENTATION_README.md)** - Technical implementation details

---

## ✅ Testing Checklist

Before deploying to production, ensure:

- [ ] All pytest tests pass
- [ ] Code coverage is > 80%
- [ ] Live Schema Registry validation completed
- [ ] Compatibility transition plan reviewed
- [ ] Reports generated and saved
- [ ] CI/CD pipeline integrated
- [ ] Team trained on compatibility modes
- [ ] Rollback plan documented

---

**Version:** 1.0.0
**Last Updated:** 2025-11-14
**Maintained By:** Platform Engineering Team
