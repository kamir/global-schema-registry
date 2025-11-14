# Schema Registry Compatibility Modes - Complete Guide

**Version:** 1.0.0
**Date:** 2025-11-14
**Status:** ✅ Production Ready

---

## ⚠️ Important Clarification: FORWARD_FULL vs FULL_TRANSITIVE

### The Naming Confusion

**FORWARD_FULL is NOT a valid Confluent Schema Registry compatibility mode.**

If you're looking for the "strictest forward compatibility strategy" that checks both forward AND backward compatibility with all previous versions, you want:

### ✅ **FULL_TRANSITIVE** (The Correct Mode)

**FULL_TRANSITIVE** provides:
- ✅ **Backward Transitive**: New schema can read data written with ALL previous schemas
- ✅ **Forward Transitive**: Data written with new schema can be read by ALL previous schemas
- ✅ **Maximum Safety**: Both producers and consumers can be upgraded independently

This is the **strictest compatibility mode** and ensures maximum safety for schema evolution.

---

## 📋 All Valid Compatibility Modes

Confluent Schema Registry supports **7 compatibility modes**:

| Mode | Description | Upgrade Order |
|------|-------------|---------------|
| **NONE** | No compatibility checking | Any order |
| **BACKWARD** | New schema can read old data (last version) | Consumers first |
| **BACKWARD_TRANSITIVE** | New schema can read old data (all versions) | Consumers first |
| **FORWARD** | Old schema can read new data (last version) | Producers first |
| **FORWARD_TRANSITIVE** | Old schema can read new data (all versions) | Producers first |
| **FULL** | Both BACKWARD and FORWARD (last version) | Any order |
| **FULL_TRANSITIVE** | Both BACKWARD_TRANSITIVE and FORWARD_TRANSITIVE | Any order |

---

## 🔄 Compatibility Mode Transitions - All Pairs

### Legend
- ✅ **SAFE**: Transition is always safe
- ⚠️ **RISKY**: Requires validation of existing schemas
- 🔴 **DANGEROUS**: High risk of breaking changes
- ⏺️ **N/A**: Same mode (no transition)

### Complete Transition Matrix (7x7 = 49 combinations)

| From ↓ / To → | NONE | BACKWARD | BACKWARD_TRANSITIVE | FORWARD | FORWARD_TRANSITIVE | FULL | FULL_TRANSITIVE |
|---------------|------|----------|---------------------|---------|-------------------|------|-----------------|
| **NONE** | ⏺️ | ⚠️ | ⚠️ | ⚠️ | ⚠️ | 🔴 | 🔴 |
| **BACKWARD** | ✅ | ⏺️ | ✅ | ⚠️ | 🔴 | ⚠️ | 🔴 |
| **BACKWARD_TRANSITIVE** | ✅ | ✅ | ⏺️ | 🔴 | 🔴 | 🔴 | 🔴 |
| **FORWARD** | ✅ | ⚠️ | 🔴 | ⏺️ | ✅ | ⚠️ | 🔴 |
| **FORWARD_TRANSITIVE** | ✅ | 🔴 | 🔴 | ✅ | ⏺️ | 🔴 | ⚠️ |
| **FULL** | ✅ | ✅ | ⚠️ | ✅ | ⚠️ | ⏺️ | ✅ |
| **FULL_TRANSITIVE** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⏺️ |

---

## 📊 Detailed Transition Scenarios

### Scenario 1: NONE → Any Mode ⚠️🔴

**Risk Level:** HIGH

**Why Risky:**
- NONE allows ANY schema changes (breaking or not)
- Switching to a stricter mode will not validate existing schema history
- Future updates may fail if historical schemas are incompatible

**Example:**
```
Version 1: {"type": "record", "name": "User", "fields": [{"name": "id", "type": "int"}]}
Version 2: {"type": "record", "name": "User", "fields": [{"name": "userId", "type": "string"}]}
           ☝️ Completely different schema! Allowed under NONE

If you switch to BACKWARD: Version 3 must be compatible with V2, but V2 wasn't compatible with V1!
```

