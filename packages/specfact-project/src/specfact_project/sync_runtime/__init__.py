"""
Sync operations for SpecFact CLI.

This module provides bidirectional synchronization between Spec-Kit artifacts,
repository changes, and SpecFact plans.
"""

from specfact_cli.models.capabilities import ToolCapabilities

from specfact_project.sync_runtime.bridge_probe import BridgeProbe
from specfact_project.sync_runtime.bridge_sync import BridgeSync, SyncOperation, SyncResult
from specfact_project.sync_runtime.bridge_watch import BridgeWatch, BridgeWatchEventHandler
from specfact_project.sync_runtime.repository_sync import RepositorySync, RepositorySyncResult
from specfact_project.sync_runtime.watcher import FileChange, SyncEventHandler, SyncWatcher


__all__ = [
    "BridgeProbe",
    "BridgeSync",
    "BridgeWatch",
    "BridgeWatchEventHandler",
    "FileChange",
    "RepositorySync",
    "RepositorySyncResult",
    "SyncEventHandler",
    "SyncOperation",
    "SyncResult",
    "SyncWatcher",
    "ToolCapabilities",
]
