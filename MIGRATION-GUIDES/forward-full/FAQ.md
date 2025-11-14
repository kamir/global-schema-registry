# FAQ - FORWARD_FULL Migration

## Allgemeine Fragen

### Was ist der Unterschied zwischen FORWARD_TRANSITIVE und FORWARD_FULL?

**FORWARD_TRANSITIVE:**
- Neue Schemas müssen mit allen vorherigen Versionen **vorwärts-kompatibel** sein
- Focus: Alte Consumer können neue Producer-Daten lesen
- Erlaubt Änderungen, die nur vorwärts-kompatibel sind

**FORWARD_FULL:**
- Neue Schemas müssen sowohl **vorwärts- als auch rückwärts-kompatibel** mit allen Versionen sein
- Focus: Maximale Sicherheit - alte UND neue Producer/Consumer funktionieren
- Strengste Forward-Variante - verhindert disruptive Änderungen

**Beispiel:**
```
Schema V1: {name: string}
Schema V2: {name: string, age: int (default: 0)}

FORWARD_TRANSITIVE: ✅ Erlaubt (V1 Consumer können V2 Daten lesen)
FORWARD_FULL: ✅ Erlaubt (zusätzlich: V2 Consumer können V1 Daten lesen)

Schema V3: {name: string, age: int (required!)}

FORWARD_TRANSITIVE: ✅ Möglicherweise erlaubt
FORWARD_FULL: ❌ Abgelehnt (V3 kann V1 Daten nicht lesen - age fehlt!)
```

---

### Können wir einfach von FORWARD_TRANSITIVE auf FORWARD_FULL wechseln?

**Ja, aber mit Bedingungen:**

✅ **Sicher, wenn:**
- Alle existierenden Schema-Versionen bereits rückwärts-kompatibel sind
- Sie nach der Migration prüfen können
- Ein Rollback-Plan existiert

⚠️ **Risiko:**
- Der Wechsel selbst führt keine Validierung der bestehenden Schemas durch
- **Erst beim nächsten Schema-Update** wird die strengere Kompatibilität geprüft
- Wenn alte Versionen nicht rückwärts-kompatibel sind, wird das nächste Update abgelehnt

**Empfehlung:** Nutzen Sie unsere Scripts zur Vorab-Prüfung:
```bash
./scripts/check_topic_compatibility.sh my-topic
```

---

### Sollten wir erst nach der Migration umstellen?

**Ja, das ist die beste Strategie!**

**Während der Cluster-Migration:**
- ✅ Behalte `FORWARD_TRANSITIVE` bei
- Mehr Flexibilität für notwendige Schema-Anpassungen
- Reduziert Komplexität während kritischer Phase

**Nach stabiler Migration:**
- ✅ Review der vorhandenen Schemas
- ✅ Dann auf `FORWARD_FULL` hochschalten
- Minimiert Risiko von Blockaden

**Timeline:**
```
Woche 1-2: Cluster Migration → FORWARD_TRANSITIVE beibehalten
Woche 3:   System stabilisiert → Schema-Analyse durchführen
Woche 4:   → FORWARD_FULL für kompatible Subjects aktivieren
```

---

### Sollten wir FORWARD_FULL für alle Topics setzen oder nur für neue?

**Empfehlung: Differenzierte Strategie**

#### ✅ Für **neue Topics**:
- **JA**, definitiv!
- Von Anfang an maximale Sicherheit
- Keine Legacy-Altlasten
- Best Practice für kritische Daten

```bash
# Automatisch für neue Topics setzen (in CI/CD Pipeline)
./scripts/set_compatibility.sh --subject new-topic-value FORWARD_FULL
```

#### 🔍 Für **bestehende Topics**:
**Nur nach Prüfung!**

**Prüfen Sie zuerst:**
```bash
# Einzelnes Topic
./scripts/check_topic_compatibility.sh existing-topic

# Alle Topics
./scripts/check_all_topics_compatibility.sh
```