**Recommendation:**
1. Audit all existing schema versions
2. Fix incompatibilities before switching
3. Start with BACKWARD, then gradually increase strictness

---

### Scenario 2: BACKWARD → BACKWARD_TRANSITIVE ✅

**Risk Level:** LOW - SAFE

**Why Safe:**
- BACKWARD_TRANSITIVE is strictly more restrictive
- If schemas worked under BACKWARD, adding transitive checking only makes it safer
- No breaking changes introduced

**Example:**
```
Under BACKWARD:
V1 → V2 ✅ (V2 compatible with V1)
V2 → V3 ✅ (V3 compatible with V2)

Under BACKWARD_TRANSITIVE:
V1 → V2 → V3 ✅ (V3 must be compatible with BOTH V1 and V2)
```

**Recommendation:** ✅ Switch immediately if you want stricter validation

---

### Scenario 3: BACKWARD → FORWARD 🔴

**Risk Level:** HIGH - DANGEROUS

**Why Dangerous:**
- Completely different compatibility semantics
- BACKWARD: "new reads old" → FORWARD: "old reads new"
- Schemas optimized for BACKWARD may violate FORWARD rules

**Example:**
```avro
# Under BACKWARD - this evolution is ALLOWED:
V1: {
  "type": "record",
  "name": "User",
  "fields": [
    {"name": "id", "type": "int"}
  ]
}

V2: {
  "type": "record",
  "name": "User",
  "fields": [
    {"name": "id", "type": "int"},
    {"name": "email", "type": "string", "default": ""}  # Added with default
  ]
}
✅ BACKWARD compatible (V2 can read V1 data)
❌ NOT FORWARD compatible (V1 cannot read V2 data - "email" field unknown)

If you switch to FORWARD, V3 updates might fail unexpectedly!
```

**Recommendation:** 🛑 Don't switch directly. Use FULL as intermediate step.

---

### Scenario 4: FORWARD_TRANSITIVE → FULL_TRANSITIVE ⚠️

**Risk Level:** MODERATE - RISKY

**Why Risky:**
- FULL_TRANSITIVE adds backward compatibility requirement
- Schemas designed for FORWARD_TRANSITIVE might not be backward compatible
- Common with write-heavy systems that only cared about old consumers

**Example:**
```avro
# Under FORWARD_TRANSITIVE - this evolution is ALLOWED:
V1: {
  "type": "record",
  "name": "Event",
  "fields": [
    {"name": "id", "type": "int"},
    {"name": "timestamp", "type": "long"},
    {"name": "optional_field", "type": ["null", "string"], "default": null}
  ]
}

V2: {
  "type": "record",
  "name": "Event",
  "fields": [
    {"name": "id", "type": "int"},
    {"name": "timestamp", "type": "long"}
    # Removed optional_field
  ]
}
✅ FORWARD_TRANSITIVE: V1 consumers can read V2 data (just ignore missing field)
❌ NOT BACKWARD: V2 consumers cannot read V1 data (no default for removed field)

Switching to FULL_TRANSITIVE will reject V3 if it's not backward compatible!
```

**Recommendation:**
1. ⚠️ Check all schema versions for backward compatibility
2. Run validation tests (see test schemas below)
3. Fix incompatibilities before switching
4. Use bulk compatibility check API

---

### Scenario 5: Any Mode → NONE ✅

**Risk Level:** LOW - SAFE (but not recommended)

**Why Safe:**
- NONE removes all restrictions
- No validation failures
- Essentially "disabling" schema governance

**Why Not Recommended:**
- Loses all safety guarantees
- Opens door to breaking changes
- Only use for emergency situations or decommissioned topics

**Recommendation:** ⚠️ Only do this temporarily for emergencies

---

### Scenario 6: FULL_TRANSITIVE → Any Mode ✅

**Risk Level:** LOW - SAFE

**Why Safe:**
- FULL_TRANSITIVE is the strictest mode
- All schemas are already compatible in every direction
- Downgrading to less strict mode won't cause validation failures

