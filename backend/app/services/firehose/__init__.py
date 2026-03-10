"""DEPRECATED: Use app.services.channels instead. This package will be removed."""
import warnings

warnings.warn(
    "firehose package is deprecated, use channels",
    DeprecationWarning,
    stacklevel=2,
)

from app.services.firehose.schemas import SensoryEvent

__all__ = ["SensoryEvent"]