**Dann entscheiden:**

| Topic-Typ | Empfehlung | Begründung |
|-----------|------------|------------|
| Kritische Business-Events | `FORWARD_FULL` (nach Prüfung) | Maximale Sicherheit erforderlich |
| Standard Application Topics | `FORWARD_TRANSITIVE` | Ausreichend, mehr Flexibilität |
| Development/Test Topics | `FORWARD` oder `NONE` | Schnelle Iteration wichtiger |
| Legacy Topics mit bekannten Issues | Bestehend beibehalten | Risiko vermeiden |

#### Gemischte Strategie möglich

Sie können problemlos verschiedene Modi parallel nutzen:

```bash
# Kritisch
./scripts/set_compatibility.sh --subject orders-value FORWARD_FULL

# Standard
./scripts/set_compatibility.sh --subject logs-value FORWARD_TRANSITIVE

# Development
./scripts/set_compatibility.sh --subject test-events-value FORWARD
```

---

## Technische Fragen

### Was passiert, wenn wir ein inkompatibles Schema registrieren wollen?

**Nach Umstellung auf FORWARD_FULL:**

```bash
curl -X POST \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data '{"schema": "...inkompatibles schema..."}' \
  http://registry:8081/subjects/my-topic-value/versions
```

**Response bei Inkompatibilität:**
```json
{
  "error_code": 409,
  "message": "Schema being registered is incompatible with an earlier schema for subject \"my-topic-value\" using compatibility FORWARD_FULL. Incompatibilities: [{oldSchemaVersion: 2, type: READER_FIELD_MISSING_DEFAULT_VALUE, location: /fields/1, message: field age at /fields/1 does not have a default value, reader: {\"type\":\"record\",\"name\":\"User\",\"fields\":[{\"name\":\"name\",\"type\":\"string\"}]}, writer: {\"type\":\"record\",\"name\":\"User\",\"fields\":[{\"name\":\"name\",\"type\":\"string\"},{\"name\":\"age\",\"type\":\"int\"}]}}]"
}
```

**Ihre Optionen:**
1. **Schema anpassen** um kompatibel zu sein (empfohlen)
2. **Kompatibilitätsmodus temporär lockern** (nur wenn absolut nötig)
3. **Neues Subject erstellen** mit neuem Schema (vermeiden wenn möglich)

---

### Können wir den Modus wieder zurücksetzen?

**Ja, jederzeit!**

```bash
# Für einzelnes Subject
./scripts/set_compatibility.sh --subject my-topic-value FORWARD_TRANSITIVE

# Global
./scripts/set_compatibility.sh --global FORWARD_TRANSITIVE
```

**Wichtig:**
- Der Wechsel ist sofort aktiv
- Betrifft nur **zukünftige** Schema-Registrierungen
- Bestehende Schemas bleiben unverändert

---

### Wie prüfen wir, ob ein Schema kompatibel wäre, OHNE es zu registrieren?

**Mit dem Compatibility Check Endpoint:**

```bash
# Teste neues Schema gegen neueste Version
curl -X POST \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data @new-schema.json \
  http://registry:8081/compatibility/subjects/my-topic-value/versions/latest

# Response:
{
  "is_compatible": true
}
```

**Oder nutze unsere Scripts:**
```bash
# Prüft alle Versionen gegen neueste
./scripts/check_topic_compatibility.sh my-topic
```

---

### Was bedeutet "version" in der Schema Registry?

**Version = Reihenfolge der Schema-Registrierungen pro Subject**

```
Subject: order-events-value

Version 1: {"type": "string"}
Version 2: {"type": "record", "name": "Order", "fields": [...]}
Version 3: {"type": "record", "name": "Order", "fields": [... mit neuem Feld ...]}
```

**Wichtig:**
- Versionen sind pro **Subject** (nicht global)
- Versionen können nicht gelöscht werden (nur Soft-Delete)
- Neueste Version wird für neue Producer genutzt

---

