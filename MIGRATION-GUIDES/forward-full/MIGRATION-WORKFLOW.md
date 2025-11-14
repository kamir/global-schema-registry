# Migration Workflow: FORWARD_TRANSITIVE → FORWARD_FULL

Dieser Workflow führt Sie Schritt für Schritt durch die sichere Migration von FORWARD_TRANSITIVE auf FORWARD_FULL.

## Phasen-Übersicht

```
Phase 1: Vorbereitung und Analyse
    ↓
Phase 2: Test und Validierung
    ↓
Phase 3: Schrittweise Migration
    ↓
Phase 4: Monitoring und Verifizierung
```

---

## Phase 1: Vorbereitung und Analyse

### 1.1 Umgebung vorbereiten

```bash
# Setze Schema Registry URL
export SCHEMA_REGISTRY_URL=http://your-schema-registry:8081

# Navigiere zum Scripts-Verzeichnis
cd MIGRATION-GUIDES/forward-full/scripts
```

### 1.2 Aktuelle Konfiguration prüfen

```bash
# Prüfe globale Kompatibilität
curl -s $SCHEMA_REGISTRY_URL/config | jq .

# Beispiel Output:
# {
#   "compatibilityLevel": "FORWARD_TRANSITIVE"
# }
```

### 1.3 Vollständige Analyse aller Subjects

```bash
# Führe Kompatibilitäts-Check für alle Subjects durch
./check_all_topics_compatibility.sh

# Output wird nach: schema_full_compatibility_report.csv
```

**Erwartetes Ergebnis:**
- CSV-Report mit allen Subjects und deren Kompatibilitätsstatus
- Liste der kompatiblen Subjects
- Liste der inkompatiblen Subjects

### 1.4 Report analysieren

```bash
# Zeige inkompatible Subjects
cat schema_full_compatibility_report.csv | grep ",false," | cut -d',' -f1 | sort -u

# Zähle kompatible vs. inkompatible
echo "Kompatibel:"
cat schema_full_compatibility_report.csv | grep ",true," | wc -l

echo "Inkompatibel:"
cat schema_full_compatibility_report.csv | grep ",false," | wc -l
```

---

## Phase 2: Test und Validierung

### 2.1 Kritische Topics identifizieren

Erstellen Sie eine Liste der kritischen Business-Topics:

```bash
# Beispiel: topics_critical.txt
cat > topics_critical.txt << EOF
order-events
customer-events
payment-transactions
inventory-updates
EOF
```

### 2.2 Einzelne kritische Topics prüfen

```bash
# Prüfe jedes kritische Topic einzeln
while read topic; do
    echo "Checking: $topic"
    ./check_topic_compatibility.sh "$topic"
    echo ""
done < topics_critical.txt
```

### 2.3 Test-Subject in Staging

**Wichtig:** Führen Sie einen Test in einer Staging-Umgebung durch!

```bash
# Wähle ein unkritisches Test-Subject
TEST_SUBJECT="test-migration-value"

# Setze FORWARD_FULL für Test-Subject
./set_compatibility.sh --subject $TEST_SUBJECT FORWARD_FULL

# Versuche ein neues Schema zu registrieren
curl -X POST \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data @test-schema.json \
  $SCHEMA_REGISTRY_URL/subjects/$TEST_SUBJECT/versions

# Bei Erfolg: {"id": 123}
# Bei Fehler: {"error_code": 409, "message": "..."}
```

---

## Phase 3: Schrittweise Migration

### Strategie A: Nur kompatible Subjects migrieren

**Empfohlen für: Produktionsumgebungen mit gemischten Kompatibilitätsanforderungen**

#### 3.1 Liste der kompatiblen Subjects erstellen

```bash
# Extrahiere alle kompatiblen Subjects aus dem Report
cat schema_full_compatibility_report.csv | \
  awk -F',' '$4=="true" {print $1}' | \
  sort -u > compatible_subjects.txt

echo "Kompatible Subjects:"
cat compatible_subjects.txt
```

#### 3.2 Migration für kompatible Subjects

```bash
# Migriere jedes kompatible Subject einzeln
while read subject; do
    echo "Migrating: $subject"

    # Setze FORWARD_FULL
    ./set_compatibility.sh --subject "$subject" FORWARD_FULL

    # Kurze Pause zwischen Subjects
    sleep 1

    echo "✓ $subject migrated"
    echo ""
done < compatible_subjects.txt
```

