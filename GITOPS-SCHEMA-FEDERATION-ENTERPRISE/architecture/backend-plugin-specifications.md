# Backend Plugin Specifications

**Version:** 3.0
**Date:** 2025-11-14
**Status:** Design & Implementation Guide

---

## Overview

This document provides detailed specifications for implementing plugins for each supported schema registry backend. Each plugin must conform to the `ISchemaRegistry` interface defined in the multi-backend architecture.

---

## Table of Contents

1. [Confluent Schema Registry Plugin](#1-confluent-schema-registry-plugin)
2. [Unity Catalog Plugin](#2-unity-catalog-plugin)
3. [AWS Glue Schema Registry Plugin](#3-aws-glue-schema-registry-plugin)
4. [Azure Purview Plugin](#4-azure-purview-plugin)
5. [Apicurio Registry Plugin](#5-apicurio-registry-plugin)
6. [Karapace Plugin](#6-karapace-plugin)
7. [Pulsar Schema Registry Plugin](#7-pulsar-schema-registry-plugin)
8. [Redpanda Schema Registry Plugin](#8-redpanda-schema-registry-plugin)
9. [Snowflake Horizon Catalog Plugin](#9-snowflake-horizon-catalog-plugin)
10. [GCP Data Catalog Plugin](#10-gcp-data-catalog-plugin)

---

## 1. Confluent Schema Registry Plugin

### 1.1 Overview

**Type:** `RegistryType.CONFLUENT`
**Supported Formats:** AVRO, PROTOBUF, JSON_SCHEMA
**API:** REST API (Confluent Schema Registry API)
**Documentation:** https://docs.confluent.io/platform/current/schema-registry/develop/api.html

### 1.2 Configuration

```yaml
type: confluent
config:
  url: https://schema-registry.example.com
  username: ${CONFLUENT_SR_KEY}  # API Key
  password: ${CONFLUENT_SR_SECRET}  # API Secret
  ssl:
    verify: true
    cert_path: /path/to/cert.pem
  timeout: 30
  max_retries: 3
```

### 1.3 Key Implementation Details

#### Compatibility Mode Mapping

Confluent SR directly supports all compatibility modes:
- NONE
- BACKWARD
- BACKWARD_TRANSITIVE
- FORWARD
- FORWARD_TRANSITIVE
- FORWARD_FULL (via FULL mode check)
- FULL
- FULL_TRANSITIVE

#### API Endpoints

| Operation | Endpoint | Method |
|-----------|----------|--------|
| Register schema | `/subjects/{subject}/versions` | POST |
| Get schema by ID | `/schemas/ids/{id}` | GET |
| Get schema version | `/subjects/{subject}/versions/{version}` | GET |
| List subjects | `/subjects` | GET |
| Get compatibility | `/config/{subject}` or `/config` | GET |
| Set compatibility | `/config/{subject}` or `/config` | PUT |
| Check compatibility | `/compatibility/subjects/{subject}/versions/{version}` | POST |

#### Special Considerations

1. **Schema ID Allocation:** Confluent SR automatically assigns global IDs
2. **Soft Delete:** Deleted schemas can be restored
3. **Mode vs. Compatibility:** SR has both "mode" (IMPORT/READONLY/READWRITE) and "compatibility"
4. **Schema References:** Supports schema references (nested types)

### 1.4 Implementation Snippet

```python
class ConfluentSchemaRegistryPlugin(ISchemaRegistry):

    def check_compatibility(
        self,
        subject: str,
        schema_content: str,
        schema_format: SchemaFormat,
        version: Optional[int] = None
    ) -> CompatibilityResult:
        """Check compatibility with Confluent SR"""

        # Determine version to check against
        version_path = f"/{version}" if version else "/latest"
        url = f"{self.base_url}/compatibility/subjects/{subject}/versions{version_path}"

        payload = {
            "schema": schema_content,
            "schemaType": self._map_format_to_confluent(schema_format)
        }

        response = self.session.post(url, json=payload)
        response.raise_for_status()

        data = response.json()

        return CompatibilityResult(
            is_compatible=data.get("is_compatible", False),
            messages=data.get("messages", []),
            compatibility_level=self.get_compatibility_mode(subject),
            errors=[]
        )

    def get_all_compatibility_modes(self) -> Dict[str, CompatibilityMode]:
        """Get subject-specific compatibility overrides"""
        url = f"{self.base_url}/config"
        response = self.session.get(url)
        response.raise_for_status()

        # Confluent SR doesn't have a single endpoint for this
        # We need to iterate through all subjects
        subjects = self.list_subjects()
        modes = {}

        for subject in subjects:
            try:
                mode = self.get_compatibility_mode(subject)
                modes[subject] = mode
            except:
                pass

        return modes
```

---

## 2. Unity Catalog Plugin

### 2.1 Overview

**Type:** `RegistryType.UNITY_CATALOG`
**Supported Formats:** ICEBERG, AVRO (via transformation), PARQUET
**API:** Databricks Unity Catalog REST API
**Documentation:** https://docs.databricks.com/api/workspace/catalogs

### 2.2 Configuration

```yaml
type: unity_catalog
config:
  url: https://workspace.databricks.com
  token: ${DATABRICKS_TOKEN}
  catalog: main
  workspace_id: ${WORKSPACE_ID}
  enable_schema_import: true
  schema_transformer:
    iceberg_to_avro: true
```

### 2.3 Key Implementation Details

#### Subject Naming Convention

Unity Catalog uses three-part naming: `catalog.schema.table`

Map to schema registry subject:
- **As-is:** `catalog.schema.table` → `catalog.schema.table`
- **Kafka-style:** Add suffix for key/value: `catalog.schema.table-value`

#### Compatibility Mode Handling

Unity Catalog doesn't have traditional "compatibility modes". Instead:
- **Schema Evolution:** Iceberg supports add, drop, rename, update, reorder columns
- **Compatibility Mapping:**
  - Allow column additions → `FORWARD`
  - Restrict deletions → `BACKWARD`
  - Both → `FULL`

Implement compatibility checking by:
1. Fetching table history
2. Comparing schemas manually
3. Applying Iceberg evolution rules

#### API Endpoints

| Operation | Endpoint | Method |
|-----------|----------|--------|
| Get table | `/api/2.1/unity-catalog/tables/{full_name}` | GET |
| List tables | `/api/2.1/unity-catalog/tables` | GET |
| Update table | `/api/2.1/unity-catalog/tables/{full_name}` | PATCH |
| Get table history | N/A - use Iceberg metadata | - |

### 2.4 Implementation Snippet

```python
class UnityCatalogPlugin(ISchemaRegistry):

    def register_schema(
        self,
        subject: str,
        schema_content: str,
        schema_format: SchemaFormat,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Schema:
        """
        Register schema by creating/updating Unity Catalog table
        """

        # Parse subject: catalog.schema.table
        catalog, schema_name, table_name = self._parse_subject(subject)

        if schema_format == SchemaFormat.ICEBERG:
            columns = self._parse_iceberg_columns(schema_content)
        elif schema_format == SchemaFormat.AVRO:
            # Transform Avro → Iceberg
            columns = self._avro_to_iceberg_columns(schema_content)
        else:
            raise ValueError(f"Unsupported format: {schema_format}")

        # Create or update table
        url = f"{self.base_url}/api/2.1/unity-catalog/tables"

        payload = {
            "name": table_name,
            "catalog_name": catalog,
            "schema_name": schema_name,
            "table_type": "MANAGED",
            "data_source_format": "ICEBERG",
            "columns": columns,
            "properties": metadata or {}
        }

        response = self.session.post(url, json=payload)
        response.raise_for_status()

        data = response.json()

        return Schema(
            id=None,  # Unity Catalog doesn't use numeric IDs
            subject=subject,
            version=1,  # Determined from table history
            schema_format=SchemaFormat.ICEBERG,
            schema_content=schema_content,
            metadata={
                "table_id": data["table_id"],
                "created_at": data["created_at"],
                "storage_location": data["storage_location"]
            },
            registry_type=self.get_registry_type()
        )

    def check_compatibility(
        self,
        subject: str,
        schema_content: str,
        schema_format: SchemaFormat,
        version: Optional[int] = None
    ) -> CompatibilityResult:
        """
        Check schema compatibility using Iceberg evolution rules
        """

        # Get current table schema
        current_schema = self.get_latest_schema(subject)

        # Parse new schema
        new_schema_parsed = self._parse_schema(schema_content, schema_format)
        current_schema_parsed = self._parse_schema(
            current_schema.schema_content,
            current_schema.schema_format
        )

        # Apply Iceberg evolution rules
        is_compatible, messages = self._check_iceberg_evolution(
            current_schema_parsed,
            new_schema_parsed
        )

        return CompatibilityResult(
            is_compatible=is_compatible,
            messages=messages,
            compatibility_level=CompatibilityMode.BACKWARD,  # Default
            errors=[] if is_compatible else messages
        )

    def _check_iceberg_evolution(
        self,
        old_schema: Dict,
        new_schema: Dict
    ) -> Tuple[bool, List[str]]:
        """
        Check Iceberg schema evolution compatibility
        """
        messages = []
        is_compatible = True

        old_fields = {f["id"]: f for f in old_schema["fields"]}
        new_fields = {f["id"]: f for f in new_schema["fields"]}

        # Check for removed required fields (breaks backward compat)
        for field_id, field in old_fields.items():
            if field_id not in new_fields and field.get("required"):
                is_compatible = False
                messages.append(
                    f"Required field '{field['name']}' (id={field_id}) was removed"
                )

        # Check for type changes
        for field_id in old_fields.keys() & new_fields.keys():
            old_type = old_fields[field_id]["type"]
            new_type = new_fields[field_id]["type"]

            if old_type != new_type:
                # Only certain type promotions are safe
                if not self._is_safe_type_promotion(old_type, new_type):
                    is_compatible = False
                    messages.append(
                        f"Incompatible type change for field '{old_fields[field_id]['name']}': "
                        f"{old_type} → {new_type}"
                    )

        return is_compatible, messages
```

---

## 3. AWS Glue Schema Registry Plugin

### 3.1 Overview

**Type:** `RegistryType.AWS_GLUE`
**Supported Formats:** AVRO, JSON_SCHEMA, PROTOBUF
**API:** AWS SDK (boto3)
**Documentation:** https://docs.aws.amazon.com/glue/latest/dg/schema-registry.html

### 3.2 Configuration

```yaml
type: aws_glue
config:
  region: us-west-2
  registry_name: my-schema-registry
  aws_access_key_id: ${AWS_ACCESS_KEY_ID}
  aws_secret_access_key: ${AWS_SECRET_ACCESS_KEY}
  session_token: ${AWS_SESSION_TOKEN}  # Optional
  endpoint_url: https://glue.us-west-2.amazonaws.com  # Optional
```

### 3.3 Key Implementation Details

#### Compatibility Modes

AWS Glue supports:
- NONE
- DISABLED
- BACKWARD
- BACKWARD_ALL (≈ BACKWARD_TRANSITIVE)
- FORWARD
- FORWARD_ALL (≈ FORWARD_TRANSITIVE)
- FULL
- FULL_ALL (≈ FULL_TRANSITIVE)

#### Schema Versions

AWS Glue has:
- **Registry:** Container for schemas
- **Schema:** Named schema with versions
- **Schema Version:** Specific version of a schema

#### Implementation Snippet

```python
import boto3
from botocore.exceptions import ClientError

class AWSGlueSchemaRegistryPlugin(ISchemaRegistry):

    def __init__(self, config: Dict[str, Any]):
        self.registry_name = config["registry_name"]
        self.region = config["region"]

        # Initialize boto3 client
        self.client = boto3.client(
            'glue',
            region_name=self.region,
            aws_access_key_id=config.get("aws_access_key_id"),
            aws_secret_access_key=config.get("aws_secret_access_key"),
            aws_session_token=config.get("session_token")
        )

    def register_schema(
        self,
        subject: str,
        schema_content: str,
        schema_format: SchemaFormat,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Schema:
        """Register schema in AWS Glue"""

        try:
            response = self.client.register_schema_version(
                SchemaId={
                    'SchemaName': subject,
                    'RegistryName': self.registry_name
                },
                SchemaDefinition=schema_content
            )

            return Schema(
                id=None,  # Glue uses ARNs
                subject=subject,
                version=response['VersionNumber'],
                schema_format=schema_format,
                schema_content=schema_content,
                metadata={
                    "schema_version_id": response['SchemaVersionId'],
                    "schema_arn": response.get('SchemaArn'),
                    "status": response.get('Status')
                },
                registry_type=self.get_registry_type()
            )

        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityNotFoundException':
                # Schema doesn't exist, create it first
                self._create_schema(subject, schema_format)
                # Retry registration
                return self.register_schema(
                    subject, schema_content, schema_format, metadata
                )
            raise

    def set_compatibility_mode(
        self,
        mode: CompatibilityMode,
        subject: Optional[str] = None
    ) -> bool:
        """Set compatibility checking for a schema"""

        if not subject:
            raise ValueError("AWS Glue requires subject for compatibility mode")

        # Map our modes to AWS Glue modes
        glue_mode = self._map_to_glue_compat_mode(mode)

        try:
            self.client.put_schema_version_metadata(
                SchemaId={
                    'SchemaName': subject,
                    'RegistryName': self.registry_name
                },
                SchemaVersionNumber={'LatestVersion': True},
                MetadataKeyValue={
                    'MetadataKey': 'compatibility',
                    'MetadataValue': glue_mode
                }
            )
            return True

        except ClientError as e:
            print(f"Error setting compatibility: {e}")
            return False

    def _map_to_glue_compat_mode(self, mode: CompatibilityMode) -> str:
        """Map CompatibilityMode to AWS Glue mode"""
        mapping = {
            CompatibilityMode.NONE: "DISABLED",
            CompatibilityMode.BACKWARD: "BACKWARD",
            CompatibilityMode.BACKWARD_TRANSITIVE: "BACKWARD_ALL",
            CompatibilityMode.FORWARD: "FORWARD",
            CompatibilityMode.FORWARD_TRANSITIVE: "FORWARD_ALL",
            CompatibilityMode.FORWARD_FULL: "FULL_ALL",
            CompatibilityMode.FULL: "FULL",
            CompatibilityMode.FULL_TRANSITIVE: "FULL_ALL"
        }
        return mapping.get(mode, "BACKWARD")
```

---

## 4. Azure Purview Plugin

### 4.1 Overview

**Type:** `RegistryType.AZURE_PURVIEW`
**Supported Formats:** Multiple (via Atlas Type System)
**API:** Azure Purview REST API (Apache Atlas compatible)
**Documentation:** https://learn.microsoft.com/en-us/rest/api/purview/

### 4.2 Configuration

```yaml
type: azure_purview
config:
  account_name: company-purview
  tenant_id: ${AZURE_TENANT_ID}
  client_id: ${AZURE_CLIENT_ID}
  client_secret: ${AZURE_CLIENT_SECRET}
  auth_url: https://login.microsoftonline.com
  api_version: "2023-09-01"
```

### 4.3 Key Implementation Details

#### Data Model

Azure Purview is based on Apache Atlas, using:
- **Types:** Schema definitions
- **Entities:** Schema instances
- **Classifications:** Tags/labels
- **Relationships:** Lineage links

#### Schema Storage

Store schemas as Purview **entities** of custom type `SchemaDefinition`:

```json
{
  "typeName": "SchemaDefinition",
  "attributes": {
    "name": "user-events-value",
    "qualifiedName": "kafka://cluster/user-events-value",
    "schemaContent": "{ ... avro schema ... }",
    "schemaFormat": "AVRO",
    "version": 1
  }
}
```

#### Compatibility Handling

Purview doesn't have built-in schema compatibility checking. Implement custom logic:

1. Query entity history via Purview lineage API
2. Fetch previous versions
3. Perform compatibility check locally
4. Store result as classification

---

## 5. Apicurio Registry Plugin

### 5.1 Overview

**Type:** `RegistryType.APICURIO`
**Supported Formats:** AVRO, PROTOBUF, JSON_SCHEMA, OPENAPI, ASYNCAPI, GRAPHQL, WSDL, XSD
**API:** REST API (Confluent-compatible + extensions)
**Documentation:** https://www.apicur.io/registry/docs/

### 5.2 Configuration

```yaml
type: apicurio
config:
  url: https://apicurio.example.com/apis/registry/v2
  auth:
    type: oidc  # or basic, none
    client_id: ${APICURIO_CLIENT_ID}
    client_secret: ${APICURIO_CLIENT_SECRET}
    token_url: https://keycloak.example.com/auth/realms/master/protocol/openid-connect/token
  storage: kafkasql  # or postgresql, inmemory
```

### 5.3 Key Implementation Details

#### API Compatibility

Apicurio provides TWO API styles:
1. **Confluent-compatible API:** Drop-in replacement for Confluent SR
2. **Apicurio native API:** Extended features (OpenAPI, AsyncAPI, etc.)

Use **Apicurio native API** for full feature support.

#### Extended Schema Formats

Apicurio supports formats beyond Kafka:
- **OpenAPI:** REST API specifications
- **AsyncAPI:** Event-driven API specs
- **GraphQL:** GraphQL schemas
- **WSDL:** SOAP service definitions
- **XSD:** XML schemas

#### Artifacts and Versions

Apicurio uses "artifacts" instead of "subjects":
- **Artifact:** Named schema (subject equivalent)
- **Version:** Specific version of artifact
- **Global ID:** Unique ID across all artifacts

#### Implementation Snippet

```python
class ApicurioRegistryPlugin(ISchemaRegistry):

    def __init__(self, config: Dict[str, Any]):
        self.base_url = config["url"]
        self.session = requests.Session()

        # Handle authentication
        if config["auth"]["type"] == "oidc":
            self._setup_oidc_auth(config["auth"])

    def register_schema(
        self,
        subject: str,
        schema_content: str,
        schema_format: SchemaFormat,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Schema:
        """Register artifact in Apicurio"""

        # Apicurio groups artifacts; default to "default" group
        group = metadata.get("group", "default") if metadata else "default"

        url = f"{self.base_url}/groups/{group}/artifacts"

        headers = {
            "X-Registry-ArtifactId": subject,
            "X-Registry-ArtifactType": self._map_format_to_apicurio(schema_format),
            "Content-Type": "application/json"
        }

        response = self.session.post(
            url,
            data=schema_content,
            headers=headers
        )
        response.raise_for_status()

        data = response.json()

        return Schema(
            id=data.get("globalId"),
            subject=subject,
            version=data.get("version"),
            schema_format=schema_format,
            schema_content=schema_content,
            metadata={
                "group": group,
                "artifact_id": data.get("id"),
                "content_id": data.get("contentId")
            },
            registry_type=self.get_registry_type()
        )

    def _map_format_to_apicurio(self, format: SchemaFormat) -> str:
        """Map SchemaFormat to Apicurio artifact type"""
        mapping = {
            SchemaFormat.AVRO: "AVRO",
            SchemaFormat.PROTOBUF: "PROTOBUF",
            SchemaFormat.JSON_SCHEMA: "JSON",
            SchemaFormat.OPENAPI: "OPENAPI",
            SchemaFormat.ASYNCAPI: "ASYNCAPI"
        }
        return mapping.get(format, "AVRO")

    def get_all_compatibility_modes(self) -> Dict[str, CompatibilityMode]:
        """Get compatibility rules for all artifacts"""
        url = f"{self.base_url}/admin/rules"
        response = self.session.get(url)
        response.raise_for_status()

        # Apicurio returns list of rule types
        # Need to query each artifact's rules
        # ... implementation continues ...
```

---

## 6. Karapace Plugin

### 6.1 Overview

**Type:** `RegistryType.KARAPACE`
**Supported Formats:** AVRO, PROTOBUF, JSON_SCHEMA
**API:** REST API (Confluent Schema Registry compatible)
**Documentation:** https://karapace.io/

### 6.2 Configuration

```yaml
type: karapace
config:
  url: https://karapace.example.com
  username: ${KARAPACE_USER}
  password: ${KARAPACE_PASSWORD}
```

### 6.3 Key Implementation Details

Karapace is a **100% Confluent Schema Registry compatible** replacement.

**Implementation Strategy:**
- Inherit from `ConfluentSchemaRegistryPlugin`
- Override only authentication if needed
- All API calls identical to Confluent SR

```python
class KarapacePlugin(ConfluentSchemaRegistryPlugin):
    """
    Karapace plugin - inherits Confluent implementation
    """

    def get_registry_type(self) -> RegistryType:
        return RegistryType.KARAPACE

    # All other methods inherited from ConfluentSchemaRegistryPlugin
```

---

## 7. Pulsar Schema Registry Plugin

### 7.1 Overview

**Type:** `RegistryType.PULSAR`
**Supported Formats:** AVRO, PROTOBUF, JSON
**API:** Pulsar Admin API
**Documentation:** https://pulsar.apache.org/docs/schema-understand/

### 7.2 Configuration

```yaml
type: pulsar
config:
  web_service_url: http://pulsar-broker:8080
  auth:
    type: token
    token: ${PULSAR_TOKEN}
```

### 7.3 Key Implementation Details

#### Differences from Kafka SR

Pulsar Schema Registry is **tightly coupled** to topics:
- Schemas are per-topic, not standalone
- No global schema IDs
- Schema stored in topic metadata

#### Subject → Topic Mapping

Map subject names to Pulsar topics:
- **Subject:** `user-events-value`
- **Topic:** `persistent://public/default/user-events`

#### Implementation Snippet

```python
class PulsarSchemaRegistryPlugin(ISchemaRegistry):

    def register_schema(
        self,
        subject: str,
        schema_content: str,
        schema_format: SchemaFormat,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Schema:
        """
        Register schema by creating/updating Pulsar topic
        """

        # Map subject to Pulsar topic
        topic = self._subject_to_topic(subject)

        # Pulsar schemas are attached to topics via topic policies
        # Not a separate registration step

        # To "register" a schema, we need to publish a message
        # with the schema definition
        # OR update topic's schema via Admin API

        url = f"{self.base_url}/admin/v2/schemas/{topic}/schema"

        payload = {
            "type": self._map_format_to_pulsar(schema_format),
            "schema": schema_content,
            "properties": metadata or {}
        }

        response = self.session.post(url, json=payload)
        response.raise_for_status()

        # Pulsar doesn't return schema ID, use hash
        schema_hash = hashlib.sha256(schema_content.encode()).hexdigest()

        return Schema(
            id=None,
            subject=subject,
            version=1,  # Pulsar doesn't version schemas explicitly
            schema_format=schema_format,
            schema_content=schema_content,
            metadata={"topic": topic, "schema_hash": schema_hash},
            registry_type=self.get_registry_type()
        )
```

---

## 8. Redpanda Schema Registry Plugin

### 8.1 Overview

**Type:** `RegistryType.REDPANDA`
**Supported Formats:** AVRO, PROTOBUF, JSON_SCHEMA
**API:** REST API (Confluent Schema Registry compatible)
**Documentation:** https://docs.redpanda.com/docs/manage/schema-registry/

### 8.2 Configuration

```yaml
type: redpanda
config:
  url: https://redpanda.example.com:8081
  username: ${REDPANDA_USER}
  password: ${REDPANDA_PASSWORD}
```

### 8.3 Key Implementation Details

Redpanda Schema Registry is **Confluent-compatible** with some differences:

**Implementation Strategy:**
- Inherit from `ConfluentSchemaRegistryPlugin`
- Redpanda-specific features (if any) override parent methods

```python
class RedpandaSchemaRegistryPlugin(ConfluentSchemaRegistryPlugin):
    """
    Redpanda plugin - mostly Confluent-compatible
    """

    def get_registry_type(self) -> RegistryType:
        return RegistryType.REDPANDA

    # Most methods inherited, override as needed
```

---

## 9. Snowflake Horizon Catalog Plugin

### 9.1 Overview

**Type:** `RegistryType.SNOWFLAKE`
**Supported Formats:** SQL_DDL, AVRO (via transformation)
**API:** Snowflake SQL API
**Documentation:** https://docs.snowflake.com/

### 9.2 Configuration

```yaml
type: snowflake
config:
  account: company.us-west-2
  user: ${SNOWFLAKE_USER}
  password: ${SNOWFLAKE_PASSWORD}
  warehouse: COMPUTE_WH
  database: SCHEMA_REGISTRY
  schema: PUBLIC
  role: SYSADMIN
```

### 9.3 Key Implementation Details

#### Schema Storage

Store schemas as Snowflake tables in a dedicated database:

```sql
CREATE TABLE SCHEMA_REGISTRY.PUBLIC.SCHEMAS (
  SCHEMA_ID NUMBER AUTOINCREMENT,
  SUBJECT VARCHAR,
  VERSION NUMBER,
  SCHEMA_FORMAT VARCHAR,
  SCHEMA_CONTENT VARIANT,
  CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  METADATA VARIANT
);
```

#### Compatibility Checking

Implement custom logic:
1. Query previous versions from `SCHEMAS` table
2. Parse DDL differences
3. Apply compatibility rules

---

## 10. GCP Data Catalog Plugin

### 10.1 Overview

**Type:** `RegistryType.GCP_DATA_CATALOG`
**Supported Formats:** Multiple (via custom entries)
**API:** Google Cloud Data Catalog API
**Documentation:** https://cloud.google.com/data-catalog/docs

### 10.2 Configuration

```yaml
type: gcp_data_catalog
config:
  project_id: my-project
  location: us-central1
  credentials_path: /path/to/service-account.json
  entry_group: schema-registry
```

### 10.3 Key Implementation Details

#### Schema Storage as Custom Entries

```python
from google.cloud import datacatalog_v1

class GCPDataCatalogPlugin(ISchemaRegistry):

    def register_schema(
        self,
        subject: str,
        schema_content: str,
        schema_format: SchemaFormat,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Schema:
        """Register schema as Data Catalog entry"""

        # Create entry
        entry = datacatalog_v1.Entry()
        entry.display_name = subject
        entry.type_ = datacatalog_v1.EntryType.FILESET
        entry.user_specified_type = f"schema-{schema_format.value}"
        entry.schema.columns.extend(
            self._parse_columns(schema_content, schema_format)
        )

        # Tag with metadata
        # ... implementation continues ...
```

---

## Plugin Development Guidelines

### 1. Error Handling

All plugins must handle:
- **Connection errors:** Retry with exponential backoff
- **Authentication errors:** Clear error messages
- **Rate limiting:** Implement backoff strategies
- **Not found errors:** Distinguish between missing schema vs. connection issues

### 2. Logging

Use structured logging:

```python
import logging

logger = logging.getLogger(f"registry.plugin.{self.get_registry_type().value}")

logger.info(
    "Registering schema",
    extra={
        "subject": subject,
        "format": schema_format.value,
        "registry_type": self.get_registry_type().value
    }
)
```

### 3. Testing

Each plugin must have:
- Unit tests (mocked backend)
- Integration tests (real backend)
- Compatibility test suite

### 4. Documentation

Each plugin must provide:
- Configuration examples
- API endpoint mappings
- Compatibility mode mappings
- Known limitations

---

## Summary Table

| Registry | Compat API | Formats | Auth | Complexity |
|----------|-----------|---------|------|------------|
| Confluent SR | ✅ Native | Avro, Proto, JSON | Basic/Token | Low |
| Unity Catalog | ❌ Custom | Iceberg, Avro* | Token/OAuth | Medium |
| AWS Glue | ✅ Native | Avro, Proto, JSON | IAM | Medium |
| Azure Purview | ❌ Custom | Multiple | OAuth | High |
| Apicurio | ✅ Extended | Avro, Proto, JSON, OpenAPI+ | OIDC/Basic | Medium |
| Karapace | ✅ Native | Avro, Proto, JSON | Basic | Low |
| Pulsar SR | ❌ Custom | Avro, Proto, JSON | Token | Medium |
| Redpanda SR | ✅ Native | Avro, Proto, JSON | Basic | Low |
| Snowflake | ❌ Custom | SQL DDL, Avro* | User/Password | Medium |
| GCP Data Catalog | ❌ Custom | Multiple | Service Account | High |

**Legend:**
- ✅ Native: Has built-in compatibility checking API
- ❌ Custom: Requires custom compatibility logic
- *: Via transformation

---

**Version:** 3.0
**Last Updated:** 2025-11-14
**Maintained By:** Platform Engineering Team - Enterprise Division