### Welche Schema-Änderungen sind unter FORWARD_FULL erlaubt?

**✅ Erlaubte Änderungen:**

| Änderung | Beispiel | Warum erlaubt? |
|----------|----------|----------------|
| Feld hinzufügen (mit Default) | `age: int (default: 0)` | Alte Consumer ignorieren neues Feld, neue Consumer nutzen Default |
| Feld löschen (mit Default) | Entfernen von `age: int (default: 0)` | Alte Consumer nutzen Default, neue Consumer ignorieren |
| Union-Typ erweitern | `["null", "string"]` → `["null", "string", "int"]` | Alte Consumer können alte Typen lesen |

**❌ Verbotene Änderungen:**

| Änderung | Beispiel | Warum verboten? |
|----------|----------|-----------------|
| Feld hinzufügen (ohne Default) | `age: int` (required) | Alte Consumer können neue Nachrichten nicht lesen |
| Feld-Typ ändern | `age: int` → `age: string` | Inkompatible Typen |
| Erforderliches Feld entfernen | Löschen von `id: string` | Alte Producer senden noch `id`, neue Consumer erwarten es nicht |
| Enum-Werte ändern | `["A", "B"]` → `["A", "C"]` | Alte Consumer kennen `C` nicht |

---

### Wie funktioniert das mit Avro Schema Evolution?

**Avro ermöglicht Schema Evolution durch:**

1. **Default Values:**
```json
{
  "type": "record",
  "name": "User",
  "fields": [
    {"name": "name", "type": "string"},
    {"name": "age", "type": "int", "default": 0}
  ]
}
```

2. **Union Types:**
```json
{
  "name": "optional_field",
  "type": ["null", "string"],
  "default": null
}
```

3. **Aliases:**
```json
{
  "name": "new_name",
  "type": "string",
  "aliases": ["old_name"]
}
```

**FORWARD_FULL nutzt diese Mechanismen und erzwingt:**
- Neue Schemas müssen alte Daten **lesen** können (Backward)
- Alte Schemas müssen neue Daten **lesen** können (Forward)

---

## Migrations-Fragen

### Wie lange dauert die Migration?

**Hängt ab von:**
- Anzahl der Subjects
- Komplexität der Schemas
- Ob Anpassungen nötig sind

**Schätzung:**

| Umgebung | Subjects | Dauer | Beschreibung |
|----------|----------|-------|--------------|
| Klein | < 50 | 1-2h | Analyse + Migration + Validierung |
| Mittel | 50-200 | 2-4h | Inkl. selektive Migration |
| Groß | > 200 | 4-8h | Inkl. ausführliche Tests |

**Plus:** 24h Monitoring nach Migration

---

### Kann die Migration Downtime verursachen?

**Nein, normalerweise nicht!**

**Der Wechsel des Kompatibilitätsmodus:**
- ✅ Erfordert **keine** Downtime
- ✅ Ist sofort aktiv
- ✅ Betrifft nur neue Schema-Registrierungen
- ✅ Laufende Producer/Consumer sind nicht betroffen

**Aber Vorsicht:**
- ⚠️ Wenn ein Schema-Update danach abgelehnt wird, kann Deployment blockiert sein
- ⚠️ Daher: Immer mit Prüfung und Rollback-Plan arbeiten

---

### Was ist, wenn wir kritische Topics haben, die nicht kompatibel sind?

**Mehrere Optionen:**

#### Option 1: Selektive Migration (Empfohlen)
```bash
# Nur kompatible Topics migrieren
cat compatible_topics.txt | while read topic; do
  ./scripts/set_compatibility.sh --subject ${topic}-value FORWARD_FULL
done

# Inkompatible Topics bleiben auf FORWARD_TRANSITIVE
```

#### Option 2: Schema-Historie bereinigen (Vorsicht!)
```bash
# Alte inkompatible Versionen löschen (Soft-Delete)
curl -X DELETE http://registry:8081/subjects/topic-value/versions/1
curl -X DELETE http://registry:8081/subjects/topic-value/versions/2

# ACHTUNG: Nur wenn keine Consumer mehr diese Versionen nutzen!
```

