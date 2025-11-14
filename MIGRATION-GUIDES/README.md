# Schema Registry Migration Guides

Dieser Ordner enthält umfassende Anleitungen für verschiedene Migrations-Szenarien in der Confluent Schema Registry.

## Verfügbare Migration Guides

### 🔒 [FORWARD_FULL Migration](./forward-full/)

**Ziel:** Migration von `FORWARD_TRANSITIVE` auf `FORWARD_FULL` für maximale Schema-Kompatibilitätssicherheit.

**Inhalt:**
- ✅ Detaillierte Dokumentation mit Best Practices
- ✅ Automatisierte Kompatibilitäts-Prüfungs-Scripts
- ✅ Schritt-für-Schritt Migration Workflow
- ✅ Helper Scripts zum Setzen von Kompatibilitätsmodi
- ✅ Troubleshooting Guide
- ✅ Rollback-Strategien

**Für wen geeignet:**
- Teams, die maximale Schema-Sicherheit benötigen
- Kritische Business-Topics mit hohen Compliance-Anforderungen
- Umgebungen nach erfolgreicher Cluster-Migration

**Quick Start:**
```bash
cd forward-full/scripts
export SCHEMA_REGISTRY_URL=http://your-registry:8081

# Prüfe ein einzelnes Topic
./check_topic_compatibility.sh my-topic

# Prüfe alle Topics und erstelle Report
./check_all_topics_compatibility.sh

# Setze Kompatibilität
./set_compatibility.sh --subject my-topic-value FORWARD_FULL
```

---

## Kompatibilitätsmodi - Übersicht

Die Confluent Schema Registry unterstützt verschiedene Kompatibilitätsmodi:

| Modus | Beschreibung | Use Case |
|-------|--------------|----------|
| **BACKWARD** | Neue Schemas können alte Daten lesen | Standard, Consumer-Updates zuerst |
| **BACKWARD_TRANSITIVE** | Neue Schemas kompatibel mit ALLEN alten | Strikte Backward-Kompatibilität |
| **FORWARD** | Alte Schemas können neue Daten lesen | Producer-Updates zuerst |
| **FORWARD_TRANSITIVE** | Alte Schemas kompatibel mit ALLEN neuen | Strikte Forward-Kompatibilität |
| **FORWARD_FULL** | FORWARD + BACKWARD für ALLE Versionen | **Höchste Sicherheit** |
| **FULL** | BACKWARD + FORWARD | Bidirektionale Kompatibilität |
| **FULL_TRANSITIVE** | FULL für ALLE Versionen | Absolute Kompatibilität |
| **NONE** | Keine Prüfungen | Nur für Development |

### Visualisierung

```
Flexibilität        ←→        Sicherheit
─────────────────────────────────────────
NONE → FORWARD → FORWARD_TRANSITIVE → FORWARD_FULL
                                              ↑
                                     Sie sind hier
```

---

## Allgemeine Best Practices

### 1. Analyse vor Migration

Führen Sie immer eine gründliche Analyse durch, bevor Sie Kompatibilitätsmodi ändern:

```bash
# Prüfe aktuelle Konfiguration
curl -s http://registry:8081/config | jq .

# Liste alle Subjects
curl -s http://registry:8081/subjects | jq .

# Prüfe Subject-spezifische Konfiguration
curl -s http://registry:8081/config/<subject-name> | jq .
```

### 2. Staging-Tests

**Niemals** direkt in Produktion migrieren!

1. Test in Staging/Development
2. Validierung mit echten Daten
3. Performance-Tests
4. Erst dann: Produktion

### 3. Schrittweise Vorgehen

```
Analyse → Test → Migration (schrittweise) → Validierung → Monitoring
```

### 4. Rollback-Plan

Haben Sie immer einen Rollback-Plan:

```bash
# Backup vor Migration
curl -s http://registry:8081/config > backup.json

# Bei Problemen: Restore
curl -X PUT \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data @backup.json \
  http://registry:8081/config
```

### 5. Dokumentation

Dokumentieren Sie:
- [ ] Grund für die Migration
- [ ] Datum und Uhrzeit
- [ ] Betroffene Subjects
- [ ] Erwartete Auswirkungen
- [ ] Verantwortliche Personen
- [ ] Rollback-Prozedur

---

## Häufige Migrations-Szenarien

### Szenario 1: Neue Umgebung aufsetzen

**Empfehlung:** Starten Sie direkt mit `FORWARD_FULL` oder `FULL_TRANSITIVE`

