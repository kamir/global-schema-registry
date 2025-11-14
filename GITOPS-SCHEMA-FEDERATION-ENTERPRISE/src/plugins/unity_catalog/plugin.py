"""
Unity Catalog (Databricks) plugin implementation.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ...core.interfaces import ISchemaRegistry
from ...core.models import (
    CompatibilityMode,
    CompatibilityResult,
    HealthStatus,
    RegistryConfig,
    RegistryType,
    Schema,
    SchemaFormat
)


logger = logging.getLogger(__name__)


class UnityCatalogPlugin(ISchemaRegistry):
    """
    Plugin for Databricks Unity Catalog.

    Supports:
    - Iceberg table schemas
    - Avro schemas (via transformation)
    - Custom compatibility checking based on Iceberg evolution rules
    """

    def __init__(self, config: RegistryConfig):
        """
        Initialize Unity Catalog plugin.

        Args:
            config: Registry configuration
        """
        super().__init__(config)
        self.base_url = config.url.rstrip('/')
        self.catalog = config.metadata.get("catalog", "main")

        # Create session with retry logic
        self.session = requests.Session()

        retry_strategy = Retry(
            total=config.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Configure authentication (Databricks PAT token)
        if config.auth.get("token"):
            self.session.headers.update({
                "Authorization": f"Bearer {config.auth['token']}"
            })

        # Configure headers
        self.session.headers.update({
            "Content-Type": "application/json"
        })

        self.timeout = config.timeout
        logger.info(f"Initialized Unity Catalog plugin: {self.base_url}")

    def get_registry_type(self) -> RegistryType:
        """Return registry type."""
        return RegistryType.UNITY_CATALOG

    def get_supported_formats(self) -> List[SchemaFormat]:
        """Return supported formats."""
        return [
            SchemaFormat.ICEBERG,
            SchemaFormat.AVRO  # Via transformation
        ]

    # ===== Schema CRUD Operations =====

    def register_schema(
        self,
        subject: str,
        schema_content: str,
        schema_format: SchemaFormat,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Schema:
        """
        Register schema by creating/updating Unity Catalog table.

        Note: Unity Catalog doesn't have a "register schema" concept.
        This creates/updates a table definition.

        Args:
            subject: Must be in format "catalog.schema.table"
            schema_content: Iceberg or Avro schema JSON
            schema_format: ICEBERG or AVRO
            metadata: Optional metadata

        Returns:
            Schema object

        Raises:
            ValueError: If subject format is invalid
        """
        # Parse subject: catalog.schema.table
        catalog, schema_name, table_name = self._parse_subject(subject)

        # Convert to Iceberg if needed
        if schema_format == SchemaFormat.AVRO:
            # TODO: Implement Avro -> Iceberg transformation
            raise NotImplementedError("Avro to Iceberg transformation not yet implemented")
        elif schema_format != SchemaFormat.ICEBERG:
            raise ValueError(f"Unsupported format: {schema_format}")

        # Parse Iceberg schema
        schema_json = json.loads(schema_content)
        columns = self._iceberg_to_uc_columns(schema_json)

        # Create/update table
        url = f"{self.base_url}/api/2.1/unity-catalog/tables"

        payload = {
            "name": table_name,
            "catalog_name": catalog,
            "schema_name": schema_name,
            "table_type": "MANAGED",
            "data_source_format": "DELTA",  # Unity Catalog uses Delta, but schema is Iceberg-compatible
            "columns": columns,
            "properties": metadata or {}
        }

        try:
            response = self.session.post(
                url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()

            return Schema(
                id=None,  # Unity Catalog doesn't use numeric IDs
                subject=subject,
                version=1,  # Would need to track versions externally
                schema_format=SchemaFormat.ICEBERG,
                schema_content=schema_content,
                metadata={
                    "table_id": data.get("table_id"),
                    "created_at": data.get("created_at"),
                    "storage_location": data.get("storage_location"),
                    "catalog": catalog,
                    "schema": schema_name,
                    "table": table_name
                },
                registry_type=self.get_registry_type()
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to register schema: {e}")
            raise

    def get_schema_by_id(self, schema_id: int) -> Schema:
        """
        Get schema by ID.

        Note: Unity Catalog doesn't use numeric IDs.
        This method is not applicable.
        """
        raise NotImplementedError(
            "Unity Catalog doesn't support lookup by numeric ID. "
            "Use get_schema_by_subject_version instead."
        )

    def get_schema_by_subject_version(
        self,
        subject: str,
        version: int
    ) -> Schema:
        """
        Get specific version of a table schema.

        Note: Unity Catalog doesn't version schemas explicitly.
        This returns the current schema.
        """
        catalog, schema_name, table_name = self._parse_subject(subject)

        full_name = f"{catalog}.{schema_name}.{table_name}"
        url = f"{self.base_url}/api/2.1/unity-catalog/tables/{full_name}"

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()

            # Convert UC columns to Iceberg schema
            schema_content = self._uc_columns_to_iceberg(data.get("columns", []))

            return Schema(
                id=None,
                subject=subject,
                version=version,  # Use provided version
                schema_format=SchemaFormat.ICEBERG,
                schema_content=json.dumps(schema_content),
                metadata={
                    "table_id": data.get("table_id"),
                    "table_type": data.get("table_type"),
                    "data_source_format": data.get("data_source_format"),
                    "storage_location": data.get("storage_location")
                },
                registry_type=self.get_registry_type()
            )

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise KeyError(f"Table {subject} not found")
            raise

    def get_latest_schema(self, subject: str) -> Schema:
        """Get the latest version of a table schema."""
        return self.get_schema_by_subject_version(subject, 1)

    def list_subjects(
        self,
        prefix: Optional[str] = None
    ) -> List[str]:
        """
        List all tables as subjects.

        Args:
            prefix: Optional prefix filter (e.g., "catalog.schema.")

        Returns:
            List of subject names in format "catalog.schema.table"
        """
        subjects = []

        try:
            # List all tables in the catalog
            # Note: This is simplified - in production, you'd iterate through
            # catalogs -> schemas -> tables

            url = f"{self.base_url}/api/2.1/unity-catalog/tables"
            params = {"catalog_name": self.catalog}

            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()
            tables = data.get("tables", [])

            for table in tables:
                subject = f"{table['catalog_name']}.{table['schema_name']}.{table['name']}"

                if prefix and not subject.startswith(prefix):
                    continue

                subjects.append(subject)

            return subjects

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to list subjects: {e}")
            return []

    def list_versions(self, subject: str) -> List[int]:
        """
        List all versions for a table.

        Note: Unity Catalog doesn't version schemas explicitly.
        Returns [1] if table exists.
        """
        try:
            self.get_latest_schema(subject)
            return [1]
        except KeyError:
            return []

    def delete_schema_version(
        self,
        subject: str,
        version: int
    ) -> bool:
        """
        Delete a table.

        Note: This deletes the entire table, not just a schema version.
        """
        catalog, schema_name, table_name = self._parse_subject(subject)

        full_name = f"{catalog}.{schema_name}.{table_name}"
        url = f"{self.base_url}/api/2.1/unity-catalog/tables/{full_name}"

        try:
            response = self.session.delete(url, timeout=self.timeout)
            response.raise_for_status()

            return True

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise KeyError(f"Table {subject} not found")
            raise

    # ===== Compatibility Operations =====

    def check_compatibility(
        self,
        subject: str,
        schema_content: str,
        schema_format: SchemaFormat,
        version: Optional[int] = None
    ) -> CompatibilityResult:
        """
        Check schema compatibility using Iceberg evolution rules.

        Unity Catalog uses Iceberg's schema evolution rules:
        - Can add optional fields
        - Can delete fields
        - Can rename fields (with aliases)
        - Cannot change field types incompatibly
        """
        try:
            # Get current schema
            current_schema = self.get_latest_schema(subject)

            # Parse new schema
            new_schema_json = json.loads(schema_content)
            current_schema_json = json.loads(current_schema.schema_content)

            # Check Iceberg evolution rules
            is_compatible, messages = self._check_iceberg_evolution(
                current_schema_json,
                new_schema_json
            )

            return CompatibilityResult(
                is_compatible=is_compatible,
                messages=messages,
                compatibility_level=CompatibilityMode.BACKWARD,  # Default for Unity Catalog
                errors=[] if is_compatible else messages
            )

        except KeyError:
            # Table doesn't exist yet - any schema is compatible
            return CompatibilityResult(
                is_compatible=True,
                messages=["New table - no compatibility check needed"],
                compatibility_level=CompatibilityMode.BACKWARD,
                errors=[]
            )
        except Exception as e:
            logger.error(f"Compatibility check failed: {e}")
            return CompatibilityResult(
                is_compatible=False,
                messages=[],
                compatibility_level=CompatibilityMode.NONE,
                errors=[str(e)]
            )

    def get_compatibility_mode(
        self,
        subject: Optional[str] = None
    ) -> CompatibilityMode:
        """
        Get compatibility mode.

        Unity Catalog doesn't have traditional compatibility modes.
        Returns BACKWARD as default (Iceberg allows backward-compatible changes).
        """
        return CompatibilityMode.BACKWARD

    def set_compatibility_mode(
        self,
        mode: CompatibilityMode,
        subject: Optional[str] = None
    ) -> bool:
        """
        Set compatibility mode.

        Unity Catalog doesn't support setting compatibility mode directly.
        This is a no-op.
        """
        logger.warning(
            "Unity Catalog doesn't support setting compatibility mode. "
            "Uses Iceberg evolution rules."
        )
        return True

    def get_all_compatibility_modes(self) -> Dict[str, CompatibilityMode]:
        """
        Get compatibility modes for all tables.

        Returns BACKWARD for all tables (Unity Catalog default).
        """
        modes = {}
        subjects = self.list_subjects()

        for subject in subjects:
            modes[subject] = CompatibilityMode.BACKWARD

        return modes

    # ===== Schema Discovery =====

    def discover_schemas(
        self,
        namespace: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Schema]:
        """Discover all table schemas."""
        schemas = []

        try:
            subjects = self.list_subjects(prefix=namespace)

            for subject in subjects:
                try:
                    schema = self.get_latest_schema(subject)
                    schemas.append(schema)
                except Exception as e:
                    logger.warning(f"Failed to get schema for {subject}: {e}")

            return schemas

        except Exception as e:
            logger.error(f"Schema discovery failed: {e}")
            return []

    # ===== Health & Status =====

    def health_check(self) -> HealthStatus:
        """Check health of Unity Catalog."""
        url = f"{self.base_url}/api/2.1/unity-catalog/catalogs"

        start_time = time.time()
        try:
            response = self.session.get(url, timeout=self.timeout)
            response_time = (time.time() - start_time) * 1000

            response.raise_for_status()

            return HealthStatus(
                healthy=True,
                status_code=response.status_code,
                message="Unity Catalog is healthy",
                response_time_ms=response_time,
                metadata={
                    "url": self.base_url,
                    "catalog": self.catalog,
                    "registry_type": self.get_registry_type().value
                }
            )

        except requests.exceptions.RequestException as e:
            response_time = (time.time() - start_time) * 1000

            return HealthStatus(
                healthy=False,
                status_code=getattr(e.response, 'status_code', 0) if hasattr(e, 'response') else 0,
                message=f"Health check failed: {str(e)}",
                response_time_ms=response_time,
                metadata={
                    "url": self.base_url,
                    "error": str(e)
                }
            )

    # ===== Metadata Operations =====

    def get_metadata(self, subject: str, version: int) -> Dict[str, Any]:
        """Get metadata for a table."""
        schema = self.get_schema_by_subject_version(subject, version)
        return schema.metadata

    def update_metadata(
        self,
        subject: str,
        version: int,
        metadata: Dict[str, Any]
    ) -> bool:
        """Update table properties."""
        catalog, schema_name, table_name = self._parse_subject(subject)

        full_name = f"{catalog}.{schema_name}.{table_name}"
        url = f"{self.base_url}/api/2.1/unity-catalog/tables/{full_name}"

        payload = {
            "properties": metadata
        }

        try:
            response = self.session.patch(
                url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update metadata: {e}")
            return False

    # ===== Helper Methods =====

    def _parse_subject(self, subject: str) -> Tuple[str, str, str]:
        """
        Parse subject into catalog, schema, table.

        Args:
            subject: Subject in format "catalog.schema.table"

        Returns:
            Tuple of (catalog, schema, table)

        Raises:
            ValueError: If subject format is invalid
        """
        parts = subject.split(".")
        if len(parts) != 3:
            raise ValueError(
                f"Subject must be in format catalog.schema.table, got: {subject}"
            )

        return parts[0], parts[1], parts[2]

    def _iceberg_to_uc_columns(self, iceberg_schema: Dict) -> List[Dict]:
        """Convert Iceberg schema to Unity Catalog column format."""
        columns = []

        for field in iceberg_schema.get("fields", []):
            column = {
                "name": field["name"],
                "type_text": self._iceberg_type_to_uc_type(field["type"]),
                "type_name": self._iceberg_type_to_uc_type_name(field["type"]),
                "position": field.get("id", 0),
                "nullable": not field.get("required", False),
                "comment": field.get("doc", "")
            }
            columns.append(column)

        return columns

    def _uc_columns_to_iceberg(self, columns: List[Dict]) -> Dict:
        """Convert Unity Catalog columns to Iceberg schema format."""
        fields = []

        for idx, column in enumerate(columns):
            field = {
                "id": column.get("position", idx + 1),
                "name": column["name"],
                "type": self._uc_type_to_iceberg_type(column["type_name"]),
                "required": not column.get("nullable", True),
                "doc": column.get("comment", "")
            }
            fields.append(field)

        return {
            "type": "struct",
            "fields": fields
        }

    def _iceberg_type_to_uc_type(self, iceberg_type: Any) -> str:
        """Convert Iceberg type to UC type string."""
        if isinstance(iceberg_type, str):
            mapping = {
                "boolean": "BOOLEAN",
                "int": "INT",
                "long": "BIGINT",
                "float": "FLOAT",
                "double": "DOUBLE",
                "string": "STRING",
                "binary": "BINARY",
                "date": "DATE",
                "timestamp": "TIMESTAMP"
            }
            return mapping.get(iceberg_type, "STRING")

        # Handle complex types (struct, list, map)
        if isinstance(iceberg_type, dict):
            type_name = iceberg_type.get("type")
            if type_name == "struct":
                return "STRUCT"
            elif type_name == "list":
                return "ARRAY"
            elif type_name == "map":
                return "MAP"

        return "STRING"

    def _iceberg_type_to_uc_type_name(self, iceberg_type: Any) -> str:
        """Get UC type name enum."""
        type_str = self._iceberg_type_to_uc_type(iceberg_type)

        mapping = {
            "BOOLEAN": "BOOLEAN",
            "INT": "INT",
            "BIGINT": "LONG",
            "FLOAT": "FLOAT",
            "DOUBLE": "DOUBLE",
            "STRING": "STRING",
            "BINARY": "BINARY",
            "DATE": "DATE",
            "TIMESTAMP": "TIMESTAMP",
            "STRUCT": "STRUCT",
            "ARRAY": "ARRAY",
            "MAP": "MAP"
        }

        return mapping.get(type_str, "STRING")

    def _uc_type_to_iceberg_type(self, uc_type: str) -> str:
        """Convert UC type to Iceberg type."""
        mapping = {
            "BOOLEAN": "boolean",
            "INT": "int",
            "LONG": "long",
            "BIGINT": "long",
            "FLOAT": "float",
            "DOUBLE": "double",
            "STRING": "string",
            "BINARY": "binary",
            "DATE": "date",
            "TIMESTAMP": "timestamp"
        }

        return mapping.get(uc_type.upper(), "string")

    def _check_iceberg_evolution(
        self,
        old_schema: Dict,
        new_schema: Dict
    ) -> Tuple[bool, List[str]]:
        """
        Check Iceberg schema evolution compatibility.

        Iceberg allows:
        - Adding optional fields
        - Deleting fields
        - Renaming fields (with aliases)
        - Widening types (int -> long, float -> double)

        Iceberg doesn't allow:
        - Changing field types incompatibly
        - Changing field nullability (nullable -> required)
        """
        messages = []
        is_compatible = True

        old_fields = {f["id"]: f for f in old_schema.get("fields", [])}
        new_fields = {f["id"]: f for f in new_schema.get("fields", [])}

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
                # Check if type promotion is safe
                if not self._is_safe_type_promotion(old_type, new_type):
                    is_compatible = False
                    messages.append(
                        f"Incompatible type change for field '{old_fields[field_id]['name']}': "
                        f"{old_type} → {new_type}"
                    )

        # Check for nullability changes (nullable -> required)
        for field_id in old_fields.keys() & new_fields.keys():
            old_nullable = not old_fields[field_id].get("required", False)
            new_nullable = not new_fields[field_id].get("required", False)

            if old_nullable and not new_nullable:
                is_compatible = False
                messages.append(
                    f"Field '{old_fields[field_id]['name']}' changed from nullable to required"
                )

        if is_compatible and not messages:
            messages.append("Schema evolution is compatible")

        return is_compatible, messages

    def _is_safe_type_promotion(self, old_type: str, new_type: str) -> bool:
        """Check if type promotion is safe."""
        safe_promotions = {
            ("int", "long"),
            ("float", "double"),
            ("date", "timestamp")
        }

        return (old_type, new_type) in safe_promotions