**Recommendation:** ✅ Safe, but you're reducing your safety guarantees

---

## 🧪 Test Schemas for All Compatibility Scenarios

### Base Schema (Version 1)

```json
{
  "type": "record",
  "name": "User",
  "namespace": "com.example",
  "fields": [
    {
      "name": "id",
      "type": "int",
      "doc": "User ID"
    },
    {
      "name": "username",
      "type": "string",
      "doc": "Username"
    }
  ]
}
```

---

### Test Case 1: BACKWARD Compatible Change

**Scenario:** Adding optional field with default

```json
{
  "type": "record",
  "name": "User",
  "namespace": "com.example",
  "fields": [
    {
      "name": "id",
      "type": "int"
    },
    {
      "name": "username",
      "type": "string"
    },
    {
      "name": "email",
      "type": "string",
      "default": ""
    }
  ]
}
```

**Compatibility:**
- ✅ BACKWARD: New schema can read old data (uses default for missing "email")
- ❌ FORWARD: Old schema cannot read new data (doesn't know about "email" field)
- ❌ FULL: Fails (not FORWARD compatible)

---

### Test Case 2: FORWARD Compatible Change

**Scenario:** Removing optional field

```json
{
  "type": "record",
  "name": "User",
  "namespace": "com.example",
  "fields": [
    {
      "name": "id",
      "type": "int"
    }
  ]
}
```

**Assuming V1 had optional "username" with default:**

```json
{
  "type": "record",
  "name": "User",
  "namespace": "com.example",
  "fields": [
    {
      "name": "id",
      "type": "int"
    },
    {
      "name": "username",
      "type": "string",
      "default": ""
    }
  ]
}
```

**Compatibility:**
- ❌ BACKWARD: New schema cannot read old data (missing field "username")
- ✅ FORWARD: Old schema can read new data (uses default for missing "username")
- ❌ FULL: Fails (not BACKWARD compatible)

---

### Test Case 3: FULL Compatible Change

**Scenario:** Adding optional field (nullable with null default)

```json
{
  "type": "record",
  "name": "User",
  "namespace": "com.example",
  "fields": [
    {
      "name": "id",
      "type": "int"
    },
    {
      "name": "username",
      "type": "string"
    },
    {
      "name": "email",
      "type": ["null", "string"],
      "default": null
    }
  ]
}
```

**Compatibility:**
- ✅ BACKWARD: New schema reads old data (uses null default)
- ✅ FORWARD: Old schema reads new data (ignores unknown field)
- ✅ FULL: Both directions work!

---

### Test Case 4: NONE (Breaking Change)

**Scenario:** Changing field type

```json
{
  "type": "record",
  "name": "User",
  "namespace": "com.example",
  "fields": [
    {
      "name": "id",
      "type": "string",
      "doc": "Changed from int to string"
    },
    {
      "name": "username",
      "type": "string"
    }
  ]
}
```

**Compatibility:**
- ❌ BACKWARD: Incompatible
- ❌ FORWARD: Incompatible
- ❌ FULL: Incompatible
- ✅ NONE: Allowed (but breaks consumers!)

---

### Test Case 5: Type Widening (BACKWARD)

**Scenario:** Union type (int or long)

```json
{
  "type": "record",
  "name": "User",
  "namespace": "com.example",
  "fields": [
    {
      "name": "id",
      "type": ["int", "long"],
      "doc": "Can now accept both int and long"
    },
    {
      "name": "username",
      "type": "string"
    }
  ]
}
```

**Compatibility:**
- ✅ BACKWARD: Can read old "int" values
- ❌ FORWARD: Old schema expects only "int", not union
- ❌ FULL: Fails forward check

---

### Test Case 6: Field Rename with Alias (FULL Compatible)

**Scenario:** Renaming field with alias

```json
{
  "type": "record",
  "name": "User",
  "namespace": "com.example",
  "fields": [
    {
      "name": "id",
      "type": "int"
    },
    {
      "name": "user_name",
      "type": "string",
      "aliases": ["username"],
      "doc": "Renamed from 'username' to 'user_name'"
    }
  ]
}
```

**Compatibility:**
- ✅ BACKWARD: Alias allows reading old data with "username"
- ✅ FORWARD: Old schema reads new data (same serialization)
- ✅ FULL: Works in both directions

---

### Test Case 7: Adding Required Field (NONE only)

**Scenario:** Adding field without default

```json
{
  "type": "record",
  "name": "User",
  "namespace": "com.example",
  "fields": [
    {
      "name": "id",
      "type": "int"
    },
    {
      "name": "username",
      "type": "string"
    },
    {
      "name": "email",
      "type": "string"
    }
  ]
}
```

**Compatibility:**
- ❌ BACKWARD: Cannot read old data (no value for "email")
- ❌ FORWARD: Old schema doesn't know about "email"
- ❌ FULL: Incompatible both ways
- ✅ NONE: Allowed (but BREAKS everything!)

---

## 🧪 Complete Test Suite

### Test Data Structure

```python
# tests/test_compatibility_transitions.py

COMPATIBILITY_TEST_CASES = {
    # Format: (from_mode, to_mode, risk_level, should_validate_before_switch)

    # NONE transitions
    ("NONE", "BACKWARD", "RISKY", True),
    ("NONE", "BACKWARD_TRANSITIVE", "RISKY", True),
    ("NONE", "FORWARD", "RISKY", True),
    ("NONE", "FORWARD_TRANSITIVE", "RISKY", True),
    ("NONE", "FULL", "DANGEROUS", True),
    ("NONE", "FULL_TRANSITIVE", "DANGEROUS", True),

    # BACKWARD transitions
    ("BACKWARD", "NONE", "SAFE", False),
    ("BACKWARD", "BACKWARD_TRANSITIVE", "SAFE", False),
    ("BACKWARD", "FORWARD", "DANGEROUS", True),
    ("BACKWARD", "FORWARD_TRANSITIVE", "DANGEROUS", True),
    ("BACKWARD", "FULL", "RISKY", True),
    ("BACKWARD", "FULL_TRANSITIVE", "DANGEROUS", True),

    # BACKWARD_TRANSITIVE transitions
    ("BACKWARD_TRANSITIVE", "NONE", "SAFE", False),
    ("BACKWARD_TRANSITIVE", "BACKWARD", "SAFE", False),
    ("BACKWARD_TRANSITIVE", "FORWARD", "DANGEROUS", True),
    ("BACKWARD_TRANSITIVE", "FORWARD_TRANSITIVE", "DANGEROUS", True),
    ("BACKWARD_TRANSITIVE", "FULL", "DANGEROUS", True),
    ("BACKWARD_TRANSITIVE", "FULL_TRANSITIVE", "DANGEROUS", True),

    # FORWARD transitions
    ("FORWARD", "NONE", "SAFE", False),
    ("FORWARD", "BACKWARD", "DANGEROUS", True),
    ("FORWARD", "BACKWARD_TRANSITIVE", "DANGEROUS", True),
    ("FORWARD", "FORWARD_TRANSITIVE", "SAFE", False),
    ("FORWARD", "FULL", "RISKY", True),
    ("FORWARD", "FULL_TRANSITIVE", "DANGEROUS", True),

    # FORWARD_TRANSITIVE transitions
    ("FORWARD_TRANSITIVE", "NONE", "SAFE", False),
    ("FORWARD_TRANSITIVE", "BACKWARD", "DANGEROUS", True),
    ("FORWARD_TRANSITIVE", "BACKWARD_TRANSITIVE", "DANGEROUS", True),
    ("FORWARD_TRANSITIVE", "FORWARD", "SAFE", False),
    ("FORWARD_TRANSITIVE", "FULL", "DANGEROUS", True),
    ("FORWARD_TRANSITIVE", "FULL_TRANSITIVE", "RISKY", True),

    # FULL transitions
    ("FULL", "NONE", "SAFE", False),
    ("FULL", "BACKWARD", "SAFE", False),
    ("FULL", "BACKWARD_TRANSITIVE", "RISKY", True),
    ("FULL", "FORWARD", "SAFE", False),
    ("FULL", "FORWARD_TRANSITIVE", "RISKY", True),
    ("FULL", "FULL_TRANSITIVE", "SAFE", False),

    # FULL_TRANSITIVE transitions (all safe - most restrictive)
    ("FULL_TRANSITIVE", "NONE", "SAFE", False),
    ("FULL_TRANSITIVE", "BACKWARD", "SAFE", False),
    ("FULL_TRANSITIVE", "BACKWARD_TRANSITIVE", "SAFE", False),
    ("FULL_TRANSITIVE", "FORWARD", "SAFE", False),
    ("FULL_TRANSITIVE", "FORWARD_TRANSITIVE", "SAFE", False),
    ("FULL_TRANSITIVE", "FULL", "SAFE", False),
}
```

---

## 🎯 Decision Matrix: Which Mode to Use?

### Use BACKWARD when:
- ✅ Consumers upgrade before producers
- ✅ Need to add optional fields frequently
- ✅ Read-heavy workloads

### Use BACKWARD_TRANSITIVE when:
- ✅ Long-lived consumers (might be many versions behind)
- ✅ Need strict backward compatibility across ALL versions
- ✅ Data warehousing scenarios

### Use FORWARD when:
- ✅ Producers upgrade before consumers
- ✅ Need to remove optional fields
- ✅ Write-heavy workloads

### Use FORWARD_TRANSITIVE when:
- ✅ Long-lived producers writing to old consumers
- ✅ Need to ensure old consumers can always read new data
- ✅ Gradual rollout scenarios

### Use FULL when:
- ✅ Independent producer/consumer upgrades
- ✅ Bidirectional compatibility needed
- ✅ Microservices architecture

### Use FULL_TRANSITIVE when:
- ✅ **Maximum safety required** ⭐ **RECOMMENDED FOR MOST CASES**
- ✅ Critical data topics
- ✅ Regulatory compliance needs
- ✅ Long schema version history
- ✅ Complex distributed systems

### Use NONE when:
- ⚠️ **NOT RECOMMENDED**
- 🔧 Emergency situations only
- 🔧 Decommissioned topics
- 🔧 Prototyping/development only

---

## 📝 Recommendations for Your Migration

### If you said "FORWARD_FULL" → You likely want FULL_TRANSITIVE

**Migration Path:**
```
Current: FORWARD_TRANSITIVE
    ↓
Step 1: Validate all schemas are backward compatible
    ↓
Step 2: Run bulk compatibility check
    ↓
Step 3: Fix any incompatibilities
    ↓
Step 4: Switch to FULL_TRANSITIVE ✅
    ↓
Result: Maximum safety for forward AND backward compatibility
```

**Commands:**
```bash
# 1. Check current compatibility
curl http://localhost:8000/api/v1/registries/my-registry/subjects/my-subject/config

# 2. Validate all versions
curl -X POST http://localhost:8000/api/v1/bulk/check-compatibility \
  -H "Content-Type: application/json" \
  -d '{
    "registry_ids": ["my-registry"],
    "target_mode": "FULL_TRANSITIVE"
  }'

# 3. If all compatible, switch
curl -X PUT http://localhost:8000/api/v1/registries/my-registry/compatibility/mode \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "FULL_TRANSITIVE",
    "subject": "my-subject"
  }'
```

---

## ✅ Summary

1. **FORWARD_FULL does not exist** → Use **FULL_TRANSITIVE** instead
2. **7 valid modes**: NONE, BACKWARD, BACKWARD_TRANSITIVE, FORWARD, FORWARD_TRANSITIVE, FULL, FULL_TRANSITIVE
3. **FULL_TRANSITIVE is the strictest** and provides maximum safety
4. **Always validate** before switching to a more restrictive mode
5. **Use test schemas** above to verify compatibility
6. **Never switch from BACKWARD to FORWARD directly** (use FULL as intermediate)

---

**Version:** 1.0.0
**Last Updated:** 2025-11-14
**Author:** Platform Engineering Team
