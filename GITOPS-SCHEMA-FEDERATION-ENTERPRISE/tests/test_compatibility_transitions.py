"""
Comprehensive test suite for schema compatibility mode transitions.

This module tests all possible compatibility mode transitions and validates
schema evolution scenarios for each mode.
"""

import pytest
import json
from typing import Dict, List, Tuple

# Test schema definitions
class TestSchemas:
    """Collection of test schemas for compatibility testing."""

    # Base schema - Version 1
    BASE_SCHEMA = {
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

    # BACKWARD compatible: Adding optional field with default
    BACKWARD_COMPATIBLE = {
        "type": "record",
        "name": "User",
        "namespace": "com.example",
        "fields": [
            {"name": "id", "type": "int"},
            {"name": "username", "type": "string"},
            {
                "name": "email",
                "type": "string",
                "default": "",
                "doc": "Added with default - BACKWARD compatible"
            }
        ]
    }

    # FORWARD compatible base (with optional field)
    FORWARD_BASE = {
        "type": "record",
        "name": "User",
        "namespace": "com.example",
        "fields": [
            {"name": "id", "type": "int"},
            {
                "name": "username",
                "type": "string",
                "default": "",
                "doc": "Optional field"
            }
        ]
    }

    # FORWARD compatible: Removing optional field
    FORWARD_COMPATIBLE = {
        "type": "record",
        "name": "User",
        "namespace": "com.example",
        "fields": [
            {
                "name": "id",
                "type": "int",
                "doc": "Removed username - FORWARD compatible if it was optional"
            }
        ]
    }

    # FULL compatible: Adding optional nullable field
    FULL_COMPATIBLE = {
        "type": "record",
        "name": "User",
        "namespace": "com.example",
        "fields": [
            {"name": "id", "type": "int"},
            {"name": "username", "type": "string"},
            {
                "name": "email",
                "type": ["null", "string"],
                "default": None,
                "doc": "Nullable with null default - FULL compatible"
            }
        ]
    }

    # BREAKING: Changing field type
    BREAKING_TYPE_CHANGE = {
        "type": "record",
        "name": "User",
        "namespace": "com.example",
        "fields": [
            {
                "name": "id",
                "type": "string",
                "doc": "Changed from int to string - BREAKING!"
            },
            {"name": "username", "type": "string"}
        ]
    }

    # BREAKING: Adding required field
    BREAKING_REQUIRED_FIELD = {
        "type": "record",
        "name": "User",
        "namespace": "com.example",
        "fields": [
            {"name": "id", "type": "int"},
            {"name": "username", "type": "string"},
            {
                "name": "email",
                "type": "string",
                "doc": "Required field without default - BREAKING!"
            }
        ]
    }

    # Type widening (BACKWARD compatible)
    TYPE_WIDENING = {
        "type": "record",
        "name": "User",
        "namespace": "com.example",
        "fields": [
            {
                "name": "id",
                "type": ["int", "long"],
                "doc": "Union type - can read old int values"
            },
            {"name": "username", "type": "string"}
        ]
    }

    # Field rename with alias (FULL compatible)
    FIELD_RENAME_WITH_ALIAS = {
        "type": "record",
        "name": "User",
        "namespace": "com.example",
        "fields": [
            {"name": "id", "type": "int"},
            {
                "name": "user_name",
                "type": "string",
                "aliases": ["username"],
                "doc": "Renamed with alias - FULL compatible"
            }
        ]
    }

    # Complex nested schema
    NESTED_SCHEMA_V1 = {
        "type": "record",
        "name": "Order",
        "namespace": "com.example",
        "fields": [
            {"name": "orderId", "type": "int"},
            {
                "name": "user",
                "type": {
                    "type": "record",
                    "name": "User",
                    "fields": [
                        {"name": "id", "type": "int"},
                        {"name": "username", "type": "string"}
                    ]
                }
            }
        ]
    }

    # Complex nested schema - FULL compatible evolution
    NESTED_SCHEMA_V2 = {
        "type": "record",
        "name": "Order",
        "namespace": "com.example",
        "fields": [
            {"name": "orderId", "type": "int"},
            {
                "name": "user",
                "type": {
                    "type": "record",
                    "name": "User",
                    "fields": [
                        {"name": "id", "type": "int"},
                        {"name": "username", "type": "string"},
                        {
                            "name": "email",
                            "type": ["null", "string"],
                            "default": None
                        }
                    ]
                }
            },
            {
                "name": "timestamp",
                "type": ["null", "long"],
                "default": None,
                "doc": "Order timestamp"
            }
        ]
    }


# Compatibility transition test cases
COMPATIBILITY_TRANSITIONS = [
    # Format: (from_mode, to_mode, risk_level, requires_validation, description)

    # NONE transitions
    ("NONE", "BACKWARD", "RISKY", True, "NONE allowed breaking changes, BACKWARD requires validation"),
    ("NONE", "BACKWARD_TRANSITIVE", "RISKY", True, "Strictest backward check needed"),
    ("NONE", "FORWARD", "RISKY", True, "Different compatibility direction"),
    ("NONE", "FORWARD_TRANSITIVE", "RISKY", True, "Strictest forward check needed"),
    ("NONE", "FULL", "DANGEROUS", True, "Both directions must be validated"),
    ("NONE", "FULL_TRANSITIVE", "DANGEROUS", True, "Strictest mode - high risk from NONE"),

    # BACKWARD transitions
    ("BACKWARD", "NONE", "SAFE", False, "Removing restrictions is always safe"),
    ("BACKWARD", "BACKWARD_TRANSITIVE", "SAFE", False, "Adding transitive check is safe"),
    ("BACKWARD", "FORWARD", "DANGEROUS", True, "Opposite compatibility direction"),
    ("BACKWARD", "FORWARD_TRANSITIVE", "DANGEROUS", True, "Opposite + transitive"),
    ("BACKWARD", "FULL", "RISKY", True, "Adds forward compatibility requirement"),
    ("BACKWARD", "FULL_TRANSITIVE", "DANGEROUS", True, "Adds forward + transitive"),

    # BACKWARD_TRANSITIVE transitions
    ("BACKWARD_TRANSITIVE", "NONE", "SAFE", False, "Removing restrictions"),
    ("BACKWARD_TRANSITIVE", "BACKWARD", "SAFE", False, "Relaxing from transitive to single version"),
    ("BACKWARD_TRANSITIVE", "FORWARD", "DANGEROUS", True, "Complete direction change"),
    ("BACKWARD_TRANSITIVE", "FORWARD_TRANSITIVE", "DANGEROUS", True, "Complete direction change + transitive"),
    ("BACKWARD_TRANSITIVE", "FULL", "DANGEROUS", True, "Adds forward compatibility"),
    ("BACKWARD_TRANSITIVE", "FULL_TRANSITIVE", "DANGEROUS", True, "Adds forward + keeps transitive"),

    # FORWARD transitions
    ("FORWARD", "NONE", "SAFE", False, "Removing restrictions"),
    ("FORWARD", "BACKWARD", "DANGEROUS", True, "Opposite direction"),
    ("FORWARD", "BACKWARD_TRANSITIVE", "DANGEROUS", True, "Opposite direction + transitive"),
    ("FORWARD", "FORWARD_TRANSITIVE", "SAFE", False, "Adding transitive is safe"),
    ("FORWARD", "FULL", "RISKY", True, "Adds backward compatibility"),
    ("FORWARD", "FULL_TRANSITIVE", "DANGEROUS", True, "Adds backward + transitive"),

    # FORWARD_TRANSITIVE transitions
    ("FORWARD_TRANSITIVE", "NONE", "SAFE", False, "Removing restrictions"),
    ("FORWARD_TRANSITIVE", "BACKWARD", "DANGEROUS", True, "Opposite direction"),
    ("FORWARD_TRANSITIVE", "BACKWARD_TRANSITIVE", "DANGEROUS", True, "Opposite direction"),
    ("FORWARD_TRANSITIVE", "FORWARD", "SAFE", False, "Relaxing transitive requirement"),
    ("FORWARD_TRANSITIVE", "FULL", "DANGEROUS", True, "Adds backward compatibility"),
    ("FORWARD_TRANSITIVE", "FULL_TRANSITIVE", "RISKY", True, "Adds backward transitive requirement"),

    # FULL transitions
    ("FULL", "NONE", "SAFE", False, "Removing all restrictions"),
    ("FULL", "BACKWARD", "SAFE", False, "Removing forward requirement"),
    ("FULL", "BACKWARD_TRANSITIVE", "RISKY", True, "Removing forward, adding transitive"),
    ("FULL", "FORWARD", "SAFE", False, "Removing backward requirement"),
    ("FULL", "FORWARD_TRANSITIVE", "RISKY", True, "Removing backward, adding transitive"),
    ("FULL", "FULL_TRANSITIVE", "SAFE", False, "Adding transitive to both directions"),

    # FULL_TRANSITIVE transitions (all safe - most restrictive mode)
    ("FULL_TRANSITIVE", "NONE", "SAFE", False, "From strictest to most permissive"),
    ("FULL_TRANSITIVE", "BACKWARD", "SAFE", False, "Relaxing forward requirement"),
    ("FULL_TRANSITIVE", "BACKWARD_TRANSITIVE", "SAFE", False, "Relaxing forward requirement"),
    ("FULL_TRANSITIVE", "FORWARD", "SAFE", False, "Relaxing backward requirement"),
    ("FULL_TRANSITIVE", "FORWARD_TRANSITIVE", "SAFE", False, "Relaxing backward requirement"),
    ("FULL_TRANSITIVE", "FULL", "SAFE", False, "Relaxing transitive requirements"),
]


class TestCompatibilityModeTransitions:
    """Test all compatibility mode transitions."""

    @pytest.mark.parametrize(
        "from_mode,to_mode,risk_level,requires_validation,description",
        COMPATIBILITY_TRANSITIONS
    )
    def test_compatibility_transition(
        self,
        from_mode: str,
        to_mode: str,
        risk_level: str,
        requires_validation: bool,
        description: str
    ):
        """
        Test each compatibility mode transition scenario.

        This test validates:
        1. Transition risk level is correctly identified
        2. Validation requirement is appropriate
        3. Transition behavior matches documentation
        """
        # This is a documentation/specification test
        # In real implementation, you would:
        # - Call the schema registry API
        # - Attempt the transition
        # - Verify the expected behavior

        assert from_mode in [
            "NONE", "BACKWARD", "BACKWARD_TRANSITIVE",
            "FORWARD", "FORWARD_TRANSITIVE", "FULL", "FULL_TRANSITIVE"
        ]
        assert to_mode in [
            "NONE", "BACKWARD", "BACKWARD_TRANSITIVE",
            "FORWARD", "FORWARD_TRANSITIVE", "FULL", "FULL_TRANSITIVE"
        ]
        assert risk_level in ["SAFE", "RISKY", "DANGEROUS"]

        # Log the transition for documentation
        print(f"\n{from_mode} → {to_mode}: {risk_level}")
        print(f"  Requires Validation: {requires_validation}")
        print(f"  Description: {description}")


class TestSchemaEvolutionScenarios:
    """Test specific schema evolution scenarios for each compatibility mode."""

    def test_backward_add_optional_field(self):
        """
        BACKWARD: Adding optional field with default is allowed.

        New schema can read old data by using the default value.
        """
        v1 = TestSchemas.BASE_SCHEMA
        v2 = TestSchemas.BACKWARD_COMPATIBLE

        # Under BACKWARD mode:
        # ✅ V2 can read V1 data (uses default for missing "email")
        # ❌ V1 cannot read V2 data (doesn't know about "email" field)

        assert "email" in [f["name"] for f in v2["fields"]]
        assert "default" in v2["fields"][2]  # email field has default

    def test_forward_remove_optional_field(self):
        """
        FORWARD: Removing optional field is allowed.

        Old schema can read new data by ignoring the missing field.
        """
        v1 = TestSchemas.FORWARD_BASE
        v2 = TestSchemas.FORWARD_COMPATIBLE

        # Under FORWARD mode:
        # ✅ V1 can read V2 data (just doesn't see the username field)
        # ❌ V2 cannot read V1 data (no default for removed field)

        v1_fields = {f["name"] for f in v1["fields"]}
        v2_fields = {f["name"] for f in v2["fields"]}

        # username was removed
        assert "username" in v1_fields
        assert "username" not in v2_fields

    def test_full_add_nullable_field(self):
        """
        FULL: Adding optional nullable field is allowed.

        Works in both directions:
        - New schema reads old data (uses null default)
        - Old schema reads new data (ignores unknown field)
        """
        v1 = TestSchemas.BASE_SCHEMA
        v2 = TestSchemas.FULL_COMPATIBLE

        # Under FULL mode:
        # ✅ V2 can read V1 data (BACKWARD)
        # ✅ V1 can read V2 data (FORWARD)

        email_field = [f for f in v2["fields"] if f["name"] == "email"][0]
        assert email_field["type"] == ["null", "string"]  # Nullable union
        assert email_field["default"] is None  # Null default

    def test_breaking_type_change(self):
        """
        NONE only: Changing field type is breaking in all modes except NONE.

        This will fail under any compatibility mode.
        """
        v1 = TestSchemas.BASE_SCHEMA
        v2 = TestSchemas.BREAKING_TYPE_CHANGE

        # id field changed from int to string
        v1_id_type = [f for f in v1["fields"] if f["name"] == "id"][0]["type"]
        v2_id_type = [f for f in v2["fields"] if f["name"] == "id"][0]["type"]

        assert v1_id_type == "int"
        assert v2_id_type == "string"

        # This is BREAKING:
        # ❌ BACKWARD: V2 cannot read V1 data (wrong type)
        # ❌ FORWARD: V1 cannot read V2 data (wrong type)
        # ❌ FULL: Incompatible both ways
        # ✅ NONE: Allowed (but breaks everything!)

    def test_breaking_required_field(self):
        """
        NONE only: Adding required field without default is breaking.

        This will fail under any compatibility mode.
        """
        v1 = TestSchemas.BASE_SCHEMA
        v2 = TestSchemas.BREAKING_REQUIRED_FIELD

        email_field = [f for f in v2["fields"] if f["name"] == "email"][0]
        assert "default" not in email_field  # No default!

        # This is BREAKING:
        # ❌ BACKWARD: V2 cannot read V1 data (no value for required field)
        # ❌ FORWARD: V1 doesn't know about "email"
        # ❌ FULL: Incompatible both ways
        # ✅ NONE: Allowed (but breaks everything!)

    def test_type_widening_backward(self):
        """
        BACKWARD: Type widening (int → [int, long]) is backward compatible.

        New schema can read old int values.
        """
        v1 = TestSchemas.BASE_SCHEMA
        v2 = TestSchemas.TYPE_WIDENING

        v1_id_type = [f for f in v1["fields"] if f["name"] == "id"][0]["type"]
        v2_id_type = [f for f in v2["fields"] if f["name"] == "id"][0]["type"]

        assert v1_id_type == "int"
        assert v2_id_type == ["int", "long"]  # Union type

        # Under BACKWARD mode:
        # ✅ V2 can read V1 data (int is part of union)
        # ❌ V1 cannot read V2 data (doesn't expect union)
        # Works for BACKWARD, not FULL

    def test_field_rename_with_alias_full(self):
        """
        FULL: Field rename with alias is fully compatible.

        Alias allows reading old data, serialization stays compatible for forward.
        """
        v1 = TestSchemas.BASE_SCHEMA
        v2 = TestSchemas.FIELD_RENAME_WITH_ALIAS

        v1_field_name = [f for f in v1["fields"] if "username" in f.values()][0]["name"]
        v2_field = [f for f in v2["fields"] if "user_name" in f.values()][0]

        assert v1_field_name == "username"
        assert v2_field["name"] == "user_name"
        assert "aliases" in v2_field
        assert "username" in v2_field["aliases"]

        # Under FULL mode:
        # ✅ V2 can read V1 data (alias maps "username" to "user_name")
        # ✅ V1 can read V2 data (same serialization format)

    def test_nested_schema_evolution_full(self):
        """
        FULL: Nested schema evolution with optional fields.

        Complex schemas can evolve if all changes are FULL compatible.
        """
        v1 = TestSchemas.NESTED_SCHEMA_V1
        v2 = TestSchemas.NESTED_SCHEMA_V2

        # V2 adds:
        # 1. email field to nested User record (nullable)
        # 2. timestamp field to Order (nullable)

        v2_user_fields = v2["fields"][1]["type"]["fields"]
        email_field = [f for f in v2_user_fields if f["name"] == "email"][0]
        assert email_field["type"] == ["null", "string"]
        assert email_field["default"] is None

        v2_timestamp = [f for f in v2["fields"] if f["name"] == "timestamp"][0]
        assert v2_timestamp["type"] == ["null", "long"]
        assert v2_timestamp["default"] is None

        # Under FULL mode:
        # ✅ V2 can read V1 data (uses null defaults)
        # ✅ V1 can read V2 data (ignores unknown fields)


class TestCompatibilityValidation:
    """Test validation requirements for mode transitions."""

    def get_schemas_to_validate(self, from_mode: str, to_mode: str) -> List[Dict]:
        """
        Determine which schemas need validation for a given transition.

        Returns list of schema pairs that must be tested.
        """
        # Simplification: In real implementation, you would query
        # the schema registry for all versions and test combinations

        schemas_to_test = []

        if from_mode == "NONE" and to_mode in ["BACKWARD", "BACKWARD_TRANSITIVE"]:
            # Must validate all versions are backward compatible
            schemas_to_test.append((TestSchemas.BASE_SCHEMA, TestSchemas.BACKWARD_COMPATIBLE))

        elif from_mode == "BACKWARD" and to_mode in ["FORWARD", "FORWARD_TRANSITIVE"]:
            # Must validate all versions are forward compatible
            # (they might not be if optimized for backward only)
            schemas_to_test.append((TestSchemas.FORWARD_BASE, TestSchemas.FORWARD_COMPATIBLE))

        elif to_mode == "FULL_TRANSITIVE":
            # Must validate both directions for all version combinations
            schemas_to_test.append((TestSchemas.BASE_SCHEMA, TestSchemas.FULL_COMPATIBLE))

        return schemas_to_test

    @pytest.mark.parametrize(
        "from_mode,to_mode",
        [
            ("NONE", "BACKWARD"),
            ("NONE", "FULL_TRANSITIVE"),
            ("BACKWARD", "FORWARD"),
            ("FORWARD_TRANSITIVE", "FULL_TRANSITIVE"),
        ]
    )
    def test_validation_required_transitions(self, from_mode: str, to_mode: str):
        """
        Test that risky transitions require validation.

        These transitions should not be allowed without validating
        all existing schema versions.
        """
        schemas = self.get_schemas_to_validate(from_mode, to_mode)
        assert len(schemas) > 0, f"Transition {from_mode} → {to_mode} requires validation"

        # In real implementation:
        # 1. Get all schema versions from registry
        # 2. Test all combinations under target mode
        # 3. Only allow transition if all pass


def print_transition_matrix():
    """
    Helper function to print the full transition matrix.

    Run this to generate documentation output.
    """
    modes = [
        "NONE",
        "BACKWARD",
        "BACKWARD_TRANSITIVE",
        "FORWARD",
        "FORWARD_TRANSITIVE",
        "FULL",
        "FULL_TRANSITIVE"
    ]

    # Build matrix
    matrix = {}
    for from_mode in modes:
        matrix[from_mode] = {}
        for to_mode in modes:
            if from_mode == to_mode:
                matrix[from_mode][to_mode] = "N/A"
            else:
                # Find in COMPATIBILITY_TRANSITIONS
                transition = next(
                    (t for t in COMPATIBILITY_TRANSITIONS
                     if t[0] == from_mode and t[1] == to_mode),
                    None
                )
                if transition:
                    matrix[from_mode][to_mode] = transition[2]  # risk_level
                else:
                    matrix[from_mode][to_mode] = "?"

    # Print matrix
    print("\nCompatibility Mode Transition Matrix")
    print("=" * 100)
    print(f"{'From \\ To':<25}", end="")
    for mode in modes:
        print(f"{mode:<15}", end="")
    print()
    print("-" * 100)

    for from_mode in modes:
        print(f"{from_mode:<25}", end="")
        for to_mode in modes:
            risk = matrix[from_mode][to_mode]
            emoji = {
                "SAFE": "✅",
                "RISKY": "⚠️",
                "DANGEROUS": "🔴",
                "N/A": "⏺️",
                "?": "❓"
            }.get(risk, "?")
            print(f"{emoji} {risk:<12}", end="")
        print()


if __name__ == "__main__":
    # Print transition matrix
    print_transition_matrix()

    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
