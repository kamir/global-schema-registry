# Migration von FORWARD_TRANSITIVE auf FULL_TRANSITIVE

> **⚠️ WICHTIGE KORREKTUR:**
> **"FORWARD_FULL" ist kein gültiger Confluent Schema Registry Kompatibilitätsmodus.**
>
> Der korrekte Modus für maximale Sicherheit ist **FULL_TRANSITIVE**.
>
> Diese Anleitung wurde aktualisiert, um die korrekte Terminologie zu verwenden.

## Übersicht

Diese Anleitung beschreibt den sicheren Wechsel von `FORWARD_TRANSITIVE` auf `FULL_TRANSITIVE` Kompatibilitätsmodus in der Confluent Schema Registry.

**Ziel:** Maximale Sicherheit bei Schema-Kompatibilitäten durch den strengsten Kompatibilitätsmodus (bidirektional + transitiv).

## Inhaltsverzeichnis

- [Unterschied zwischen FORWARD_TRANSITIVE und FULL_TRANSITIVE](#unterschied-zwischen-forward_transitive-und-full_transitive)
- [Risiken und Empfehlungen](#risiken-und-empfehlungen)
- [Migrationsstrategie](#migrationsstrategie)
- [Verwendung der Scripts](#verwendung-der-scripts)
- [Best Practices](#best-practices)

---

## Unterschied zwischen FORWARD_TRANSITIVE und FULL_TRANSITIVE

### FORWARD_TRANSITIVE
- **Regel:** Neue Schemas müssen vorwärts-kompatibel mit allen früheren Versionen sein
- **Fokus:** Consumer der Zukunft können alte Daten lesen
- **Prüfung:** Nur vorwärts (alte Schemas lesen neue Daten)
- **Anwendungsfall:** Standard-Forward-Kompatibilität mit guter Flexibilität

### FULL_TRANSITIVE ⭐ (Empfohlen)
- **Regel:** Neue Schemas müssen **vorwärts UND rückwärts** kompatibel mit allen früheren Versionen sein
- **Fokus:** Maximale Sicherheit - alte Producer UND alte Consumer funktionieren weiterhin
- **Prüfung:** Bidirektional + transitiv (BACKWARD_TRANSITIVE + FORWARD_TRANSITIVE)
- **Anwendungsfall:** Kritische Topics, bei denen absolute Kompatibilität erforderlich ist

**Wichtig:** FULL_TRANSITIVE ist der **strengste Kompatibilitätsmodus** in Confluent Schema Registry und verhindert effektiv disruptive Änderungen.

---

## Risiken und Empfehlungen

### ✅ Darf man einfach von FORWARD_TRANSITIVE auf FULL_TRANSITIVE wechseln?

**Ja - aber mit Vorsicht!**

Der Wechsel ist sicher, **solange alle existierenden Schema-Versionen rückwärts-kompatibel sind**.

#### Was passiert beim Wechsel?

- Der Wechsel selbst führt **keine Migration** aus
- Die Registry prüft ab dem Umschalten alle **zukünftigen** Schema-Updates gegen die striktere Full-Kompatibilität
- Bestehende Schemas bleiben unverändert

#### ⚠️ Risiko

Wenn es in alten Versionen Änderungen gab, die **nicht rückwärts-kompatibel** sind:
- Könnte ein zukünftiges Schema-Update nach dem Umschalten **abgelehnt werden**
- Obwohl es vorher unter FORWARD_TRANSITIVE erlaubt gewesen wäre
- Sie bekommen beim Setzen der Kompatibilität **keinen Fehler** für bestehende Versionen
- Der Fehler tritt erst beim **nächsten Schema-Update** auf

---

## Migrationsstrategie

### 🎯 Empfohlener Zeitpunkt

**Nach einer stabilen Migration** umstellen!

```
Während der Migration    → FORWARD_TRANSITIVE beibehalten (flexibler)
Nach stabiler Migration  → Review der vorhandenen Schemas
Dann erst umschalten    → Auf FULL_TRANSITIVE hochschalten
```

**Vorteile:**
- Reduziert das Risiko, dass Migrations-Schritte durch strengere Validierung blockiert werden
- Ermöglicht es, Kompatibilitätsprobleme gezielt zu identifizieren und zu beheben
- Vermeidet unerwartete Blockaden während kritischer Migrationsphasen

### 📋 Sollten wir das nur für neue Topics machen oder für alle?

#### Für bestehende Topics

**Nur wenn alle aktuellen Versionen tatsächlich rückwärts-kompatibel sind.**

❌ **Nicht empfohlen, wenn:**
- Die Schema-Historie unbekannte Änderungen enthält
- Es bereits bekannte inkompatible Versionen gibt
- Kritische Anwendungen betroffen sind, die nicht getestet wurden

✅ **Empfohlen, wenn:**
- Alle Schemas wurden geprüft und sind kompatibel
- Die Anwendung ist gut getestet
- Ein Rollback-Plan existiert

#### Für neue Topics

✅ **Ja, das ist der beste Ort, um FULL_TRANSITIVE standardmäßig zu aktivieren.**

**Vorteile:**
- Keine Legacy-Altlasten
- Von Anfang an maximale Sicherheit
- Klare Richtlinien für neue Entwicklungen

### 🔄 Gemischte Strategie möglich

Sie können problemlos eine **gemischte Welt** haben:

| Topic-Typ | Empfohlene Strategie | Begründung |
|-----------|---------------------|------------|
| Kritische Business-Topics | `FULL_TRANSITIVE` | Maximale Sicherheit, keine Ausfälle |
| Interne/Development-Topics | `FORWARD_TRANSITIVE` | Mehr Flexibilität bei der Entwicklung |
| Volatile/Experimental Topics | `FORWARD` | Schnelle Iteration möglich |

---

## Verwendung der Scripts

Wir bieten zwei Scripts zur Kompatibilitätsprüfung:

### Script #1: Einzelnes Topic prüfen
```bash
./scripts/check_topic_compatibility.sh <topic-name>
```

**Verwendung:**
```bash
SCHEMA_REGISTRY_URL=http://schema-registry:8081 \
  ./scripts/check_topic_compatibility.sh my-important-topic
```

**Was wird geprüft:**
- Prüft `<topic>-key` und `<topic>-value` Subjects
- Testet alle älteren Versionen gegen die neueste Version
- Gibt klare OK/FAILED Meldungen aus
- Exit Code 0 = sicher für FULL_TRANSITIVE
- Exit Code 2 = nicht kompatibel

### Script #2: Alle Topics prüfen
```bash
./scripts/check_all_topics_compatibility.sh
```

**Verwendung:**
```bash
SCHEMA_REGISTRY_URL=http://schema-registry:8081 \
  REPORT_FILE=compatibility_report.csv \
  ./scripts/check_all_topics_compatibility.sh
```

**Output:**
- CSV-Report mit detaillierten Ergebnissen
- Zeigt für jede Subject/Version-Kombination die Kompatibilität
- Zusammenfassung am Ende

**CSV-Format:**
```csv
subject,version,latest_version,is_compatible
my-topic-value,1,3,true
my-topic-value,2,3,true
my-topic-value,3,3,true
```

---

## Best Practices

### Vorgehen in der Praxis

#### Schritt 1: Bestehende Schemas prüfen

**Option A: Mit Confluent CLI**
```bash
confluent schema-registry compatibility test \
  --subject my-topic-value \
  --version latest \
  --schema schema.avsc
```

**Option B: Mit unseren Scripts**
```bash
./scripts/check_topic_compatibility.sh my-topic
```

#### Schritt 2: Strengere Kompatibilität aktivieren

**Global setzen:**
```bash
curl -X PUT -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data '{"compatibility": "FULL_TRANSITIVE"}' \
  http://schema-registry:8081/config
```

**Pro Subject setzen:**
```bash
curl -X PUT -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data '{"compatibility": "FULL_TRANSITIVE"}' \
  http://schema-registry:8081/config/my-topic-value
```

#### Schritt 3: Erstes neues Schema bewusst deployen

**Wichtig:** Wenn das erste Schema nach dem Umschalten akzeptiert wird, wissen Sie, dass die Historie kompatibel ist.

**Test-Deployment:**
```bash
# Schema registrieren (wird validiert gegen FULL_TRANSITIVE)
curl -X POST -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data @new-schema.json \
  http://schema-registry:8081/subjects/my-topic-value/versions
```

**Bei Erfolg:**
```json
{"id": 42}
```

**Bei Fehler:**
```json
{
  "error_code": 409,
  "message": "Schema being registered is incompatible with an earlier schema"
}
```

### Rollback-Strategie

Falls Probleme auftreten:

```bash
# Zurück zu FORWARD_TRANSITIVE
curl -X PUT -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data '{"compatibility": "FORWARD_TRANSITIVE"}' \
  http://schema-registry:8081/config/my-topic-value
```

---

## Zusammenfassung

### ✅ Do's

- **Nach der Migration** umstellen
- **Schemas vorher prüfen** mit den bereitgestellten Scripts
- **Für neue Topics** standardmäßig FULL_TRANSITIVE aktivieren
- **Gemischte Strategie** je nach Topic-Kritikalität verwenden
- **Rollback-Plan** bereithalten
- **Erstes Schema nach Umstellung bewusst testen**

### ❌ Don'ts

- **Nicht während laufender Migration** umstellen
- **Nicht ohne Prüfung** für alle bestehenden Topics aktivieren
- **Nicht ohne Testphase** in Produktion rollout
- **Kein Deployment** ohne Monitoring der Registry-Logs

---

## Support und Fragen

Bei Fragen zur Migration:

1. **Scripts ausführen** und Report analysieren
2. **Inkompatible Subjects identifizieren**
3. **Entscheidung treffen:** Schema-Historie bereinigen oder Subject ausschließen
4. **Schrittweise Migration** durchführen

## Siehe auch

- [Confluent Schema Registry Dokumentation](https://docs.confluent.io/platform/current/schema-registry/avro.html)
- [Schema Evolution and Compatibility](https://docs.confluent.io/platform/current/schema-registry/avro.html#schema-evolution-and-compatibility)
- [Scripts in diesem Verzeichnis](./scripts/)