#### 3.3 Verifizierung

```bash
# Prüfe Konfiguration für jedes Subject
while read subject; do
    config=$(curl -s "$SCHEMA_REGISTRY_URL/config/$subject" | jq -r '.compatibilityLevel')
    echo "$subject: $config"
done < compatible_subjects.txt
```

---

### Strategie B: Globale Migration

**Empfohlen für: Neuere Umgebungen, wo alle Subjects kompatibel sind**

#### 3.1 Voraussetzungen prüfen

```bash
# Stelle sicher, dass ALLE Subjects kompatibel sind
incompatible_count=$(cat schema_full_compatibility_report.csv | grep ",false," | wc -l)

if [ "$incompatible_count" -gt 0 ]; then
    echo "WARNUNG: $incompatible_count inkompatible Subject-Versionen gefunden!"
    echo "Globale Migration nicht empfohlen."
    exit 1
fi
```

#### 3.2 Backup der aktuellen Konfiguration

```bash
# Sichere aktuelle globale Konfiguration
curl -s $SCHEMA_REGISTRY_URL/config > config_backup.json
echo "Backup erstellt: config_backup.json"
```

#### 3.3 Globale Migration durchführen

```bash
# Setze globale Kompatibilität auf FORWARD_FULL
./set_compatibility.sh --global FORWARD_FULL

# Verifiziere
curl -s $SCHEMA_REGISTRY_URL/config | jq .
```

---

## Phase 4: Monitoring und Verifizierung

### 4.1 Continuous Monitoring Setup

Erstellen Sie ein Monitoring-Script:

```bash
cat > monitor_registry.sh << 'EOF'
#!/bin/bash
SCHEMA_REGISTRY_URL="${SCHEMA_REGISTRY_URL:-http://localhost:8081}"

echo "=== Schema Registry Monitoring ==="
echo "Zeit: $(date)"
echo ""

# Globale Konfiguration
echo "Globale Kompatibilität:"
curl -s $SCHEMA_REGISTRY_URL/config | jq .
echo ""

# Zähle Subjects nach Kompatibilität
echo "Subjects nach Kompatibilität:"
echo "FORWARD_FULL:"
curl -s $SCHEMA_REGISTRY_URL/subjects | jq -r '.[]' | while read subject; do
    compat=$(curl -s "$SCHEMA_REGISTRY_URL/config/$subject" 2>/dev/null | jq -r '.compatibilityLevel // "GLOBAL"')
    if [ "$compat" = "FORWARD_FULL" ]; then
        echo "  - $subject"
    fi
done
EOF

chmod +x monitor_registry.sh
```

### 4.2 Test neuer Schema-Registrierungen

```bash
# Wähle ein migriertes Subject
SUBJECT="your-migrated-subject-value"

# Test 1: Kompatibles Schema (sollte funktionieren)
curl -X POST \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data '{"schema": "{\"type\": \"record\", \"name\": \"Test\", \"fields\": [{\"name\": \"id\", \"type\": \"string\"}]}"}' \
  $SCHEMA_REGISTRY_URL/subjects/$SUBJECT/versions

# Erwartung: {"id": <schema-id>}
```

### 4.3 Rollback-Prozedur (falls nötig)

Wenn Probleme auftreten:

```bash
# Option 1: Einzelnes Subject zurücksetzen
./set_compatibility.sh --subject problematic-subject-value FORWARD_TRANSITIVE

# Option 2: Globale Konfiguration zurücksetzen
./set_compatibility.sh --global FORWARD_TRANSITIVE

# Option 3: Aus Backup wiederherstellen
curl -X PUT \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data @config_backup.json \
  $SCHEMA_REGISTRY_URL/config
```

### 4.4 Erfolgs-Metriken

Erstellen Sie einen Validierungs-Report:

