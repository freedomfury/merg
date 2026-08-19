class DeepMergeError(Exception):
    """Base exception for merg library."""

class InvalidTypeError(DeepMergeError):
    """Raised when an object type is not a valid JSON/YAML type."""
