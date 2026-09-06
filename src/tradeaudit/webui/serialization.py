"""JSON-safe serialization for domain dataclasses (datetimes, enums, nested dataclasses/dicts)."""
import dataclasses
from datetime import datetime
from enum import Enum


def to_jsonable(obj):
    """Recursively convert dataclasses/datetimes/enums/dicts/lists into plain JSON-safe values."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, datetime):
        return obj.isoformat()
    if dataclasses.is_dataclass(obj):
        return {f.name: to_jsonable(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, dict):
        return {str(to_jsonable(k)): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_jsonable(v) for v in obj]
    return obj