#### Option 3: Neues Subject starten
```bash
# Altes Subject weiter nutzen (FORWARD_TRANSITIVE)
# Neues Subject für neue Daten (FORWARD_FULL)
# Beispiel:
#   Alt: orders-value
#   Neu: orders-v2-value
```

#### Option 4: Inkompatible Topics akzeptieren
```bash
# Behalte FORWARD_TRANSITIVE für problematische Topics
# Akzeptiere, dass zukünftige Updates flexibler sind
# Dokumentiere die Entscheidung
```

---

### Müssen wir alle Consumer/Producer neu deployen?

**Nein!**

Der Wechsel des Kompatibilitätsmodus:
- ✅ Erfordert **keine** Application-Changes
- ✅ Consumer/Producer müssen **nicht** neu deployed werden
- ✅ Betrifft nur das Verhalten der Schema Registry

**Applications sind erst betroffen:**
- Wenn sie versuchen, ein neues **inkompatibles** Schema zu registrieren
- Dann wird die Registrierung abgelehnt
- Das betroffene Deployment schlägt fehl

**Best Practice:**
1. Migriere Kompatibilitätsmodus
2. **Dann** teste nächstes Application-Deployment
3. Falls Probleme: Rollback des Modus (nicht der Application)

---

## Monitoring & Operations

### Wie überwachen wir die Schema Registry nach Migration?

**Wichtige Metriken:**

```bash
# 1. Kompatibilitätsmodus prüfen
curl -s http://registry:8081/config | jq .

# 2. Anzahl Subjects
curl -s http://registry:8081/subjects | jq '. | length'

# 3. Schema Registry Health
curl -s http://registry:8081/subjects
# HTTP 200 = Healthy

# 4. Kafka Backend Topic
kafka-topics --bootstrap-server localhost:9092 \
  --describe --topic _schemas
```

**Nutze Monitoring-Script:**
```bash
./scripts/monitor_registry.sh
```

**In Prometheus/Grafana:**
- `kafka_schema_registry_registered_count`
- `kafka_schema_registry_schemas_created`
- `kafka_schema_registry_api_errors_total`

---

### Was loggen wir am besten?

**Vor der Migration:**
```bash
# Snapshot der Konfiguration
curl -s http://registry:8081/config > pre_migration_config.json

# Liste aller Subjects mit Kompatibilität
curl -s http://registry:8081/subjects | jq -r '.[]' | while read subject; do
  compat=$(curl -s "http://registry:8081/config/$subject" 2>/dev/null | jq -r '.compatibilityLevel // "GLOBAL"')
  echo "$subject: $compat"
done > pre_migration_subjects.txt
```

**Nach der Migration:**
```bash
# Gleiche Informationen sammeln
curl -s http://registry:8081/config > post_migration_config.json

# Diff erstellen
diff pre_migration_subjects.txt post_migration_subjects.txt
```

**Kontinuierliches Logging:**
- Schema Registry Logs (stdout/stderr)
- Fehlgeschlagene Schema-Registrierungen
- Performance-Metriken (Response Times)

---

### Gibt es Performance-Auswirkungen?

**Normalerweise: Nein.**

**FORWARD_FULL vs FORWARD_TRANSITIVE:**
- Beide prüfen Kompatibilität beim Schema-Update
- FORWARD_FULL prüft zusätzlich Backward-Kompatibilität
- **Minimaler** zusätzlicher Overhead (< 10ms)

**Typische Latencies:**
- Schema Read (Cache Hit): < 1ms
- Schema Read (Cache Miss): 10-50ms
- Schema Write (mit Validation): 50-200ms

**FORWARD_FULL fügt hinzu:**
- Extra Validation: ~5-10ms

**Conclusion:** Vernachlässigbar für die meisten Use Cases

---

## Fehlerbehebung

### Script schlägt fehl: "jq not found"

