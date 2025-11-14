"""
Tests for Confluent Schema Registry plugin.
"""

import pytest
from unittest.mock import Mock, patch

from src.core import (
    CompatibilityMode,
    RegistryConfig,
    RegistryType,
    SchemaFormat
)
from src.plugins.confluent import ConfluentSchemaRegistryPlugin


@pytest.fixture
def config():
    """Create test configuration."""
    return RegistryConfig(
        id="test-confluent",
        type=RegistryType.CONFLUENT,
        url="http://localhost:8081",
        auth={},
        timeout=10,
        max_retries=1
    )


@pytest.fixture
def plugin(config):
    """Create plugin instance."""
    return ConfluentSchemaRegistryPlugin(config)


def test_plugin_initialization(plugin):
    """Test plugin initializes correctly."""
    assert plugin.get_registry_type() == RegistryType.CONFLUENT
    assert SchemaFormat.AVRO in plugin.get_supported_formats()


def test_supported_formats(plugin):
    """Test supported formats."""
    formats = plugin.get_supported_formats()
    assert SchemaFormat.AVRO in formats
    assert SchemaFormat.PROTOBUF in formats
    assert SchemaFormat.JSON_SCHEMA in formats


@patch('requests.Session.get')
def test_list_subjects(mock_get, plugin):
    """Test listing subjects."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = ["topic1-value", "topic2-value"]
    mock_get.return_value = mock_response

    subjects = plugin.list_subjects()

    assert "topic1-value" in subjects
    assert "topic2-value" in subjects
    assert len(subjects) == 2


@patch('requests.Session.get')
def test_health_check_success(mock_get, plugin):
    """Test successful health check."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = []
    mock_get.return_value = mock_response

    health = plugin.health_check()

    assert health.healthy is True
    assert health.status_code == 200


@patch('requests.Session.get')
def test_health_check_failure(mock_get, plugin):
    """Test failed health check."""
    mock_get.side_effect = Exception("Connection refused")

    health = plugin.health_check()

    assert health.healthy is False
    assert "Connection refused" in health.message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
