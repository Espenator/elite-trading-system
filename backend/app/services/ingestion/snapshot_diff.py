"""snapshot_diff — compare two snapshot dicts, emit only changed fields.

Polling adapters (Finviz, FRED, etc.) call ``compute_snapshot_diff`` to
detect which fields changed since the last fetch.  Only changed records
are emitted as new ``SourceEvent`` objects, avoiding redundant ingestion.

``snapshot_hash`` provides a fast equality check (no diff allocation) when
only a "changed / not changed" answer is needed.

Usage::

    from app.services.ingestion.snapshot_diff import compute_snapshot_diff, snapshot_hash

    old_snapshot = {"AAPL": {"price": 182.5, "volume": 1_200_000}}
    new_snapshot = {"AAPL": {"price": 183.0, "volume": 1_350_000}}

    diff = compute_snapshot_diff(old_snapshot["AAPL"], new_snapshot["AAPL"])
    if diff.has_changes:
        for change in diff.changed_fields:
            print(change.key, change.old, "→", change.new)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class FieldChange:
    """A single field that changed between two snapshots."""

    key: str
    old: Any
    new: Any

    def to_dict(self) -> Dict[str, Any]:
        return {"key": self.key, "old": self.old, "new": self.new}


@dataclass
class SnapshotDiff:
    """Structured comparison result between two snapshot dicts.

    Attributes:
        added_keys:      Keys present in *new* but not in *old*.
        removed_keys:    Keys present in *old* but not in *new*.
        changed_fields:  Keys present in both snapshots whose values differ.
    """

    added_keys: List[str] = field(default_factory=list)
    removed_keys: List[str] = field(default_factory=list)
    changed_fields: List[FieldChange] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        """True iff any key was added, removed, or changed."""
        return bool(self.added_keys or self.removed_keys or self.changed_fields)

    def to_dict(self) -> Dict[str, Any]:
        """Serializable representation for logging / SourceEvent payloads."""
        return {
            "has_changes": self.has_changes,
            "added_keys": self.added_keys,
            "removed_keys": self.removed_keys,
            "changed_fields": [c.to_dict() for c in self.changed_fields],
        }


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------

def compute_snapshot_diff(
    old: Optional[Dict[str, Any]],
    new: Dict[str, Any],
) -> SnapshotDiff:
    """Compare two flat snapshot dicts and return a :class:`SnapshotDiff`.

    Args:
        old: Previous snapshot dict, or ``None`` (treated as empty — every key
             in *new* is considered "added").
        new: Current snapshot dict.

    Returns:
        A :class:`SnapshotDiff` describing which keys were added, removed, or
        changed.  Values are compared with ``==``; no deep comparison is
        performed on nested structures (use a flat snapshot for reliable diffs).
    """
    if old is None:
        return SnapshotDiff(added_keys=sorted(new.keys()))

    old_keys: Set[str] = set(old.keys())
    new_keys: Set[str] = set(new.keys())

    added = sorted(new_keys - old_keys)
    removed = sorted(old_keys - new_keys)
    changed = [
        FieldChange(key=k, old=old[k], new=new[k])
        for k in sorted(old_keys & new_keys)
        if old[k] != new[k]
    ]

    return SnapshotDiff(added_keys=added, removed_keys=removed, changed_fields=changed)


def snapshot_hash(snapshot: Dict[str, Any]) -> str:
    """Return a stable SHA-256 hex digest of *snapshot* for quick equality checks.

    Serializes with ``sort_keys=True`` so key order doesn't affect the hash.
    Nested objects are serialized via ``default=str`` to avoid ``TypeError``
    on non-JSON-native types (e.g. ``datetime``).
    """
    serialized = json.dumps(snapshot, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()
