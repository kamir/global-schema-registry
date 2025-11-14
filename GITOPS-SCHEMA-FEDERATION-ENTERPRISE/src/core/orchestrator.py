"""
Multi-backend orchestrator for coordinating operations across registries.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

from .interfaces import ISchemaRegistry
from .models import (
    BulkCheckResult,
    CompatibilityMode,
    CompatibilityResult,
    HealthStatus,
    RegistryConfig,
    Schema
)
from .plugin_registry import PluginRegistry


logger = logging.getLogger(__name__)


class MultiBackendOrchestrator:
    """
    Orchestrates operations across multiple schema registry backends.
    """

    def __init__(self, plugin_registry: PluginRegistry):
        """
        Initialize orchestrator.

        Args:
            plugin_registry: PluginRegistry instance
        """
        self.plugin_registry = plugin_registry
        self.active_registries: Dict[str, ISchemaRegistry] = {}
        self.executor = ThreadPoolExecutor(max_workers=10)

        logger.info("Multi-backend orchestrator initialized")

    def add_registry(
        self,
        config: RegistryConfig
    ):
        """
        Add a registry backend.

        Args:
            config: Registry configuration
        """
        instance = self.plugin_registry.create_instance(
            config=config,
            instance_id=config.id
        )
        self.active_registries[config.id] = instance

        logger.info(f"Added registry: {config.id} ({config.type.value})")

    def get_registry(self, instance_id: str) -> Optional[ISchemaRegistry]:
        """
        Get a registry instance by ID.

        Args:
            instance_id: Registry instance ID

        Returns:
            Registry instance or None
        """
        return self.active_registries.get(instance_id)

    def list_registries(self) -> List[Dict[str, Any]]:
        """
        List all active registries.

        Returns:
            List of registry information dicts
        """
        registries = []

        for instance_id, registry in self.active_registries.items():
            registries.append({
                "id": instance_id,
                "type": registry.get_registry_type().value,
                "supported_formats": [f.value for f in registry.get_supported_formats()]
            })

        return registries

    def remove_registry(self, instance_id: str):
        """
        Remove a registry instance.

        Args:
            instance_id: Registry instance ID
        """
        if instance_id in self.active_registries:
            del self.active_registries[instance_id]
            logger.info(f"Removed registry: {instance_id}")

    # ===== Cross-Registry Operations =====

    def query_all(
        self,
        operation: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute an operation across all active registries.

        Args:
            operation: Method name to call on each registry
            **kwargs: Arguments to pass to the method

        Returns:
            Dict mapping instance_id to result
        """
        results = {}

        for instance_id, registry in self.active_registries.items():
            try:
                method = getattr(registry, operation)
                result = method(**kwargs)
                results[instance_id] = {
                    "status": "success",
                    "data": result
                }
            except Exception as e:
                logger.error(f"Operation {operation} failed for {instance_id}: {e}")
                results[instance_id] = {
                    "status": "error",
                    "error": str(e)
                }

        return results

    def find_schema_across_registries(
        self,
        subject: str
    ) -> Dict[str, Schema]:
        """
        Find a schema by subject across all registries.

        Args:
            subject: Subject name

        Returns:
            Dict mapping instance_id to Schema
        """
        results = {}

        for instance_id, registry in self.active_registries.items():
            try:
                schema = registry.get_latest_schema(subject)
                results[instance_id] = schema
            except Exception as e:
                logger.debug(f"Schema not found in {instance_id}: {e}")
                # Schema not found in this registry

        return results

    def compare_compatibility_modes(self) -> Dict[str, Dict[str, Any]]:
        """
        Get compatibility modes from all registries for comparison.

        Returns:
            Dict mapping instance_id to compatibility info
        """
        results = {}

        for instance_id, registry in self.active_registries.items():
            try:
                global_mode = registry.get_compatibility_mode()
                subject_modes = registry.get_all_compatibility_modes()

                results[instance_id] = {
                    "global": global_mode.value,
                    "subjects": {
                        k: v.value for k, v in subject_modes.items()
                    }
                }
            except Exception as e:
                logger.error(f"Failed to get compatibility for {instance_id}: {e}")
                results[instance_id] = {
                    "error": str(e)
                }

        return results

    def health_check_all(self) -> Dict[str, HealthStatus]:
        """
        Check health of all registries.

        Returns:
            Dict mapping instance_id to HealthStatus
        """
        results = {}

        for instance_id, registry in self.active_registries.items():
            try:
                health = registry.health_check()
                results[instance_id] = health
            except Exception as e:
                logger.error(f"Health check failed for {instance_id}: {e}")
                results[instance_id] = HealthStatus(
                    healthy=False,
                    status_code=0,
                    message=f"Health check exception: {str(e)}",
                    response_time_ms=0,
                    metadata={"error": str(e)}
                )

        return results

    # ===== Bulk Operations =====

    def bulk_check_compatibility(
        self,
        registry_ids: List[str],
        target_mode: CompatibilityMode,
        subject_filter: Optional[str] = None
    ) -> BulkCheckResult:
        """
        Check compatibility for multiple subjects across registries.

        Args:
            registry_ids: List of registry instance IDs
            target_mode: Target compatibility mode to check for
            subject_filter: Optional subject prefix filter

        Returns:
            BulkCheckResult with aggregated results
        """
        import time as time_module

        start_time = time_module.time()

        all_results = []
        compatible_count = 0
        incompatible_count = 0
        error_count = 0
        total_checked = 0

        for registry_id in registry_ids:
            registry = self.active_registries.get(registry_id)
            if not registry:
                logger.warning(f"Registry {registry_id} not found")
                continue

            try:
                # List subjects
                subjects = registry.list_subjects(prefix=subject_filter)

                # Check each subject in parallel
                futures = {}
                for subject in subjects:
                    future = self.executor.submit(
                        self._check_single_subject,
                        registry,
                        subject,
                        target_mode
                    )
                    futures[future] = (registry_id, subject)

                # Collect results
                for future in as_completed(futures):
                    registry_id, subject = futures[future]
                    total_checked += 1

                    try:
                        result = future.result()

                        result_dict = {
                            "registry_id": registry_id,
                            "subject": subject,
                            "is_compatible": result.is_compatible,
                            "messages": result.messages,
                            "errors": result.errors
                        }

                        all_results.append(result_dict)

                        if result.is_compatible:
                            compatible_count += 1
                        else:
                            incompatible_count += 1

                    except Exception as e:
                        logger.error(f"Check failed for {subject} in {registry_id}: {e}")
                        error_count += 1
                        all_results.append({
                            "registry_id": registry_id,
                            "subject": subject,
                            "is_compatible": False,
                            "messages": [],
                            "errors": [str(e)]
                        })

            except Exception as e:
                logger.error(f"Failed to check registry {registry_id}: {e}")
                error_count += 1

        duration = time_module.time() - start_time

        return BulkCheckResult(
            total_checked=total_checked,
            compatible=compatible_count,
            incompatible=incompatible_count,
            errors=error_count,
            duration_seconds=duration,
            results=all_results
        )

    def bulk_set_compatibility(
        self,
        registry_ids: List[str],
        mode: CompatibilityMode,
        subject_filter: Optional[str] = None
    ) -> Dict[str, Dict[str, str]]:
        """
        Set compatibility mode for multiple subjects across registries.

        Args:
            registry_ids: List of registry instance IDs
            mode: Compatibility mode to set
            subject_filter: Optional subject prefix filter

        Returns:
            Dict mapping registry_id to dict of subject: status
        """
        results = {}

        for registry_id in registry_ids:
            registry = self.active_registries.get(registry_id)
            if not registry:
                logger.warning(f"Registry {registry_id} not found")
                continue

            registry_results = {}

            try:
                if subject_filter:
                    # Set for filtered subjects
                    subjects = registry.list_subjects(prefix=subject_filter)

                    for subject in subjects:
                        try:
                            success = registry.set_compatibility_mode(mode, subject)
                            registry_results[subject] = "success" if success else "failed"
                        except Exception as e:
                            logger.error(f"Failed to set mode for {subject}: {e}")
                            registry_results[subject] = f"error: {str(e)}"
                else:
                    # Set global
                    try:
                        success = registry.set_compatibility_mode(mode)
                        registry_results["global"] = "success" if success else "failed"
                    except Exception as e:
                        registry_results["global"] = f"error: {str(e)}"

                results[registry_id] = registry_results

            except Exception as e:
                logger.error(f"Failed to process registry {registry_id}: {e}")
                results[registry_id] = {"error": str(e)}

        return results

    # ===== Helper Methods =====

    def _check_single_subject(
        self,
        registry: ISchemaRegistry,
        subject: str,
        target_mode: CompatibilityMode
    ) -> CompatibilityResult:
        """
        Check compatibility for a single subject.

        This checks if the subject's schemas are compatible with the target mode.

        Args:
            registry: Registry instance
            subject: Subject name
            target_mode: Target compatibility mode

        Returns:
            CompatibilityResult
        """
        try:
            # Get all versions
            versions = registry.list_versions(subject)

            if len(versions) < 2:
                # Only one version - always compatible
                return CompatibilityResult(
                    is_compatible=True,
                    messages=["Single version - no compatibility check needed"],
                    compatibility_level=target_mode,
                    errors=[]
                )

            # Get latest version
            latest = registry.get_schema_by_subject_version(subject, versions[-1])

            # Check compatibility with all previous versions
            all_compatible = True
            messages = []

            for version in versions[:-1]:
                try:
                    result = registry.check_compatibility(
                        subject=subject,
                        schema_content=latest.schema_content,
                        schema_format=latest.schema_format,
                        version=version
                    )

                    if not result.is_compatible:
                        all_compatible = False
                        messages.extend(result.messages)

                except Exception as e:
                    all_compatible = False
                    messages.append(f"Check failed for version {version}: {str(e)}")

            return CompatibilityResult(
                is_compatible=all_compatible,
                messages=messages if messages else ["All versions compatible"],
                compatibility_level=target_mode,
                errors=[]
            )

        except Exception as e:
            return CompatibilityResult(
                is_compatible=False,
                messages=[],
                compatibility_level=target_mode,
                errors=[str(e)]
            )

    def shutdown(self):
        """Shutdown the orchestrator and cleanup resources."""
        self.executor.shutdown(wait=True)
        logger.info("Orchestrator shutdown complete")