```bash
cat > validation_report.sh << 'EOF'
#!/bin/bash
SCHEMA_REGISTRY_URL="${SCHEMA_REGISTRY_URL:-http://localhost:8081}"

echo "=== Migration Validation Report ==="
echo "Generated: $(date)"
echo ""

# Globale Konfiguration
global_compat=$(curl -s $SCHEMA_REGISTRY_URL/config | jq -r '.compatibilityLevel')
echo "Global Compatibility: $global_compat"
echo ""

# Zähle Subjects
total_subjects=$(curl -s $SCHEMA_REGISTRY_URL/subjects | jq '. | length')
echo "Total Subjects: $total_subjects"
echo ""

# Zähle nach Kompatibilität
echo "Subjects by Compatibility:"
declare -A compat_counts

curl -s $SCHEMA_REGISTRY_URL/subjects | jq -r '.[]' | while read subject; do
    compat=$(curl -s "$SCHEMA_REGISTRY_URL/config/$subject" 2>/dev/null | jq -r '.compatibilityLevel // "GLOBAL"')
    echo "$compat"
done | sort | uniq -c

echo ""
echo "=== Migration Status: SUCCESS ==="
EOF

chmod +x validation_report.sh
./validation_report.sh
```

---

## Troubleshooting

### Problem 1: Schema-Registrierung wird abgelehnt

**Symptom:**
```json
{
  "error_code": 409,
  "message": "Schema being registered is incompatible with an earlier schema"
}
```

**Lösung:**
```bash
# 1. Prüfe welche Version inkompatibel ist
curl -s "$SCHEMA_REGISTRY_URL/subjects/$SUBJECT/versions"

# 2. Teste Kompatibilität explizit
./check_topic_compatibility.sh <topic-name>

# 3. Entscheidung:
#    a) Schema anpassen, um kompatibel zu sein
#    b) Subject auf FORWARD_TRANSITIVE zurücksetzen
#    c) Schema-Historie bereinigen (vorsichtig!)
```

### Problem 2: Unerwartete Performance-Probleme

**Symptom:** Schema Registry antwortet langsam

**Lösung:**
```bash
# Prüfe Registry Logs
docker logs schema-registry | tail -100

# Prüfe Kafka Backend
kafka-topics --bootstrap-server localhost:9092 \
  --describe --topic _schemas

# Reduziere Last: Migriere schrittweise statt global
```

### Problem 3: Alte Consumer brechen ab

**Symptom:** Consumer können neue Nachrichten nicht lesen

**Analyse:**
```bash
# Das sollte mit FORWARD_FULL nicht passieren!
# Prüfe ob tatsächlich FORWARD_FULL aktiv ist
curl -s $SCHEMA_REGISTRY_URL/config/<subject> | jq .

# Prüfe Consumer-Konfiguration
# - Verwendet Consumer das richtige Schema?
# - Ist Auto-Schema-Update aktiviert?
```

---

## Checkliste

### Vor der Migration

- [ ] Backup der aktuellen Schema Registry Konfiguration
- [ ] Alle Subjects auf Kompatibilität geprüft
- [ ] Test in Staging-Umgebung durchgeführt
- [ ] Kritische Topics identifiziert
- [ ] Rollback-Plan dokumentiert
- [ ] Team informiert

### Während der Migration

- [ ] Schritt-für-Schritt vorgehen
- [ ] Jedes Subject nach Migration verifizieren
- [ ] Logs kontinuierlich überwachen
- [ ] Bei Problemen: sofort Rollback durchführen

### Nach der Migration

- [ ] Alle migrierten Subjects verifiziert
- [ ] Neue Schema-Registrierung getestet
- [ ] Monitoring für 24h aktiv
- [ ] Dokumentation aktualisiert
- [ ] Team über Erfolg informiert

---

## Zusammenfassung

**Minimale Migrations-Schritte:**

```bash
# 1. Analyse
./check_all_topics_compatibility.sh

# 2. Entscheidung treffen
#    - Strategie A (selektiv) oder B (global)

# 3. Migration
./set_compatibility.sh --subject <subject-name> FORWARD_FULL
# oder
./set_compatibility.sh --global FORWARD_FULL

# 4. Verifizierung
curl -s $SCHEMA_REGISTRY_URL/config/<subject> | jq .

# 5. Test
# Registriere ein neues Test-Schema
```

**Zeitaufwand (Schätzung):**
- Kleine Umgebung (<50 Subjects): 1-2 Stunden
- Mittlere Umgebung (50-200 Subjects): 2-4 Stunden
- Große Umgebung (>200 Subjects): 4-8 Stunden + Monitoring

**Risiko-Level:**
- Mit vollständiger Analyse: **Niedrig**
- Ohne Analyse: **Hoch**
- Mit Rollback-Plan: **Sehr niedrig**