```bash
# Setze globale Konfiguration
curl -X PUT \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data '{"compatibility": "FORWARD_FULL"}' \
  http://registry:8081/config
```

### Szenario 2: Nach Cluster-Migration

**Empfehlung:**
1. Migration abschließen mit bisheriger Konfiguration
2. System stabilisieren
3. Dann: Kompatibilitätsmodus upgraden

Siehe: [FORWARD_FULL Migration Guide](./forward-full/)

### Szenario 3: Gemischte Umgebung

**Empfehlung:** Unterschiedliche Modi für verschiedene Topic-Typen

```bash
# Kritische Business-Topics
./set_compatibility.sh --subject business-events-value FORWARD_FULL

# Interne Logs
./set_compatibility.sh --subject app-logs-value FORWARD_TRANSITIVE

# Development Topics
./set_compatibility.sh --subject dev-test-value FORWARD
```

### Szenario 4: Legacy-System mit vielen Inkompatibilitäten

**Empfehlung:**
1. Neue Topics: Strikte Kompatibilität
2. Legacy Topics: Bestehendes beibehalten
3. Schrittweise bereinigen

```bash
# Nur neue Topics migrieren
for topic in $(cat new_topics.txt); do
  ./set_compatibility.sh --subject ${topic}-value FORWARD_FULL
done
```

---

## Tools und Scripts

Alle Migration Guides enthalten fertige Scripts:

### Kompatibilitäts-Prüfung
- `check_topic_compatibility.sh` - Einzelnes Topic prüfen
- `check_all_topics_compatibility.sh` - Alle Topics analysieren

### Konfiguration
- `set_compatibility.sh` - Kompatibilität setzen (global oder per Subject)

### Monitoring
- `monitor_registry.sh` - Kontinuierliches Monitoring
- `validation_report.sh` - Validierungs-Report nach Migration

---

## Troubleshooting

### Problem: Schema wird abgelehnt

```json
{"error_code": 409, "message": "Schema being registered is incompatible"}
```

**Lösung:**
1. Prüfe Kompatibilität mit Scripts
2. Analysiere welche Änderung inkompatibel ist
3. Passe Schema an ODER lockere Kompatibilitätsmodus

### Problem: Performance-Degradation

**Symptome:** Schema Registry antwortet langsam

**Lösung:**
1. Prüfe Kafka Backend (Topic `_schemas`)
2. Überprüfe Registry Logs
3. Reduziere Anzahl gleichzeitiger Schema-Registrierungen

### Problem: Consumer/Producer Fehler

**Symptome:** Applications können keine Nachrichten senden/empfangen

**Lösung:**
1. Verifiziere Schema Registry Erreichbarkeit
2. Prüfe Schema Cache in Application
3. Prüfe Subject-Naming-Strategy
4. Verifiziere Serializer/Deserializer Konfiguration

---

## Weitere Ressourcen

### Offizielle Confluent Dokumentation
- [Schema Evolution and Compatibility](https://docs.confluent.io/platform/current/schema-registry/avro.html#schema-evolution-and-compatibility)
- [Schema Registry API Reference](https://docs.confluent.io/platform/current/schema-registry/develop/api.html)
- [Schema Registry Configuration](https://docs.confluent.io/platform/current/schema-registry/installation/config.html)

### In diesem Repository
- [Schema ID Creation](../DOCS/schema-id-creation.md)
- [GitOps Schema Federation](../GITOPS-SCHEMA-FEDERATION/)
- [Allianz Schema Registry Analysis](../CUSTOM_RESEARCH/Allianz-Schema-Registry-Analysis.md)

---

## Support

Bei Fragen oder Problemen:

1. **Dokumentation prüfen:** Jeder Migration Guide enthält ausführliche Troubleshooting-Sektionen
2. **Scripts nutzen:** Die bereitgestellten Scripts helfen bei Analyse und Diagnose
3. **Logs analysieren:** Schema Registry und Kafka Logs enthalten wertvolle Hinweise
4. **Community:** Confluent Community Forum und GitHub Issues

---

## Changelog

### 2024-11-14
- ✨ Initial Release
- 📝 FORWARD_FULL Migration Guide hinzugefügt
- 🛠️ Kompatibilitäts-Prüfungs-Scripts
- 📖 Workflow-Dokumentation
- 🔧 Helper Scripts

---

## Beitragen

Weitere Migration Guides geplant:
- [ ] BACKWARD_TRANSITIVE Migration
- [ ] FULL_TRANSITIVE Migration
- [ ] Multi-Datacenter Schema Migration
- [ ] Schema Registry Version Upgrades

Contributions sind willkommen!