**Problem:** `jq` ist nicht installiert

**Lösung:**
```bash
# Ubuntu/Debian
sudo apt-get install jq

# CentOS/RHEL
sudo yum install jq

# macOS
brew install jq

# Alpine
apk add jq
```

---

### Script schlägt fehl: "Connection refused"

**Problem:** Schema Registry nicht erreichbar

**Lösung:**
```bash
# Prüfe URL
echo $SCHEMA_REGISTRY_URL

# Teste Verbindung
curl -v http://your-registry:8081/subjects

# Prüfe Schema Registry läuft
docker ps | grep schema-registry
# oder
ps aux | grep schema-registry
```

---

### Script zeigt viele inkompatible Versionen

**Das ist normal!**

**Nicht jede Inkompatibilität ist kritisch:**

1. **Analyse:** Prüfe das CSV-Report genau
```bash
cat schema_full_compatibility_report.csv | grep ",false," | less
```

2. **Entscheidung pro Subject:**
   - Kritischer Business-Impact? → Fixe Schema
   - Legacy Topic? → Behalte FORWARD_TRANSITIVE
   - Neuentwicklung? → Starte neues Subject

3. **Selektive Migration:**
```bash
# Migriere nur eindeutig kompatible Subjects
grep ",true," schema_full_compatibility_report.csv | \
  cut -d',' -f1 | sort -u > safe_to_migrate.txt
```

---

### Schema Registry Logs zeigen Compatibility-Errors

**Beispiel Log:**
```
[2024-11-14 10:15:23] ERROR - Schema incompatible with version 3
```

**Analyse:**
```bash
# Prüfe betroffenes Subject
./scripts/check_topic_compatibility.sh affected-topic

# Prüfe Version 3 Details
curl -s http://registry:8081/subjects/affected-topic-value/versions/3 | jq .

# Teste Kompatibilität explizit
curl -X POST \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data @new-schema.json \
  http://registry:8081/compatibility/subjects/affected-topic-value/versions/3
```

---

## Best Practices

### ✅ Do's

- **Immer** Scripts zur Prüfung nutzen vor Migration
- **Immer** in Staging testen
- **Immer** Rollback-Plan haben
- **Immer** Migration dokumentieren
- **Selektiv** migrieren (nicht blind alle)
- **Monitoring** für 24h nach Migration

### ❌ Don'ts

- **Nicht** direkt in Produktion migrieren ohne Tests
- **Nicht** alle Topics gleichzeitig migrieren
- **Nicht** ohne Analyse der Kompatibilität
- **Nicht** ohne Backup der Konfiguration
- **Nicht** während Peak-Zeiten migrieren
- **Nicht** ohne Team-Koordination

---

## Zusammenfassung

**Die 5 wichtigsten Punkte:**

1. **FORWARD_FULL = Höchste Sicherheit** - Aber auch strengste Validation
2. **Nach Migration umstellen** - Nicht währenddessen
3. **Prüfe erst, migriere dann** - Nutze die bereitgestellten Scripts
4. **Selektive Strategie** - Nicht alle Topics müssen FORWARD_FULL haben
5. **Rollback-Plan** - Immer bereit zum Zurücksetzen

**Quick Reference:**
```bash
# 1. Prüfen
./scripts/check_topic_compatibility.sh my-topic

# 2. Migrieren
./scripts/set_compatibility.sh --subject my-topic-value FORWARD_FULL

# 3. Verifizieren
curl -s http://registry:8081/config/my-topic-value | jq .

# 4. Bei Problemen: Rollback
./scripts/set_compatibility.sh --subject my-topic-value FORWARD_TRANSITIVE
```

---

**Weitere Fragen?**

Siehe auch:
- [README.md](./README.md) - Hauptdokumentation
- [MIGRATION-WORKFLOW.md](./MIGRATION-WORKFLOW.md) - Detaillierter Workflow
- [Scripts](./scripts/) - Alle verfügbaren Scripts
